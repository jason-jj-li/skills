#!/usr/bin/env python3
# Variable Exploration Template
# Purpose: Understand variable types, distributions, and patterns

import pandas as pd
import numpy as np

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file = "data.csv"
variable_name = "your_variable"  # Change to your variable name
# ============================================================================

# Load data
df = pd.read_csv(data_file)

print("\n" + "=" * 40)
print(f"VARIABLE EXPLORATION: {variable_name}")
print("=" * 40 + "\n")

# 1. Check dtype
print("Variable dtype:")
print(f"  {df[variable_name].dtype}\n")

# 2. Check unique values
print(f"Unique values (n={df[variable_name].nunique()}):")
print(df[variable_name].value_counts(dropna=False))

# 3. Check for missing values
missing_count = df[variable_name].isna().sum()
missing_pct = missing_count / len(df) * 100
print(f"\nMissing values:")
print(f"  Count: {missing_count}")
print(f"  Percentage: {missing_pct:.1f}%\n")

# 4. Check first few values
print("First 10 values:")
print(df[variable_name].head(10))

# 5. Summary statistics (if numeric)
if pd.api.types.is_numeric_dtype(df[variable_name]):
    print("\nSummary statistics:")
    print(df[variable_name].describe())
    print(f"\nMean: {df[variable_name].mean():.2f}")
    print(f"SD:   {df[variable_name].std():.2f}")

print("\n" + "=" * 40)
