# MD-First ResearchOS

Use a project-native operating system instead of a chat-native workflow.

## Minimal Layout

```text
project_name/
  AGENTS.md
  STATE.md
  TASKS.md
  CHANGELOG.md
  01_question/
  02_literature/
    cards/
  03_design/
  04_data/
  05_analysis/
  06_draft/
  07_output/
  meetings/
  process/
```

## Why This Layout Works

- problem statements live near evidence
- data, analysis, and draft outputs are not scattered
- the next action is visible in a file, not trapped in chat history
- both humans and agents can resume quickly

## Memory Model

Use two layers, not one:

- Markdown control layer: current working memory
- Git history layer: durable change memory

The split is deliberate:

- `AGENTS.md` keeps stable rules
- `STATE.md` keeps the current truth
- `TASKS.md` keeps the execution queue
- `CHANGELOG.md` keeps high-signal decision history
- Git keeps the exact file-level diff history

Do not force Git to answer questions it is bad at, such as the current blocker or the next action. Do not force `STATE.md` to behave like a full version-control system.

## Control-Layer Roles

### `AGENTS.md`

Keep stable instructions:

- identity and scope
- what counts as good work
- fail-safe rules
- writing and citation constraints
- logging requirements

### `STATE.md`

Keep dynamic state:

- current phase or slice
- completed work
- active files
- blockers
- open questions
- next step

### `TASKS.md`

Keep executable tasks:

- `P0`: now
- `P1`: next
- `P2`: later
- `P3`: parked

Every task should name the inputs, deliverable, and definition of done.

### `CHANGELOG.md`

Keep concise project memory:

- major edits
- decision reversals
- scope changes
- handoff-relevant notes

## Git as Historical Memory

Use Git for:

- small reviewable commits
- diff inspection before and after major edits
- checkpoint branches for risky rewrites
- tags for milestones such as submission, rebuttal, or camera-ready snapshots

Avoid these failure modes:

- using commit messages as the only explanation of current state
- batching too many unrelated changes into one commit
- leaving no checkpoint before a risky restructuring step
- assuming an old chat summary can replace the Git plus Markdown record

## Optional Publication Controls

Only add these when needed:

- `process/spec.md`
- `process/claims.md`
- `process/submission_checklist.md`

Do not create a second state machine unless a concrete tool depends on it.

## Design Rule

If your future self cannot re-enter the project in five minutes by reading the control layer, the system is too complicated.
