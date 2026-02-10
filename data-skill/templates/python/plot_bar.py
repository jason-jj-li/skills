#!/usr/bin/env python3
# Bar Chart Template
# Purpose: Create bar chart for categorical data

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file = "plot_data.csv"
category_var = "category"      # Change to your category variable
value_var = "value"            # Change to your value variable
# ============================================================================

# Load data
df = pd.read_csv(data_file)

# ============================================================================
# THEME SETTINGS
# ============================================================================
sns.set_theme(style="whitegrid")
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.titleweight'] = 'bold'

# WHO color scheme
who_colors = {
    'blue': '#4D9DE0',
    'navy': '#104E8B'
}

# ============================================================================
# CREATE PLOT
# ============================================================================
fig, ax = plt.subplots(figsize=(8, 6))

bars = sns.barplot(data=df, x=category_var, y=value_var,
                   color=who_colors['blue'], ax=ax)

# Add value labels on bars
for bar in bars.patches:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height)}',
            ha='center', va='bottom', fontsize=10)

ax.set_title("Bar Chart Title")
ax.set_xlabel("Category Label")
ax.set_ylabel("Value Label")
ax.spines['top'].set_visible(True)
ax.spines['right'].set_visible(True)

plt.xticks(rotation=45, ha='right')
plt.tight_layout()

# ============================================================================
# SAVE OUTPUT
# ============================================================================
plt.savefig("bar_chart.png", dpi=300, bbox_inches='tight')
print("Plot saved to: bar_chart.png")
plt.close()
