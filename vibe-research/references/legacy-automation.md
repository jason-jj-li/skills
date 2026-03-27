# Legacy Automation

The `legacy/scripts/` and `legacy/assets/*.json` path in this skill is legacy JSON-first automation from the earlier version of `vibe-research`.

## Current Policy

For new projects:

- use `AGENTS.md`
- use `STATE.md`
- use `TASKS.md`
- use `CHANGELOG.md`
- add `process/spec.md`, `process/claims.md`, and `process/submission_checklist.md` only when needed

Treat Markdown as canonical.

## When to Use Legacy Automation

Use the old scripts only when:

- you are maintaining an existing project that already depends on them
- you need a specific utility and are willing to treat its JSON/YAML outputs as disposable exports
- you are migrating an older workspace and cannot replace the automation yet

## What to Avoid

- Do not hand-maintain both Markdown and JSON as competing sources of truth.
- Do not initialize new projects with the old state-machine scripts by default.
- Do not treat `workflow_state.json` or `research_tasks.json` as canonical for new work.

## Practical Rule

If a script requires structured inputs:

1. maintain the truth in Markdown
2. export the minimal structured file if needed
3. run the script
4. fold any accepted result back into Markdown
