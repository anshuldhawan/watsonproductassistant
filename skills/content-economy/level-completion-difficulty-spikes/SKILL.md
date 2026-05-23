---
name: level-completion-difficulty-spikes
description: "Runs the Lighthouse User Level Discovery Barriers analysis for Content & Game Economy. Use when the analyst is asked to run `level-completion-difficulty-spikes` or investigate pinpoint barriers where users abandon progression loops or curated taste challenges."
---

# Skill: User Level Discovery Barriers

## Identity

- Skill key: `level-completion-difficulty-spikes`
- Group: `content-economy` (Content & Game Economy)
- Owning agent: `economy-analyst`
- Primary metric hint: `level_completion_difficulty_spikes_index`

## When To Use

Use this skill when the user selects `level-completion-difficulty-spikes` or asks for: Pinpoint barriers where users abandon progression loops or curated taste challenges.

## Required Inputs

- catalog tables for tracks, artists, albums, playlists, rewards, or discovery surfaces.
- play and interaction events mapped to content ids.
- users catalog for lifecycle and subscription segmentation.
- Default date range: the run configuration value, falling back to the trailing 30 days.
- Default comparison: the prior equivalent window or the trailing cohort baseline when no explicit comparison is supplied.

## Method

1. Map user activity to tracks, artists, albums, playlists, rewards, or discovery experiences as required.
2. Compute consumption velocity, completion, gap, reward, source-sink, or progression metrics for the configured cohort.
3. Segment by catalog attributes, user lifecycle, subscription tier, platform, and geography when available.
4. Distinguish content supply issues from recommendation, UX, or demand issues before recommending action.
5. Create a content table, progression curve, or source-sink artifact.

## Evidence To Produce

- A metric table with current value, baseline value, absolute delta, relative delta, sample size, and segment.
- At least one inspectable artifact when a finding is emitted: chart PNG, CSV table, model summary, or funnel/cohort table.
- A short explanation of the statistical comparison used, stored in `stat_test`.

## What Counts As Noteworthy

- Consumption, completion, gap, reward, or progression movement exceeds 10% relative change or configured threshold.
- The affected content, reward, or progression surface has meaningful reach or strategic value.
- The recommendation distinguishes supply, recommendation, UX, and demand causes.

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
