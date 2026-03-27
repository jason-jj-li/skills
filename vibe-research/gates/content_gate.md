# Gate Contract: Content Gate

## Purpose

Use this gate during `Submit` mode to confirm that the draft is structurally complete and aligned with the project spec.

## Canonical Inputs

Use Markdown as the source of truth:

- `process/spec.md`
- `process/claims.md` when the draft contains publishable numbers or high-stakes comparisons
- draft files in `06_draft/` or `manuscript/`

Do not require `process/claims.json` or `process/manuscript_spec.yaml` as hand-maintained inputs.

## Required Artifacts

| Artifact | Path | Required | Validation |
|----------|------|----------|------------|
| Draft | `06_draft/` or `manuscript/` | YES | Main draft file exists |
| Project Spec | `process/spec.md` | YES | Non-empty and target constraints stated |
| Claims Ledger | `process/claims.md` | CONDITIONAL | Present when claim-bearing prose exists |

## Validation Questions

1. Does the draft satisfy the sections and constraints listed in `process/spec.md`?
2. Are required figures and tables present and referenced?
3. Is placeholder text gone?
4. Are contribution and limitation statements explicit?
5. If numbers appear, are they recorded in `process/claims.md`?

## Manual Check Structure

### Structure

- required sections present
- output target respected
- no obvious section drift from `process/spec.md`

### Completeness

- no placeholders
- figures and tables exist
- all major outputs referenced in text

### Claim Hygiene

- claims ledger exists when needed
- key numbers in prose can be matched to `process/claims.md`
- no unsupported headline claim appears in abstract, results, or discussion

## Pass Criteria

- `process/spec.md` exists and is usable
- the draft is structurally complete
- claim-bearing prose is traceable to `process/claims.md`
- no blocking placeholder or reference mismatch remains

## Failure Actions

- tighten or expand draft sections to match `process/spec.md`
- add missing figure or table references
- move unsupported claims out of the draft until verified
- fill gaps in `process/claims.md`
