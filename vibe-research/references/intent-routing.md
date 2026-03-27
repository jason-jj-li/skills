# Intent-First Routing

Legacy note: this file documents the older JSON-first routing path. For new MD-first projects, keep routing decisions in `STATE.md`, `TASKS.md`, and optionally `process/spec.md`. Use this reference only when maintaining or selectively reusing the old automation.

How vibe-research should avoid over-committing to one method (for example, forcing meta-analysis).

## 1) Project Contract First

Create `process/project_contract.json` from the user's request:
- delivery tier (`explore`, `draft`, `submission_ready`)
- quality bar (`exploratory`, `submission`, `top_tier_submission`)
- target journal and standards
- preferred method (`auto` by default)
- whether mode switching is allowed

This contract is the source of truth for all routing decisions.

## 2) Feasibility Before Method Lock

Evaluate multiple candidate topics with objective signals:
- evidence density (`all_count`)
- prior synthesis pressure (`meta_count`)
- extractability signal (abstract-level OR/HR/RR and CI language)
- age/population fit

Compute publishability score:

```text
Publishability = 0.20*Novelty + 0.35*Evidence + 0.30*Extractability + 0.15*JournalFit
```

Thresholds and weights are policy-driven:
- default from skill profile
- override per project with `process/decision_thresholds.json`
- log `policy_used` in feasibility and routing outputs for auditability

## 3) Route Method, Do Not Assume Method

Route to one of:
- `meta_analysis`
- `systematic_review_no_meta`
- `scoping_review`
- `evidence_gap_map`
- `protocol`

Use hard no-go checks for submission-grade meta-analysis:
- minimum evidence volume
- minimum extractability signal
- user quality tier constraints
- innovation and quality readiness when required by contract (`innovation_and_quality`)

Intent-adaptive policy:
- If quality bar is `top_tier_submission` and route returns `go=false`, stop immediately at routing.
- If intent is exploratory/scoping, allow continuation with explicit limitations.

## 4) Pivot Guard

If requested mode is infeasible:
- record no-go in `process/no_go_topics.json`
- provide replacement mode
- prevent repeated selection of the same blocked direction in current project
- include execution policy (`stop_after_routing`) in `process/mode_decision.json`

## 5) Exemplar Alignment Before Execution

For journal-targeted work, add an exemplar pass before retrieval/write-up:
- build `process/exemplar_benchmark.json` and `.md`
- build `process/writing_blueprint.json` and `process/writing_outline.md`
- extract observed paper patterns (structure + method reporting)
- convert patterns to task constraints and section-level writing outline

Top-tier targets should fail the gate when exemplar artifacts are missing.

## 6) Deliverable Integrity

Do not label outputs as submission-ready when routed mode is exploratory.
Always align manuscript claims with route decision.
