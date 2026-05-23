# Lighthouse Analyst House Style

Use these shared rules whenever running a Lighthouse product analyst skill.

## Operating Principles

1. Start from the configured run scope: date range, segment filters, cohort definition, comparison window, and execution mode.
2. Use the skill-specific `SKILL.md` as the source of truth for methodology and noteworthiness.
3. Prefer evidence-backed insights over exhaustive reporting. A clean run should return `[]`.
4. Save artifacts for charts, tables, and model summaries before referencing them in output JSON.
5. Quantify magnitude, confidence, business impact, and recommended actions in PM-readable language.
6. Flag missing data, invalid denominators, sample-ratio mismatches, or other data-quality blockers instead of silently proceeding.

## Shared Metric Defaults

- Active user: a user with at least one qualifying app-open, session, or play event in the analysis window.
- Payer: a user with an active paid subscription or successful purchase in the analysis window.
- Conversion rate: unique converted users divided by unique eligible users.
- Retention: unique users active at the requested horizon divided by users eligible for that horizon.
- Revenue impact: estimated incremental gross revenue or LTV impact over the stated horizon; use `0` when impact is not monetizable from available data.

## Output Discipline

Return only valid JSON. Do not include prose outside the JSON payload. Use `[]` when there is no noteworthy finding.
