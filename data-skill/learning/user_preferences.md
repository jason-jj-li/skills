# User Preferences

This file tracks user-specific preferences for data analysis workflows.

## Last Updated
2025-01-18

## Language Preferences
- **R**: When working with `.R` files, `tidyverse`, `ggplot2`, or `.qmd` with R chunks
- **Python**: When working with `.py` files, `pandas`, `seaborn`, or `.qmd` with Python chunks

## Tool Preferences
- **Package Manager**: uv (not pip)
- **Testing**: pytest (not unittest)
- **Linter**: ruff for Python
- **R Style**: tidyverse style guide

## Code Style Preferences
- Use snake_case for variable names
- Prefer pipe operators (%>% or .pipe()) over nested functions
- Always add comments explaining non-obvious operations
- Use meaningful variable names (no single letters except i, j in loops)

## Visualization Preferences
- Color scheme: WHO colors (blue: #4D9DE0, navy: #104E8B)
- Default figure size: 8x6 inches
- DPI: 300 for publications, 100 for drafts
- Font size: 11pt default
- Theme: minimal with clean grid

## Statistical Preferences
- Alpha level: 0.05
- Always report effect sizes with confidence intervals
- Use Welch's t-test by default (doesn't assume equal variance)
- Prefer non-parametric tests when n < 30 or non-normal data

## Workflow Preferences
- Always test code in bash before adding to qmd
- Use templates for common tasks
- Verify results before moving to next step
- Commit working code to git frequently

## MCP Query Preferences
- Use Context7 for package documentation
- Use Web-Search for latest research/methods
- Use Web-Reader for full documentation pages

## Causal Inference Preferences
- Always draw DAG first
- Use Target Trial Emulation framework
- Check DAG with dagitty if available
- Document assumptions explicitly

## QMD Preferences
- Always name chunks
- Add fig.cap for figures
- Use echo=FALSE for final reports
- Suppress warnings with warning=FALSE
- Test in bash before rendering
