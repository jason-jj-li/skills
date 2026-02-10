#!/usr/bin/env python3
# Data Processing Template
# Purpose: Filter, recode, transform, and aggregate data

import pandas as pd

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file = "data.csv"
# ============================================================================

# Load data
df = pd.read_csv(data_file)

# ============================================================================
# DATA PROCESSING PIPELINE
# ============================================================================
plot_data = df.copy()

# 1. Filter observations
# plot_data = plot_data[plot_data['variable_name'].notna()]

# 2. Mutate / Recode variables
plot_data = plot_data.assign(
    # Example: Chinese to English labels
    # new_var=plot_data['variable_name'].map({
    #     '中文值1': 'English Label 1',
    #     '中文值2': 'English Label 2'
    # }),

    # Example: Create binary variable
    # binary_var=plot_data['variable_name'].apply(lambda x: 1 if x == '是' else 0),

    # Example: Calculate derived variable
    # percentage=lambda x: x['n'] / x['n'].sum() * 100
)

# 3. Group and aggregate
# plot_data = plot_data.groupby('grouping_var').agg({
#     'numeric_var': ['count', 'mean', 'std']
# }).reset_index()

# 4. Arrange
# plot_data = plot_data.sort_values('count', ascending=False)

# ============================================================================
# VERIFY OUTPUT
# ============================================================================
print("\n" + "=" * 40)
print("PROCESSED DATA")
print("=" * 40 + "\n")

print(plot_data)

print(f"\nDimensions: {plot_data.shape[0]} rows x {plot_data.shape[1]} cols")
print(f"Column names: {list(plot_data.columns)}")

# Export for plotting
# plot_data.to_csv("plot_data.csv", index=False)

print("\n" + "=" * 40)
