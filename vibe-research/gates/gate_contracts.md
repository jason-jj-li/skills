# Gate Contract: Submission Specification Gate

## Purpose

Use this gate at the start of `Submit` mode to make sure the project has a written release target.

## Canonical Inputs

- `process/spec.md`
- `STATE.md`
- `TASKS.md`

## Required Artifacts

| Artifact | Path | Required | Validation |
|----------|------|----------|------------|
| Project Spec | `process/spec.md` | YES | Non-empty |
| Current State | `STATE.md` | YES | Reflects actual project status |
| Active Tasks | `TASKS.md` | YES | Submission tasks are explicit |

## Validation Questions

1. Does `process/spec.md` define the output target and quality bar?
2. Does it list scope and non-goals?
3. Does it define structural requirements for the draft or deliverable?
4. Does `STATE.md` reflect current blockers and next actions?
5. Does `TASKS.md` contain the concrete work needed to reach release readiness?

## Pass Criteria

- `process/spec.md` exists and names the output target
- release constraints are explicit enough to guide work
- `STATE.md` and `TASKS.md` are aligned with the current submission effort

## Failure Actions

- write or tighten `process/spec.md`
- update `STATE.md` to reflect actual blockers
- rewrite vague submission tasks into executable items
