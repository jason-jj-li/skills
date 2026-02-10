# Data Analysis Patterns

This file accumulates successful data analysis patterns discovered through usage.

## Last Updated
2025-01-18

## Common Patterns

### Variable Exploration
- Always check `str()` and `summary()` first
- Use `table()` for categorical variables
- Check missing values with `sum(is.na())` or `.isna().sum()`

### Data Cleaning
- Remove duplicates before analysis
- Handle outliers with IQR method: Q1 - 1.5*IQR, Q3 + 1.5*IQR
- Always verify data types after loading

### Visualization
- Scatter plots for numeric vs numeric
- Box plots for numeric vs categorical
- Bar charts for categorical distributions
- Histograms for single variable distributions

### Statistical Tests
- t-test for 2 groups
- ANOVA for 3+ groups
- Correlation for numeric vs numeric
- Chi-square for categorical vs categorical

## Language-Specific Patterns

### R (tidyverse)
```r
# Standard loading pattern
library(tidyverse)
df <- read_csv("data.csv")

# Pipe operations
df %>%
  filter(condition) %>%
  group_by(variable) %>%
  summarize(mean_val = mean(value))
```

### Python (pandas)
```python
# Standard loading pattern
import pandas as pd
df = pd.read_csv("data.csv")

# Method chaining
df = (df
    .query("condition")
    .groupby("variable")
    .agg(mean_val=("value", "mean"))
)
```

## Causal Inference Patterns

### DAG Construction
- Draw DAG before analysis
- Identify confounders (parents of both treatment and outcome)
- Never condition on colliders
- Consider mediators separately

### TTE Components
1. Eligibility criteria
2. Treatment strategies
3. Assignment strategy
4. Outcome definition

## QMD Workflow Patterns

### Chunk Options by Task
- Data loading: `message=FALSE, cache=TRUE`
- Exploration: `echo=FALSE, warning=FALSE`
- Plots: `fig.width=8, fig.height=6, fig.cap="Caption"`
- Tests: `echo=FALSE, warning=FALSE`

### Best Practices
- Test code in bash before adding to qmd
- Use chunk names for cross-referencing
- Render frequently to catch errors
