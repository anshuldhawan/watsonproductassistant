---
name: feature-adoption-heatmap
description: "Runs the Lighthouse Feature Adoption Heatmap analysis for Engagement & Usage Patterns. Use when the analyst is asked to run `feature-adoption-heatmap` or investigate monitor user interaction across playlists, search, lyrics, library, and sharing."
---

# Skill: Feature Adoption Heatmap

## Identity

- Skill key: `feature-adoption-heatmap`
- Group: `engagement-patterns` (Engagement & Usage Patterns)
- Owning agent: `engagement-analyst`
- Primary metric hint: `feature_adoption_heatmap_index`

## When To Use

Use this skill when the user selects `feature-adoption-heatmap` or asks for: Monitor user interaction across playlists, search, lyrics, library, and sharing.

## Required Inputs

- play events with user_id, timestamp, platform, track, and playback duration.
- screen or feature interaction events when connected.
- users catalog for cohort and subscription segmentation.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Sessionize product events and listening activity using the configured inactivity gap, defaulting to 30 minutes.
2. Compute active-user, frequency, duration, depth, feature-usage, and platform splits for the analysis window.
3. Compare each segment to the trailing baseline and to peer segments with similar audience size.
4. Separate broad usage changes from isolated platform, time-of-day, feature, or navigation-path effects.
5. Create a trend, heatmap, or distribution artifact that makes the behavioral pattern inspectable.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- Engagement movement exceeds 10% relative change or 1.5 standard deviations from baseline.
- A segment, platform, feature, or time window explains a meaningful share of the movement.
- The pattern is sustained for at least two comparable periods unless the effect is severe.

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
