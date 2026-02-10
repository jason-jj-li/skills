# Workflow Phases Guide

This guide explains when to use each analysis phase and how to navigate them flexibly.

## Phase Decision Tree

```
Start
  ↓
Do you have data loaded?
  → No → Phase 1: Understand Data
  → Yes → Is data clean?
            → No → Phase 2: Prepare Data
            → Yes → What do you need?
                      → Summarize patterns → Phase 3: Analyze
                      → Visualize → Phase 4: Visualize
                      → Explain findings → Phase 5: Report
```

## When to Use Each Phase

### Phase 1: Understand Data

**Trigger**: New dataset or unfamiliar data

**Actions**:
- Load data: `read_csv()`, `pd.read_csv()`
- Check structure: `head()`, `info()`, `str()`
- Explore variables: Use `explore_variable` template
- Identify issues: Missing values, wrong types, inconsistencies

**Output**: Understanding of data quality and structure

---

### Phase 2: Prepare Data

**Trigger**: Data quality issues found or transformations needed

**Actions**:
- Handle missing: Drop or impute
- Remove duplicates
- Fix types: Convert to numeric, factor, datetime
- Recode variables: Chinese→English, string→numeric
- Create derived: Age from DOB, percentages, groups

**Output**: Clean `plot_data` ready for analysis

---

### Phase 3: Analyze

**Trigger**: Need statistical summaries or tests

**Actions**:
- Descriptive: Summary statistics, frequencies
- Group comparisons: t-tests, ANOVA
- Relationships: Correlation, regression
- Significance: Use `statistical_test` template

**Output**: Statistical results with p-values

---

### Phase 4: Visualize

**Trigger**: Need to show patterns graphically

**Chart Selection Guide**:

| Question | Chart Type | Template |
|----------|-----------|----------|
| Relationship between 2 numeric variables | Scatter | `plot_scatter` |
| Compare categories | Bar | `plot_bar` |
| Show distributions by group | Box | `plot_box` |
| Show single distribution | Histogram | Generate custom |
| Time series trend | Line | Generate custom |

**Actions**:
- Pick appropriate chart type
- Use template or AI-generate
- Apply themes
- Export at 300+ DPI

**Output**: High-resolution figure files

---

### Phase 5: Report

**Trigger**: Need to communicate findings

**Actions**:
- Interpret statistical significance
- Write clear, concise text
- Include figures and tables
- Format for publication

**Output**: Final report or presentation

## Common Workflows

### Quick Exploration
```
Phase 1 → Phase 4 (visualize immediately)
```

### Full Analysis
```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
```

### Just Plotting
```
Skip to Phase 4 if data is already clean
```

### Statistical Report
```
Phase 1 → Phase 2 → Phase 3 → Phase 5
```

## Phase Skipping Rules

- **Can skip Phase 2** if data is already clean
- **Can skip Phase 3** if only visualization needed
- **Can skip Phase 4** if only statistics needed
- **Never skip Phase 1** with completely unknown data

## Template Matching by Phase

| Phase | Templates Available |
|-------|---------------------|
| Phase 1 | `explore_variable` |
| Phase 2 | `clean_data`, `process_data` |
| Phase 3 | `statistical_test` |
| Phase 4 | `plot_scatter`, `plot_bar`, `plot_box` |
| Phase 5 | None (use AI to write) |
