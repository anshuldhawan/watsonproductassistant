---
name: n-day-activity-curves
description: "Runs the Lighthouse N-Day Activity Curves analysis for Retention & Churn. Use when the analyst is asked to run `n-day-activity-curves` or investigate analyse the probability of a user staying active after exactly N days of continuous app usage."
---

# Skill: N-Day Activity Curves

## Identity

- Skill key: `n-day-activity-curves`
- Group: `retention-churn` (Retention & Churn)
- Owning agent: `retention-analyst`
- Primary metric hint: `n_day_activity_curves_index`

## When To Use

Use this skill when the user selects `n-day-activity-curves` or asks for: Analyse the probability of a user staying active after exactly N days of continuous app usage.

## Required Inputs

- users catalog with signup_date and segment attributes.
- play or app-open events that qualify a user as active.
- run configuration for cohort grain, retention horizon, and segment filters.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Assign users to cohorts using the configured cohort definition, defaulting to signup date.
2. Compute classic and rolling retention where relevant, plus churn, resurrection, and survival curves when requested.
3. Segment by acquisition channel, country, platform, subscription tier, genre affinity, and lifecycle stage when supported.
4. Compare cohorts against historical cohort baselines and flag statistically meaningful decay or recovery.
5. Create retention curves, cohort tables, or survival plots with enough context for a PM to inspect the movement.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- Retention or churn movement exceeds 3 percentage points or 1.5 standard deviations from baseline.
- A cohort shows monotonic deterioration or recovery across at least three periods.
- The affected cohort is large enough to materially influence active users or LTV.

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
