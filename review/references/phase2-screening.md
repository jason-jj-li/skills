# Phase 2: Literature Screening Methodology

## Overview

This document provides comprehensive guidance for screening literature in scoping and systematic reviews, adapted from PRISMA guidelines.

## Screening Workflow

### Phase 1: Preparation

1. **Define Inclusion Criteria**
   - Study design (RCT, cohort, case-control, cross-sectional)
   - Population characteristics
   - Intervention/exposure definitions
   - Outcome measures
   - Language (typically English)
   - Publication date range

2. **Define Exclusion Criteria**
   - Case reports with n < 5
   - Conference abstracts without full text
   - Non-original research (editorials, commentaries)
   - Duplicate publications
   - Retracted articles
   - Animal studies (if human-focused)

### Phase 2: Deduplication

Remove duplicate articles before screening:

```bash
# Use literature-review skill's deduplication
# Or manually check duplicates by DOI/title
```

**Documentation**:
```
Initial: 155 articles
After deduplication: 142 articles (13 duplicates removed)
```

### Phase 3: Title Screening

Review all titles against inclusion/exclusion criteria:

1. Import titles into spreadsheet or screening tool
2. Mark each title as:
   - **Include**: Meets inclusion criteria
   - **Exclude**: Does not meet criteria (record reason)
   - **Uncertain**: Need abstract review
3. Document exclusion reasons:
   - Wrong population
   - Wrong intervention
   - Wrong outcome
   - Wrong study design
   - Not original research

**Expected exclusion rate**: 30-50%

### Phase 4: Abstract Screening

For titles marked "Include" or "Uncertain":

1. Read abstracts carefully
2. Apply full inclusion/exclusion criteria
3. Mark each as:
   - **Include**: Proceed to full-text review
   - **Exclude**: Does not meet criteria (record specific reason)
4. Document detailed exclusion reasons

**Key considerations**:
- Study design appropriateness
- Sample size adequacy
- Relevance to research question
- Quality of methods description

**Expected exclusion rate**: 40-60% of remaining

### Phase 5: Full-Text Screening

Obtain and review full texts of included abstracts:

1. Retrieve full-text articles
2. Apply all inclusion/exclusion criteria rigorously
3. Assess study quality
4. Mark as:
   - **Include**: In final review
   - **Exclude**: Does not meet criteria (record specific reason)

**Quality assessment**:
- RCTs: Cochrane Risk of Bias tool
- Observational: Newcastle-Ottawa Scale
- Systematic reviews: AMSTAR 2

**Expected exclusion rate**: 20-40% of remaining

## PRISMA Flow Diagram

Create a flow diagram documenting screening process:

```
Identification (PubMed, other databases)
n = 155

↓ After duplicates removed
n = 142

↓ After title screening
n = 89 (53 excluded)

↓ After abstract screening
n = 52 (37 excluded)

↓ After full-text screening
n = 38 (14 excluded)

↓ Included in review
n = 38
```

## Screening Tools

### Option A: Quick Screening (Built-in)

```bash
python scripts/screen_papers.py process/phase1_pubmed_results.json \
  --include "exercise" "cognition" \
  --exclude "animal" "review" \
  --abstract-only \
  -o process/phase2_screened.json
```

**Pros**: Fast, keyword-based
**Cons**: Limited criteria, no PRISMA diagram

### Option B: Systematic Screening (Manual)

1. Use spreadsheet template
2. Track: PMID, Title, Abstract, Decision, Reason
3. Document each decision
4. Generate PRISMA diagram manually

**Pros**: Complete documentation, PRISMA compliant
**Cons**: Time-intensive

## Documentation Template

### Screening Log

| PMID | Title | Include? | Screening Phase | Exclusion Reason |
|------|-------|----------|-----------------|-----------------|
| 12345678 | Study title... | Yes | Full-text | - |
| 12345679 | Another study... | No | Abstract | Wrong population |

### Exclusion Reasons Summary

| Reason | Count | Percentage |
|--------|-------|------------|
| Wrong population | 15 | 28.3% |
| Wrong study design | 12 | 22.6% |
| No full text available | 8 | 15.1% |
| Not original research | 6 | 11.3% |
| Other | 12 | 22.6% |

## Best Practices

1. **Two reviewers**: For systematic reviews, have two reviewers screen independently
2. **Calibration**: Screen 10-20 articles together to establish consistency
3. **Documentation**: Record reasons for all exclusions
4. **Blinding**: Reviewers blinded to each other's decisions
5. **Reconciliation**: Resolve disagreements through discussion

## Common Issues

| Issue | Solution |
|-------|----------|
| Too many articles | Narrow inclusion criteria |
| Uncertain decisions | Error on the side of inclusion |
| No abstract available | Exclude or try to find full text |
| Non-English articles | Use translation or exclude |
| Multiple reports of same study | Select most complete version |

## References

- PRISMA: http://www.prisma-statement.org/
- Cochrane Handbook: https://training.cochrane.org/handbook
- Institute of Medicine: Finding What Works in Health Care
