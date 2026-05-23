---
name: paywall-hit-rate-conversion
description: "Runs the Lighthouse Paywall Hit Rate & Conversion analysis for Funnel & Conversion. Use when the analyst is asked to run `paywall-hit-rate-conversion` or investigate examine how often free users hit paywall gates and the immediate upgrade success rate."
---

# Skill: Paywall Hit Rate & Conversion

## Identity

- Skill key: `paywall-hit-rate-conversion`
- Group: `funnel-conversion` (Funnel & Conversion)
- Owning agent: `funnel-analyst`
- Primary metric hint: `conversion_rate`

## When To Use

Use this skill when the user selects `paywall-hit-rate-conversion` or asks for: Examine how often free users hit paywall gates and the immediate upgrade success rate.

## Required Inputs

- ordered product events for the selected funnel.
- users catalog for segmentation.
- run configuration specifying date range, funnel window, and comparison baseline.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Define the ordered funnel steps and the qualifying population before measuring drop-off.
2. Deduplicate repeated events, preserve step order, and handle users who skip, repeat, or abandon a step.
3. Compute conversion, elapsed time, re-entry, and abandonment by segment and comparison window.
4. Identify the first step with material incremental loss rather than only reporting the final conversion delta.
5. Create a funnel chart or step table with counts, rates, deltas, and segment splits.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- A funnel step changes by at least 3 percentage points or accounts for at least 20% of incremental loss.
- The drop-off is concentrated in an actionable step, device, country, or cohort.
- Sample size is sufficient to avoid noisy step-level rates.

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
