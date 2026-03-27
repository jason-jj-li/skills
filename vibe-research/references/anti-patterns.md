# Anti-Patterns

## Core Anti-Patterns

| Anti-Pattern | Problem | Better Approach |
|--------------|---------|-----------------|
| Trust AI citations blindly | Hallucinated references | Verify every citation |
| Skip human checkpoints | Method/interpretation failure | Keep critical sign-off |
| One-shot giant runs | Hard to debug/verify | Incremental research slices |
| Force meta-analysis without feasibility gate | Thin evidence and weak claims | Route method from intent + feasibility |
| No project control layer | Context loss across sessions | Maintain `STATE.md` + `TASKS.md` |
| Ignore reproducibility | Unverifiable conclusions | Log and rerun critical steps |
| Over-automate judgment | False confidence | Human oversight on key decisions |

## V2 Anti-Patterns (Lessons from Multi-Iteration Projects)

| Anti-Pattern | Problem | Better Approach |
|--------------|---------|-----------------|
| **Write without spec** | Output drifts from target format | Define `process/spec.md` first |
| **Unverified numeric claims** | "42%" when code says "18.7%" | Register all critical numbers in `process/claims.md` |
| **Placeholder creep** | "[Author Name]" persists to final | Block gate passage with placeholders |
| **Network fig hairball** | Unreadable visualizations | Apply network quality standards |
| **Assume novelty** | Similar work already published | Check existing literature explicitly |
| **Skip data gate** | Data/code mismatch found in review | Verify claims before writing |
| **No checkpoints** | Long task hallucination | Keep `STATE.md`, `TASKS.md`, and `CHANGELOG.md` current |
| **Review too late** | Major issues found post-completion | Early gate validation |
| **Single-criterion screening** | 86% of relevant articles excluded (80 vs 496) | Use multi-criteria OR-logic inclusion for bibliometrics |
| **No exclusion audit** | Restrictive criteria silently lose data | Audit when >50% excluded |
| **Ignore user volume concerns** | "Why so few?" dismissed | Immediate screening review |
