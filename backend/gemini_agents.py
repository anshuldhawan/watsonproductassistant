import asyncio
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .dataset_environment import resolve_analysis_environment
from .models import AnalysisDefinition, KPIDefinition


SKILLS_ROOT = Path(__file__).resolve().parent.parent / "skills"

INSIGHT_OUTPUT_CONTRACT = """
Return only valid JSON. The top-level value must be either an array of Insight
objects or an object with an "insights" array. Each Insight object must include:
title, summary, group, skill, metric, direction, magnitude {value, unit,
relative}, confidence, stat_test, segment, business_impact {metric,
estimate_usd, horizon}, recommended_actions, artifacts, and data_window {start,
end}. Return [] when there is no noteworthy finding.
""".strip()


@dataclass
class GeminiInteractionRecord:
    interaction_id: Optional[str]
    environment_id: Optional[str]
    output_text: str


@dataclass
class GeminiAgentResult:
    insights: List[Dict[str, Any]]
    interaction_ids: List[str] = field(default_factory=list)
    environment_id: Optional[str] = None


def resolve_gemini_mode(config: Optional[Dict[str, Any]] = None) -> str:
    """
    Resolve the execution mode without forcing credentials in local development.
    Explicit config wins, then env, then Gemini only when a key is present.
    """
    config = config or {}
    configured = config.get("execution_mode") or config.get("agent_mode") or os.getenv("GEMINI_AGENT_MODE")
    if configured:
        mode = str(configured).strip().lower()
    else:
        mode = "gemini" if os.getenv("GEMINI_API_KEY") else "local"

    if mode not in {"gemini", "local"}:
        raise ValueError("GEMINI_AGENT_MODE must be either 'gemini' or 'local'.")
    return mode


def extract_json_payload(text: str) -> Any:
    """
    Parse JSON from Gemini output. Managed agents should emit raw JSON, but this
    accepts fenced code blocks and surrounding explanatory text for resilience.
    """
    if not text or not text.strip():
        return []

    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        stripped = fenced.group(1).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    candidates = []
    for start_char, end_char in (("[", "]"), ("{", "}")):
        start = stripped.find(start_char)
        end = stripped.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            candidates.append(stripped[start : end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError("Gemini response did not contain parseable JSON insight output.")


def normalize_insights(
    payload: Any,
    *,
    default_group: str,
    default_skill: str,
) -> List[Dict[str, Any]]:
    if payload is None:
        return []

    if isinstance(payload, dict):
        raw_items = payload.get("insights", [])
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
    elif isinstance(payload, list):
        raw_items = payload
    else:
        raise ValueError("Gemini insight output must be a JSON array or an object with an insights array.")

    normalized = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue

        title = str(raw.get("title") or "").strip()
        summary = str(raw.get("summary") or "").strip()
        if not title or not summary:
            continue

        insight = dict(raw)
        insight["insight_id"] = str(insight.get("insight_id") or uuid.uuid4())
        insight["group"] = str(insight.get("group") or insight.get("group_key") or default_group)
        insight["skill"] = str(insight.get("skill") or insight.get("skill_key") or default_skill)
        insight["title"] = title
        insight["summary"] = summary
        insight["direction"] = str(insight.get("direction") or "neutral")
        insight["confidence"] = _coerce_float(insight.get("confidence"), default=0.8)
        insight["recommended_actions"] = _coerce_str_list(insight.get("recommended_actions"))
        insight["artifacts"] = _coerce_str_list(insight.get("artifacts"))
        insight["magnitude"] = _normalize_magnitude(insight)
        insight["business_impact"] = _normalize_business_impact(insight)
        insight["data_window"] = _normalize_data_window(insight)
        normalized.append(insight)

    return normalized


def _coerce_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _normalize_magnitude(raw: Dict[str, Any]) -> Dict[str, Any]:
    magnitude = raw.get("magnitude") if isinstance(raw.get("magnitude"), dict) else {}
    return {
        "value": _coerce_float(magnitude.get("value", raw.get("magnitude_value")), default=0.0),
        "unit": str(magnitude.get("unit", raw.get("magnitude_unit") or "index")),
        "relative": _coerce_float(magnitude.get("relative", raw.get("magnitude_relative")), default=0.0),
    }


def _normalize_business_impact(raw: Dict[str, Any]) -> Dict[str, Any]:
    impact = raw.get("business_impact") if isinstance(raw.get("business_impact"), dict) else {}
    return {
        "metric": str(impact.get("metric", raw.get("business_impact_metric") or "unknown")),
        "estimate_usd": _coerce_float(
            impact.get("estimate_usd", raw.get("business_impact_value")),
            default=0.0,
        ),
        "horizon": str(impact.get("horizon", raw.get("business_impact_horizon") or "unknown")),
    }


def _normalize_data_window(raw: Dict[str, Any]) -> Dict[str, Any]:
    window = raw.get("data_window") if isinstance(raw.get("data_window"), dict) else {}
    return {
        "start": str(window.get("start", raw.get("data_window_start") or "")),
        "end": str(window.get("end", raw.get("data_window_end") or "")),
    }


class GeminiAgentClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required when Gemini execution mode is enabled.")

        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("Install google-genai>=1.55.0 to use Gemini Managed Agents.") from exc

        self._client = genai.Client(api_key=self.api_key)

    async def run_single_analysis(
        self,
        definition: AnalysisDefinition,
        config: Optional[Dict[str, Any]] = None,
    ) -> GeminiAgentResult:
        config = config or {}
        environment = resolve_analysis_environment(config)
        prompt = _single_analysis_prompt(definition, config)
        interaction = await self._create_interaction(
            agent=definition.agent_id,
            input=prompt,
            environment=environment,
        )
        insights = normalize_insights(
            extract_json_payload(interaction.output_text),
            default_group=definition.group_key,
            default_skill=definition.key,
        )
        return GeminiAgentResult(
            insights=insights,
            interaction_ids=_compact_ids([interaction.interaction_id]),
            environment_id=interaction.environment_id,
        )

    async def run_group_analysis(
        self,
        group_key: str,
        group_name: str,
        agent_id: str,
        definitions: Sequence[AnalysisDefinition],
        config: Optional[Dict[str, Any]] = None,
    ) -> GeminiAgentResult:
        config = config or {}
        base_environment = resolve_analysis_environment(config)
        loader = await self._create_interaction(
            agent=agent_id,
            input=_group_loader_prompt(group_name, definitions, config),
            environment=base_environment,
        )

        environment = loader.environment_id or base_environment
        all_insights: List[Dict[str, Any]] = []
        interaction_ids = _compact_ids([loader.interaction_id])

        for definition in definitions:
            interaction = await self._create_interaction(
                agent=agent_id,
                input=_group_skill_prompt(definition, config),
                environment=environment,
            )
            interaction_ids.extend(_compact_ids([interaction.interaction_id]))
            payload = extract_json_payload(interaction.output_text)
            all_insights.extend(
                normalize_insights(
                    payload,
                    default_group=group_key,
                    default_skill=definition.key,
                )
            )

        return GeminiAgentResult(
            insights=all_insights,
            interaction_ids=interaction_ids,
            environment_id=loader.environment_id,
        )

    async def run_kpi_monitoring(
        self,
        kpis: Iterable[KPIDefinition],
        config: Optional[Dict[str, Any]] = None,
    ) -> GeminiAgentResult:
        config = config or {}
        environment = resolve_analysis_environment(config)
        interaction = await self._create_interaction(
            agent=config.get("agent_id") or os.getenv("GEMINI_KPI_AGENT_ID", "kpi-monitor"),
            input=_kpi_monitor_prompt(kpis, config),
            environment=environment,
        )
        insights = normalize_insights(
            extract_json_payload(interaction.output_text),
            default_group="predictive-modelling",
            default_skill="anomaly-detection-kpi",
        )
        return GeminiAgentResult(
            insights=insights,
            interaction_ids=_compact_ids([interaction.interaction_id]),
            environment_id=interaction.environment_id,
        )

    async def _create_interaction(self, **kwargs: Any) -> GeminiInteractionRecord:
        return await asyncio.to_thread(self._create_interaction_sync, **kwargs)

    def _create_interaction_sync(self, **kwargs: Any) -> GeminiInteractionRecord:
        response = self._client.interactions.create(**kwargs)
        return GeminiInteractionRecord(
            interaction_id=_read_attr(response, "id", "name"),
            environment_id=_read_environment_id(response),
            output_text=_read_output_text(response),
        )


def _read_skill_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def _skill_instructions(definition: AnalysisDefinition) -> str:
    shared = _read_skill_file(SKILLS_ROOT / "AGENTS.md")
    skill = _read_skill_file(SKILLS_ROOT / definition.group_key / definition.key / "SKILL.md")

    sections = []
    if shared:
        sections.append(f"Shared analyst instructions:\n{shared}")
    if skill:
        sections.append(f"Skill-specific instructions:\n{skill}")
    if not sections:
        sections.append("Skill instruction file not found; use the catalog description and output contract.")
    return "\n\n".join(sections)


def _group_skill_summary(definitions: Sequence[AnalysisDefinition]) -> str:
    rows = [
        {
            "key": definition.key,
            "name": definition.name,
            "description": definition.description,
            "instructions_path": f"skills/{definition.group_key}/{definition.key}/SKILL.md",
        }
        for definition in definitions
    ]
    return json.dumps(rows, sort_keys=True, default=str)


def _single_analysis_prompt(definition: AnalysisDefinition, config: Dict[str, Any]) -> str:
    return f"""
Run Lighthouse skill `{definition.key}` ({definition.name}) for group `{definition.group_key}`.

Skill description: {definition.description or "No description provided."}
Run configuration: {json.dumps(config, sort_keys=True, default=str)}

{_skill_instructions(definition)}

Use the available product analytics data environment. Compute the methodology,
save any artifacts inside the agent environment, and emit only noteworthy
findings.

{INSIGHT_OUTPUT_CONTRACT}
""".strip()


def _group_loader_prompt(
    group_name: str,
    definitions: Sequence[AnalysisDefinition],
    config: Dict[str, Any],
) -> str:
    skills = ", ".join(definition.key for definition in definitions)
    return f"""
Prepare a shared Lighthouse data snapshot for the `{group_name}` group run.
The skills in scope are: {skills}.
Skill catalog metadata: {_group_skill_summary(definitions)}
Run configuration: {json.dumps(config, sort_keys=True, default=str)}

Inspect and cache the datasets required by these skills for reuse by follow-up
skill interactions. Do not emit insights in this loader step. Return [].
""".strip()


def _group_skill_prompt(definition: AnalysisDefinition, config: Dict[str, Any]) -> str:
    return f"""
Using the shared data snapshot in this environment, run Lighthouse skill
`{definition.key}` ({definition.name}).

Skill description: {definition.description or "No description provided."}
Run configuration: {json.dumps(config, sort_keys=True, default=str)}

{_skill_instructions(definition)}

{INSIGHT_OUTPUT_CONTRACT}
""".strip()


def _kpi_monitor_prompt(kpis: Iterable[KPIDefinition], config: Dict[str, Any]) -> str:
    kpi_rows = [
        {
            "metric": kpi.metric,
            "name": kpi.name,
            "baseline_window": kpi.baseline_window,
            "threshold_warning": kpi.threshold_warning,
            "threshold_critical": kpi.threshold_critical,
            "schedule": kpi.schedule,
        }
        for kpi in kpis
    ]
    return f"""
Run the Lighthouse KPI Monitor agent against these monitored KPIs:
{json.dumps(kpi_rows, sort_keys=True, default=str)}

Run configuration: {json.dumps(config, sort_keys=True, default=str)}

Compare current values against baselines, forecast bands, and configured
thresholds. Emit Insight objects only for real breaches. If all KPIs are green,
return [].

{INSIGHT_OUTPUT_CONTRACT}
""".strip()


def _read_attr(obj: Any, *names: str) -> Optional[str]:
    for name in names:
        value = getattr(obj, name, None)
        if value:
            return str(value)
    return None


def _read_environment_id(response: Any) -> Optional[str]:
    environment_id = _read_attr(response, "environment_id")
    if environment_id:
        return environment_id
    environment = getattr(response, "environment", None)
    if environment is None:
        return None
    return _read_attr(environment, "id", "name")


def _read_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    text_parts: List[str] = []
    for step in getattr(response, "steps", []) or []:
        for name in ("text", "output_text"):
            value = getattr(step, name, None)
            if value:
                text_parts.append(str(value))
    return "\n".join(text_parts)


def _compact_ids(values: Iterable[Optional[str]]) -> List[str]:
    return [value for value in values if value]
