# Build Spec — Automated Product Analyst on the Spotify Dataset

> **Status:** Draft v0.2 — updated after M0 completion
> **Scope:** Implementation build of an automated product analyst against the now-verified
> Spotify sample dataset, using Gemini Managed Agents.
> **Change in v0.2:** M0 (data loading) is complete. The dataset schema, layout, dates,
> and row counts are now **confirmed** — no longer assumed. Skills, metric definitions,
> and scope are revised to the real data.
> **Companion docs:** product vision (`automated-product-analyst-spec.md`),
> data-loading task (`spotify-data-loading-spec.md`).
> **Last updated:** 2026-05-23

---

## 1. Status and scope

**M0 — Data loading: COMPLETE.** The Spotify sample dataset is generated and verified;
all 8 validation checks (V1–V8) passed. `dataset-manifest.json` and `canonical-schema.md`
are produced. The dataset is verified at `dataset_version: spotify-v1`,
`schema_hash: d7a16100…28de1`.

**One pending bridge step (M0.5):** the dataset currently exists from a *local* script;
the manifest's `environment_id` is the placeholder `local-baked-env`. Before any agent
can run, the dataset must be baked into a real Gemini base environment (§3.2). Agent
creation must reject any non-baked environment id.

**In scope for this build:** M0.5 remote bake, 5 group agents and their skills,
single-analysis and group-run execution, the insight output contract, lightweight KPI
monitoring.

**Out of scope** — see §11. The dataset has no transaction, review, funnel-event, or
referral data, so the Monetization, Feedback, Funnel, and Social catalog groups cannot
run on it.

---

## 2. Dataset — CONFIRMED

### 2.1 Layout and sizes

The generator's actual layout (the spec defers to the generator — `date=` not `dt=`,
dimensions under `catalog/`):

```
data/
  play_events/
    date=2026-05-01/  *.parquet     ┐
    date=2026-05-02/  *.parquet     │  30 contiguous day-partitions
    ...                             │  6,619,263 rows, ~89.20 MB
    date=2026-05-30/  *.parquet     ┘  ~220k plays/day
  catalog/
    users.parquet            10,000 rows
    tracks.parquet           20,000 rows
    playlist_tracks.parquet  27,357 rows  (500 unique playlists)
    albums.parquet            2,000 rows
    artists.parquet           1,000 rows
```

Date range: **2026-05-01 to 2026-05-30**, fixed calendar dates. Total ~90 MB.

`playlist_tracks` is a junction table — 27,357 (playlist, track) mappings across **500**
playlists (~55 tracks/playlist). There is no standalone `playlists` dimension file;
playlist identity lives only in this mapping.

### 2.2 Canonical schema

`canonical-schema.md` is the authoritative reference for exact PyArrow field names and
dtypes. Summary of the documented fields:

**`play_events`** (fact table, partitioned by `date`)
| Field | Notes |
|---|---|
| event timestamp | play completion time |
| `user_id` | FK → users |
| `track_id` | FK → tracks |
| `platform` | mobile / desktop / web |
| `shuffle` | boolean |
| reason indicators | how the play started and ended (e.g. `trackdone`, `fwdbtn`) |
| skip label(s) | whether/how the track was skipped |

> Note: `play_events` carries **no `ms_played`** field. Completion and skip are derived
> from the reason indicators and skip label(s), not from a played-duration field. This
> changes the metric definitions in §6.1.

**`users`** (dimension) — `user_id`, age, gender, country, sign-up info,
`subscription_tier` (free / premium), and a **baseline activity probability index**
(see §2.4).

**`tracks`** (dimension) — `track_id`, title, `album_id`, `artist_id`, popularity index,
playback duration in **seconds**.

**`albums`** (dimension) — `album_id`, title, **release year** (year granularity, not a
full date), `artist_id`.

**`artists`** (dimension) — `artist_id`, name, popularity score, primary genre.

**`playlist_tracks`** (mapping) — `playlist_id`, `track_id`.

Referential integrity is verified (V5): all FK relationships resolve, key columns have
zero nulls (V6).

### 2.3 Time coverage and consequences

30 days. D1 / D7 / D14 / D30 retention are computable; **D60 / D90 are not**. About 4
weekly cohorts fit. Album recency is only available at **year** granularity, so
new-release velocity analysis is coarse (§5, `content-analyst`).

### 2.4 Generator ground-truth field — handling rule

`users` carries a **baseline activity probability index** — a synthetic field the
generator uses to drive how active each simulated user is. This is *generative ground
truth*, not a field a real streaming product would have.

**Rule (enforced in `AGENTS.md`):** skills must **never** use this field as an input
feature for any analysis or model — doing so is leakage and would not generalize to real
data. It is, however, valuable as a **validation target**: `churn-propensity-scoring`
and `user-fatigue-modeling` can be checked for whether their behavior-derived scores
correlate with this index. Use it to grade the analyst, never to feed it.

---

## 3. Data delivery — baked base environment

**Decision (unchanged):** the dataset is baked into one base environment; every
interaction forks it, so `data/` is on disk instantly — deterministic, zero per-run cost.

### 3.1 What is done

The dataset is generated and verified locally. `dataset-manifest.json` records version,
seed (42), date range, row counts, and schema hash. `environment_id` is the placeholder
`local-baked-env` with — per the manifest convention — an implied non-baked status.

### 3.2 M0.5 — bake to a remote environment (pending, blocks M1)

The data exists only locally; the durable source of truth is the generator + seed
(seed 42). To produce a real Gemini environment:

1. **Push the generator** (`scripts/generate_data.py`) to a Git repo so it is reachable
   and version-pinned (replaces `generator_repo: local-script` / `generator_sha: local`).
2. **Seed run** — one `interactions.create` that clones the generator, runs it with
   seed 42, and writes `data/` with the §2.1 layout. Capture `interaction.environment_id`.
3. **Re-verify** in the baked environment with `scripts/verify_data.py` (V1–V8). Confirm
   the `schema_hash` matches `d7a16100…28de1` — proof the remote bake is identical.
4. **Update the manifest** — real `environment_id`, real `generator_sha`,
   `environment_status: baked`.

```python
seed = client.interactions.create(
    agent="antigravity-preview-05-2026",
    input="Clone <generator-repo>, run scripts/generate_data.py with seed 42 to write "
          "the dataset into data/ (play_events/date=*, catalog/*.parquet), then run "
          "scripts/verify_data.py and print the report.",
    environment="remote",
)
BAKED_ENV = seed.environment_id          # replaces local-baked-env
```

**Guard:** the agent-creation step must reject any `environment_id` starting with
`local-` or whose `environment_status` is not `baked`. This turns "forgot to bake" into
an early, clear error.

**Alternative:** upload the verified parquet to GCS and pass `gs://…` in
`base_environment.sources`. Equivalent; default to the seed-run path so the dataset
stays reproducible from source.

---

## 4. Agent and skill architecture

One skills repo; one group agent per in-scope group; all point at `BAKED_ENV`.

```python
agent = client.agents.create(
    id="engagement-analyst",
    base_agent="antigravity-preview-05-2026",
    system_instruction=ENGAGEMENT_SYSTEM_PROMPT,
    base_environment=BAKED_ENV,                # data already on disk
)
```

The base agent auto-loads `.agents/AGENTS.md` (shared house style + metric definitions)
and every `SKILL.md` under `.agents/skills/`. The `system_instruction` scopes each agent
to its own group's skills.

**In-scope group agents:**

| Agent ID | Group | Fit |
|---|---|---|
| `engagement-analyst` | Engagement & Usage | Rich play stream — the dataset's strength |
| `retention-analyst` | Retention & Churn | 30-day window supports D1–D30 |
| `content-analyst` | Content & Catalog | Tracks / artists / genres / playlists |
| `segmentation-analyst` | Segmentation & Personas | Behavioral data + demographics + tier |
| `predictive-analyst` | Predictive & Monitoring | Anomaly detection, churn propensity |

---

## 5. Skill catalog for this build

Each skill is one `SKILL.md`. **(adapted)** = catalog analysis tailored to music
streaming; **(new)** = music-specific addition. Notes reflect the confirmed schema.

### `engagement-analyst`
| Skill | Notes |
|---|---|
| `dau-wau-mau-stickiness` | Active user = ≥1 play event/day (no `ms_played` — see §6.1). |
| `session-frequency-duration-depth` | Sessionize by 30-min inactivity gap; depth = plays/session. |
| `time-of-day-day-of-week-usage` | Listening-hour and weekday heatmaps. |
| `platform-usage-split` (adapted) | mobile / desktop / web. |
| `skip-rate-completion-analysis` (new) | Core music metric — derived from reason/skip fields; `shuffle` as a split dimension. |
| `power-vs-casual-listener-segmentation` (adapted) | Play-volume tiers. |

### `retention-analyst`
| Skill | Notes |
|---|---|
| `cohort-retention-curves` | D1/D7/D14/D30. Cohort = signup-week **if** signups span the window, else first-seen-in-window (O-1). |
| `n-day-activity-curves` | |
| `rolling-vs-classic-retention` | |
| `magic-number-analysis` | Which week-1 behavior predicts week-4 retention. |
| `churn-risk-flagging` (adapted) | Activity-decay flag; short-window caveat. |

### `content-analyst`
| Skill | Notes |
|---|---|
| `genre-artist-consumption` | Listening share by genre (from `artists`) and artist. |
| `track-popularity-distribution` | Long-tail / whale curve; popularity index vs actual plays. |
| `catalog-coverage-gap-analysis` (adapted) | % of 20k tracks ever played; dead catalog. |
| `playlist-catalog-influence` (adapted) | **Correlational only** — `play_events` has no playlist-context field, so this compares play volume of in-playlist vs non-playlist tracks rather than attributing plays to playlists. |
| `catalog-age-consumption-mix` (adapted) | Listening split by album `release_year` (year granularity — replaces fine-grained new-release velocity). |

### `segmentation-analyst`
| Skill | Notes |
|---|---|
| `behavioral-clustering` | k-means on play-behavior features. |
| `rfm-segmentation` | Recency / frequency / play-volume (no monetary — §11). |
| `lifecycle-stage-segmentation` | new / active / at-risk / dormant. |
| `high-value-listener-profiling` (adapted) | Power-listener profiles. |
| `demographic-engagement-crosstab` (new) | Engagement by age / gender / country / `subscription_tier`. |

### `predictive-analyst`
| Skill | Notes |
|---|---|
| `anomaly-detection-kpi` | Powers KPI monitoring (§8). |
| `churn-propensity-scoring` | Short-window caveat; behavior-derived only. May be **validated** against the §2.4 ground-truth index, never trained on it. |
| `user-fatigue-modeling` | Rising skip rate / falling session length over the window. |

**~24 skills** for v1.

---

## 6. Skill format

### 6.1 Shared `AGENTS.md` — metric definitions (revised for the confirmed schema)

Loaded by every agent. Enforces: emit structured Insight objects; compute every number
via code execution, never assert numbers from reasoning; state the statistical test and
confidence; respect each skill's noteworthiness bar; save charts as files; flag
data-quality problems. **Forbids using the §2.4 baseline-activity index as a feature.**
Canonical definitions:

- **Active user (day)** — ≥1 play event on that day. (There is no `ms_played`; the old
  "≥30s played" definition does not apply.)
- **Engaged-active user (day)** — ≥1 *completed, non-skipped* play that day. Used where a
  quality bar matters.
- **Session** — plays grouped by ≤30-min inactivity gaps on the event timestamp; session
  *depth* = plays per session, session *duration* = span between first and last play.
- **Completed play** — reason-end indicates a natural finish and the skip label is false.
  Confirm the exact reason-end vocabulary against `canonical-schema.md` (O-2).
- **Skipped play** — skip label true (or a skip reason-end).
- **Skip rate** — skipped plays ÷ total plays.

### 6.2 Worked example — `SKILL.md`

```markdown
# Skill: Skip-Rate & Completion Analysis

## When to use
The user wants skip rate and completion rate, optionally split by a segment.

## Required inputs
- data/play_events/date=*   (date range; default: all 30 days)
- data/catalog/users.parquet, tracks.parquet  (optional splits)

## Method
1. Classify each play as completed / skipped using the reason and skip fields
   (see AGENTS.md definitions).
2. Compute overall skip rate and completion rate; trend by day.
3. If requested, split by platform, shuffle, subscription_tier, or genre.
4. Chart skip-rate trend and the segment comparison.

## What counts as a noteworthy finding
- Overall skip rate above 0.55, or up >0.05 vs the first week.
- A segment whose skip rate deviates >2 sigma from the population.

## Output contract
Emit Insight object(s) per the schema, plus skip_rate_trend.png and
skip_rate_by_segment.csv.
```

---

## 7. Insight output contract

Skills emit findings as structured JSON (Gemini structured outputs), per the Insight
schema in the product spec §9.1. For this build `business_impact` is **omitted** — there
is no revenue data — so feed ranking uses magnitude, confidence, and novelty only. The
Insight Engine (scoring, dedupe, ranking) behaves as in the product spec; this build
feeds it.

---

## 8. Execution model

**Single analysis** — one `interactions.create` on the group agent,
`environment=BAKED_ENV`, `input` = run one skill with the given config. `stream=true`
for the live run view. No data-load step — data is already baked.

**Group run** — because the data is baked in, there is no data-load step; just fan out:

```python
for skill in ENGAGEMENT_SKILLS:
    client.interactions.create(
        agent="engagement-analyst",
        environment=BAKED_ENV,        # forks the baked dataset, clean each time
        input=f"Run skill `{skill}` for the full 30-day window.",
    )
```

Bounded concurrency (default 4). Collect Insight objects → Insight Engine → consolidated
group briefing. A failed skill is excluded and noted; the run does not fail wholesale.

**KPI monitoring** — `anomaly-detection-kpi` checks headline KPIs (DAU, plays-per-DAU,
completion rate, skip rate, WAU) against a baseline window. On a static 30-day dataset
this runs once, or on a simulated moving "as-of date" cursor; it emits alert Insight
objects only on breach.

---

## 9. Acceptance criteria

| ID | Criterion |
|---|---|
| AC-0 | **(M0 — met)** All 8 verification checks pass; manifest and canonical schema produced. |
| AC-1 | **(M0.5)** Remote seed run produces `BAKED_ENV`; re-verification yields `schema_hash = d7a16100…28de1`; manifest updated to `environment_status: baked`. |
| AC-2 | Agent creation rejects any non-baked / `local-` environment id. |
| AC-3 | A single-analysis run (`skip-rate-completion-analysis`) completes < 2 min and returns ≥1 valid Insight object plus named artifacts. |
| AC-4 | An `engagement-analyst` group run fans out across all its skills, aggregates, and produces a consolidated briefing. |
| AC-5 | **Determinism** — the same analysis run twice on `BAKED_ENV` returns identical numbers. |
| AC-6 | **Ground truth** — agent-reported DAU/WAU/MAU exactly matches an independent pandas/PyArrow computation on the same parquet (zero tolerance). |
| AC-7 | Every run persists its `interaction_id`(s) and `steps` for audit. |
| AC-8 | A skill whose noteworthiness bar is not met produces no surfaced insight. |

---

## 10. Build milestones

| Milestone | Status | Deliverable |
|---|---|---|
| **M0 — Data baked & verified** | **Done** | Generated dataset; V1–V8 pass; `dataset-manifest.json`, `canonical-schema.md`. |
| **M0.5 — Remote bake** | Next | Generator in a repo; seed run; `BAKED_ENV`; re-verified; manifest `status: baked`. |
| **M1 — One agent end to end** | | `engagement-analyst` + skills; single-analysis mode; insight output (AC-3, AC-6). |
| **M2 — Group runs** | | Fan-out + aggregation; consolidated briefing (AC-4). |
| **M3 — All five agents** | | `retention`, `content`, `segmentation`, `predictive` agents + skills. |
| **M4 — Insight Engine + monitoring** | | Scoring/dedupe/feed; `anomaly-detection-kpi` (AC-8). |

---

## 11. Out of scope (and why)

| Catalog group | Status | Reason |
|---|---|---|
| Monetization & Revenue | **Out** | No transaction, price, or subscription-event data. `subscription_tier` is usable only as a segment dimension, never for revenue analysis. |
| Acquisition & Onboarding | **Partial** | Signup-cohort retention/activation is possible (`users` has sign-up info). Channel attribution is **out** — no acquisition-channel field. |
| Funnel & Conversion | **Out** | The play stream has no funnel / micro-conversion events. |
| Feedback & Sentiment | **Out** | No reviews, NPS, or survey data. |
| Social & Viral | **Out** | No referral, sharing, or social-graph data. |
| A/B Testing & Experimentation | **Out** | No experiment-assignment data. |
| Behavioral Economics | **Out** | Needs pricing / offer-exposure data. |

Adding any of these is a dataset extension, not an agent-design change — the agents and
skills exist in the product-spec catalog and switch on when the data is added.

---

## 12. Open questions

| ID | Item | Status |
|---|---|---|
| O-1 | Do `users` sign-up dates span the window, or are all 10,000 present from day 1? Determines whether retention cohorts are signup-based or first-seen-based. | **Open** — quick query on `users.signup_date`. |
| O-2 | Exact reason-end vocabulary (which values mean "natural finish" vs "skip"). Needed to finalize the completion definition in `AGENTS.md`. | **Open** — read from `canonical-schema.md` / sample `play_events`. |
| O-3 | KPI monitoring on a static dataset — run once, or simulate a moving "as-of date" cursor for a more realistic demo? | **Open** — product call. |
| O-4 | Environment durability — how long does a baked Gemini environment persist before expiry? Determines re-bake frequency. | **Open.** |
| ~~O-5~~ | ~~Schema confirmation~~ | **Resolved** — `canonical-schema.md`, `schema_hash d7a16100…28de1`. |
| ~~O-6~~ | ~~Standalone playlists dimension~~ | **Resolved** — none; playlist identity lives in `playlist_tracks` (500 unique). |
| ~~O-7~~ | ~~Date range fixed vs relative~~ | **Resolved** — fixed calendar, 2026-05-01 to 2026-05-30. |

---

## Appendix A — Reference calls

```python
# M0.5 — remote bake
seed = client.interactions.create(
    agent="antigravity-preview-05-2026",
    input="Clone <generator-repo>, run scripts/generate_data.py with seed 42, then run "
          "scripts/verify_data.py and print the report.",
    environment="remote",
)
BAKED_ENV = seed.environment_id

# Create a group agent
agent = client.agents.create(
    id="engagement-analyst",
    base_agent="antigravity-preview-05-2026",
    system_instruction=ENGAGEMENT_SYSTEM_PROMPT,
    base_environment=BAKED_ENV,
)

# Run one analysis (streamed)
run = client.interactions.create(
    agent="engagement-analyst",
    environment=BAKED_ENV,
    input="Run skill `skip-rate-completion-analysis` for the full 30-day window, "
          "split by platform and subscription_tier. Emit Insight objects per the "
          "output contract.",
    stream=True,
)
```
