# Vibe-Research Upgrade Plan (Next Step)

Date: 2026-02-21

## Goal

Upgrade from "pipeline can run" to "pipeline can be audited, graded, and safely promoted across gates."

## Milestones

1. M1: Contractization Layer (implemented)
- Add machine-readable gate contract template.
- Add strict gate checker for `EXECUTE`, `DECISION`, `PUBLISH`.
- Persist report to `process/gate_contracts.json`.

2. M2: Independent Evaluation Layer (implemented)
- Add evaluator independent from generation pipeline.
- Score retrieval/citation consistency and artifact completeness.
- Persist report to `outputs/eval_report.json`.

3. M3: Runner Integration (implemented)
- Extend `run_full_pipeline.py` with:
  - `--run-eval`
  - `--gate-state`
  - `--gate-soft-fail`
  - `--eval-fail-below`
- Keep this stage optional to avoid breaking legacy runs.

4. M4: Review-Round Policy (next)
- Encode reviewer vote policy into machine-readable thresholds.
- Add one command to convert review outputs into a decision label.
- Require decision summary artifact before `DECISION -> PUBLISH`.

5. M5: Replication Contract (next)
- Add replication checklist template with mandatory fields.
- Add artifact validator for code/data/figure-paper consistency.

## Acceptance Criteria

- Every long run can produce:
  - `outputs/manifest.json`
  - `process/gate_contracts.json`
  - `outputs/eval_report.json`
- Gate reports can fail fast when required artifacts are missing.
- Evaluation can fail CI by grade threshold (`--eval-fail-below`).
- Existing users can still run baseline pipeline without `--run-eval`.
