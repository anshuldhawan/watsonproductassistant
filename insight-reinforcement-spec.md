# Spec — Insight Reinforcement Loop

> **Status:** Draft v0.1 — for review
> **Scope:** The closed-loop learning system that improves insight prioritization as
> insights are generated and feedback accumulates.
> **Companion docs:** product vision (`automated-product-analyst-spec.md`, esp. §9
> Insight Engine), build spec (`spotify-analyst-build-spec-v0.2.md`).
> **Last updated:** 2026-05-23

---

## 1. Purpose and interpretation

The Automated Product Analyst generates a stream of insights. Not all of them deserve
equal attention, and which ones matter differs by team and changes over time. The
**Insight Reinforcement Loop** is the learning system that, *as insights are generated*,
decides how to rank and surface them — and continuously improves that decision from user
feedback.

"Reinforcement" here means a feedback-driven policy that is rewarded for surfacing
insights users find genuinely valuable and penalized for noise. It is implemented as a
**contextual bandit**, not full deep RL — see §6.3 for why.

**This spec replaces the fixed attention-score weighting in product spec §9.2** with a
learned policy. The fixed weights become the cold-start prior.

---

## 2. The non-negotiable principle: validity ≠ relevance

A reinforcement loop optimized purely on "did the user like this insight" will, given
enough data, learn to **suppress unwelcome-but-true findings** — declining retention,
rising churn, a failing feature — because bad news gets marked "not useful." That is the
single worst failure mode for an automated analyst, and the architecture is built to
make it impossible.

The loop is split into two strictly separated concerns:

| Concern | Owned by | Learnable? |
|---|---|---|
| **Validity** — is this finding statistically real, correctly computed, material in magnitude? | The skill + the **validity floor** (§10.1) | **No.** Never tunable downward by feedback. |
| **Relevance / priority** — given a set of valid findings, which deserve attention first, for this team, now? | The reinforcement loop | Yes. |

The loop only ever **reorders and personalizes within the space of valid insights**. It
can never decide a valid, material finding goes unsurfaced. Truth is not a reward
dimension.

---

## 3. Where it sits

```
 agents generate          ┌────────── Insight Reinforcement Loop ──────────┐
 raw insights ──► Insight  │  validity floor ─► ranking policy (bandit) ─►  │ ──► Feed
                  objects  │        ▲                    │                 │
                           │        │  reward            │ surfaced w/      │
                           │   reward shaping ◄───────────┼─ logged          │
                           │        ▲                    │  propensity      │
                           └────────┼────────────────────┼─────────────────┘
                                    │  feedback events    │
                              user reactions ◄────────────┘  (feed UI)
```

It consumes Insight objects (product spec §9.1), produces the ordered feed, and learns
from feedback events the feed UI emits.

---

## 4. The loop lifecycle

1. **Generate** — agents emit Insight objects from a run.
2. **Floor** — each insight is checked against the validity floor (§10.1). Floor-passers
   are *guaranteed* a place in the feed.
3. **Score** — the ranking policy produces a value estimate per candidate insight.
4. **Rank & surface** — insights are ordered; an exploration slot (§8) is mixed in;
   the **propensity** (probability this insight was shown at this rank) is logged.
5. **Observe** — user reactions (explicit and implicit, §5) are captured as feedback
   events.
6. **Reward** — feedback is converted to calibrated reward signals (§5.3).
7. **Update** — the policy updates: incrementally per feedback event, and in periodic
   batch refits (§14).
8. **Audit** — safety audits (§10) run on every batch cycle.

Steps 1–4 are inline (sub-second per feed render). Steps 6–8 run continuously and in
batch.

---

## 5. Feedback and reward signals

### 5.1 Explicit feedback taxonomy

The single "useful / not useful" control is too coarse — "not useful" conflates four
very different things. The feed UI must offer a granular taxonomy:

| Signal | Meaning |
|---|---|
| **Acted on it** | The insight changed a decision or triggered follow-up work. |
| **Useful** | Valuable, even if no action yet. |
| **Already knew this** | Correct and material, but not new to this team. |
| **Not actionable** | True and notable, but the team can't act on it. |
| **Not important** | True, but below this team's attention bar. |
| **Wrong / I disagree** | The user believes the finding is incorrect. |

The last two rows of "not useful" and especially **Wrong / I disagree** are routed
differently — see §5.4.

### 5.2 Implicit signals

Explicit feedback is sparse. The loop also uses implicit signals, weighted lower:
opened/expanded an insight (+), viewed an artifact (+), surfaced-but-never-opened (−),
dwell time. Implicit signals carry a confidence weight below explicit ones and never
trigger large policy moves alone.

### 5.3 Reward shaping

Feedback maps to a scalar reward for the ranking policy, plus, for some signals, a
**targeted** update to a specific feature sub-model rather than the global reward:

| Signal | Ranking reward | Targeted update |
|---|---|---|
| Acted on it | **+1.0** | — (the gold signal) |
| Useful | +0.6 | — |
| Opened/expanded (implicit) | +0.15 | — |
| Already knew this | **~0** | strong negative to the **novelty** feature for this pattern/team |
| Not actionable | −0.3 | negative to the **actionability** feature |
| Not important | −0.5 | informs the **threshold controller** (§7, L2) |
| Dismissed, no rating | −0.3 | — |
| Surfaced, ignored (implicit) | −0.1 | — |
| Wrong / I disagree | **withheld** | routed to methodology review (§5.4) |

"Already knew this" is the key non-obvious case: the insight was *good*, so it must not
be punished as if it were noise — it just lacked novelty *for this team*. Decomposing
the reward prevents the loop from learning "correct findings are bad."

### 5.4 The "Wrong / I disagree" path

This signal does **not** feed the reward at all. It routes the insight to a
**methodology review queue**: it may indicate a genuine bug — a bad metric definition, a
data-quality issue, a flawed skill. Letting it silently down-weight a skill would hide
real defects. A cluster of "wrong" feedback on one skill pauses that skill pending
review. Disagreement is a QA signal, not a popularity signal.

---

## 6. The learning formulation

### 6.1 Contextual bandit

Each surfaced insight is a decision under context. The loop learns a value function
`V(insight, context)` — this *is* the attention score, now learned rather than
hand-weighted.

**Context features** per insight: magnitude (normalized), statistical confidence,
group, skill, metric type, direction/valence, segment size, novelty score,
actionability score, recency; plus team and time-of-cycle features.

**Policy:** Bayesian linear model with **Thompson Sampling** — sample a weight vector
from the posterior, score candidates, rank. Thompson Sampling gives principled
exploration for free and is robust and cheap to update online.

**Reward:** as shaped in §5.3, observed only for insights actually surfaced (with logged
propensity for off-policy evaluation, §13).

### 6.2 What it produces

A ranked feed. Floor-passing insights (§10.1) are always included; the policy orders
them and decides which sub-floor-but-valid candidates also make the cut. The policy
output is combined with the validity floor and the diversity guard (§10.4) — it is not
the sole gatekeeper.

### 6.3 Why a bandit, not deep RL

Most of the problem is a one-step decision: surface this insight, get feedback. There is
no long action-sequence requiring credit assignment, so full RL adds instability and
sample-inefficiency for no gain. The one genuinely delayed signal — "acted on it" and
downstream KPI movement — is handled as a delayed reward attached to the same bandit
arm (§11), not as a separate RL horizon. If multi-step insight *campaigns* are added
later, revisit.

---

## 7. Three control loops

The reinforcement system is three loops at different timescales, not one:

**L1 — Insight ranking (the bandit).** Inline scoring; incremental posterior update on
every feedback event. Fast. §6.

**L2 — Per-skill noteworthiness thresholds.** Each `SKILL.md` defines a bar for "what
counts as a noteworthy finding." A slow controller adjusts each skill's bar from
aggregate feedback: a skill whose insights are consistently "not important" gets its bar
**raised**; a skill whose insights are consistently acted on may get its bar lowered —
**but never below the validity floor** (§10.1). Runs weekly. Bounded step size.

**L3 — Skill-selection priors.** In group runs and scheduling, which analyses to
prioritize. Skills that have produced high-reward insights for a team get run earlier /
more often. Purely a prioritization prior — it never disables a skill the user explicitly
selects.

---

## 8. Exploration

A pure exploit policy collapses onto a narrow band of insight types and stops learning
(and stops surprising the PM — which is half the product's value). The loop reserves an
**exploration budget**: a fixed fraction of feed slots (default ~15%) for insights the
current policy would rank lower. Thompson Sampling supplies exploration naturally;
the explicit budget guarantees a floor on it. Exploration insights still must pass
validity and are clearly the same as any other insight to the user — exploration is
about *what gets attention*, never about surfacing something unvetted.

---

## 9. Personalization hierarchy

Preferences differ by team; a single global policy is wrong, but a per-team policy
starves on sparse data. Use **partial pooling** (hierarchical Bayes):

```
global policy  ──prior──►  team policy  ──prior──►  (optional) user policy
```

A new or low-data team inherits the global policy and adapts as its feedback
accumulates; a high-data team diverges as far as its evidence supports. Teams are
isolated — one team's feedback never directly moves another team's ranking, only the
shared global prior.

---

## 10. Guardrails and safety

### 10.1 Validity floor (hard, non-learnable)
An insight passes the floor if `confidence ≥ τ_conf` **and** `|magnitude| ≥ τ_mag`
**and** data-quality checks pass. Floor-passers are **always** in the feed. The bandit
orders them; it can never bury one. `τ_conf`, `τ_mag` are governance-set constants, not
learned parameters.

### 10.2 Truth is not a reward dimension
Covered in §2 and §5.4. "Wrong" feedback routes to QA, never to reward.

### 10.3 Bad-news / anti-sycophancy audit
Every batch cycle, audit the policy for **valence bias**: is it systematically
down-ranking negative-direction insights (declines, churn, regressions) relative to
positive ones of equal validity and magnitude? Measure surfacing parity across insight
valence. A detected skew raises an alert and applies a counter-correction. An analyst
that learns to soft-pedal bad news has failed, regardless of feedback metrics.

### 10.4 Diversity / filter-bubble guard
Enforce minimum feed coverage across analysis groups and metric types so the feed cannot
collapse onto whatever one team clicks most. The policy optimizes ranking *within* a
diversity-constrained slate.

### 10.5 Feedback robustness
Down-weight low-volume and implicit-only feedback; require a minimum support count
before any large policy or threshold move; cap per-cycle step size. Detect and discount
anomalous feedback bursts (one user mass-rating).

### 10.6 Reversibility
Every deployed policy and threshold set is versioned (§14); any update can be rolled
back. No update is irreversible.

---

## 11. Delayed rewards and credit assignment

"Acted on it" and downstream KPI movement arrive days after an insight is surfaced. They
are attributed back to the originating insight via its `insight_id` and a time-decayed
credit window (default 30 days). Delayed positive reward reinforces the same bandit arm.
Because attribution weakens over time, delayed signals carry a decay weight and are
treated as confirmatory, not primary. If a metric an insight flagged later moves in the
predicted direction after a logged action, that is the strongest available reward.

---

## 12. Cold start

- **Ranking policy** — initialized to the fixed attention-score weights from product
  spec §9.2 as the Bayesian prior. The loop behaves sensibly from day one and improves.
- **Thresholds** — start at each `SKILL.md`'s authored defaults.
- **Exploration** — exploration fraction is set higher early (e.g. 30%) and annealed to
  the steady-state ~15% as evidence accumulates.
- A team with no history runs entirely on the global policy until it has enough feedback
  to justify divergence (§9).

---

## 13. Evaluation

- **Offline replay / off-policy evaluation (OPE)** — because surfacing propensities are
  logged, candidate policies are evaluated with inverse-propensity-scoring / doubly-robust
  estimators on historical feedback *before* deployment. No policy ships without OPE.
- **Online A/B / interleaving** — new policy vs incumbent on live feeds.
- **Headline metrics:** feed precision@k (% of surfaced insights marked useful or acted
  on), action rate, "already knew" rate (should fall over time), coverage/diversity,
  **valence-surfacing parity** (§10.3), and exploration regret.
- A policy that improves precision@k while *failing* the valence-parity audit is
  **rejected** — it has learned to flatter, not to inform.

---

## 14. Update cadence and versioning

| Loop | Cadence |
|---|---|
| L1 posterior update | Incremental, per feedback event. |
| L1 full refit | Daily batch. |
| L2 threshold controller | Weekly. |
| L3 skill-selection priors | Weekly. |
| Safety audits (§10.3–10.5) | Every batch cycle. |

Every batch produces a versioned `PolicyVersion` (and threshold set). Each is OPE-graded
and audit-checked before promotion; the prior version is retained for rollback.

---

## 15. Data model

- **FeedbackEvent** — `insight_id`, user, team, signal type, explicit/implicit, timestamp.
- **SurfacingRecord** — `insight_id`, feed position, logged propensity, policy version,
  whether it was an exploration slot.
- **RewardRecord** — `insight_id`, shaped reward, targeted-update components, delayed-
  reward additions, credit-window state.
- **PolicyVersion** — model parameters, prior, training window, OPE scores, audit
  results, status (candidate / live / rolled-back).
- **ThresholdState** — per skill, current bar, history, last controller move.
- **BanditState** — per team, posterior parameters.

---

## 16. Open questions

| ID | Item |
|---|---|
| R-1 | Granularity of personalization — team-level only for v1, or per-user too? Per-user worsens sparsity; team-level is the safer default. |
| R-2 | Exact reward scalars in §5.3 — defaults proposed; calibrate from the first weeks of feedback. |
| R-3 | Delayed-reward attribution — how is "acted on it" actually captured (manual tag, integration with an experiment/issue tracker)? Determines how reliable the gold signal is. |
| R-4 | Validity-floor constants `τ_conf`, `τ_mag` — set per metric type or global? Likely per metric type. |
| R-5 | Cold-start period length before a team is allowed to diverge from the global policy. |
| R-6 | Should a learned reward model (predicting reward from features) replace direct reward shaping in v2, to densify sparse feedback? |

---

## Appendix A — Ranking update (pseudocode)

```python
# Inline: score and rank candidates for a feed render
def rank_feed(candidates, team, policy):
    theta = policy.sample_weights(team)          # Thompson Sampling draw
    scored = []
    for ins in candidates:
        x = features(ins, team)
        value = dot(theta, x)
        scored.append((ins, value, x))

    floor_pass = [s for s in scored if passes_validity_floor(s[0])]
    others     = [s for s in scored if s not in floor_pass]

    feed = diversity_constrained_rank(floor_pass + others)   # §10.4
    feed = inject_exploration(feed, budget=0.15)             # §8
    for rank, (ins, value, x) in enumerate(feed):
        log_surfacing(ins.id, rank, propensity_of(ins, feed), policy.version)
    return feed

# On feedback: update posterior
def on_feedback(event, policy):
    if event.signal == "wrong_disagree":
        route_to_methodology_review(event.insight_id)        # §5.4 — no reward
        return
    r = shaped_reward(event)                                 # §5.3
    x = features_of(event.insight_id)
    policy.bayesian_update(team_of(event), x, r)             # incremental
    apply_targeted_updates(event)                            # novelty / actionability
```

## Appendix B — Reward reference

| Signal | Ranking reward | Routed to |
|---|---|---|
| Acted on it | +1.0 | + delayed-reward credit window |
| Useful | +0.6 | — |
| Opened / expanded | +0.15 | — |
| Already knew this | ~0 | novelty sub-model (strong −) |
| Not actionable | −0.3 | actionability sub-model |
| Not important | −0.5 | L2 threshold controller |
| Dismissed | −0.3 | — |
| Ignored (implicit) | −0.1 | — |
| Wrong / I disagree | none | methodology review queue |
