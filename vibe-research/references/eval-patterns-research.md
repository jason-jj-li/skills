# Evaluation Patterns for Vibe-Research

## Core Gates

1. Traceability gate
- every major claim links to retrieved evidence
- citation verification passes

2. Method gate
- design/statistics match question type
- confounders and assumptions are documented

3. Reproducibility gate
- key steps rerunnable from commands or legacy scripts when needed
- outputs deterministic enough for review

4. Interpretation gate
- supports/refutes hypothesis with effect and uncertainty
- limitations explicitly acknowledged

## Metric Patterns

- Retrieval completeness: abstracts/DOI/duplicates coverage
- Screening precision proxy: retained set size + relevance threshold
- Citation integrity: missing citekeys = 0
- Reproducibility: pass^k on critical contracts

## pass@k vs pass^k

- pass@k: exploratory work where one successful run is useful
- pass^k: production/reporting work requiring consistent correctness
