---
name: voc-theme-extraction
description: "Runs the Lighthouse Voice of Customer (VOC) Theme Extraction analysis for Feedback & Sentiment. Use when the analyst is asked to run `voc-theme-extraction` or investigate aggregate user forums, support emails, and surveys to flag trending complaints and feature requests."
---

# Skill: Voice of Customer (VOC) Theme Extraction

## Identity

- Skill key: `voc-theme-extraction`
- Group: `feedback-sentiment` (Feedback & Sentiment)
- Owning agent: `feedback-analyst`
- Primary metric hint: `voc_theme_extraction_index`

## When To Use

Use this skill when the user selects `voc-theme-extraction` or asks for: Aggregate user forums, support emails, and surveys to flag trending complaints and feature requests.

## Required Inputs

- NPS, CSAT, survey, review, support, forum, or feature-request records when connected.
- users catalog or account metadata for affected cohort analysis.
- product event data for behavioral validation.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Collect and normalize feedback, review, survey, NPS, CSAT, or request records for the configured window.
2. Cluster or classify themes, sentiment, severity, and affected product areas.
3. Connect qualitative themes to quantitative cohorts, retention, conversion, support, or revenue metrics where possible.
4. Avoid surfacing small anecdotal themes unless they are rapidly growing, high severity, or tied to material business impact.
5. Create a theme table with examples, volume, sentiment, trend, and recommended owner.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- Theme volume, sentiment, severity, or growth rate crosses the configured threshold.
- Qualitative evidence is connected to a product area and affected cohort.
- The theme is actionable and not just a one-off anecdote unless severity is high.

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
