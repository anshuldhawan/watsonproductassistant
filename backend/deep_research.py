import asyncio
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .gemini_agents import extract_json_payload, normalize_insights
from .research_playbooks import ResearchPlaybook


RESEARCH_INSIGHT_CONTRACT = """
Return only valid JSON with an "insights" array. Each research insight must include:
title, summary, group, skill, metric, direction, confidence, segment,
recommended_actions, evidence_strength, citations, source, playbook_id,
research_job, and report_id. Use source="research".
""".strip()


@dataclass
class ResearchInteractionRecord:
    interaction_id: Optional[str]
    output_text: str
    status: str = "completed"
    citations: List[Dict[str, Any]] = field(default_factory=list)
    raw: Optional[Dict[str, Any]] = None


class DeepResearchClient:
    """
    Small adapter around Gemini Deep Research.

    The live API is intentionally isolated here because Deep Research is a
    preview surface. When credentials are absent, the adapter returns deterministic
    local records so the rest of the product and tests can exercise the job flow.
    """

    def __init__(self, api_key: Optional[str] = None, force_local: bool = False):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.force_local = force_local or not self.api_key
        self._client = None
        if not self.force_local:
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                self.force_local = True

    async def create_plan(
        self,
        playbook: ResearchPlaybook,
        focus: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ResearchInteractionRecord:
        prompt = playbook.render_prompt(focus, context)
        if self.force_local:
            return self._local_plan(playbook, focus, prompt)
        return await self._create_interaction(
            agent=playbook.model,
            input=prompt,
            agent_config=self._agent_config(collaborative_planning=True),
            tools=self._tools(playbook),
            background=True,
            store=True,
        )

    async def refine_plan(
        self,
        playbook: ResearchPlaybook,
        previous_interaction_id: str,
        refinement: str,
    ) -> ResearchInteractionRecord:
        if self.force_local:
            return ResearchInteractionRecord(
                interaction_id=f"local-plan-{uuid.uuid4()}",
                output_text=f"Refined plan for {playbook.name}:\n\n{refinement.strip()}",
            )
        return await self._create_interaction(
            agent=playbook.model,
            input=refinement,
            agent_config=self._agent_config(collaborative_planning=True),
            previous_interaction_id=previous_interaction_id,
            background=True,
            store=True,
        )

    async def approve_and_run(
        self,
        playbook: ResearchPlaybook,
        previous_interaction_id: str,
    ) -> ResearchInteractionRecord:
        if self.force_local:
            return self._local_report(playbook, previous_interaction_id)
        return await self._create_interaction(
            agent=playbook.model,
            input="Plan approved. Execute the research and produce the cited report.",
            agent_config=self._agent_config(collaborative_planning=False),
            previous_interaction_id=previous_interaction_id,
            background=True,
            store=True,
        )

    async def poll_until_complete(
        self,
        interaction_id: Optional[str],
        *,
        max_attempts: int = 120,
        delay_seconds: float = 2.0,
    ) -> ResearchInteractionRecord:
        if self.force_local or not interaction_id:
            return ResearchInteractionRecord(interaction_id=interaction_id, output_text="", status="completed")

        for _ in range(max_attempts):
            record = await self._get_interaction(interaction_id)
            if record.status in {"completed", "failed", "cancelled"}:
                return record
            await asyncio.sleep(delay_seconds)
        return ResearchInteractionRecord(interaction_id=interaction_id, output_text="", status="in_progress")

    async def extract_insights(
        self,
        playbook: ResearchPlaybook,
        report_interaction_id: Optional[str],
        report_text: str,
        report_id: str,
    ) -> List[Dict[str, Any]]:
        if self.force_local:
            payload = self._local_extraction(playbook, report_id)
        else:
            interaction = await self._create_interaction(
                model=os.getenv("GEMINI_RESEARCH_EXTRACTION_MODEL", "gemini-3.1-pro-preview"),
                input=(
                    "Extract each distinct finding from the completed research report as "
                    f"structured JSON.\n\n{RESEARCH_INSIGHT_CONTRACT}"
                ),
                previous_interaction_id=report_interaction_id,
            )
            payload = extract_json_payload(interaction.output_text)

        insights = normalize_insights(
            payload,
            default_group="product-user-research",
            default_skill=playbook.playbook_id,
        )
        for insight in insights:
            insight["source"] = "research"
            insight["playbook_id"] = playbook.playbook_id
            insight["research_job"] = playbook.research_job
            insight["report_id"] = report_id
            insight["evidence_strength"] = _coerce_float(insight.get("evidence_strength"), 0.75)
            insight["citations"] = _coerce_citations(insight.get("citations"))
            insight.setdefault("metric", "evidence_strength")
            insight.setdefault("stat_test", "qualitative evidence scoring")
            insight.setdefault("magnitude", {"value": insight["evidence_strength"], "unit": "evidence", "relative": 0.0})
            insight.setdefault("business_impact", {"metric": "research_priority", "estimate_usd": 0.0, "horizon": "unknown"})
        return insights

    async def follow_up(
        self,
        previous_interaction_id: Optional[str],
        question: str,
    ) -> ResearchInteractionRecord:
        if self.force_local:
            return ResearchInteractionRecord(
                interaction_id=f"local-followup-{uuid.uuid4()}",
                output_text=f"Follow-up response based on the report: {question.strip()}",
            )
        return await self._create_interaction(
            input=question,
            previous_interaction_id=previous_interaction_id,
        )

    async def _create_interaction(self, **kwargs: Any) -> ResearchInteractionRecord:
        return await asyncio.to_thread(self._create_interaction_sync, **kwargs)

    def _create_interaction_sync(self, **kwargs: Any) -> ResearchInteractionRecord:
        response = self._client.interactions.create(**kwargs)
        return _record_from_response(response)

    async def _get_interaction(self, interaction_id: str) -> ResearchInteractionRecord:
        return await asyncio.to_thread(self._get_interaction_sync, interaction_id)

    def _get_interaction_sync(self, interaction_id: str) -> ResearchInteractionRecord:
        response = self._client.interactions.get(interaction_id)
        return _record_from_response(response)

    def _agent_config(self, collaborative_planning: bool) -> Dict[str, Any]:
        return {
            "type": "deep-research",
            "thinking_summaries": "auto",
            "visualization": "auto",
            "collaborative_planning": collaborative_planning,
        }

    def _tools(self, playbook: ResearchPlaybook) -> List[Dict[str, Any]]:
        tools = []
        if "google_search" in playbook.tools:
            tools.append({"type": "google_search"})
        if "url_context" in playbook.tools:
            tools.append({"type": "url_context"})
        if "file_search" in playbook.tools and playbook.file_search_stores:
            tools.append(
                {
                    "type": "file_search",
                    "file_search_store_names": playbook.file_search_stores,
                }
            )
        return tools

    def _local_plan(self, playbook: ResearchPlaybook, focus: str, prompt: str) -> ResearchInteractionRecord:
        return ResearchInteractionRecord(
            interaction_id=f"local-plan-{uuid.uuid4()}",
            output_text=(
                f"Research plan for {playbook.name}\n\n"
                f"Focus: {focus or 'current product priorities'}\n\n"
                "1. Search public sources for recent user language and competitor mentions.\n"
                "2. Cluster findings into themes, segments, and decision drivers.\n"
                "3. Validate material claims against multiple independent sources.\n"
                "4. Produce a cited report with priority recommendations.\n\n"
                "Approve this plan to run the research."
            ),
            raw={"prompt": prompt},
        )

    def _local_report(self, playbook: ResearchPlaybook, previous_interaction_id: str) -> ResearchInteractionRecord:
        citations = [
            {
                "title": "Local research stub",
                "url": "https://example.com/research-placeholder",
                "source_type": "web",
            }
        ]
        return ResearchInteractionRecord(
            interaction_id=f"local-report-{uuid.uuid4()}",
            output_text=(
                f"# {playbook.name} Report\n\n"
                "This local report stands in for a Gemini Deep Research result when credentials "
                "or the preview API are unavailable.\n\n"
                "## Key Finding\n"
                "Users show a recurring need for clearer product value, faster issue resolution, "
                "and transparent comparisons against alternatives.\n\n"
                "## Citations\n"
                "- Local research stub: https://example.com/research-placeholder\n"
            ),
            citations=citations,
            raw={"previous_interaction_id": previous_interaction_id},
        )

    def _local_extraction(self, playbook: ResearchPlaybook, report_id: str) -> Dict[str, Any]:
        return {
            "insights": [
                {
                    "title": f"{playbook.name} theme needs PM review",
                    "summary": "Research found a recurring, cited theme that should be reviewed before roadmap prioritization.",
                    "group": "product-user-research",
                    "skill": playbook.playbook_id,
                    "metric": "evidence_strength",
                    "direction": "neutral",
                    "confidence": 0.8,
                    "stat_test": "qualitative evidence scoring",
                    "segment": "all users",
                    "recommended_actions": [
                        "Review the cited report and validate the theme against internal product priorities.",
                        "Assign an owner to decide whether the theme warrants discovery or delivery work.",
                    ],
                    "evidence_strength": 0.8,
                    "citations": [
                        {
                            "title": "Local research stub",
                            "url": "https://example.com/research-placeholder",
                            "source_type": "web",
                        }
                    ],
                    "source": "research",
                    "playbook_id": playbook.playbook_id,
                    "research_job": playbook.research_job,
                    "report_id": report_id,
                }
            ]
        }


def _record_from_response(response: Any) -> ResearchInteractionRecord:
    return ResearchInteractionRecord(
        interaction_id=_read_attr(response, "id", "name"),
        output_text=_read_output_text(response),
        status=_read_status(response),
        citations=_read_citations(response),
        raw=None,
    )


def _read_attr(obj: Any, *names: str) -> Optional[str]:
    for name in names:
        value = getattr(obj, name, None)
        if value:
            return str(value)
    return None


def _read_status(response: Any) -> str:
    status = getattr(response, "status", None) or getattr(response, "state", None)
    if not status:
        return "completed"
    return str(status).lower()


def _read_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    parts: List[str] = []
    for step in getattr(response, "steps", []) or []:
        for name in ("text", "output_text"):
            value = getattr(step, name, None)
            if value:
                parts.append(str(value))
    return "\n".join(parts)


def _read_citations(response: Any) -> List[Dict[str, Any]]:
    raw = getattr(response, "citations", None) or []
    citations = []
    for item in raw:
        if isinstance(item, dict):
            citations.append(item)
        else:
            citations.append(
                {
                    "title": _read_attr(item, "title") or _read_attr(item, "name") or "Source",
                    "url": _read_attr(item, "url", "uri") or "",
                    "source_type": _read_attr(item, "source_type") or "web",
                }
            )
    return citations


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_citations(value: Any) -> List[Dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, str):
        urls = re.findall(r"https?://\S+", value)
        return [{"title": url, "url": url, "source_type": "web"} for url in urls]
    if isinstance(value, list):
        citations = []
        for item in value:
            if isinstance(item, dict):
                citations.append(item)
            elif item:
                citations.append({"title": str(item), "url": str(item), "source_type": "web"})
        return citations
    return []
