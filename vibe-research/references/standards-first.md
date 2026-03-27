# Standards-First Gate

Mandatory when user asks to benchmark a journal or follow named reporting/method standards.

## Purpose

Convert "journal style" requests into explicit, verifiable constraints before running retrieval/analysis/write-up.

## Trigger Conditions

Run this gate if the prompt includes any of the following:
- target journal names (eg, Lancet, NEJM, JAMA, BMJ)
- reporting standards (eg, PRISMA, MOOSE, STROBE, CONSORT)
- method handbooks/frameworks (eg, Cochrane)

## Required Source Priority

1. Official journal author instructions (publisher/journal official site)
2. Official reporting guideline sources (eg, PRISMA official site or statement paper)
3. Official method handbook sources (eg, Cochrane Handbook)

If level-1 source is unavailable, document why and continue with highest-confidence fallback.

## Required Artifact

Create `process/standards_snapshot.md` with this structure:

```markdown
# Standards Snapshot

Date: YYYY-MM-DD
Project: <path>
Target: <journal and/or standards>

## Sources Checked
- URL:
  - Accessed on:
  - Type: journal|reporting|method
  - Status: reachable|blocked
  - Confidence: high|medium|low

## Extracted Requirements
1. Requirement:
   - Source:
   - How it changes execution:

## Execution Constraints Applied
- search/reporting/statistics/writing constraints reflected in `STATE.md` and `TASKS.md`

## Blockers and Caveats
- Missing pages, ambiguity, or unresolved conflicts
```

## Go/No-Go Rule

No retrieval, synthesis, or manuscript drafting in journal-targeted tasks until:
- `process/standards_snapshot.md` exists, and
- extracted requirements are mapped into actionable tasks and constraints.

## Common Failure Modes

- Starting analysis before checking current journal guidance
- Using remembered (possibly outdated) formatting/reporting rules
- Citing secondary blog summaries without official source traceability
