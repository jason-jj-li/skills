# Causal Inference Reference

This guide covers causal inference methods for observational data analysis, including DAGs and Target Trial Emulation.

## Overview

Causal inference aims to estimate causal effects from observational data by addressing confounding and mimicking randomized controlled trials.

## Core Concepts

### Potential Outcomes Framework

For each individual, there are potential outcomes under different treatments:

| Notation | Meaning |
|----------|---------|
| Y(1) | Outcome if treated |
| Y(0) | Outcome if not treated |
| ITE | Individual Treatment Effect = Y(1) - Y(0) |
| ATE | Average Treatment Effect |
| ATT | Average Treatment Effect on the Treated |

**Fundamental Problem**: We only observe one potential outcome per person.

### DAGs (Directed Acyclic Graphs)

DAGs visualize causal relationships and identify confounders.

**Key elements**:
- **Nodes**: Variables
- **Arrows**: Direct causal effects
- **Confounder**: Causes both treatment and outcome
- **Collider**: Caused by two variables (should NOT be conditioned on)
- **Mediator**: On the causal path (part of the effect)

**Example DAG**:

```
    Confounder (C)
         ↙  ↘
    Treatment (T) → Outcome (Y)
         ↑
    Mediator (M)
```

**R packages**:
- `dagitty`: DAG analysis and adjustment sets
- `ggdag`: Plot DAGs with ggplot2

```r
library(dagitty)
library(ggdag)

# Define DAG
dag <- dagitty::dagitty("dag {
    C -> T
    C -> Y
    T -> Y
    T -> M -> Y
}")

# Plot
ggdag(dag) + theme_dag()

# Find adjustment sets
adjustmentSets(dag, exposure = "T", outcome = "Y")
```

**Python packages**:
- `dowhy`: DAG-based causal inference
- `networkx`: Graph visualization

```python
from dowhy import CausalModel
import networkx as nx
import matplotlib.pyplot as plt

# Create causal graph
causal_graph = nx.DiGraph()
causal_graph.add_edges_from([
    ("C", "T"),
    ("C", "Y"),
    ("T", "Y"),
    ("T", "M"),
    ("M", "Y")
])

# Visualize
nx.draw(causal_graph, with_labels=True, arrows=True)
```

## Target Trial Emulation (TTE)

Target Trial Emulation uses observational data to mimic a randomized controlled trial.

### The 4 Components of TTE

1. **Eligibility** - Define who would be eligible for the trial
2. **Treatment Strategies** - Define treatment protocols to compare
3. **Assignment** - Emulate randomization at baseline
4. **Outcomes** - Define follow-up period and endpoints

### TTE Workflow

```r
library(tidyverse)

# 1. Define eligibility criteria
eligible <- df %>%
  filter(age >= 18) %>%
  filter(!is.na(baseline_covariate))

# 2. Define treatment strategies
# Strategy A: Always treat
# Strategy B: Never treat
# Strategy C: Treat according to observed protocol

# 3. Emulate assignment at baseline
tte_data <- eligible %>%
  mutate(
    index_date = as.Date(baseline_date),
    strategy_A = 1,  # Everyone gets treatment
    strategy_B = 0,  # No one gets treatment
    strategy_C = ifelse(observed_treatment == 1, 1, 0)  # As observed
  )

# 4. Define outcomes at follow-up time
tte_data <- tte_data %>%
  mutate(
    follow_up_days = as.numeric(end_date - index_date),
    # Include only if within follow-up window
    included = follow_up_days >= 0 & follow_up_days <= 365
  )

# 5. Analyze outcomes (simple comparison)
tte_data %>%
  filter(included == 1) %>%
  group_by(strategy) %>%
  summarise(
    n = n(),
    mean_outcome = mean(outcome, na.rm = TRUE),
    sd_outcome = sd(outcome, na.rm = TRUE)
  )
```

### TTE with Cloning

Cloning creates multiple copies of each person under different strategies:

```r
# Create cloned dataset
cloned_data <- eligible %>%
  select(id, index_date, treatment, outcome, covariates) %>%
  # Clone for Strategy A
  mutate(
    strategy = "A",
    assigned_treatment = 1
  ) %>%
  bind_rows(
    # Clone for Strategy B
    eligible %>%
      select(id, index_date, treatment, outcome, covariates) %>%
      mutate(
        strategy = "B",
        assigned_treatment = 0
      )
  ) %>%
  # Inverse probability weighting
  group_by(id) %>%
  mutate(
    ipw = ifelse(treatment == assigned_treatment,
                  1,  # No weight if followed protocol
                  NA)  # Would need PS calculation
  )
```

## Common Causal Inference Methods

### 1. Propensity Score Matching

Matches treated and control units with similar propensity scores.

**R**:
```r
library(MatchIt)

# Estimate propensity scores
m.out <- matchit(treatment ~ confounder1 + confounder2 + confounder3,
                  data = df, method = "nearest", ratio = 1)

# Check balance
summary(m.out, un = TRUE)

# Get matched data
matched_data <- match.data(m.out)

# Estimate treatment effect
model <- lm(outcome ~ treatment, data = matched_data, weights = weights)
summary(model)
```

**Python**:
```python
from causalinference import CausalModel

causal = CausalModel(
    Y=df['outcome'].values,
    D=df['treatment'].values,
    X=df[['confounder1', 'confounder2', 'confounder3']].values
)

# Propensity score matching
causal.est_via_matching()
print(causal.estimates)
```

### 2. Inverse Probability Weighting (IPW)

Uses weights to create a pseudo-population where treatment is independent of confounders.

**R**:
```r
library(ipw)

# Estimate propensity scores
ps_model <- glm(treatment ~ confounder1 + confounder2 + confounder3,
                family = binomial(), data = df)
df$ps <- predict(ps_model, type = "response")

# Calculate weights
df$weight <- ifelse(df$treatment == 1,
                   1/df$ps,
                   1/(1 - df$ps))

# Stabilize weights (optional)
numerator <- ifelse(df$treatment == 1,
                     mean(df$treatment == 1),
                     mean(df$treatment == 0))
df$stabilized_weight <- numerator / df$ps

# Trim extreme weights
df$weight_trimmed <- ifelse(df$weight > quantile(df$weight, 0.99),
                              quantile(df$weight, 0.99),
                              df$weight)

# Estimate treatment effect
ipw_model <- lm(outcome ~ treatment, data = df, weights = weight_trimmed)
summary(ipw_model)
```

**Python**:
```python
from sklearn.linear_model import LogisticRegression
import statsmodels.formula.api as smf
import numpy as np

# Estimate propensity scores
ps_model = LogisticRegression()
ps_model.fit(df[['confounder1', 'confounder2', 'confounder3']], df['treatment'])
df['ps'] = ps_model.predict_proba(df[['confounder1', 'confounder2', 'confounder3']])[:, 1]

# Calculate weights
df['weight'] = np.where(
    df['treatment'] == 1,
    1 / df['ps'],
    1 / (1 - df['ps'])
)

# Estimate treatment effect
ipw_model = smf.wls('outcome ~ treatment', data=df, weights=df['weight'])
result = ipw_model.fit(cov_type='HC3')  # Robust SE
print(result.summary())
```

### 3. Instrumental Variables (IV)

**When to use**: When there is unmeasured confounding

**Requirements**:
1. **Relevance**: Instrument affects treatment
2. **Exclusion restriction**: Instrument affects outcome only through treatment
3. **Independence**: Instrument is independent of confounders

**R**:
```r
library(AER)

# Two-stage least squares
iv_model <- ivreg(outcome ~ treatment | instrument,
                  data = df)
summary(iv_model, diagnostics = TRUE)

# First stage F-statistic (check strength)
summary(lm(treatment ~ instrument + confounders, data = df))
```

**Python**:
```python
import linearmodels.iv as iv
import statsmodels.api as sm

# Add constant
X = sm.add_constant(df[['confounder1', 'confounder2']])

# Two-stage least squares
iv_model = iv.IV2SLS(
    df['outcome'],
    X,
    df['treatment'],
    df['instrument']
)
result = iv_model.fit()
print(result.summary)
```

### 4. Difference-in-Differences (DiD)

**Use case**: Pre-post comparisons with treatment and control groups

**Assumptions**:
1. **Parallel trends**: Treatment and control would have similar trends without treatment
2. **No simultaneous changes**: No other interventions at same time

**R**:
```r
library(fixest)

# DiD regression
did_model <- feols(outcome ~ treatment * post_period + confounder1 + confounder2,
                   data = df, fixed_effect = ~group_id)
summary(did_model)

# Visualize parallel trends
df %>%
  group_by(group_id, treatment, period) %>%
  summarise(mean_outcome = mean(outcome)) %>%
  ggplot(aes(x = period, y = mean_outcome, color = treatment, group = group_id)) +
  geom_line() +
  labs(title = "Parallel Trends Check")
```

**Python**:
```python
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt

# DiD regression
df['interaction'] = df['treatment'] * df['post_period']

did_model = smf.ols('outcome ~ treatment + post_period + interaction + confounder1 + confounder2',
                     data=df).fit(cov_type='cluster', cov_kwds={'groups': df['group_id']})
print(did_model.summary())

# Visualize parallel trends
for group in df['group_id'].unique():
    subset = df[df['group_id'] == group]
    for treatment in [0, 1]:
        treat_subset = subset[subset['treatment'] == treatment]
        plt.plot(treat_subset['period'], treat_subset['outcome'],
                marker='o', label=f'Group {group}, Treatment {treatment}')
plt.legend()
plt.title('Parallel Trends Check')
plt.show()
```

### 5. Regression Discontinuity (RD)

**Use case**: Treatment assigned based on threshold

**R**:
```r
library(rdrobust)

# Sharp RD
rd_model <- rdrobust(outcome ~ running_variable,
                     data = df, cutoff = threshold)
summary(rd_model)

# Plot
rdplot(df$outcome, df$running_variable, c = threshold)

# Fuzzy RD (with instrument)
rd_fuzzy <- rdrobust_fuzzy(outcome ~ running_variable,
                          treatment ~ running_variable,
                          data = df, cutoff = threshold)
summary(rd_fuzzy)
```

**Python**:
```python
import rdrobust
import matplotlib.pyplot as plt

# Sharp RD
rd_model = rdrobust.rdrobust(
    y=df['outcome'].values,
    x=df['running_variable'].values,
    c=threshold
)
print(rd_model)

# Plot
plt.scatter(df['running_variable'], df['outcome'], alpha=0.3)
plt.axvline(x=threshold, color='red', linestyle='--')
plt.xlabel('Running Variable')
plt.ylabel('Outcome')
plt.title('Regression Discontinuity')
plt.show()
```

## Mediation Analysis

Decompose total effect into direct and indirect (through mediator) effects.

**R**:
```r
library(mediation)

# Mediation analysis
med_fit <- mediate(
  model.m ~ mediator + treatment,
  model.y ~ outcome + treatment + mediator,
  treat = "treatment",
  mediator = "mediator",
  data = df
)
summary(med_fit)

# Proportion mediated
proportion_mediated <- med_fit$d0 / med_fit$d1
```

**Python**:
```python
import statsmodels.api as sm
from statsmodels.stats.mediation import Mediation

# Mediator model
M_model = sm.OLS(df['mediator'],
                   sm.add_constant(df[['treatment', 'confounder1', 'confounder2']]))
M_result = M_model.fit()

# Outcome model
Y_model = sm.OLS(df['outcome'],
                   sm.add_constant(df[['treatment', 'mediator', 'confounder1', 'confounder2']]))
Y_result = Y_model.fit()

# Mediation analysis
med = Mediation(df['outcome'].values,
                 df['mediator'].values,
                 df['treatment'].values,
                 X_sm=df[['confounder1', 'confounder2']].values)

med.fit(M_model, Y_model)
print(med.summary)
```

## Sensitivity Analysis

Test robustness to unmeasured confounding.

### E-value

Minimum strength of unmeasured confounder needed to explain away the result.

**R**:
```r
library(EValue)

# Calculate E-value from risk ratio
evalues <- evalues.RR(
    estimate = 1.5,     # Risk ratio
    lower = 1.2,        # Lower CI bound
    beersda_hops = FALSE
)
print(evalues)

# For hazard ratio
evalues_HR <- evalues.HR(estimate = 1.8, lower = 1.3)
print(evalues_HR)
```

### Negative Control Outcomes

Test for residual confounding using outcomes that should NOT be affected by treatment.

```r
# Test outcome that should NOT be affected
null_model <- lm(null_outcome ~ treatment + confounders, data = df)
summary(null_model)

# If significant, suggests unmeasured confounding
```

### Positive Control Outcomes

Test using outcomes known to be affected by treatment (validation).

## Best Practices

1. **Draw DAG first** - Identify confounders, colliders, mediators
2. **Pre-specify analysis** - Define TTE protocol before looking at data
3. **Check assumptions** - Parallel trends, exclusion restriction, balance
4. **Sensitivity analysis** - Test robustness to unmeasured confounding
5. **Report transparently** - Show both crude and adjusted estimates
6. **Avoid Table 2 fallacy** - Don't adjust for mediators when estimating total effect

## MCP Usage Guide

When this reference doesn't have enough detail, use available MCP tools to find more information.

### Context7 - Query Package Documentation

Use for: Looking up R/Python package functions, parameters, and examples.

**Available MCP functions**:
- `resolve-library-id` - Find package ID
- `query-docs` - Query package documentation

**Common R packages for causal inference**:

| Package | Use for | Context7 Query |
|---------|---------|-----------------|
| `dagitty` | DAG analysis | `/cran/dagitty` |
| `ggdag` | DAG plotting | `/cran/ggdag` |
| `MatchIt` | Propensity score matching | `/cran/MatchIt` |
| `ipw` | Inverse probability weighting | `/cran/ipw` |
| `AER` | Instrumental variables | `/cran/AER` |
| `fixest` | DiD regression | `/cran/fixest` |
| `rdrobust` | Regression discontinuity | `/cran/rdrobust` |
| `mediation` | Mediation analysis | `/cran/mediation` |
| `EValue` | E-value calculations | `/cran/EValue` |

**Common Python packages**:

| Package | Use for | Context7 Query |
|---------|---------|-----------------|
| `causalinference` | Causal inference | `causalinference` |
| `linearmodels.iv` | Instrumental variables | `linearmodels` |
| `dowhy` | DAG-based inference | `dowhy` |
| `statsmodels` | Statistical models | `statsmodels` |
| `scikit-learn` | Machine learning | `scikit-learn` |

**Example queries**:
```
"How to use adjustmentSets() in dagitty?"
"Propensity score matching with MatchIt package examples"
"Instrumental variables two-stage least squares with AER"
"Difference-in-differences with fixest package"
```

### Web-Search - Find Latest Research

Use for: Finding recent papers, tutorials, best practices.

**Example queries**:
```
"Target Trial Emulation observational data 2024"
"DAG confounder selection best practices"
"propensity score matching assumptions checklist"
"instrumental variable weak instrument test"
"E-value interpretation causal inference"
```

### Web-Reader - Read Documentation

Use for: Reading full documentation pages, tutorials, vignettes.

**Example URLs**:
- `https://cran.r-project.org/web/packages/dagitty/vignettes/dagitty.html`
- `https://cran.r-project.org/web/packages/MatchIt/vignettes/MatchIt.html`
- Package vignettes and tutorials

## Decision Support

### Choosing the Right Method

```
┌─ What is your research question?
│
├─ "What is the causal effect of X on Y?"
│  └─→ Potential Outcomes Framework
│
├─ "What variables should I adjust for?"
│  └─→ DAG (dagitty/ggdag)
│     → MCP: Search "DAG confounder selection guidelines"
│
├─ "Can I emulate a randomized trial?"
│  └─→ Target Trial Emulation
│     → MCP: Search "Target Trial Emulation observational data"
│
├─ "I have confounding, what do I do?"
│  ├─ Many confounders → PS Matching / IPW
│  ├─ Unmeasured confounding → Instrumental Variables
│  └─ Time series data → Difference-in-Differences
│
├─ "Treatment assigned by threshold?"
│  └─→ Regression Discontinuity
│
└─ "How sensitive are my results to unmeasured confounding?"
   └─→ E-value, Negative Controls
```

### Getting Help with MCP

When stuck with a causal inference problem:

1. **Define your question clearly**
   - Example: "How do I check balance after propensity score matching?"

2. **Choose the right MCP tool**
   - Package syntax → Context7
   - Recent methods/papers → Web-Search
   - Full documentation → Web-Reader

3. **Iterate based on answers**
   - Get code example → Test via bash
   - Check assumptions → Modify as needed
   - Integrate into qmd → Render

## References

- Hernán MA, Robins JM (2020). *Causal Inference: What If*
- Ding P, Miratrix LJ (2023). "To Causal Inference and Back Again with Target Trial Emulation"
- Imbens GW, Rubin DB (2015). *Causal Inference for Statistics, Social, and Biomedical Sciences*
- Pearl J (2009). *Causality: Models, Reasoning, and Inference*
