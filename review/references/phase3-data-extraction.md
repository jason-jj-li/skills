# Phase 3: Data Extraction for Literature Reviews

## Overview

Data extraction is the systematic process of collecting relevant information from included studies into a structured format. This creates the evidence base for synthesis and analysis.

## Core Principle

**Standardize first, extract second.** Create your extraction form before extracting any data to ensure consistency across all studies.

---

## Preparation

### 1. Define Extraction Items

Identify what data you need based on your research question:

**Minimum Required Items:**
- Study ID (PMID, first author, year)
- Study design (RCT, cohort, case-control, cross-sectional)
- Population characteristics (sample size, age, setting)
- Intervention/exposure description
- Outcome measures (primary, secondary)
- Key results (effect sizes, confidence intervals, p-values)

**Optional Items (depending on review type):**
- Duration of follow-up
- Subgroup analyses
- Statistical methods
- Funding sources
- Conflict of interest declarations
- Quality assessment domains

### 2. Create Extraction Form

**Options:**
- **Spreadsheet**: Excel/Google Sheets for simple reviews
- **Database**: Access, FileMaker Pro for complex reviews
- **Specialized software**: Covidence, Rayyan, DistillerSR
- **Template**: Use Appendix E form below

**Best Practices:**
- Pilot test on 3-5 studies
- Include drop-down menus for common values
- Add free-text fields for unique data
- Include extraction notes column

---

## Standardized Extraction Form

### Template (Appendix E Format)

```
STUDY: Author______ Year______ DOI______
DESIGN: □RCT □Cohort □Case-Control □Cross-sectional □Other______
POPULATION: n=_____ Age_____ Setting_____
INTERVENTION/EXPOSURE: _____
OUTCOMES: Primary_____ Secondary_____
RESULTS: Effect size_____ 95%CI_____ p=_____
QUALITY: □Low □Moderate □High RoB
FUNDING/COI: _____
NOTES: _____
```

---

## Evidence Table Formats

### Format A: Summary Table (for scoping reviews)

| Study | Design | Population | Intervention | Outcomes | Key Findings |
|-------|--------|------------|--------------|----------|--------------|
| Author (Year) | RCT | n=100, Age 65+ | Exercise 3x/week | Cognitive function | Improved by 20% (p<0.05) |
| Author (Year) | Cohort | n=500, Age 50+ | Daily walking | Memory | HR=0.85 (95%CI: 0.75-0.96) |

### Format B: Detailed Table (for systematic reviews)

| Study | Design | Sample | Age | Setting | Intervention | Comparison | Duration | Primary Outcome | Effect Size (95% CI) | p-value | Quality |
|-------|--------|--------|-----|--------|--------------|------------|----------|-----------------|---------------------|---------|---------|
| Smith (2023) | RCT | 100 | 68 | Community | Aerobic exercise | Stretching | 12 weeks | MMSE score | +2.5 points (+1.2 to +3.8) | 0.001 | Low RoB |
| Jones (2024) | Cohort | 500 | 55 | Clinical | Physical activity | Sedentary | 5 years | Incident dementia | HR=0.78 (0.65-0.94) | 0.009 | Moderate |

### Format C: Quality Assessment Table

| Study | Selection Bias | Performance Bias | Detection Bias | Attrition Bias | Reporting Bias | Overall Quality |
|-------|----------------|------------------|----------------|----------------|----------------|-----------------|
| Smith (2023) | Low | Low | Low | Low | Low | High |
| Jones (2024) | Moderate | Low | Low | High | Low | Moderate |

---

## Quality Assessment Tools

### RCTs: Cochrane Risk of Bias 2.0

**Domains:**
1. Randomization process
2. Deviations from intended interventions
3. Missing outcome data
4. Measurement of the outcome
5. Selection of reported result

**Judgments:** Low | Some concerns | High

### Observational Studies: Newcastle-Ottawa Scale

**Domains:**
1. Selection (4 points max)
2. Comparability (2 points max)
3. Outcome (3 points max)

**Total score:** 0-9 points
- ≥7 points: High quality
- 5-6 points: Moderate quality
- ≤4 points: Low quality

### Systematic Reviews: AMSTAR 2

**Domains:** 16 critical and non-critical items

**Overall rating:** High | Moderate | Low | Critically low

---

## Extraction Workflow

### Step 1: Preparation
1. Finalize extraction form
2. Pilot test on 3-5 studies
3. Refine form based on pilot
4. Create data dictionary (define all variables)

### Step 2: Independent Extraction
- **Two reviewers** extract independently for systematic reviews
- **Single reviewer** acceptable for scoping reviews
- Document extraction time per study

### Step 3: Verification
- Compare extractions between reviewers
- Resolve discrepancies through discussion
- Consult third reviewer if needed
- Calculate inter-rater reliability (Cohen's kappa)

### Step 4: Data Cleaning
- Check for out-of-range values
- Standardize units of measurement
- Verify calculations (effect sizes, CIs)
- Document any data transformations

---

## Handling Common Issues

### Missing Data

| Issue | Solution |
|-------|----------|
| Incomplete reporting | Document as "not reported" |
| Contact authors | Send email, wait 2 weeks |
| Estimate from figures | Use digital ruler, document method |
| Exclude study | If >20% critical data missing |

### Inconsistent Reporting

| Issue | Solution |
|-------|----------|
| Different outcome measures | Convert to standardized effect size |
| Multiple time points | Pre-specify primary time point |
| Multiple intervention arms | Combine or analyze separately |
| Different units | Convert to common units |

### Complex Study Designs

| Design | Extraction Approach |
|--------|---------------------|
| Crossover RCT | Extract paired data only |
| Cluster RCT | Adjust for clustering effect |
| Non-inferiority trial | Extract margin and CI |
| Multi-arm trial | Extract all relevant arms |

---

## Data Synthesis Preparation

### For Meta-Analysis:
- Extract sample sizes (n) for each group
- Extract means and standard deviations (or convert from other statistics)
- Extract correlation coefficients for within-subject designs
- Document effect size metrics (OR, RR, MD, SMD)

### For Narrative Synthesis:
- Extract key findings in prose format
- Note study strengths and limitations
- Identify patterns across studies
- Document effect direction and magnitude

---

## Documentation Template

### Extraction Log

| Date | Study ID | Extractor | Verified | Notes |
|------|----------|-----------|----------|-------|
| 2024-01-15 | PMID: 12345678 | Reviewer A | Reviewer B | Missing SD, estimated from Figure 2 |
| 2024-01-16 | PMID: 12345679 | Reviewer B | Reviewer A | All data complete |

### Discrepancy Resolution

| Study ID | Field | Reviewer A | Reviewer B | Resolution | Final Value |
|----------|-------|------------|------------|------------|-------------|
| PMID: 12345678 | Sample size | 98 | 100 | Checked methods (2 lost to follow-up) | 98 |

---

## Best Practices

1. **Blind extraction**: Extractors blinded to each other's decisions
2. **Calibration**: Extract 10 studies together to establish consistency
3. **Documentation**: Record all decisions and deviations
4. **Version control**: Track changes to extraction form
5. **Backup**: Save extraction files in multiple locations
6. **Verification**: Double-check all entered values
7. **Transparency**: Publish extraction form as appendix

---

## Tools and Software

| Tool | Type | Cost | Best For |
|------|------|------|----------|
| Excel/Google Sheets | Spreadsheet | Free | Simple reviews, small teams |
| Covidence | Web-based | $ | Systematic reviews, screening + extraction |
| Rayyan | Web-based | Free | Screening, simple extraction |
| DistillerSR | Web-based | $$$ | Large teams, complex workflows |
| EPPI-Reviewer | Desktop | $ | Mixed methods, complex reviews |

---

## Common Pitfalls

| Pitfall | Prevention |
|---------|------------|
| Inconsistent units | Create data dictionary with specified units |
| Missing outliers | Check range during data entry |
| Copy-paste errors | Double-verify all entered values |
| Lost work | Autosave, cloud backup, version control |
| Ambiguous categories | Use drop-down menus with clear labels |

---

## Quality Control Checklist

Before proceeding to synthesis:
- [ ] All studies extracted
- [ ] Discrepancies resolved
- [ ] Data cleaned and standardized
- [ ] Missing data documented
- [ ] Quality assessments completed
- [ ] Inter-rater reliability calculated (if applicable)
- [ ] Extraction form archived
- [ ] Data ready for analysis

---

## References

- Cochrane Handbook: https://training.cochrane.org/handbook
- PRISMA: http://www.prisma-statement.org/
- MOOSE guidelines: Meta-analysis Of Observational Studies in Epidemiology
