# Statistical Tests Selection Guide

This guide helps you choose the right statistical test for your data.

## Decision Tree

```
What type of data do you have?
│
├─ Categorical vs Categorical → Chi-Square Test
├─ Numeric vs Categorical (2 groups) → t-test (Independent)
├─ Numeric vs Categorical (2 groups, paired) → t-test (Paired)
├─ Numeric vs Categorical (3+ groups) → ANOVA
├─ Numeric vs Numeric → Correlation (Pearson/Spearman)
└─ Numeric vs Numeric (controlling for other vars) → Regression
```

## Test Quick Reference

| Test | Purpose | Data Required | Template |
|------|---------|---------------|----------|
| **Chi-Square** | Test independence between categorical variables | 2 categorical variables | `statistical_test` |
| **t-test (Independent)** | Compare means between 2 groups | 1 numeric, 1 binary (2 groups) | `statistical_test` |
| **t-test (Paired)** | Compare before/after measurements | 2 numeric (same subjects) | Generate custom |
| **ANOVA** | Compare means across 3+ groups | 1 numeric, 1 categorical (3+ groups) | Generate custom |
| **Pearson Correlation** | Linear relationship between 2 numeric | 2 numeric variables | `statistical_test` |
| **Spearman Correlation** | Monotonic relationship (non-linear) | 2 numeric variables | Generate custom |
| **Regression** | Predict numeric outcome from predictors | 1 numeric outcome, 1+ predictors | Generate custom |

## When to Use Each Test

### Chi-Square Test of Independence

**Use when**: Both variables are categorical

**Example**: Is there an association between gender (male/female) and treatment outcome (success/failure)?

**R**: `chisq.test(contingency_table)`
**Python**: `stats.chi2_contingency(contingency_table)`

---

### Independent t-test

**Use when**:
- Comparing means of 2 independent groups
- Outcome is numeric
- Groups are mutually exclusive

**Examples**:
- Do males and females have different average heights?
- Is there a difference in test scores between control and treatment groups?

**R**: `t.test(outcome ~ group)`
**Python**: `stats.ttest_ind(group1, group2)`

**Assumptions**:
- Normal distribution (or large sample size)
- Equal variances (use Welch's t-test if violated)

---

### Paired t-test

**Use when**:
- Comparing before/after measurements
- Same subjects measured twice

**Examples**:
- Does a weight loss program reduce weight?
- Does a training program improve test scores?

**R**: `t.test(before, after, paired = TRUE)`
**Python**: `stats.ttest_rel(before, after)`

---

### ANOVA

**Use when**:
- Comparing means across 3+ independent groups
- Outcome is numeric

**Examples**:
- Do three different teaching methods produce different test scores?
- Is there a difference in satisfaction across 5 age groups?

**R**: `aov(outcome ~ group)`
**Python**: `stats.f_oneway(group1, group2, group3)`

---

### Pearson Correlation

**Use when**:
- Testing linear relationship between 2 numeric variables
- Both variables are continuous and approximately normal

**Examples**:
- Is height correlated with weight?
- Does study time correlate with exam scores?

**R**: `cor.test(var1, var2, method = "pearson")`
**Python**: `stats.pearsonr(var1, var2)`

**Interpretation**:
- r = 0.1: Weak correlation
- r = 0.3: Moderate correlation
- r = 0.5+: Strong correlation

---

### Spearman Correlation

**Use when**:
- Testing monotonic (not necessarily linear) relationship
- At least one variable is ordinal or non-normal

**Examples**:
- Is income rank correlated with education level?
- Does ranking correlate with performance score?

**R**: `cor.test(var1, var2, method = "spearman")`
**Python**: `stats.spearmanr(var1, var2)`

---

## Interpreting p-values

| p-value | Interpretation |
|---------|---------------|
| p < 0.001 | Very strong evidence against null hypothesis |
| p < 0.01 | Strong evidence against null hypothesis |
| p < 0.05 | Moderate evidence against null hypothesis |
| p ≥ 0.05 | Insufficient evidence to reject null |

**Note**: p-value does NOT measure effect size or practical significance. Always report effect sizes with confidence intervals.

## Common Mistakes

1. **Using t-test for 3+ groups** → Use ANOVA instead
2. **Using Pearson on non-normal data** → Use Spearman
3. **Using parametric tests on tiny samples** → Consider non-parametric alternatives
4. **Not checking assumptions** → Always verify normality, equal variances
5. **p-hacking** → Pre-register your analysis plan

## Effect Size Guidelines

| Effect Size | Small | Medium | Large |
|-------------|-------|--------|-------|
| **Cohen's d** (t-test) | 0.2 | 0.5 | 0.8 |
| **Pearson r** | 0.1 | 0.3 | 0.5 |
| **Eta-squared** (ANOVA) | 0.01 | 0.06 | 0.14 |

Always report effect sizes alongside p-values.
