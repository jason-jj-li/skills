# Gate Contract: Data Gate

## Purpose

Use this gate before high-confidence writing or release.

The goal is not to force a JSON registry. The goal is to ensure that the numbers and findings in the draft can be traced back to actual evidence.

## Canonical Inputs

- `process/claims.md`
- analysis notes under `05_analysis/`
- outputs under `07_output/` or `outputs/`
- supporting tables, figures, or code logs

## Required Artifacts

| Artifact | Path | Required | Validation |
|----------|------|----------|------------|
| Claims Ledger | `process/claims.md` | YES for claim-bearing work | Rows contain statement, source, and verification status |
| Analysis Notes | `05_analysis/` | YES | Non-empty, auditable |
| Output Artifacts | `07_output/` or `outputs/` | YES | Files exist for the reported findings |

## Validation Questions

1. Are key claims recorded in `process/claims.md`?
2. Does each claim point to a real source: code, table, figure, or retrieved evidence?
3. Are claims marked `verified`, `pending`, or `failed`?
4. Do the visible outputs support the draft language?
5. Are unresolved discrepancies surfaced instead of hidden?

## Minimum Claim Fields

Each row in `process/claims.md` should cover:

- claim id
- draft location
- statement
- source
- verification status
- notes

## Pass Criteria

- all release-critical claims are present in `process/claims.md`
- no claim marked `failed` remains unresolved
- analysis outputs exist for the claims being used publicly
- the draft does not outrun the verified evidence

## Failure Actions

- add missing claim rows
- downgrade or remove unsupported prose
- rerun analysis or inspect outputs
- separate descriptive findings from stronger interpretations
