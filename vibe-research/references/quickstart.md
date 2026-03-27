# Quick Start

## Bootstrap a New MD-First Research Project

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/vibe-research"
PROJECT_ROOT="/path/to/project_name"

python "$SKILL_DIR/scripts/bootstrap_md_research_os.py" \
  "$PROJECT_ROOT" \
  --sample-notes \
  --git-init
```

Add Submit-mode files only when needed:

```bash
python "$SKILL_DIR/scripts/bootstrap_md_research_os.py" \
  "$PROJECT_ROOT" \
  --submit
```

Equivalent manual setup if you do not want to use the bootstrap script:

```bash
mkdir -p "$PROJECT_ROOT"/{01_question,02_literature/cards,03_design,04_data,05_analysis,06_draft,07_output,meetings,process}
cp "$SKILL_DIR/templates/agents.template.md" "$PROJECT_ROOT/AGENTS.md"
cp "$SKILL_DIR/templates/state.template.md" "$PROJECT_ROOT/STATE.md"
cp "$SKILL_DIR/templates/tasks.template.md" "$PROJECT_ROOT/TASKS.md"
cp "$SKILL_DIR/templates/changelog.template.md" "$PROJECT_ROOT/CHANGELOG.md"
cp "$SKILL_DIR/templates/literature-card.template.md" "$PROJECT_ROOT/02_literature/cards/example_card.md"
cp "$SKILL_DIR/templates/meeting-note.template.md" "$PROJECT_ROOT/meetings/example_meeting.md"
find "$PROJECT_ROOT" -type d -empty -exec touch {}/.gitkeep \;
```

Manual Submit-mode additions:

```bash
cp "$SKILL_DIR/templates/spec.template.md" "$PROJECT_ROOT/process/spec.md"
cp "$SKILL_DIR/templates/claims.template.md" "$PROJECT_ROOT/process/claims.md"
cp "$SKILL_DIR/templates/checklist.template.md" "$PROJECT_ROOT/process/submission_checklist.md"
```

## First Working Pass

1. Fill in `AGENTS.md` with scope, guardrails, and writing norms.
2. Fill in `STATE.md` with the current project status.
3. Fill in `TASKS.md` with a small, prioritized queue.
4. If the project is not already versioned, use `--git-init` or initialize Git and make the bootstrap commit manually.
5. Start with one task that has explicit inputs and a deliverable.
6. After work, update `STATE.md`, `TASKS.md`, and `CHANGELOG.md`.
7. Review the diff and commit small, auditable checkpoints.

Example:

```bash
cd "$PROJECT_ROOT"
git init
git add AGENTS.md STATE.md TASKS.md CHANGELOG.md 01_question 02_literature 03_design 04_data 05_analysis 06_draft 07_output meetings process
git commit -m "Bootstrap MD-first research OS"
```

## Daily Resume Pattern

When you come back to the project:

1. Read `AGENTS.md`
2. Read `STATE.md`
3. Read `TASKS.md`
4. Open only the files referenced by the top active task

Do not rebuild context from memory or from an empty chat window.

Use Git to inspect historical changes, not to infer the entire current state. The runtime restore path remains `AGENTS.md` -> `STATE.md` -> `TASKS.md`.

## When to Add Submission Controls

Add `process/spec.md`, `process/claims.md`, and `process/submission_checklist.md` only when:

- you are drafting a paper, report, rebuttal, or formal memo
- numeric claims need explicit verification
- external readers will rely on the output

Markdown is canonical. Only export JSON or YAML if a tool truly requires it.

Git complements this setup:

- Markdown files hold current state and next actions
- Git holds diffs, rollback points, and milestone snapshots

For older script-driven projects, see [legacy-automation.md](legacy-automation.md).
