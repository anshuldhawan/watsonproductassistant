# Watsons: an army of automated Product Analysts

An AI-powered product analytics system that transforms raw product data into a prioritized feed of actionable business insights. Watsons orchestrates [Gemini Managed Agents](https://ai.google.dev/gemini-api/docs/agents) for quantitative analysis and the [Gemini Deep Research Agent](https://ai.google.dev/gemini-api/docs/interactions/deep-research) for qualitative user and market research, delivering a unified "what needs attention" stream for product managers.

---

## How It Works

Watsons replaces the manual analyst workflow of pulling data, computing metrics, and interpreting results. A PM selects an analysis (or an entire category), and Watsons runs it end-to-end: pulls data, executes the methodology, produces charts, and returns **ranked insights worth attention** rather than raw numbers.

The system operates in three modes:

| Mode | Description |
|------|-------------|
| **Single Analysis** | Run one specific analysis (e.g., cohort retention curves) with configurable parameters |
| **Group Run** | Run an entire category of analyses (e.g., all 12 Monetization analyses) with a shared data snapshot |
| **Continuous Monitoring** | Scheduled KPI anomaly detection that alerts only on genuine statistical breaches |

Additionally, a qualitative research layer uses the Gemini Deep Research Agent to answer "why" questions — what users want, what they're saying, and which competitors they're switching to.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Watsons Web App                                    │
│  Insight Feed · Analysis Catalog · Live Run View · KPI Monitor · Research│
└──────────┬─────────────────────────────────────┬─────────────────────────┘
           │                                     │
   ┌───────▼────────┐                  ┌─────────▼──────────┐
   │  Control Plane  │                  │   Insight Engine    │
   │  (Orchestrator) │◄───insights─────┤  score · dedupe ·   │
   │  run scheduler  │                  │  cluster · rank     │
   └───────┬─────────┘                  └─────────┬──────────┘
           │                                      │
           │ interactions.create                   │ Reinforcement
           │                                      │ Learning Loop
   ┌───────▼──────────────────────────────────────▼──────────────────────┐
   │                    Gemini APIs                                        │
   │                                                                      │
   │  ┌─────────────────────────┐    ┌────────────────────────────────┐  │
   │  │  Managed Agents         │    │  Deep Research Agent            │  │
   │  │  (Interactions API)     │    │  (Interactions API)             │  │
   │  │                         │    │                                  │  │
   │  │  13 group agents        │    │  Plan → Search → Read →         │  │
   │  │  87 analyst skills      │    │  Iterate → Cited Report         │  │
   │  │  KPI monitor agent      │    │                                  │  │
   │  │  Code execution sandbox │    │  Collaborative planning          │  │
   │  └─────────────────────────┘    │  File Search (internal corpora)  │  │
   │                                  │  Google Search + URL Context     │  │
   │                                  └────────────────────────────────┘  │
   └───────┬──────────────────────────────────────────────────────────────┘
           │ read-only connectors
   ┌───────▼──────────────────────────────────────────────────────────────┐
   │  Data Layer: Spotify Parquet Dataset (6.6M events · 10K users)       │
   │  DuckDB in-process analytics · Date-partitioned event stream          │
   └──────────────────────────────────────────────────────────────────────┘
```

---

## Gemini Agent Integration

### Managed Agents — Quantitative Analysis

Watsons maps its 87-analysis catalog onto the [Gemini Managed Agents](https://ai.google.dev/gemini-api/docs/agents) framework. Each analysis becomes a reusable agent **skill** (`SKILL.md`); each of the 13 categories becomes a **group agent** with its own system instructions.

**How it works:**

```python
# Single analysis via the Interactions API
interaction = client.interactions.create(
    agent="retention-analyst",
    input="Run skill `cohort-retention-curves` for trailing 90 days, "
          "weekly cohorts, segmented by acquisition_channel.",
    environment="remote",
    stream=True,
)
```

The framework provides:
- **Sandboxed environments** — each agent runs code (pandas, numpy, statsmodels, scikit-learn) in an isolated Linux sandbox
- **Environment reuse** — group runs load data once, then fork the environment for each skill (the "data-snapshot pattern")
- **Streaming** — live reasoning steps streamed to the PM dashboard via Server-Sent Events
- **Structured output** — agents emit structured Insight JSON objects per a strict output contract

**Group run (data-snapshot pattern):**

```python
# 1. Load data once into the sandbox
loader = client.interactions.create(
    agent="monetization-analyst",
    input="Load all datasets for trailing 90 days into /data.",
    environment="remote",
)
env = loader.environment_id

# 2. Fan out: each skill gets the same data, fresh conversation
for skill in MONETIZATION_SKILLS:
    client.interactions.create(
        agent="monetization-analyst",
        environment=env,               # shared data files
        input=f"Run skill `{skill}`.", # no previous_interaction_id = clean context
    )
```

### Deep Research Agent — Qualitative Research

The [Gemini Deep Research Agent](https://ai.google.dev/gemini-api/docs/interactions/deep-research) handles the qualitative, outward-facing half of the analyst. It autonomously plans, searches the web, reads sources, iterates, and synthesizes cited reports.

**Three research playbooks:**

| Playbook | Question | Model |
|----------|----------|-------|
| **User Wants** | What features and changes do users demand? | `deep-research-preview-04-2026` |
| **Voice of Customer** | What are users saying; what themes are emerging? | `deep-research-preview-04-2026` |
| **Competitor & Switching** | Which competitors do users switch to, and why? | `deep-research-max-preview-04-2026` |

**Collaborative planning flow:**

```python
# 1. Request a research plan (PM reviews before costly execution)
plan = client.interactions.create(
    agent="deep-research-max-preview-04-2026",
    input=COMPETITOR_PLAYBOOK_PROMPT,
    agent_config={
        "type": "deep-research",
        "thinking_summaries": "auto",
        "visualization": "auto",
        "collaborative_planning": True,
    },
    tools=[
        {"type": "google_search"},
        {"type": "url_context"},
        {"type": "file_search",
         "file_search_store_names": ["fileSearchStores/churn-surveys"]},
    ],
    background=True,
)

# 2. PM refines the plan
refined = client.interactions.create(
    agent="deep-research-max-preview-04-2026",
    input="Focus more on the EU market and pricing comparisons.",
    agent_config={"type": "deep-research", "collaborative_planning": True},
    previous_interaction_id=plan.id,
    background=True,
)

# 3. Approve and execute
report = client.interactions.create(
    agent="deep-research-max-preview-04-2026",
    input="Plan approved.",
    agent_config={"type": "deep-research", "collaborative_planning": False},
    previous_interaction_id=refined.id,
    background=True,
)
```

**Structured extraction** — since Deep Research does not support structured output, a follow-up call with a standard model converts the cited report into structured Insight objects:

```python
extraction = client.interactions.create(
    input="Extract each finding as structured JSON insight.",
    model="gemini-3.1-pro-preview",
    previous_interaction_id=report.id,
)
```

**Deep Research capabilities used:**
- `background=True` for async multi-minute tasks
- Collaborative planning for cost gating and quality control
- `google_search` + `url_context` for web research
- `file_search` for internal qualitative corpora (tickets, reviews, surveys)
- `visualization: "auto"` for charts in reports
- Streaming with `thinking_summaries: "auto"` for live progress
- `previous_interaction_id` for follow-up questions without re-running
- Multi-turn plan refinement

### Quant-to-Qual Handoff

When a quantitative insight is notable (e.g., "D7 retention dropped 6pts"), the feed card carries a **"Research Why"** action that triggers a targeted Deep Research task. The resulting qualitative findings link back to the originating quantitative insight, creating a complete picture.

---

## The Insight Engine

The system's core differentiator. Agents produce findings; the Insight Engine decides **what gets attention**.

**Attention scoring:**

```
attention = w₁·magnitude + w₂·confidence + w₃·business_impact
          + w₄·novelty + w₅·actionability − w₆·staleness
```

**Key behaviors:**
- **Deduplication** — correlated insights (e.g., "DAU down" and "sessions down") are clustered into one card
- **Validity floor** — findings below statistical thresholds are never surfaced regardless of score
- **Anti-sycophancy** — well-evidenced unwelcome findings cannot be suppressed by feedback

### Reinforcement Learning Loop

A contextual bandit policy learns from PM feedback to rank insights. The system:
1. Extracts feature vectors from each insight (magnitude, confidence, novelty, actionability, valence)
2. Ranks using Thompson Sampling over a learned weight distribution
3. Refits daily from feedback events (useful / not important / methodology disagreement / acted on)
4. Runs offline policy evaluation (OPE) before promoting new weights
5. Enforces valence parity — negative-valence insights cannot be systematically suppressed

---

## Analysis Catalog

87 analyses across 13 groups, each implemented as a `SKILL.md`:

| # | Group | Analyses | Agent |
|---|-------|----------|-------|
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

---

## Dataset

A realistic Spotify-like product dataset for development and demonstration:

- **10,000 users** with demographic profiles (age, country, subscription tier, genre preferences)
- **20,000 tracks** across 1,000 artists and 2,000 albums
- **6.6 million listening events** over 30 days, date-partitioned as Snappy Parquet (~89 MB)
- Queryable in milliseconds via DuckDB

---

## Project Structure

```
ProductAssistant/
├── backend/
│   ├── main.py                    # FastAPI application and API routes
│   ├── orchestrator.py            # Execution modes A/B/C for quantitative analysis
│   ├── gemini_agents.py           # Gemini Managed Agent client (Interactions API)
│   ├── deep_research.py           # Deep Research Agent client (plan/approve/extract)
│   ├── research_orchestrator.py   # Research job lifecycle management
│   ├── research_playbooks.py      # Three qualitative research playbook definitions
│   ├── research_corpora.py        # File Search corpus registration
│   ├── insight_engine.py          # Attention scoring, deduplication, clustering
│   ├── reinforcement_loop.py      # Contextual bandit policy and feedback learning
│   ├── dataset_environment.py     # Gemini environment resolution for baked datasets
│   ├── models.py                  # SQLAlchemy data models
│   ├── schemas.py                 # Pydantic request/response schemas
│   ├── database.py                # SQLite database setup
│   ├── seed.py                    # Catalog seeding (87 analyses, KPIs)
│   └── env.py                     # Environment variable loading
├── skills/
│   ├── AGENTS.md                  # Shared analyst house style and output rules
│   └── <group-key>/
│       └── <skill-key>/
│           └── SKILL.md           # Per-analysis methodology and output contract
├── scripts/
│   ├── generate_data.py           # Synthetic Spotify dataset generator
│   ├── verify_data.py             # Dataset integrity verification
│   └── bake_gemini_environment.py # Bakes dataset into Gemini remote sandbox
├── templates/
│   └── index.html                 # PM dashboard (Insight Feed, Catalog, KPI Monitor)
├── static/                        # Frontend assets
├── data/
│   ├── catalog/                   # Dimension tables (users, tracks, artists, albums)
│   └── play_events/               # Date-partitioned event stream (30 daily partitions)
├── tests/
│   ├── test_gemini_agents.py      # Managed Agent integration tests
│   └── test_research.py           # Deep Research flow tests
├── dataset-manifest.json          # Dataset version, row counts, environment reference
├── requirements.txt               # Python dependencies
└── .env.example                   # Configuration template
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- A [Gemini API key](https://ai.google.dev/gemini-api/docs/api-keys) (optional for local mode)

### Installation

```bash
git clone <repo-url> && cd ProductAssistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env`:

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Gemini API key |
| `GEMINI_AGENT_MODE` | `local` (DuckDB fallback) or `gemini` (remote agents) |
| `GEMINI_DATASET_PROFILE` | `demo` for the small Gemini demo environment, `full` for the full dataset |
| `GEMINI_DEMO_AGENT_ID` | Managed agent to use for demo runs when custom group agents are not provisioned |
| `GEMINI_BAKE_AGENT` | Agent version for environment baking |
| `GEMINI_KPI_AGENT_ID` | Agent ID for KPI monitoring |

### Generate the Dataset

```bash
python scripts/generate_data.py
python scripts/verify_data.py
```

### Run the Server

```bash
uvicorn backend.main:app --reload
```

The PM dashboard is available at `http://localhost:8000`.

### Gemini-First Demo

For a fast demo that still uses real Gemini Managed Agents, bake the small fake
dataset instead of the full 6.6M-row dataset:

```bash
scripts/run_gemini_demo_bake.sh --python .venv-gemini/bin/python
```

Set these values in `.env`:

```bash
GEMINI_AGENT_MODE=gemini
GEMINI_DATASET_PROFILE=demo
GEMINI_DEMO_AGENT_ID=antigravity-preview-05-2026
```

The demo bake writes `demo-dataset-manifest.json` with a real Gemini
`environment_id`. Backend run requests then call `client.interactions.create`
against Gemini using that demo environment, and the Insight Engine ranks the
structured JSON returned by the managed agent.

### Bake for Gemini Remote Agents

To run analyses in Gemini's remote sandboxes (instead of local DuckDB):

```bash
scripts/run_bake_gemini_environment.sh
```

This uploads the dataset into a Gemini environment, verifies integrity, and updates `dataset-manifest.json` with the remote `environment_id`.

---

## API Reference

### Quantitative Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/catalog` | GET | List all 13 groups and 87 analyses |
| `/api/runs` | POST | Start an analysis or group run |
| `/api/runs/{id}` | GET | Get run status and results |
| `/api/runs/{id}/stream` | GET | SSE stream of live execution steps |
| `/api/insights` | GET | Prioritized insight feed (bandit-ranked) |
| `/api/insights/{id}/feedback` | POST | Submit feedback (useful / not important / acted on) |
| `/api/kpis` | GET/POST | List or define monitored KPIs |

### Qualitative Research

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/research/playbooks` | GET | List available research playbooks |
| `/api/research/jobs` | POST | Submit a new research job (returns plan) |
| `/api/research/jobs/{id}/refine` | POST | Refine the research plan |
| `/api/research/jobs/{id}/approve` | POST | Approve plan and execute research |
| `/api/research/jobs/{id}/report` | GET | Get the full cited research report |
| `/api/research/jobs/{id}/stream` | GET | SSE stream of research progress |
| `/api/research/jobs/{id}/followup` | POST | Ask follow-up questions on a report |
| `/api/insights/{id}/research-why` | POST | Trigger qualitative research from a quantitative insight |
| `/api/research/corpora` | GET/POST | Manage internal qualitative data corpora |
| `/api/research/schedules` | GET/POST | Schedule recurring research tasks |

### Admin & Reinforcement Learning

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/status` | GET | Active policy, weights, parity score |
| `/api/admin/refit` | POST | Trigger policy weight refit from feedback |
| `/api/admin/thresholds` | GET | Per-skill surfacing thresholds |
| `/api/admin/thresholds/auto-adjust` | POST | Auto-tune thresholds from feedback stats |
| `/api/admin/reviews` | GET | Methodology disagreements awaiting review |

---

## Key Design Decisions

1. **13 focused agents vs. one mega-agent** — each group agent loads only its own skills, keeping context lean and reducing hallucination. Skills are scoped per group via `system_instruction`.

2. **Insight Engine over raw reports** — agents produce findings; the engine decides what deserves attention. This prevents feed noise and ensures PMs see a prioritized stream, not a dump.

3. **Collaborative planning for research** — Deep Research tasks cost $1–7 each. Returning a plan first lets the PM gate spend and improve research direction before execution.

4. **Structured extraction bridge** — Deep Research cannot emit structured output, so a follow-up call with a standard model converts reports into Insight objects for the feed.

5. **Dual execution modes** — `local` mode uses DuckDB for development without API costs; `gemini` mode runs real agents in remote sandboxes for production.

6. **Reinforcement learning for ranking** — rather than static weights, a contextual bandit learns from PM feedback which insight types matter most to each team, with governance constraints preventing suppression of valid negative findings.

---

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python, FastAPI, SQLAlchemy, SQLite |
| AI/ML | Gemini Managed Agents, Gemini Deep Research, Interactions API |
| Analytics | DuckDB, pandas, numpy, statsmodels, scikit-learn, lifelines |
| Data | Apache Parquet (Snappy), PyArrow, date-partitioned event streams |
| Frontend | HTML/JS dashboard with SSE for live streaming |
| Testing | pytest |

---

## Further Reading

- [Gemini Managed Agents Overview](https://ai.google.dev/gemini-api/docs/agents)
- [Gemini Deep Research Agent](https://ai.google.dev/gemini-api/docs/interactions/deep-research)
- [Gemini Interactions API](https://ai.google.dev/gemini-api/docs/interactions)
- [`automated-product-analyst-spec.md`](automated-product-analyst-spec.md) — full quantitative analyst product spec
- [`product-user-research-spec.md`](product-user-research-spec.md) — qualitative research feature spec
