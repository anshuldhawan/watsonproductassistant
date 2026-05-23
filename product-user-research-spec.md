# Spec — Product & User Research

> **Status:** Draft v0.1 — for review
> **Scope:** A feature that researches the world outside the product data — what users
> want, what users are saying, and which competitors users choose and why — built on the
> **Gemini Deep Research Agent**.
> **Companion docs:** product vision (`automated-product-analyst-spec.md`), build spec
> (`spotify-analyst-build-spec-v0.2.md`), reinforcement loop (`insight-reinforcement-spec.md`).
> **Last updated:** 2026-05-23

---

## 1. Summary

The Automated Product Analyst, so far, answers **"what happened in our data"** — it runs
quantitative analyses on the internal product dataset. It cannot answer **"why,"** and it
is blind to anything outside the warehouse: reviews, forums, competitor moves, market
shifts, unmet demand.

**Product & User Research** is the qualitative, outward-facing half of the analyst. It
answers three questions:

1. **What do users want** — unmet needs and feature demand.
2. **What are users saying** — voice of customer: themes, sentiment, emerging issues.
3. **Which competitors do users use, and why** — competitive landscape and switching
   drivers.

It is built on the **Gemini Deep Research Agent**, which plans → searches → reads →
iterates → synthesizes a cited report. Deep Research is the right primitive because this
work is open-ended web research, not computation over a fixed dataset — it is an
"analyst-in-a-box," asynchronous and multi-step by design.

The feature's outputs flow into the **same insight feed and reinforcement loop** as the
quantitative side, so a PM sees one prioritized stream of "what needs attention" drawn
from both internal data and the outside world.

---

## 2. Goals and non-goals

### Goals
- Let a PM commission rigorous, cited research on demand across the three questions above.
- Continuously monitor voice-of-customer and competitor activity, surfacing only what changed.
- Pair quantitative findings with qualitative explanation — when retention drops, research *why*.
- Ground research in the company's **own** qualitative data (tickets, reviews, surveys), not just the web.

### Non-goals
- Not a real-time chat tool — research tasks run for minutes, asynchronously.
- Not a replacement for direct user interviews; it synthesizes existing signal.
- Does not take action — it informs; humans decide.
- Not deterministic — see §13.

---

## 3. The three research jobs

| Job | Question | Primary sources |
|---|---|---|
| **A — User Wants** | What features and changes do users want; what needs are unmet? | Feature-request boards, app-store review asks, forums/social, internal feature-request corpus, competitor launches users praise. |
| **B — Voice of Customer** | What are users saying; what themes and sentiment; what's emerging? | App-store reviews, social, forums, plus internal NPS verbatims, survey open-ends, support tickets. |
| **C — Competitor & Switching** | Which competitors do users compare/switch to, and why? | Comparison/review sites, competitor sites, social, plus internal churn surveys, win/loss notes, sales-call notes. |

Each job is implemented as a **Research Playbook** (§6) — a reusable, configured Deep
Research task, analogous to the `SKILL.md` skills on the quantitative side.

---

## 4. Why the Deep Research Agent — capability mapping

| Deep Research capability | How this feature uses it |
|---|---|
| Plan → search → read → iterate → cited report | The core research loop for all three jobs. |
| `background=true` + polling / streaming | Every research task is async (minutes, up to 60). The feature is a job system (§9). |
| **Collaborative planning** | On-demand research returns a plan first; the PM reviews/refines/approves before the costly run executes (§8.1). Doubles as a cost gate. |
| **File Search** tool | Grounds research in the company's own qualitative corpora — tickets, reviews, surveys (§7). |
| `google_search` + `url_context` | The web-research engine — competitors, public reviews, market. |
| `visualization: "auto"` | Sentiment-over-time and share-of-voice charts in reports (must be requested in the prompt). |
| Streaming + `thinking_summaries: "auto"` | Live research-progress view; reconnect on drop via `last_event_id`. |
| Follow-up via `previous_interaction_id` | PM asks follow-ups on a finished report without re-running. |
| Multimodal input (image / document) | Feed in competitor screenshots, a competitor pricing-page PDF, prior research. |
| `deep-research` vs `deep-research-max` | Fast variant for routine monitoring; Max for deep competitive due diligence (§14). |

**Key limitation to design around:** the Deep Research Agent **does not support
structured output**. The main analyst's pipeline runs on structured Insight objects. The
workaround is a post-processing extraction step (§10).

---

## 5. Architecture

```
  PM / trigger ─► Playbook ─► Collaborative ─► Deep Research ─► cited
                  config       planning         (background)     report
                                  │                                │
                          PM refines/approves                       ▼
                                                          Structured Extraction
  File Search stores ◄── internal qual-data ingestion          (standard model,
  (tickets, reviews, surveys)                                  structured output)
                                                                     │
                                                                     ▼
                                                       Insight objects ─► Insight
                                                       (evidence-scored)    Feed +
                                                                          Reinforcement
                                                                            Loop
```

Components: **Research Playbooks** (configured tasks); the **async job system** (submit,
poll, stream, reconnect); the **File Search ingestion pipeline** (internal qual data);
the **structured extraction** step; integration with the existing Insight Engine and
reinforcement loop.

---

## 6. Research Playbooks

A playbook is a config object — the qualitative analog of a `SKILL.md`:

```json
{
  "playbook_id": "competitor-switching",
  "research_job": "C",
  "model": "deep-research-max-preview-04-2026",
  "agent_config": { "type": "deep-research", "thinking_summaries": "auto",
                    "visualization": "auto", "collaborative_planning": true },
  "tools": ["google_search", "url_context", "file_search", "code_execution"],
  "file_search_stores": ["churn-surveys", "win-loss-notes"],
  "prompt_template": "<see Appendix B>",
  "default_cadence": "monthly",
  "cost_ceiling_usd": 7
}
```

### Playbook A — User Wants / Unmet Needs
- **Model:** `deep-research` (fast). **Tools:** search, url_context, file_search (feature-request corpus).
- **Prompt** asks for: ranked demand themes; demand frequency/intensity signal; which user segment each theme comes from; whether competitors already offer it (gap vs parity); suggested priority. Charts: demand-theme frequency.
- **Output sections:** Top demand themes · Demand by segment · Competitive gap · Suggested priorities.

### Playbook B — Voice of Customer
- **Model:** `deep-research` (fast). **Tools:** search, url_context, file_search (reviews, NPS verbatims, survey open-ends, tickets).
- **Prompt** asks for: theme extraction with sentiment; emerging vs declining themes **versus the prior run** (prior summary passed as context); spikes; paraphrased representative quotes (never verbatim reproduction of copyrighted reviews). Charts: sentiment-over-time, share-of-theme.
- **Output sections:** Theme map · Sentiment by theme · Emerging issues · Trend vs prior run.

### Playbook C — Competitor & Switching
- **Model:** `deep-research-max` (comprehensive). **Tools:** search, url_context, file_search (churn surveys, win/loss notes, sales-call notes); multimodal for competitor screenshots/pricing PDFs.
- **Prompt** asks for: which competitors users compare/switch to; per competitor, *why* (features, price, UX, reliability) for both inbound and outbound switching; a feature/pricing comparison table; recent competitor moves; a watch-list. Internal churn-survey corpus is mined for stated switching reasons.
- **Output sections:** Competitor map · Switching drivers (to / from) · Feature & pricing comparison · Recent moves · Watch-list.

PMs can also run a free-form research task that doesn't fit a playbook; playbooks exist
because they make runs consistent, comparable across time, and cost-bounded.

---

## 7. Data inputs

**Web** — `google_search` + `url_context`, on by default. The external world.

**Internal qualitative corpora — via File Search.** The feature's differentiator: it
researches the company's *own* unstructured voice-of-customer data, which the
quantitative warehouse doesn't hold. An **ingestion pipeline** syncs these into Gemini
File Search stores (`fileSearchStores/...`):

| Corpus | Feeds |
|---|---|
| Support tickets | B (VOC), A (requests) |
| App-store / marketplace reviews (exported) | A, B |
| NPS / CSAT verbatims | B |
| Survey open-ends | A, B |
| Churn / cancellation survey responses | C |
| Win/loss notes, sales-call notes | C |

**PII is redacted at ingestion** — these corpora contain customer PII; redaction happens
before anything reaches a File Search store (see §15).

**Multimodal** — competitor screenshots, pricing-page PDFs, prior research documents,
passed as `image` / `document` input items.

---

## 8. Execution model

### 8.1 On-demand research (default: collaborative planning ON)

1. PM picks a playbook and a focus (e.g. "competitor switching, focus on the EU market").
2. The feature submits with `collaborative_planning: true`, `background: true` — Deep
   Research returns a **plan**, not a report.
3. PM reviews the plan; refines it over multi-turn (`previous_interaction_id`, planning
   still on); or approves.
4. On approval, resubmit with `collaborative_planning: false` — the research executes.

Collaborative planning is on by default for on-demand runs: it improves results **and**
gates spend — the PM sees the scope before a $1–7 task runs.

### 8.2 Scheduled monitoring

Playbooks B and C run on a recurring cadence (default: VOC weekly, competitor monthly).
Scheduled runs **skip collaborative planning** — they use a pre-approved fixed plan
template. Each run is **delta-focused**: the prior run's theme summary is passed as
context so the report emphasizes *what changed* (new complaint themes, new competitor
moves), not a full restatement.

### 8.3 Triggered research (quant → qual handoff)

This is the feature's highest-value mode. When the quantitative analyst emits a notable
insight — "D7 retention down 6 pts for the paid cohort" — the feed card carries a
**"Research why"** action that composes a targeted research task ("investigate likely
causes of a retention decline among [segment] during [window]: user complaints, app
issues, competitor launches"). The resulting research insights are **linked back** to
the originating quantitative insight as explanatory context.

Triggered research is **suggested by default** (one click), not automatic — each run
costs real money. Auto-trigger is available for high-severity insights only, behind an
explicit budget and toggle.

---

## 9. The async job system

Every research task is long-running, so the feature is a job manager:

- Submit with `background: true` (which **requires `store: true`**); persist `interaction.id`.
- **Poll** `interactions.get(id)` for `in_progress → completed / failed`; or **stream**
  with `stream: true` + `thinking_summaries: "auto"` for a live progress view (thought,
  text, image deltas).
- **Reconnection** — streaming connections drop; tasks can run up to 60 minutes. The job
  manager tracks `interaction_id` and `last_event_id` and resumes the stream from the
  last event, per the Deep Research streaming guidance.
- On `failed`, capture `interaction.error`, surface it, and offer retry.
- A job record stores: playbook, inputs, `interaction_id`, status, the final report,
  citations, cost, and the extracted insights (§10).

---

## 10. Structured extraction — turning reports into insights

The Deep Research Agent produces an excellent cited report but **cannot emit structured
output**. The rest of the analyst (feed, reinforcement loop) runs on structured Insight
objects. Bridge:

When a research interaction completes, run a **follow-up call** — using a standard model,
which *does* support structured output — that points at the completed interaction:

```python
extraction = client.interactions.create(
    input="From the research report above, extract each distinct finding as a "
          "structured insight: title, summary, theme, the question it answers "
          "(wants / saying / competitor), evidence sources with URLs, evidence "
          "strength, sentiment/direction, affected segment. Return JSON.",
    model="gemini-3.1-pro-preview",          # standard model -> structured output OK
    previous_interaction_id=research_interaction.id,
)
```

The output is parsed into Insight objects, each carrying its **citations** (the source
URLs and File-Search references the report cited). The full cited report is retained and
linked from every insight derived from it.

---

## 11. Integration with the Insight Engine and reinforcement loop

Research insights flow into the **same feed and reinforcement loop** as quantitative
insights, with one adaptation.

The reinforcement spec's **validity floor** is statistical (confidence × magnitude). That
does not apply to qualitative findings. Research insights instead carry an
**evidence-strength score** — a function of: number of *independent* sources, source
quality and diversity, **internal + external corroboration** (a theme seen in both the
company's tickets *and* public reviews is stronger), citation count, and recency.

Evidence strength is the research analog of the validity floor: a finding above the
evidence-strength floor is **always surfaced**; the reinforcement loop only ranks within
the set of well-evidenced findings. The §2 principle of the reinforcement spec holds
unchanged — a well-evidenced unwelcome finding ("users are leaving for Competitor X
because of price") must never be suppressible because PMs dislike it. The anti-sycophancy
audit applies.

`source: "research"` distinguishes these insights in the feed; they carry their
playbook, research job, citations, and a link to the full report.

---

## 12. Output and UX

- **Research report view** — the full cited report with inline citations and any
  agent-generated charts; a live progress view (thinking summaries) while running.
- **Feed cards** — extracted research insights in the prioritized feed alongside
  quantitative ones, each linking to its citations and source report.
- **Follow-ups** — from a finished report, the PM asks clarifying/elaboration questions
  (`previous_interaction_id`) without re-running the task.
- **Linked insights** — a triggered-research card shows its link to the quantitative
  insight that prompted it, and vice versa.
- **Plan review** — the collaborative-planning step is a first-class UI: see the plan,
  edit scope, approve.

---

## 13. Determinism and trust

Unlike the quantitative analyses (deterministic on the baked dataset), research is
**non-deterministic and time-varying** — it depends on the live web and the agent's
autonomous path. Reports are therefore not reproducible run-to-run, and the feature does
not claim they are. Trust comes instead from **citations**: every research insight is
traceable to sources the PM can verify, and the feature surfaces citations prominently
and prompts review of them (§15).

---

## 14. Model selection

| Variant | Use for | Est. cost/task |
|---|---|---|
| `deep-research-preview-04-2026` | Routine VOC and user-wants monitoring; streamed to UI. | ~$1–3 |
| `deep-research-max-preview-04-2026` | Deep competitor due diligence, comparative landscaping. | ~$3–7 |

Playbook A and B default to fast; Playbook C defaults to Max. Per-run override allowed
within the playbook's cost ceiling.

---

## 15. Safety

Giving an agent the web **and** the company's private files together creates real risk;
the Deep Research docs flag three, and the feature mitigates each:

- **Prompt injection via files and web pages** — uploaded documents and web content can
  carry hidden instructions. Mitigation: research output is treated as untrusted — it
  never auto-triggers actions; the structured-extraction step and human review sit
  between a report and any decision; citations are surfaced for verification.
- **Exfiltration** — combining sensitive internal corpora (File Search) with web browsing
  in one interaction is an exfiltration surface. Mitigations: **(a)** PII is redacted
  before ingestion into any File Search store; **(b)** playbook-level rules govern which
  internal stores may attach when web tools are on — competitor/web-heavy runs do not
  attach the most sensitive stores; **(c)** for high-sensitivity work, prefer separate
  interactions — one web pass, one internal pass — then synthesize.
- **Web-content risk** — the agent may encounter malicious pages. Mitigation: review the
  `citations`; low-quality or untrustworthy sources are down-weighted in evidence scoring.

Per copyright: extraction and reports **paraphrase** user reviews and source content —
they never reproduce verbatim review text, lyrics, or substantial source passages.

---

## 16. Acceptance criteria

| ID | Criterion |
|---|---|
| AC-1 | A playbook run executes via `background=true`, is polled/streamed to completion, and returns a cited report. |
| AC-2 | Streaming resumes correctly after a dropped connection using `last_event_id`. |
| AC-3 | Collaborative planning returns a plan; the plan is refinable over multi-turn and approvable. |
| AC-4 | File Search corpora are queried and cited alongside web sources in a report. |
| AC-5 | Structured extraction converts a completed report into valid Insight objects, each carrying citations. |
| AC-6 | Research insights appear in the feed and reinforcement loop with an evidence-strength score. |
| AC-7 | Every research insight has resolvable citations linking to its sources. |
| AC-8 | On-demand runs enforce the collaborative-planning gate; per-task cost stays within the playbook ceiling. |
| AC-9 | A triggered-research task links bidirectionally to the originating quantitative insight. |
| AC-10 | No verbatim reproduction of copyrighted review/source text in reports or extracted insights. |

---

## 17. Phasing

| Phase | Scope |
|---|---|
| **P1 — On-demand research** | The 3 playbooks, web tools only, async job system (poll + stream + reconnect), collaborative planning, report view. |
| **P2 — Internal corpora** | File Search ingestion pipeline + PII redaction; internal qual data in research. |
| **P3 — Feed integration** | Structured extraction; research insights into the feed + reinforcement loop with evidence scoring. |
| **P4 — Monitoring** | Scheduled VOC and competitor playbooks; delta detection vs prior runs. |
| **P5 — Quant ↔ qual** | Triggered research from quantitative insights; linked insights. |

---

## 18. Open questions

| ID | Item |
|---|---|
| Q-1 | Which internal corpora ship in P2 first, and what is the PII-redaction standard before File Search ingestion? |
| Q-2 | Auto-trigger budget and severity threshold for §8.3 — what insight severity justifies spending without a PM click? |
| Q-3 | How are research themes deduped/diffed across scheduled runs — pass the prior summary as context, or diff extracted insights post-hoc, or both? |
| Q-4 | Are any internal systems (e.g. a feature-request board, a CRM) worth connecting as `mcp_server` tools rather than File Search corpora? |
| Q-5 | Evidence-strength scoring weights — calibrate corroboration vs source count vs recency. |
| Q-6 | Cadence for scheduled monitoring — weekly VOC may be too costly at scale; tune cadence vs freshness vs budget. |
| Q-7 | Deep Research is preview — `agent` version strings and `agent_config` schema may change; isolate all calls behind the job system. |

---

## Appendix A — Reference calls

**On-demand: request a plan, then approve.**
```python
plan = client.interactions.create(
    agent="deep-research-max-preview-04-2026",
    input=COMPETITOR_PLAYBOOK_PROMPT,
    agent_config={"type": "deep-research", "thinking_summaries": "auto",
                  "visualization": "auto", "collaborative_planning": True},
    tools=[{"type": "file_search",
            "file_search_store_names": ["fileSearchStores/churn-surveys"]}],
    background=True,
)
# ... PM reviews plan.output_text, optionally refines via previous_interaction_id ...
report = client.interactions.create(
    agent="deep-research-max-preview-04-2026",
    input="Plan approved.",
    agent_config={"type": "deep-research", "collaborative_planning": False},
    previous_interaction_id=plan.id,
    background=True,
)
```

**Structured extraction (follow-up on the completed report).**
```python
extraction = client.interactions.create(
    input="Extract each finding from the report as a structured insight (JSON): "
          "title, summary, research_job, evidence_sources[], evidence_strength, "
          "sentiment, segment.",
    model="gemini-3.1-pro-preview",
    previous_interaction_id=report.id,
)
```

## Appendix B — Playbook C prompt template (sketch)

```
Research which competitors users of <PRODUCT> compare against and switch to or from,
and why, focused on <FOCUS>.

Use public sources (comparison sites, reviews, forums, social, competitor sites) and
our internal corpora (churn surveys, win/loss notes).

If specific figures are unavailable, state so explicitly — do not estimate.
Paraphrase user feedback; do not reproduce review text verbatim.

Format as a report with:
1. Competitor map — who users consider, by segment
2. Switching drivers — why users switch TO and FROM each competitor
3. Feature & pricing comparison — include a data table
4. Recent competitor moves (last 6 months)
5. Watch-list — what to monitor

Include charts comparing competitor share-of-voice and feature coverage.
```
