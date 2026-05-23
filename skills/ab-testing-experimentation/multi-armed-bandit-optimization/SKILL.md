---
name: multi-armed-bandit-optimization
description: "Runs the Lighthouse Multi-Armed Bandit Evaluation analysis for A/B Testing & Experimentation. Use when the analyst is asked to run `multi-armed-bandit-optimization` or investigate analyze live reward rates of dynamic traffic-allocating bandit algorithms for promo banners."
---

# Skill: Multi-Armed Bandit Evaluation

## Identity

- Skill key: `multi-armed-bandit-optimization`
- Group: `ab-testing-experimentation` (A/B Testing & Experimentation)
- Owning agent: `experimentation-analyst`
- Primary metric hint: `multi_armed_bandit_optimization_index`

## When To Use

Use this skill when the user selects `multi-armed-bandit-optimization` or asks for: Analyze live reward rates of dynamic traffic-allocating bandit algorithms for promo banners.

## Required Inputs

- experiment assignment and exposure logs.
- primary outcome and guardrail events.
- run configuration with experiment id, date range, and metric definition.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Verify assignment, exposure, variant labels, sample ratio, and the configured success metric before testing outcomes.
2. Exclude users who were not eligible or not exposed according to the experiment design.
3. Compute lift, confidence interval, statistical test result, and guardrail metrics for each variant.
4. Use difference-in-differences or pre/post controls only when randomized assignment is unavailable.
5. Create an experiment summary artifact with sample sizes, effect sizes, confidence, and guardrails.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- Primary metric movement is statistically credible and guardrails do not materially regress.
- Confidence interval excludes trivial lift or the result is flagged as inconclusive.
- Sample ratio, exposure, and data quality checks pass.

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
