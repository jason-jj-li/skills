# MCP Query Log

This file records successful MCP queries for future reference.

## Last Updated
2025-01-18

## Context7 Queries

### R Packages

| Query | Purpose | Result |
|-------|---------|--------|
| `/cran/dagitty` | DAG analysis | Found adjustmentSets() function |
| `/cran/ggdag` | DAG plotting | Found theme_dag() and ggdag() |
| `/cran/MatchIt` | Propensity score matching | Found matchit() function |
| `/cran/ipw` | IPW estimation | Found ipwpoint() function |
| `/cran/fixest` | DiD regression | Found feols() for fast estimation |
| `/cran/rdrobust` | Regression discontinuity | Found rdrobust() function |

### Python Packages

| Query | Purpose | Result |
|-------|---------|--------|
| `pandas` | Data manipulation | Found groupby and agg patterns |
| `seaborn` | Visualization | Found boxplot with hue parameter |
| `statsmodels` | Statistical models | Found ols() and t_test_ind() |
| `scikit-learn` | Machine learning | Found LinearRegression for g-formula |

## Web-Search Queries

### Causal Inference

| Query | Purpose | Result |
|-------|---------|--------|
| "Target Trial Emulation observational data 2024" | TTE methods | Found recent papers on TTE |
| "DAG confounder selection best practices" | DAG guidance | Found dagitty documentation |
| "propensity score matching assumptions checklist" | PSM validation | Found positivity/overlap checks |

### Data Analysis

| Query | Purpose | Result |
|-------|---------|--------|
| "ggplot2 facet wrap multiple plots" | Multi-panel figures | Found facet_wrap() syntax |
| "pandas groupby multiple aggregations" | Data aggregation | Found .agg() with named tuples |
| "quarto figure options reference" | QMD figures | Found fig.width, fig.height, fig.cap |

## Web-Reader Queries

| URL | Purpose | Key Takeaway |
|-----|---------|--------------|
| cran.r-project.org/web/packages/dagitty | DAGitty docs | Use adjustmentSets() for minimal adjustment |
| cran.r-project.org/web/packages/ggdag | ggdag docs | Load ggplot2 before ggdag for ggsave() |
| quarto.org/docs/computations | QMD options | Set echo=FALSE to hide code in reports |

## Query Patterns

### When to Use Context7
- Package function syntax
- Parameter names and defaults
- Return value structure
- Code examples

### When to Use Web-Search
- Latest research papers
- Best practice guides
- Comparison of methods
- Recent package updates

### When to Use Web-Reader
- Full documentation pages
- Package vignettes
- Tutorial articles
- API references

## Failed Queries (for reference)

| Query | Issue | Solution |
|-------|-------|----------|
| `/cran/tte` | Package doesn't exist | Use general web search instead |
| "R survival analysis" | Too broad | Add specific method name |
| `pandas time series` | Multiple results | Specify function name like resample() |

## Query Templates

### For Package Functions
```
"{function_name} in {package_name} examples"
"{package_name} {task} syntax"
```

### For Methods/Concepts
```
"{method_name} {domain} best practices"
"{concept} vs {alternative} comparison"
```

### For Problems
```
"{error message} {package} solution"
"{task} in {language} example code"
```
