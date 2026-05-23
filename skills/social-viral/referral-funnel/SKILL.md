---
name: referral-funnel
description: "Runs the Lighthouse Referral Funnel Conversion analysis for Social & Viral. Use when the analyst is asked to run `referral-funnel` or investigate track the invitation lifecycle: Sent -> Clicked -> Installed -> Signed Up."
---

# Skill: Referral Funnel Conversion

## Identity

- Skill key: `referral-funnel`
- Group: `social-viral` (Social & Viral)
- Owning agent: `social-viral-analyst`
- Primary metric hint: `conversion_rate`

## When To Use

Use this skill when the user selects `referral-funnel` or asks for: Track the invitation lifecycle: Sent -> Clicked -> Installed -> Signed Up.

## Required Inputs

- invite, referral, sharing, friend, or collaboration events.
- users catalog for sender and recipient segmentation.
- downstream activation, retention, and monetization events.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Build invitation, sharing, referral, friend, or collaborative-playlist event chains for the configured window.
2. Compute sender, recipient, conversion, k-factor, contagion, or network-value metrics depending on the skill.
3. Separate organic social behavior from paid acquisition or platform-level seasonality.
4. Validate that downstream gains are not simply from larger or already healthier user cohorts.
5. Create a network, referral funnel, or cohort comparison artifact.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- Referral, sharing, k-factor, or network-value movement exceeds 10% relative change or configured threshold.
- The effect creates measurable downstream activation, retention, or monetization impact.
- The chain from social action to outcome can be traced without double counting.

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
