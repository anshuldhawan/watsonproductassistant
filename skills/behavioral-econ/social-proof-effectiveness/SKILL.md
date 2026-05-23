---
name: social-proof-effectiveness
description: "Runs the Lighthouse Social Proof & Social Signal Conversions analysis for Behavioral Economics & Psychology. Use when the analyst is asked to run `social-proof-effectiveness` or investigate track conversion lift of paywalls that display 'Joined by 50,000 others in your country'."
---

# Skill: Social Proof & Social Signal Conversions

## Identity

- Skill key: `social-proof-effectiveness`
- Group: `behavioral-econ` (Behavioral Economics & Psychology)
- Owning agent: `behavioral-econ-analyst`
- Primary metric hint: `conversion_rate`

## When To Use

Use this skill when the user selects `social-proof-effectiveness` or asks for: Track conversion lift of paywalls that display 'Joined by 50,000 others in your country'.

## Required Inputs

- exposure records for the behavioral treatment or nudge.
- decision, conversion, engagement, and guardrail events.
- users catalog for eligibility and segmentation.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Identify the behavioral treatment or nudge exposure and construct comparable exposed and unexposed cohorts.
2. Measure the target decision outcome plus guardrails such as churn, fatigue, refund, or support-contact rates.
3. Control for eligibility, pricing, country, subscription tier, and prior engagement where possible.
4. Interpret results as behavioral lift only when the counterfactual is credible.
5. Create a segment comparison artifact that shows treatment effect and guardrail movement.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- Treatment lift is statistically credible and not offset by guardrail harm.
- The effect is concentrated in a segment that can be targeted or productized.
- The interpretation has a credible counterfactual, not just exposed-vs-unexposed correlation.

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
