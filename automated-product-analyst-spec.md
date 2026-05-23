# Product Spec — "Lighthouse": Automated Product Analyst

> **Status:** Draft v0.1 — for review
> **Working codename:** Lighthouse (placeholder)
> **Owner:** TBD
> **Last updated:** 2026-05-23

---

## 1. Summary

Lighthouse is an automated product analyst. A product manager (PM) selects an analysis — or a whole category of analyses — and Lighthouse runs it end to end: pulls the data, computes the methodology, produces charts and tables, and returns a ranked set of **insights worth attention** rather than a raw dump of numbers. It also runs continuously in the background, monitoring high-level KPIs and alerting only when something is genuinely anomalous.

It is built on the **Gemini Managed Agents** framework (Interactions API + custom agents). Each of the ~87 analyses in the analysis catalog becomes a reusable agent **skill**; each of the 13 categories becomes a **group agent** that loads its group's skills. The product's value is not the agents themselves but the orchestration and the **Insight Engine** layered on top that scores, dedupes, and ranks what comes back.

---

## 2. Goals and non-goals

### 2.1 Goals
- Let a PM run any individual analysis from the catalog with a few clicks, no SQL, no notebook.
- Let a PM run an entire category (e.g. *Monetization & Revenue*) as one action and get a consolidated briefing.
- Continuously monitor a defined set of headline KPIs and proactively flag anomalies.
- Surface a **prioritized insight feed** — the system decides what deserves attention, not the user.
- Every insight is explainable, reproducible, and links back to the underlying data and charts.

### 2.2 Non-goals (v1)
- Not a BI tool / not a replacement for dashboards. It produces insights, not pixel-perfect dashboards.
- No write-back to production systems. Read-only on all data sources.
- No automated decision-making or auto-shipped experiments. Lighthouse recommends; humans act.
- Not a general chat assistant. Conversational follow-up is a v2 capability (see §13).

---

## 3. Personas and core use cases

| Persona | Need | How Lighthouse serves it |
|---|---|---|
| Growth PM | "Which channels bring high-LTV users?" | Runs *Source/medium quality analysis* on demand. |
| Monetization PM | "What changed in revenue this week?" | Runs the *Monetization & Revenue* group; gets a ranked briefing. |
| Head of Product | "Tell me what I should be worried about." | Reads the daily prioritized insight feed + KPI monitor alerts. |
| Data team | Wants to offload repetitive analyses | Catalog covers the standard requests; data team curates skills. |

**Primary use case:** Monday morning. Head of Product opens Lighthouse. The insight feed shows 4 cards ranked by attention score: D7 retention for the Feb paid-acquisition cohort dropped 6 points; a checkout step is leaking 12% more than baseline; ARPPU is up but driven by one whale; NPS detractor themes shifted toward "load times." Each card links to charts and the analysis that produced it.

---

## 4. Mapping to the Gemini Managed Agents framework

The framework gives us four primitives we lean on directly:

| Framework primitive | How Lighthouse uses it |
|---|---|
| **Interaction** (`client.interactions.create`) | One run of one analysis (or one group). Provisions a sandbox, runs the agent loop, returns output + `steps` + files. |
| **Custom agent** (`client.agents.create`) | One agent per analysis group. Bundles `system_instruction`, the base environment, and the group's skills. |
| **`base_environment` + sources** | Data connectors, analysis libraries, the shared `AGENTS.md`, and `SKILL.md` files loaded from a GitHub repo. |
| **Environment reuse** | Pull data once, snapshot the environment, fork it for every skill in a group run — clean conversation, shared data files. |

Key facts from the framework we design around:
- The agent automatically loads `.agents/AGENTS.md` as system instructions and any `SKILL.md` under `.agents/skills/` as capabilities.
- Each invocation **forks the base environment** — every run starts clean and isolated.
- The API tracks two independent states: **conversation context** (`previous_interaction_id`) and **environment state** (`environment`). We exploit "clear conversation, keep files" for group runs.
- **Streaming** (`stream=true`) yields step deltas — used for the live run view.
- **Automatic context compaction** kicks in around 135k tokens — long group runs won't blow the context window.
- Files created in the sandbox are retrieved via the **Files API** (`files/environment-{env_id}:download`).
- Base managed agent: `antigravity-preview-05-2026` (set as `base_agent`).

---

## 5. The analysis catalog

The attached catalog defines **13 groups** and ~87 analyses. Every analysis becomes one skill (`SKILL.md`). Every group becomes one custom agent. A user can run **one analysis** or **a whole group**.

| # | Group | Analyses | Group agent ID |
|---|---|---|---|
| 1 | Acquisition & Onboarding | 6 | `acquisition-analyst` |
| 2 | Engagement & Usage Patterns | 9 | `engagement-analyst` |
| 3 | Retention & Churn | 7 | `retention-analyst` |
| 4 | Monetization & Revenue | 12 | `monetization-analyst` |
| 5 | Funnel & Conversion | 6 | `funnel-analyst` |
| 6 | Segmentation & Personas | 6 | `segmentation-analyst` |
| 7 | A/B Testing & Experimentation | 5 | `experimentation-analyst` |
| 8 | Behavioral Economics & Psychology | 6 | `behavioral-econ-analyst` |
| 9 | Social & Viral | 6 | `social-viral-analyst` |
| 10 | Content & Game Economy | 6 | `economy-analyst` |
| 11 | UX & Product Quality | 6 | `ux-quality-analyst` |
| 12 | Feedback & Sentiment | 5 | `feedback-analyst` |
| 13 | Predictive Modelling | 7 | `predictive-analyst` |

The full analysis → skill mapping is in **Appendix A**.

---

## 6. System architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Lighthouse Web App  (catalog · run config · live view · feed) │
└───────────────┬────────────────────────────────┬──────────────┘
                │                                │
        ┌───────▼────────┐              ┌────────▼─────────┐
        │  Control Plane │              │  Insight Engine  │
        │  (Orchestrator)│◄────insights─┤  score · dedupe  │
        │  run scheduler │              │  rank · feed     │
        └───────┬────────┘              └────────┬─────────┘
                │ interactions.create             │
        ┌───────▼─────────────────────────────────▼──────────┐
        │              Gemini Interactions API                │
        │   group agents · KPI monitor agent · sandboxes       │
        └───────┬──────────────────────────────────────────────┘
                │ read-only connectors (in sandbox env)
        ┌───────▼──────────────────────────────────────────────┐
        │  Data sources: warehouse · product analytics ·        │
        │  app stores · survey tools                            │
        └───────────────────────────────────────────────────────┘
```

### 6.1 Components

**Web App** — catalog browser, run configuration, live streamed run view, insight feed, KPI monitor dashboard, scheduling.

**Control Plane (Orchestrator)** — the only component that calls the Gemini API. Translates a user's selection into one or more `interactions.create` calls, manages environment snapshots, handles fan-out/concurrency for group runs, enforces cost caps, persists run records and `interaction.id`s for audit, runs the scheduler for KPI monitoring and recurring analyses.

**Insight Engine** — ingests structured insight objects emitted by agents, scores them, dedupes correlated insights, ranks them, and writes the prioritized feed. Detailed in §9.

**Group agents** — 13 custom agents, one per catalog group. Each loads only its group's skills (keeps context lean, lowers token cost, reduces hallucination).

**KPI Monitor agent** — a separate agent for continuous headline-KPI monitoring and anomaly detection. Detailed in §8.

**Base environment** — a single `analyst-base` environment shared by all agents: read-only data connectors, the analysis library stack (pandas, numpy, statsmodels, `lifelines` for survival/hazard models, scikit-learn, matplotlib), and the shared `AGENTS.md`.

---

## 7. Agent and skill design

### 7.1 Agent topology

One **base agent** definition shared via `base_environment`, then 13 group agents plus the KPI monitor:

```python
# Base environment created once, then referenced by every agent.
agent = client.agents.create(
    id="monetization-analyst",
    base_agent="antigravity-preview-05-2026",
    system_instruction=MONETIZATION_SYSTEM_PROMPT,
    base_environment={
        "type": "remote",
        "sources": [
            {"type": "inline",
             "target": ".agents/AGENTS.md",
             "content": HOUSE_ANALYST_STYLE},          # shared insight style
            {"type": "repository",
             "source": "https://github.com/ourorg/lighthouse-skills",
             "target": ".agents/skills"},               # all SKILL.md files
        ],
    },
)
```

All 13 agents point at the **same skills repo**. The `system_instruction` scopes each agent to its group so it only ever invokes its own skills. (Alternative considered: one mega-agent with all 87 skills — rejected; too much context, weaker skill selection. Open question O-2 in §16.)

### 7.2 Skill structure (`SKILL.md`)

Each analysis is one `SKILL.md`. The skill encodes the domain knowledge the agent would otherwise have to guess. Template:

```markdown
# Skill: Cohort Retention Curves

## When to use
The user wants D1/D7/D14/D30/D60/D90 retention by cohort.

## Required inputs
- events table with user_id, event_ts, event_name
- cohort definition (default: install date, weekly grain)
- date range (default: trailing 90 days)

## Method
1. Assign each user to a cohort by first-seen date.
2. For each cohort, compute the % active on day N (active = ≥1 qualifying event).
3. Use rolling retention if requested; classic otherwise.
4. Chart retention curves; build the cohort triangle table.

## What counts as a noteworthy finding
- A cohort's D7 retention deviates >1.5σ from the trailing-cohort mean.
- A monotonic decline across ≥3 consecutive cohorts.

## Output contract
Emit one or more Insight objects (see insight schema) plus:
- retention_curves.png, cohort_triangle.csv
```

The "noteworthy finding" section is what makes Lighthouse an *analyst* and not a report generator — the skill itself defines the bar for what is worth surfacing.

### 7.3 Shared `AGENTS.md` (house style)

Loaded by every agent. Enforces: always emit structured Insight objects via structured outputs; always state confidence and the statistical test used; never surface a finding below the skill's noteworthiness bar; always save charts as files; quantify business impact where possible; flag data-quality problems instead of silently proceeding.

---

## 8. KPI monitoring subsystem

Separate from the on-demand catalog. The PM defines a set of **headline KPIs** (e.g. DAU, new-user activation rate, ARPDAU, D1 retention, crash-free rate, conversion-to-payer). The KPI Monitor agent runs on a schedule.

**Mechanics:**
- Scheduler triggers `interactions.create` against the `kpi-monitor` agent on a cron (default daily; configurable hourly for volatile metrics).
- The agent pulls the latest KPI values, compares against (a) a baseline window, (b) a forecast band (e.g. seasonal-naive or Prophet-style expectation), and (c) hard thresholds the PM set.
- Anomaly detection per the catalog's *Anomaly detection (unusual spikes/drops in KPIs)* skill — statistical, not just threshold, so it catches level shifts and trend breaks.
- Output: alerts **only** when a KPI breaches its band/threshold. A clean run produces no feed noise — just a logged "all green."
- Each alert is an Insight object, fed into the Insight Engine alongside on-demand results, so monitoring and analysis share one feed.

**Escalation:** alerts above a severity cutoff can trigger email/Slack; configurable per KPI.

**Drill-down hook:** a KPI alert can optionally auto-trigger the most relevant catalog analysis (e.g. a DAU drop auto-runs *Cohort retention curves* and *Channel attribution*). v1.1 — gated behind a toggle.

---

## 9. The Insight Engine

This is the core differentiator. Agents produce findings; the Insight Engine decides **what gets attention**.

### 9.1 Insight object schema

Every agent emits findings as structured JSON (via Gemini structured outputs):

```json
{
  "insight_id": "uuid",
  "title": "D7 retention down 6pts for Feb paid cohort",
  "summary": "One-paragraph plain-language explanation.",
  "group": "retention-churn",
  "skill": "cohort-retention-curves",
  "metric": "d7_retention",
  "direction": "down",
  "magnitude": { "value": -0.06, "unit": "pp", "relative": -0.18 },
  "confidence": 0.93,
  "stat_test": "z-test vs trailing-cohort mean, p=0.004",
  "segment": "acquisition_channel = paid_social",
  "business_impact": { "metric": "revenue", "estimate_usd": -42000, "horizon": "90d" },
  "recommended_actions": ["Investigate Feb paid-social creative", "..."],
  "artifacts": ["retention_curves.png", "cohort_triangle.csv"],
  "data_window": { "start": "2026-02-01", "end": "2026-05-20" },
  "run_id": "...", "interaction_id": "..."
}
```

### 9.2 Attention score

Each insight gets an **attention score** in [0,1] that drives feed ranking:

```
attention = w1·magnitude_norm
          + w2·confidence
          + w3·business_impact_norm
          + w4·novelty
          + w5·actionability
          - w6·staleness
```

- **magnitude_norm** — effect size, normalized within metric type.
- **confidence** — statistical confidence reported by the agent.
- **business_impact_norm** — modeled $ or retention impact, normalized.
- **novelty** — penalizes insights similar to ones already surfaced recently (embedding similarity over title+summary+segment).
- **actionability** — heuristic on whether `recommended_actions` are concrete.
- **staleness** — decays the score of aging, un-acted-on insights.

Weights are config, tuned from feedback (§9.4). v1 ships sensible defaults.

### 9.3 Deduplication and clustering

Correlated insights (e.g. "DAU down" and "sessions down" pointing at the same cause) are clustered by embedding similarity + shared segment/metric lineage. The cluster surfaces as **one card** with a primary insight and supporting findings nested underneath, so the feed shows distinct problems, not echoes.

### 9.4 Feedback loop

Each feed card has lightweight signals: *useful / not useful / already knew this / acted on it*. These tune the attention-score weights and the per-skill noteworthiness bars over time. This is how Lighthouse gets better at "what deserves attention" for a given team.

---

## 10. Execution model

### 10.1 Mode A — single analysis

1. User picks one analysis + run config (date range, segment filters, cohort def).
2. Orchestrator calls `interactions.create` on the relevant group agent with `environment="remote"` and an `input` instructing it to run **exactly that one skill** with the given parameters.
3. Optionally `stream=true` → live run view shows reasoning, tool calls, code execution from `interaction.steps`.
4. On completion: parse Insight objects from `output_text`, download artifacts via the Files API, persist the run, push insights to the Insight Engine.

### 10.2 Mode B — group run (the data-snapshot pattern)

Running a whole group naively = N independent data pulls. Instead we exploit the framework's independent conversation/environment states:

1. **Data-load interaction** — one `interactions.create` whose only job is to pull every dataset the group's skills need into the sandbox and save them as files. Keep `interaction.environment_id`.
2. **Snapshot** — that environment is now a "data-loaded" environment.
3. **Fan-out** — for each skill in the group, call `interactions.create` with:
   - `agent` = the group agent,
   - `environment = <snapshot env id>` (keep files) **and no `previous_interaction_id`** (fresh conversation) — the framework's documented "clear conversation, keep files" pattern,
   - `input` = run this one skill.
   Run these with bounded concurrency (default 4).
4. **Aggregate** — collect all Insight objects, send the batch to the Insight Engine, which dedupes/clusters/ranks and produces a **consolidated group briefing** (one ranked document + the individual insight cards).

Benefits: data is extracted once, each skill still runs isolated and clean, cost is attributable per skill, and one slow/failing skill doesn't block the others.

### 10.3 Mode C — continuous KPI monitoring

Scheduled, as described in §8. Same downstream path into the Insight Engine.

### 10.4 Reliability
- Per-interaction timeout and retry with backoff.
- A failed skill in a group run is marked failed and excluded; the briefing notes it. The run does not fail wholesale.
- Every run records its `interaction_id`(s) and `steps` for audit and reproduction.

---

## 11. Data layer and connectors

Connectors run **inside the agent's environment** with **read-only, scoped** credentials injected as environment secrets.

| Source type | Examples | Used by |
|---|---|---|
| Warehouse | BigQuery, Snowflake, Redshift, Databricks | Most groups |
| Product analytics | Amplitude, Mixpanel, GA4 | Acquisition, Engagement, Funnel |
| App stores | App Store / Play Store reviews APIs | UX & Quality, Feedback |
| Survey / VOC | Delighted, Qualtrics, in-app survey export | Feedback & Sentiment |

- Network egress from the environment is allow-listed to required data endpoints only.
- A **semantic layer / metric definitions** file ships in the skills repo so every skill computes, e.g., "active user" or "ARPPU" identically.
- Connector setup is an admin task; the catalog greys out analyses whose required source isn't connected.

---

## 12. User experience

**Catalog** — 13 group cards; expand a card to see its analyses. Each analysis has *Run* and *Schedule*. Each group card has *Run whole group*.

**Run configuration** — date range, segment filters, cohort grain/definition, comparison window. Sensible per-skill defaults so a one-click run always works.

**Live run view** — for streamed runs: a timeline of the agent's steps (reasoning, code execution, tool calls) rendered from step deltas. Reassures the user the analysis is real and inspectable.

**Insight feed ("what needs attention")** — the home screen. Ranked cards. Each card: title, plain-language summary, magnitude + confidence, the chart, business-impact estimate, recommended actions, links to artifacts and the source run. Feedback controls per card.

**KPI monitor dashboard** — the headline KPIs, current value, status (green / watch / alert), sparkline, last-checked time. Alerts also appear in the feed.

**Scheduling** — any analysis or group can be set to recur; results flow to the feed.

**Export** — any insight or group briefing exports to PDF; artifacts download individually.

---

## 13. Product API (Lighthouse backend)

Internal API the web app uses; also enables future programmatic access.

| Endpoint | Purpose |
|---|---|
| `GET /catalog` | Groups, analyses, connection status. |
| `POST /runs` | Start a run. Body: `{type: analysis\|group, id, config}`. |
| `GET /runs/{id}` | Run status, streamed steps, results. |
| `GET /insights` | Prioritized feed; filters by group, severity, date. |
| `POST /insights/{id}/feedback` | Useful / not useful / acted-on. |
| `GET /kpis` / `POST /kpis` | List / define monitored KPIs. |
| `POST /schedules` | Create a recurring run. |

**v2 candidates:** conversational follow-up on an insight ("why?" → multi-turn via `previous_interaction_id`); cross-group "investigations" that chain agents; auto-drill-down from KPI alerts.

---

## 14. Data model (core entities)

- **AnalysisDefinition** — catalog metadata, required sources, default config, the skill ID.
- **Group** — catalog grouping, group-agent ID.
- **Run** — type, target id, config, status, cost, list of `interaction_id`s, timestamps.
- **Insight** — the §9.1 schema, plus attention score, cluster id, feedback.
- **KPIDefinition** — metric, source, baseline window, thresholds, schedule, escalation rule.
- **Schedule** — target, cron, owner, enabled.
- **Connector** — type, credentials ref (vault), scope, status.

---

## 15. Security, privacy, governance, cost

- **Read-only everywhere.** No connector has write scope.
- **Credentials** in a secrets manager; injected to environments as ephemeral env secrets; never logged.
- **PII** — skills operate on aggregates; raw user-level data stays in the sandbox and is not persisted into insights. PII redaction policy in `AGENTS.md`.
- **Audit** — every run stores its `interaction_id`(s) and `steps`; any insight is fully traceable to code that produced it.
- **Tenant isolation** — each invocation forks a fresh sandbox; no cross-run data bleed.
- **Cost controls** — per-run token/cost cap enforced by the Orchestrator; group runs have a fan-out ceiling; monthly budget alerts. Context compaction (~135k tokens) bounds long runs automatically.
- **Observability** — dashboards for run latency, failure rate, cost per group, insight volume, and feedback-derived precision (% of surfaced insights marked useful).

---

## 16. Open questions and risks

| ID | Item | Notes |
|---|---|---|
| O-1 | Hallucinated numbers | Mitigation: agents must compute via code execution, never assert numbers from reasoning; charts/tables are the source of truth; spot-check harness compares agent output to a SQL ground-truth on a sample. |
| O-2 | One mega-agent vs 13 group agents | Spec assumes 13. Revisit if skill-selection accuracy is high enough to consolidate. |
| O-3 | Data freshness vs cost of re-pull | Snapshot pattern (§10.2) caches data per group run; need a TTL policy for how long a snapshot is reusable. |
| O-4 | Attention-score cold start | Ship default weights; the feedback loop needs ~weeks of data per team to tune well. |
| O-5 | Managed Agents is in preview | API surface (`Api-Revision` header, agent version `antigravity-preview-05-2026`) may change; isolate all Gemini calls behind the Orchestrator so a version bump is one change. |
| O-6 | Semantic-layer drift | If metric definitions differ from the company's BI tool, PMs lose trust. Source metric definitions from the existing semantic layer where one exists. |

---

## 17. Phased rollout

| Phase | Scope |
|---|---|
| **Phase 0 — Foundations** | Base environment, skills repo, one group agent (*Retention & Churn*), warehouse connector, single-analysis mode, basic insight rendering. |
| **Phase 1 — On-demand catalog** | All 13 group agents + ~87 skills. Group-run mode with the snapshot pattern. Insight Engine v1 (scoring + dedupe + feed). |
| **Phase 2 — Monitoring** | KPI monitor agent, scheduling, anomaly detection, alerting/escalation. |
| **Phase 3 — Intelligence** | Feedback-tuned scoring, insight clustering quality, auto-drill-down from KPI alerts. |
| **Phase 4 — Conversational** | Multi-turn follow-up on insights, cross-group investigations. |

**Phase 1 success metrics:** ≥80% of runs complete without manual intervention; ≥60% of surfaced insights marked useful; median single-analysis run < 3 min.

---

## Appendix A — Analysis → skill mapping

Skill IDs are kebab-case; all live under `.agents/skills/` in the skills repo.

### Group 1 — Acquisition & Onboarding (`acquisition-analyst`)
`channel-attribution`, `install-to-registration-conversion`, `ftue-funnel`, `onboarding-completion-dropoff`, `time-to-first-value`, `source-medium-quality`

### Group 2 — Engagement & Usage Patterns (`engagement-analyst`)
`dau-wau-mau-stickiness`, `session-frequency-duration-depth`, `feature-adoption-heatmap`, `power-vs-casual-segmentation`, `time-of-day-day-of-week-usage`, `session-interval`, `content-screen-consumption`, `navigation-path-flow-sankey`, `dead-end-rage-tap`

### Group 3 — Retention & Churn (`retention-analyst`)
`cohort-retention-curves`, `rolling-vs-classic-retention`, `churn-prediction-survival`, `resurrection-analysis`, `retention-by-segment`, `n-day-activity-curves`, `magic-number-analysis`

### Group 4 — Monetization & Revenue (`monetization-analyst`)
`arpu-arppu-arpdau`, `conversion-to-payer-funnel`, `time-to-first-purchase`, `rfm-purchase-recency`, `revenue-concentration-whale-curve`, `price-sensitivity-elasticity`, `sku-item-sales`, `ltv-modeling`, `ltv-to-cac-by-channel`, `subscription-renewal-cancellation`, `trial-to-paid-conversion`, `iap-basket-analysis`

### Group 5 — Funnel & Conversion (`funnel-analyst`)
`multi-step-conversion-funnel`, `micro-conversion-tracking`, `funnel-stage-dropoff`, `funnel-comparison-by-segment`, `cart-checkout-abandonment`, `paywall-hit-rate-conversion`

### Group 6 — Segmentation & Personas (`segmentation-analyst`)
`behavioral-clustering`, `rfm-segmentation`, `psychographic-segmentation`, `lifecycle-stage-segmentation`, `motivational-segmentation`, `high-value-user-profiling`

### Group 7 — A/B Testing & Experimentation (`experimentation-analyst`)
`controlled-experiment-analysis`, `multi-armed-bandit-optimization`, `holdout-group-analysis`, `interleaving-experiments`, `pre-post-launch-impact`

### Group 8 — Behavioral Economics & Psychology (`behavioral-econ-analyst`)
`loss-aversion-endowment`, `anchoring-effect-pricing`, `scarcity-urgency-impact`, `social-proof-effectiveness`, `default-nudge-effect`, `sunk-cost-progression`

### Group 9 — Social & Viral (`social-viral-analyst`)
`viral-coefficient-kfactor`, `referral-funnel`, `social-sharing-behavior`, `network-effect-measurement`, `guild-clan-group-dynamics`, `peer-influence-contagion`

### Group 10 — Content & Game Economy (`economy-analyst`)
`content-consumption-velocity`, `difficulty-progression-curve`, `economy-sink-source-balance`, `loot-reward-distribution`, `content-gap-analysis`, `level-completion-difficulty-spikes`

### Group 11 — UX & Product Quality (`ux-quality-analyst`)
`heatmaps-scroll-maps`, `error-crash-impact`, `load-time-engagement-correlation`, `accessibility-device-compatibility`, `app-rating-review-sentiment`, `support-ticket-clustering`

### Group 12 — Feedback & Sentiment (`feedback-analyst`)
`nps-csat-trends`, `in-app-survey-analysis`, `app-store-review-mining`, `voc-theme-extraction`, `feature-request-prioritization`

### Group 13 — Predictive Modelling (`predictive-analyst`)
`churn-propensity-scoring`, `next-best-action`, `recommendation-engine-performance`, `early-ltv-prediction`, `anomaly-detection-kpi`, `propensity-to-purchase`, `user-fatigue-modeling`

> `anomaly-detection-kpi` is also the engine behind the KPI Monitor agent (§8).

---

## Appendix B — Reference Gemini calls

**Single analysis (Mode A):**
```python
interaction = client.interactions.create(
    agent="retention-analyst",
    input="Run skill `cohort-retention-curves` for trailing 90 days, "
          "weekly cohorts, segmented by acquisition_channel. "
          "Emit Insight objects per the output contract.",
    environment="remote",
    stream=True,
)
```

**Group run (Mode B):**
```python
# 1. Load data once
loader = client.interactions.create(
    agent="monetization-analyst",
    input="Load all datasets required by the Monetization & Revenue skills "
          "for trailing 90 days and save them to /data.",
    environment="remote",
)
env = loader.environment_id

# 2. Fan out per skill, reusing the data-loaded environment (fresh conversation)
for skill in MONETIZATION_SKILLS:
    client.interactions.create(
        agent="monetization-analyst",
        environment=env,                  # keep files
        input=f"Run skill `{skill}` using the datasets in /data.",
    )                                     # no previous_interaction_id -> clean conversation
```

**KPI monitor (Mode C, scheduled):**
```python
client.interactions.create(
    agent="kpi-monitor",
    input="Check all monitored KPIs against baseline and forecast bands. "
          "Emit an Insight object only for breaches.",
    environment="remote",
)
```
