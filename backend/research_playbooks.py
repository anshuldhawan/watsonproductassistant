from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ResearchPlaybook:
    playbook_id: str
    name: str
    research_job: str
    description: str
    model: str
    tools: List[str]
    prompt_template: str
    default_cadence: Optional[str] = None
    cost_ceiling_usd: float = 3.0
    collaborative_planning: bool = True
    file_search_stores: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def render_prompt(self, focus: str, context: Optional[Dict[str, Any]] = None) -> str:
        context = context or {}
        context_lines = []
        if context:
            context_lines.append("Additional context:")
            for key, value in sorted(context.items()):
                if value not in (None, "", [], {}):
                    context_lines.append(f"- {key}: {value}")

        return self.prompt_template.format(
            focus=focus.strip() or "the current product priorities",
            context="\n".join(context_lines),
        ).strip()


PLAYBOOKS: Dict[str, ResearchPlaybook] = {
    "user-wants": ResearchPlaybook(
        playbook_id="user-wants",
        name="User Wants / Unmet Needs",
        research_job="user_wants",
        description="Research unmet needs, feature demand, and competitor parity gaps.",
        model="deep-research-preview-04-2026",
        tools=["google_search", "url_context"],
        default_cadence=None,
        cost_ceiling_usd=3.0,
        prompt_template="""
Research what users want and which needs remain unmet, focused on: {focus}.

Use public sources such as feature-request boards, app-store reviews, forums,
social discussions, competitor release notes, and product communities. Identify
ranked demand themes, user segments, demand intensity, whether competitors
already solve the need, and suggested priorities.

Paraphrase user feedback. Do not reproduce review text verbatim. Include
citations for every material claim and call out uncertainty explicitly.

Report sections:
1. Top demand themes
2. Demand by user segment
3. Competitive gap versus parity
4. Suggested priorities

{context}
""",
    ),
    "voice-of-customer": ResearchPlaybook(
        playbook_id="voice-of-customer",
        name="Voice of Customer",
        research_job="voice_of_customer",
        description="Research user sentiment, themes, emerging issues, and trend shifts.",
        model="deep-research-preview-04-2026",
        tools=["google_search", "url_context"],
        default_cadence="weekly",
        cost_ceiling_usd=3.0,
        prompt_template="""
Research what users are saying, focused on: {focus}.

Use public reviews, forums, social discussions, product communities, and support
knowledge sources when available. Extract themes, sentiment, severity, emerging
issues, and declining issues. Compare against any prior-run context supplied
below and emphasize what changed.

Paraphrase user feedback. Do not reproduce review text verbatim. Include
citations for every material claim and call out uncertainty explicitly.

Report sections:
1. Theme map
2. Sentiment by theme
3. Emerging issues
4. Trend versus prior run

{context}
""",
    ),
    "competitor-switching": ResearchPlaybook(
        playbook_id="competitor-switching",
        name="Competitor & Switching",
        research_job="competitor_switching",
        description="Research competitors users compare or switch to and why.",
        model="deep-research-max-preview-04-2026",
        tools=["google_search", "url_context"],
        default_cadence="monthly",
        cost_ceiling_usd=7.0,
        prompt_template="""
Research which competitors users compare against and switch to or from, focused
on: {focus}.

Use public sources such as comparison sites, reviews, forums, social discussion,
competitor sites, pricing pages, launch notes, and product communities. For each
competitor, explain why users switch to or from it across features, price, UX,
reliability, ecosystem, and trust.

If specific figures are unavailable, state so explicitly. Do not estimate.
Paraphrase user feedback. Do not reproduce review text verbatim. Include
citations for every material claim and call out uncertainty explicitly.

Report sections:
1. Competitor map
2. Switching drivers to and from each competitor
3. Feature and pricing comparison
4. Recent competitor moves
5. Watch-list

{context}
""",
    ),
}


def list_playbooks() -> List[Dict[str, Any]]:
    return [playbook.to_dict() for playbook in PLAYBOOKS.values()]


def get_playbook(playbook_id: str) -> ResearchPlaybook:
    try:
        return PLAYBOOKS[playbook_id]
    except KeyError as exc:
        raise ValueError(f"Unknown research playbook: {playbook_id}") from exc
