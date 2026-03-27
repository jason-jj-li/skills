# Submission Controls for MD-First Projects

This skill no longer treats JSON trackers as the canonical project memory.

Use Markdown as the source of truth:

- `process/spec.md`
- `process/claims.md`
- `process/submission_checklist.md`

Only derive structured exports if a script or downstream tool requires them.

For the old script-driven JSON workflow, see [legacy-automation.md](legacy-automation.md).

## Operating Modes

### Explore

Required:

- `AGENTS.md`
- `STATE.md`
- `TASKS.md`
- `CHANGELOG.md`

No formal submission gates.

### Build

Required:

- the core control layer
- outputs under `04_data/`, `05_analysis/`, `06_draft/`, `07_output/`

Recommended:

- literature cards
- meeting notes

### Submit

Required:

- `process/spec.md`
- `process/claims.md`
- `process/submission_checklist.md`

## `process/spec.md`

Use for:

- target venue or output type
- section requirements
- quality bar
- non-goals
- figure or citation expectations

If the project is not submission-bound, skip it.

## `process/claims.md`

Use for:

- numeric claims
- sensitive comparative claims
- statements that require explicit source tracing

Minimum fields:

- claim id
- location in draft
- statement
- source file or citation
- verification status
- notes

## `process/submission_checklist.md`

Use before external release.

Minimum checks:

- claims verified
- figures and tables match text
- references are real and grounded
- no placeholder text remains
- main contribution and limitations are stated clearly

## Guardrails

- Do not write unsupported claims into the public draft.
- Do not treat benchmark wins as scientific conclusions.
- Do not maintain the same truth in both Markdown and JSON by hand.
- If a validator requires JSON or YAML, export from Markdown and treat the export as disposable.
