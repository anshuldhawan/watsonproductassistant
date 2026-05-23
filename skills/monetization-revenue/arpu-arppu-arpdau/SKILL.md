---
name: arpu-arppu-arpdau
description: "Runs the Lighthouse ARPU / ARPPU / ARPDAU Metrics analysis for Monetization & Revenue. Use when the analyst is asked to run `arpu-arppu-arpdau` or investigate analyze revenue per user, per paying user, and daily active user to track commercial viability."
---

# Skill: ARPU / ARPPU / ARPDAU Metrics

## Identity

- Skill key: `arpu-arppu-arpdau`
- Group: `monetization-revenue` (Monetization & Revenue)
- Owning agent: `monetization-analyst`
- Primary metric hint: `revenue_or_conversion_rate`

## When To Use

Use this skill when the user selects `arpu-arppu-arpdau` or asks for: Analyze revenue per user, per paying user, and daily active user to track commercial viability.

## Required Inputs

- subscription, purchase, ad, trial, renewal, or cancellation records when connected.
- users catalog with subscription_tier and signup_date.
- play events for active-user denominators.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Define payers, active users, revenue events, refunds, trials, and subscription states consistently before computing metrics.
2. Compute the relevant unit economics: ARPU, ARPPU, ARPDAU, LTV, conversion, renewal, cancellation, or concentration.
3. Separate free, trial, paid, geography, platform, and acquisition cohorts before assigning business impact.
4. Compare against the configured baseline and normalize for active-user mix so volume changes do not masquerade as monetization changes.
5. Create a revenue bridge, cohort table, funnel, or concentration artifact depending on the skill.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- Revenue, conversion, renewal, cancellation, or LTV movement exceeds 5% relative change or the configured threshold.
- The movement changes projected 30, 90, or 180 day business impact.
- The result remains after normalizing for active-user and payer mix.

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
