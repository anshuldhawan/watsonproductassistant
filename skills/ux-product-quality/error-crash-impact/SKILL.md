---
name: error-crash-impact
description: "Runs the Lighthouse Playback Error & Crash Impact On Retention analysis for UX & Product Quality. Use when the analyst is asked to run `error-crash-impact` or investigate correlate audio buffer errors or application crashes to immediate active churn."
---

# Skill: Playback Error & Crash Impact On Retention

## Identity

- Skill key: `error-crash-impact`
- Group: `ux-product-quality` (UX & Product Quality)
- Owning agent: `ux-quality-analyst`
- Primary metric hint: `retention_rate`

## When To Use

Use this skill when the user selects `error-crash-impact` or asks for: Correlate audio buffer errors or application crashes to immediate active churn.

## Required Inputs

- screen interaction, latency, error, crash, support, or app-version signals when connected.
- play and engagement events for impact measurement.
- users catalog for platform, device, and subscription segmentation.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Identify the affected surface, device, platform, app version, screen, or error class before measuring impact.
2. Join quality or interaction signals to engagement, retention, conversion, and support outcomes.
3. Compare affected users to similar unaffected users and to a historical baseline.
4. Prioritize findings by user reach, severity, recurrence, and downstream product impact.
5. Create a quality-impact artifact such as a heatmap, platform split, error trend, or latency curve.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- Quality, latency, crash, or UX movement has measurable downstream impact on retention, conversion, or support.
- The issue is concentrated enough to route to an owner but broad enough to matter.
- Severity, reach, recurrence, and business impact justify surfacing.

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
