---
name: vibe-research
description: "Project-native, MD-first research operating system for AI-assisted research. Use when Codex needs to run literature review, hypothesis generation, experiment planning, data analysis, evidence synthesis, or research writing inside a project folder that should stay readable by both humans and agents. Prefer this skill when the user wants AGENTS.md, STATE.md, TASKS.md, and CHANGELOG.md as the shared control layer, with lighter process overhead than heavy JSON-first phase management while still keeping evidence traceability and submission guardrails."
---

# Vibe-Research

Use this skill to build and run a research project as a small operating system inside the project folder.

The control layer is Markdown-first:

- `AGENTS.md`: stable rules, boundaries, writing norms, and handoff conventions
- `STATE.md`: current reality of the project
- `TASKS.md`: executable queue with priorities and done criteria
- `CHANGELOG.md`: concise record of meaningful changes and decisions

These files are the shared memory for both humans and agents. Do not split the same project state across multiple JSON trackers unless a script strictly requires a derived export.

Git is the historical memory layer:

- use Git for audited change history, diffs, rollback, and milestone snapshots
- do not use Git commit history as the only source of current state or next actions
- keep runtime memory in `AGENTS.md`, `STATE.md`, `TASKS.md`, and `CHANGELOG.md`

## Core Principles

1. Use the project folder, not the chat window, as the execution unit.
2. Prefer structure over prompt cleverness.
3. Keep evidence, analysis, and writing close to each other.
4. Convert vague requests into explicit tasks before execution.
5. Use Git as history memory, not as the only runtime memory.
6. Keep final identification, interpretation, and public claims human-owned.

## Minimal Project Layout

Use this shape by default:

```text
project_name/
  AGENTS.md
  STATE.md
  TASKS.md
  CHANGELOG.md
  01_question/
  02_literature/
  03_design/
  04_data/
  05_analysis/
  06_draft/
  07_output/
  meetings/
  process/
```

Optional supporting docs:

- `process/spec.md`: requirements for publication or handoff
- `process/claims.md`: claim ledger for numeric or high-stakes assertions
- `process/submission_checklist.md`: final submission or delivery checks
- `02_literature/cards/*.md`: structured literature cards
- `meetings/*.md`: structured meeting notes

## Session Start

Always begin in this order:

1. Read `AGENTS.md`.
2. Read `STATE.md`.
3. Read `TASKS.md`.
4. Pick one active task.
5. Read only the files listed in that task's inputs or the state note.

Do not load the whole project just because it exists.

## Control Layer

### `AGENTS.md`

Use for stable rules:

- project identity and scope
- workflow priorities
- fail-safety rules
- writing and citation rules
- logging expectations
- collaboration rules for Codex and Claude Code

`AGENTS.md` should change rarely.

### `STATE.md`

Use for the current truth:

- where the project stands
- what has already been completed
- what matters right now
- active files
- blockers
- next actions
- open questions

Update `STATE.md` after any meaningful work session or meeting.

### `TASKS.md`

Use for executable work, not vague wishes.

Every active task should include:

- priority
- goal
- inputs
- deliverable
- definition of done
- status

If a task does not have a deliverable or done condition, it is not ready for execution.

### `CHANGELOG.md`

Use for high-signal history:

- what changed
- why it changed
- which files moved
- what decision was made

Do not turn `CHANGELOG.md` into a diary. Keep it terse and useful for resuming work.

## Git Memory Layer

Use Git as the durable history of the project:

- diffs show what changed
- commits capture reviewable checkpoints
- branches isolate risky work
- tags mark submission or release milestones

Do not rely on commit messages to answer:

- what the current blocker is
- which task should run next
- which claim is still unresolved
- why a framing decision is active right now

Those belong in the Markdown control layer.

Practical rule:

- `STATE.md` answers "what is true now"
- `TASKS.md` answers "what should happen next"
- `CHANGELOG.md` answers "what changed and why at a high level"
- Git answers "exactly how the files changed over time"

## Working Modes

### Explore

Use for early-stage work:

- topic scouting
- literature triage
- argument mapping
- framing alternatives

Required files:

- `AGENTS.md`
- `STATE.md`
- `TASKS.md`
- `CHANGELOG.md`

Avoid heavy gate machinery here.

### Build

Use for active project execution:

- data work
- analysis
- drafting
- figure production
- slide or memo generation

Add:

- literature cards
- meeting notes
- project subfolders for data, analysis, and draft outputs

### Submit

Use when the work is nearing publication, review, or formal delivery.

Add only three extra control artifacts:

- `process/spec.md`
- `process/claims.md`
- `process/submission_checklist.md`

Markdown remains canonical. If a script requires JSON or YAML, generate it from these files instead of hand-maintaining two competing sources of truth.

## Evidence and Claim Discipline

- Do not invent citations, results, or benchmark outcomes.
- Distinguish evidence summary from interpretation.
- Distinguish descriptive statements from causal claims.
- Keep code, tables, figures, and prose auditable against each other.
- If context is incomplete, state assumptions explicitly.
- For publishable numbers or sensitive claims, record them in `process/claims.md` before hardening the prose.

## Daily Work Loop

Use this default loop:

1. Open the project folder.
2. Read `AGENTS.md`, `STATE.md`, and `TASKS.md`.
3. Choose one `P0` or `P1` task first.
4. Execute against the files named in that task.
5. Produce or revise the deliverable.
6. Update `STATE.md`, `TASKS.md`, and `CHANGELOG.md`.
7. Review the diff and make a small commit when the change is a stable checkpoint.
8. Stop with the next action already written down.

## Delegation

- Use `review` for source-grounded literature retrieval and citation work.
- Use `data-skill` for data cleaning, statistics, and plots.
- Use `playwright` or `webapp-testing` when a browser flow is part of the research workflow.
- Use `openai-docs` only for official OpenAI product or API questions.

Both Codex and Claude Code should read the same project files. Do not maintain parallel memory systems for different agents.

## Reference Files

- [references/quickstart.md](references/quickstart.md): bootstrap a new MD-first research project
- [references/research-factory.md](references/research-factory.md): project layout and control-layer design
- [references/long-running-research.md](references/long-running-research.md): resume and handoff patterns
- [references/gate-specs.md](references/gate-specs.md): lightweight submission controls for MD-first projects
- [references/git-memory.md](references/git-memory.md): how Git complements the Markdown control layer
- [references/legacy-automation.md](references/legacy-automation.md): when and how to use the old JSON-first scripts safely
- [references/skill-integration.md](references/skill-integration.md): when to delegate to other skills
