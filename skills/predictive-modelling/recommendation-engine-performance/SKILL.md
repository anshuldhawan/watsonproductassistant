---
name: recommendation-engine-performance
description: "Runs the Lighthouse Curated Playlist Performance Prediction analysis for Predictive Modelling. Use when the analyst is asked to run `recommendation-engine-performance` or investigate evaluate play-through and retention metrics of algorithmic vs. human curated discovery lists."
---

# Skill: Curated Playlist Performance Prediction

## Identity

- Skill key: `recommendation-engine-performance`
- Group: `predictive-modelling` (Predictive Modelling)
- Owning agent: `predictive-analyst`
- Primary metric hint: `recommendation_engine_performance_index`

## When To Use

Use this skill when the user selects `recommendation-engine-performance` or asks for: Evaluate play-through and retention metrics of algorithmic vs. human curated discovery lists.

## Required Inputs

- historical user, play, monetization, quality, and lifecycle features.
- clearly defined target labels or KPI history.
- run configuration for prediction horizon and scoring population.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Define the prediction target, horizon, eligible population, and leakage-safe observation window.
2. Build features from recent engagement, monetization, content, platform, and lifecycle behavior.
3. Evaluate model or rule performance with calibration, lift, precision/recall, or forecast-error metrics as appropriate.
4. Translate scores into actionable segments and avoid recommendations that cannot be operationalized.
5. Create a model summary artifact with drivers, score distribution, and recommended interventions.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- Model, forecast, or scoring output identifies a segment with meaningful lift over baseline.
- Predicted impact is actionable within the configured horizon.
- Performance checks are adequate; otherwise emit a data-quality or inconclusive finding instead.

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
