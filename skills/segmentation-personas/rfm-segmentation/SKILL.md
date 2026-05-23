---
name: rfm-segmentation
description: "Runs the Lighthouse RFM Segment Profiling analysis for Segmentation & Personas. Use when the analyst is asked to run `rfm-segmentation` or investigate analyze user recency, frequency, and duration of sessions to build standard engagement classes."
---

# Skill: RFM Segment Profiling

## Identity

- Skill key: `rfm-segmentation`
- Group: `segmentation-personas` (Segmentation & Personas)
- Owning agent: `segmentation-analyst`
- Primary metric hint: `rfm_segmentation_index`

## When To Use

Use this skill when the user selects `rfm-segmentation` or asks for: Analyze user recency, frequency, and duration of sessions to build standard engagement classes.

## Required Inputs

- user-level activity, content, session, and monetization features.
- users catalog for stable demographic and subscription attributes.
- run configuration for segment filters and minimum segment size.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Build user-level features from recency, frequency, duration, content taste, monetization, and lifecycle behavior.
2. Normalize features, handle outliers, and document the features used for clustering or scoring.
3. Create interpretable segments with names derived from observed behavior, not stereotypes.
4. Validate segments by size, stability, and business relevance before surfacing recommendations.
5. Create a segment profile artifact showing top distinguishing features and KPI differences.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- A segment is stable, interpretable, and meaningfully different on at least two product KPIs.
- The segment is large enough to target or high-value enough to justify action.
- Recommended actions differ by segment and are not generic product advice.

## Guardrails

- Return [] when the evidence does not clear the noteworthiness bar.
- Do not invent tables, columns, events, or business impact. State data-quality blockers as findings only when they are actionable.
- Prefer segment-level explanations that a PM can act on over broad descriptive summaries.
- Use consistent metric definitions for active users, payers, retention, conversion, and revenue across skills.
- Save every chart or table artifact referenced in the Insight object.

## Output Contract

- Emit only valid JSON: either an array of Insight objects or an object with an `insights` array.
- Each Insight must include: title, summary, group, skill, metric, direction, magnitude {value, unit, relative}, confidence, stat_test, segment, business_impact {metric, estimate_usd, horizon}, recommended_actions, artifacts, and data_window {start, end}.
- Use the exact skill key and group key from this file.
- Use `direction` as one of: up, down, neutral.
- Use confidence in the range 0 to 1 and explain uncertainty through `stat_test`.

## Recommended Actions

- Tie each recommendation to the observed segment, metric movement, and expected business impact.
- Prefer product, growth, lifecycle, pricing, quality, or research actions that an owner can execute within one planning cycle.
- Avoid generic recommendations such as "monitor this metric" unless monitoring is the specific next best action.
