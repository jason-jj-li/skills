# Long-Running Research

Use this pattern for multi-session work without recreating context each time.

## Resume Order

At the start of a session:

1. Read `AGENTS.md`
2. Read `STATE.md`
3. Read `TASKS.md`
4. Open only the files named by the active task or state note

This is the only required restore path for most projects.

## End-of-Session Update

Before stopping:

1. Update `STATE.md`
2. Update `TASKS.md`
3. Append a short entry to `CHANGELOG.md`
4. Review the Git diff and confirm the session changed what you think it changed
5. If the work reached a stable checkpoint, make a small commit
6. If a meeting happened, save a meeting note in `meetings/`
7. If evidence changed a key claim, update `process/claims.md`

## What `STATE.md` Must Answer

- What is the project trying to do?
- What has already been completed?
- What matters right now?
- Which files should be opened next?
- What is blocked?
- What is the next concrete action?

## What `TASKS.md` Must Answer

- What should the agent do first?
- What inputs are required?
- What output counts as completion?
- What can be ignored for now?

## Failure Handling

If a task fails:

- keep the failed attempt visible
- record the reason in `STATE.md` or `CHANGELOG.md`
- update the task status instead of silently retrying
- separate infrastructure failure from method failure

## Git Checkpoint Rule

Git is the durable history of the work session, not the runtime control layer.

Use a commit when:

- a task deliverable is complete
- a risky edit should have a rollback point
- a submission or review milestone is reached

Do not wait until many unrelated edits accumulate. Small checkpoints are easier to review and safer to resume from.

## Handoff Rule

Never end a session with only a summary. End with a ready-to-run next task.
