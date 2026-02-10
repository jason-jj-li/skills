---
name: data-skill
description: AI-driven hybrid data analysis workflow supporting R (tidyverse and ggplot2) and Python (pandas and seaborn). Provides templates for 70 percent of common tasks including variable exploration, data cleaning, processing, and plotting. Also generates AI code for custom needs. Uses bash testing with iteration and MCP Context7 for function references. Use when analyzing data files, creating visualizations, cleaning and transforming data, running statistical tests, creating publication quality figures, or working with Quarto qmd documents.
---

# Data Analysis Workflow

Hybrid approach combining **templates** for common patterns with **AI generation** for custom needs.

## How It Works

```text
User Request → Pattern Matching → [Template Available?]
                                          ↓
                    Yes (Quick Start) ←──→ No (AI Generate)
                          ↓                    ↓
                          └────→ Bash Test ←────┘
                                  ↓
                           [Success?]
                                  ↓
                    No ←──────────→ Yes
                    ↓                  ↓
              Iterate/Fix         Return Working Code
```

## Quick Start

### 1. Detect Language

**R**: When user mentions `tidyverse`, `ggplot2`, `dplyr`, `.R` files
**Python**: When user mentions `pandas`, `seaborn`, `.py` files

Ask if uncertain.

### 2. Pattern Matching

Check if the request matches a **common template**:

| Task | Use Template |
|------|-------------|
| Explore variable types and distributions | `templates/*/explore_variable.*` |
| Clean missing values and outliers | `templates/*/clean_data.*` |
| Recode/transform variables | `templates/*/process_data.*` |
| Create scatter plot | `templates/*/plot_scatter.*` |
| Create bar chart | `templates/*/plot_bar.*` |
| Create box plot | `templates/*/plot_box.*` |
| Run t-test/correlation | `templates/*/statistical_test.*` |
| Plot causal DAG | `templates/*/plot_dag.*` |
| Target Trial Emulation | `templates/*/tte_cloning.*` |

**If match found**: Provide template, let user modify, run via bash.

**If no match**: AI generates custom code (use MCP Context7 for syntax lookup).

### 3. Test and Iterate

```bash
# Write code to temp file
# Run: Rscript temp.R or python temp.py
# Analyze output/errors
# Fix and retry if needed
```

### 4. QMD Integration (When Working in Quarto)

**When user is working with qmd documents**:

1. **Bash test** the code first to ensure it works
2. **Edit qmd file** directly with the working code
3. **Render** to verify: `quarto render report.qmd`
4. **Iterate** if render fails

See [QMD Integration](#qmd-integration) below for chunk options and best practices.

## Analysis Phases

Instead of rigid steps, use **flexible phases**:

### Phase 1: Understand Data
- Load and inspect data structure
- Explore variable types and distributions
- Identify quality issues (missing values, outliers)

### Phase 2: Prepare Data
- Clean missing values and outliers
- Transform and recode variables
- Create derived features

### Phase 3: Analyze
- Descriptive statistics
- Hypothesis testing
- Modeling (if needed)

### Phase 4: Visualize
- Create appropriate plots for the data type
- Apply publication-ready themes
- Export high-resolution figures

### Phase 5: Report
- Interpret statistical results
- Write narrative text
- Compile final report

## When to Use Templates vs AI Generation

### Use Templates For
- Standard variable exploration
- Common chart types (scatter, bar, box)
- Routine data cleaning
- Basic statistical tests

### Use AI Generation For
- Custom transformations
- Advanced or unusual visualizations
- Complex statistical models
- Domain-specific analysis patterns

## MCP Integration

When uncertain about function syntax, query Context7 MCP:

- "How to use geom_smooth() in ggplot2?"
- "pandas groupby and aggregate syntax"
- "seaborn boxplot with hue parameter"

## QMD Integration

### QMD Workflow

```text
1. Generate/test code via bash
2. Edit qmd with working code
3. Render: quarto render report.qmd
4. Iterate if needed
```

### Recommended Chunk Options

#### R Chunks

```markdown
```{r chunk-name, fig.width=8, fig.height=6, fig.cap="Caption"}
# Code here
```
```

#### Python Chunks

```markdown
```{python chunk-name, fig.width=8, fig.height=6, fig.cap="Caption"}
# Code here
```
```

### Auto-Recommended Options by Chart Type

| Chart Type | fig.width | fig.height | Notes |
|------------|-----------|------------|-------|
| Scatter plot | 8 | 6 | Standard |
| Bar chart | 8 | 6 | Add `fig.cap` |
| Box plot | 8 | 6 | Add `fig.cap` |
| Histogram | 8 | 5 | Taller not needed |
| Line plot | 10 | 6 | Wider for time series |
| Multi-panel | 12 | 8 | Larger for facets |

### QMD Best Practices

1. **Always use chunk names** for cross-referencing
2. **Add fig.cap** for figure captions in reports
3. **Test code** in bash before adding to qmd
4. **Use echo=FALSE** to hide source code if needed
5. **Use warning=FALSE** to suppress warnings in output

### Complete Chunk Options Reference

#### Output Control Options

| Option | Values | Default | Purpose |
|--------|--------|---------|---------|
| `echo` | TRUE/FALSE | TRUE | Show/hide source code |
| `eval` | TRUE/FALSE | TRUE | Run code or skip |
| `include` | TRUE/FALSE | TRUE | Show code output |
| `warning` | TRUE/FALSE | TRUE | Show warning messages |
| `message` | TRUE/FALSE | TRUE | Show package load messages |
| `error` | TRUE/FALSE | TRUE | Stop on errors or continue |
| `collapse` | TRUE/FALSE | FALSE | Merge output with code |
| `results` | markup/asis/hide/hold | markup | How to display output |

#### Figure Options

| Option | Purpose |
|--------|---------|
| `fig.width` | Figure width in inches |
| `fig.height` | Figure height in inches |
| `fig.cap` | Figure caption text |
| `fig.alt` | Alt text for accessibility |
| `fig.align` | left/right/center/default |
| `out.width` | Output width (e.g., "80%") |
| `out.height` | Output height (e.g., "auto") |

#### Cache Options

| Option | Purpose |
|--------|---------|
| `cache` | TRUE/FALSE - cache results |
| `cache.path` | Custom cache directory |
| `dependson` | Chunk dependencies for cache |

### Common Chunk Patterns

Publication figure (no code, with caption):

```markdown
```{r my-plot, echo=FALSE, fig.width=8, fig.height=6, fig.cap="My figure caption"}
# Your plot code here
```
```

Data loading (suppress messages, with cache):

```markdown
```{r load-data, message=FALSE, cache=TRUE}
# Your data loading code here
```
```

Analysis (hide code, show output):

```markdown
```{r analysis, echo=FALSE, warning=FALSE}
# Your analysis code here
```
```

Draft mode (quick render, no cache):

```markdown
```{r draft, cache=FALSE, eval=TRUE}
# Your code here
```
```

Setup (run but don't show):

```markdown
```{r setup, include=FALSE}
library(tidyverse)
```
```

## Bundled Resources

### Templates (`templates/`)

**R templates** (`templates/r/`):
- `explore_variable.R` - Variable type and distribution analysis
- `clean_data.R` - Handle missing values, duplicates, outliers
- `process_data.R` - Filter, recode, transform
- `plot_scatter.R` - Scatter plots with themes
- `plot_bar.R` - Bar charts for categorical data
- `plot_box.R` - Box plots for distributions
- `statistical_test.R` - t-tests, correlations
- `plot_dag.R` - Causal DAG visualization with dagitty/ggdag
- `tte_cloning.R` - Target Trial Emulation cloning

**Python templates** (`templates/python/`):
- Mirror of R templates using pandas/seaborn/networkx

### References (`references/`)

- `workflow_phases.md` - When to do what, decision trees
- `data_patterns.md` - Common transformation patterns
- `statistical_tests.md` - Test selection guide

### Assets (`assets/`)

- `themes/theme_r.R` - ggplot2 publication theme
- `themes/theme_python.py` - seaborn/matplotlib theme

### Learning (`learning/`)

Domain-specific knowledge accumulated through usage:

- `analysis_patterns.md` - Successful analysis patterns
- `user_preferences.md` - User-specific preferences
- `mcp_queries.md` - Successful MCP queries for reference

**Note**: This directory works with the `reflect` skill for automatic learning from corrections.

## Best Practices

1. **Always test code** via bash before presenting to user
2. **Iterate on errors** - analyze output, fix, retry
3. **Use MCP for syntax** - don't guess function parameters
4. **Prefer templates** for common tasks (faster, tested)
5. **Generate custom code** only when templates don't fit
6. **For qmd**: Test in bash, then edit and render
