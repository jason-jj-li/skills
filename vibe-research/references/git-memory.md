# Git as Historical Memory

Use Git as the project's durable history layer, not as the only project memory.

## Split the Memory Model

Use the Markdown control layer for runtime coordination:

- `AGENTS.md`: stable rules
- `STATE.md`: current truth
- `TASKS.md`: next executable work
- `CHANGELOG.md`: high-signal human-readable history

Use Git for historical coordination:

- diffs
- commit checkpoints
- branches for risky work
- tags for milestones

## Why the Split Matters

Git is strong at:

- showing exact file changes
- preserving rollback points
- supporting review of incremental edits
- marking submission-ready snapshots

Git is weak at:

- telling you the current blocker
- telling you the next task to run
- explaining the active framing choice at a glance
- replacing a live claims ledger

That is why Markdown remains the operating layer.

## Practical Rules

1. Start by reading `AGENTS.md`, `STATE.md`, and `TASKS.md`, not by scanning commit history.
2. Keep commits small enough that a diff still explains one idea.
3. Make a checkpoint commit before risky rewrites, large restructuring, or submission packaging.
4. Use tags for milestones such as `submission-ready`, `rebuttal-draft`, or `camera-ready`.
5. If a decision changes project direction, record the rationale in `CHANGELOG.md` or `STATE.md` even if the commit exists.

## Good Commit Boundaries

Good examples:

- one literature-synthesis refactor
- one figure redesign plus matching caption updates
- one packaging fix
- one claims-ledger sync after evidence review

Bad examples:

- one giant commit mixing framing rewrites, bibliography cleanup, and code edits
- relying on `git log` to recover the current blocker
- leaving a risky experiment uncommitted with no rollback point

## Resume Rule

To resume a project:

1. Read the Markdown control layer.
2. Open the active files listed there.
3. Use Git only after that to inspect the recent history or compare checkpoints.

If Git is doing the job of `STATE.md`, the project is under-documented.
