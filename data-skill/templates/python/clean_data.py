#!/usr/bin/env python3
# Data Cleaning Template
# Purpose: Handle missing values, duplicates, and outliers

import pandas as pd
import numpy as np

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file = "data.csv"
# ============================================================================

# Load data
df = pd.read_csv(data_file)

print("\n" + "=" * 40)
print("DATA CLEANING REPORT")
print("=" * 40 + "\n")

# Initial dimensions
print(f"Original dimensions: {df.shape[0]} rows x {df.shape[1]} cols\n")

# ============================================================================
# 1. Remove Duplicates
# ============================================================================
df_clean = df.drop_duplicates()
removed_dup = len(df) - len(df_clean)
print(f"Duplicates removed: {removed_dup}")

# ============================================================================
# 2. Handle Missing Values
# ============================================================================
missing_by_col = df_clean.isna().sum()[df_clean.isna().sum() > 0].sort_values(ascending=False)

if len(missing_by_col) > 0:
    print("\nMissing values by column:")
    print(missing_by_col)
else:
    print("\nNo missing values found.")

# Option: Drop rows with missing values
# df_clean = df_clean.dropna()

# Option: Fill missing values
# for col in df_clean.select_dtypes(include=[np.number]).columns:
#     df_clean[col] = df_clean[col].fillna(df_clean[col].mean())

# ============================================================================
# 3. Detect Outliers (for numeric columns)
# ============================================================================
numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()

if numeric_cols:
    print("\nOutlier detection (IQR method):")
    for col in numeric_cols:
        Q1 = df_clean[col].quantile(0.25)
        Q3 = df_clean[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        outliers = ((df_clean[col] < lower) | (df_clean[col] > upper)).sum()
        if outliers > 0:
            print(f"  {col}: {outliers} outliers")

# Final dimensions
print(f"\nClean dimensions: {df_clean.shape[0]} rows x {df_clean.shape[1]} cols")
print(f"Data removed: {(1 - len(df_clean)/len(df)) * 100:.1f}%")

print("\n" + "=" * 40)

# Save cleaned data
# df_clean.to_csv("data_cleaned.csv", index=False)
