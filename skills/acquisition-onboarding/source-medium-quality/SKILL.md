---
name: source-medium-quality
description: "Runs the Lighthouse Source/Medium Quality Analysis analysis for Acquisition & Onboarding. Use when the analyst is asked to run `source-medium-quality` or investigate compare user cohorts from Google, Meta, referral, organic, etc., on long-term value metrics."
---

# Skill: Source/Medium Quality Analysis

## Identity

- Skill key: `source-medium-quality`
- Group: `acquisition-onboarding` (Acquisition & Onboarding)
- Owning agent: `acquisition-analyst`
- Primary metric hint: `source_medium_quality_index`

## When To Use

Use this skill when the user selects `source-medium-quality` or asks for: Compare user cohorts from Google, Meta, referral, organic, etc., on long-term value metrics.

## Required Inputs

- users catalog with signup_date, country, subscription_tier, and acquisition dimensions when connected.
- registration, onboarding, and first-play events.
- run configuration for date range, segment filters, and comparison window.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Define the acquisition or onboarding population and exclude users outside the configured date range.
2. Build cohorts by channel, source, campaign, country, device, and subscription tier when those dimensions are available.
3. Measure activation, registration, first-value, and downstream quality metrics against the prior baseline window.
4. Rank segments by both conversion lift and retained value so low-quality volume does not look successful.
5. Create a funnel or cohort artifact that shows where the material difference appears.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- Conversion or activation delta is at least 5 percentage points or 1.5 standard deviations from baseline.
- A channel or cohort materially changes retained value, LTV, or first-value rate.
- The finding affects at least 2% of eligible users or has a clear high-value segment impact.

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
