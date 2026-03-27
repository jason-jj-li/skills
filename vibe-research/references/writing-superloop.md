# Writing Superloop

Legacy note: this loop was designed for the earlier JSON-first gate stack. In MD-first projects, use it only as optional automation; keep the accepted conclusions and task updates in Markdown control files.

## Why It Exists

Single-pass writing gates are good for diagnostics but weak for convergence.
Submission-grade manuscripts need an enforced revise-recheck loop.

## Core Loop

1. Run style/prose/content/citation/split (and triad when required).
2. Collect failed checks as a machine-readable revision task list.
3. Rewrite only the paragraphs linked to failed checks.
4. Re-run the full gate set.
5. Stop only when all required gates pass, or max rounds is reached.

## Artifacts

- `process/writing_superloop_report.json`
- `process/writing_superloop_report.md`
- `process/writing_superloop/round_XX/revision_tasks.json`
- `process/writing_superloop/round_XX/revision_tasks.md`

## Recommended Defaults

- `top_tier_submission`: 5 rounds max
- `submission`: 3 rounds max
- `draft/exploratory`: 2 rounds max

## Operational Rules

- Do not claim submission readiness if `verdict != pass`.
- For publish decisions, split flagged technical sections into supplement.
- For top-tier targets, require triad pass within the same convergence loop.
