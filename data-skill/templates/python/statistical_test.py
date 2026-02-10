#!/usr/bin/env python3
# Statistical Test Template
# Purpose: Run common hypothesis tests

import pandas as pd
from scipy import stats

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file = "data.csv"

# Test type: "t_test", "correlation", "chisquare"
test_type = "t_test"

# For t-test
group_var = "group"       # Binary grouping variable
numeric_var = "outcome"   # Numeric outcome variable

# For correlation
var1 = "variable1"
var2 = "variable2"
# ============================================================================

# Load data
df = pd.read_csv(data_file)

print("\n" + "=" * 40)
print("STATISTICAL TEST RESULTS")
print("=" * 40 + "\n")

if test_type == "t_test":
    # Independent samples t-test
    print("Independent Samples t-test")
    print("-" * 40)
    print(f"Grouping variable: {group_var}")
    print(f"Outcome variable: {numeric_var}\n")

    # Group means
    group_means = df.groupby(group_var)[numeric_var].agg(['count', 'mean', 'std'])
    print(group_means)

    # Run t-test
    groups = df[group_var].unique()
    group1 = df[df[group_var] == groups[0]][numeric_var].dropna()
    group2 = df[df[group_var] == groups[1]][numeric_var].dropna()

    t_stat, p_value = stats.ttest_ind(group1, group2)

    print(f"\nt-statistic: {t_stat:.4f}")
    print(f"p-value: {p_value:.4f}")

elif test_type == "correlation":
    # Pearson correlation
    print("Pearson Correlation")
    print("-" * 40)
    print(f"Variable 1: {var1}")
    print(f"Variable 2: {var2}\n")

    # Drop NA pairs
    valid_data = df[[var1, var2]].dropna()

    # Run correlation
    corr, p_value = stats.pearsonr(valid_data[var1], valid_data[var2])

    print(f"Correlation: {corr:.4f}")
    print(f"t-statistic: {corr * ((len(valid_data)-2)/(1-corr**2))**0.5:.4f}")
    print(f"p-value: {p_value:.4f}")

elif test_type == "chisquare":
    # Chi-square test of independence
    print("Chi-Square Test of Independence")
    print("-" * 40)
    print(f"Variables: {var1}, {var2}\n")

    # Create contingency table
    contingency_table = pd.crosstab(df[var1], df[var2])
    print(contingency_table)

    # Run chi-square test
    chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)

    print(f"\nChi-square: {chi2:.4f}")
    print(f"Degrees of freedom: {dof}")
    print(f"p-value: {p_value:.4f}")

print("\n" + "=" * 40)
