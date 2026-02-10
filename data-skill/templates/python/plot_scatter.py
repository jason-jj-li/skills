#!/usr/bin/env python3
# Scatter Plot Template
# Purpose: Create scatter plot with proper styling

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file = "plot_data.csv"
x_var = "x_variable"    # Change to your x-axis variable
y_var = "y_variable"    # Change to your y-axis variable
color_var = None        # Optional: variable for color grouping
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
    'navy': '#104E8B',
    'gray': '#A8A8A8'
}

# ============================================================================
# CREATE PLOT
# ============================================================================
fig, ax = plt.subplots(figsize=(8, 6))

if color_var:
    sns.scatterplot(data=df, x=x_var, y=y_var, hue=color_var,
                    s=100, alpha=0.7, ax=ax)
else:
    sns.scatterplot(data=df, x=x_var, y=y_var,
                    color=who_colors['blue'], s=100, alpha=0.7, ax=ax)

# Optional: Add trend line
# sns.regplot(data=df, x=x_var, y=y_var, scatter=False, ax=ax)

ax.set_title("Scatter Plot Title")
ax.set_xlabel("X Axis Label")
ax.set_ylabel("Y Axis Label")
ax.spines['top'].set_visible(True)
ax.spines['right'].set_visible(True)
ax.spines['top'].set_color('black')
ax.spines['right'].set_color('black')
ax.spines['top'].set_linewidth(0.5)
ax.spines['right'].set_linewidth(0.5)

plt.tight_layout()

# ============================================================================
# SAVE OUTPUT
# ============================================================================
plt.savefig("scatter_plot.png", dpi=300, bbox_inches='tight')
print("Plot saved to: scatter_plot.png")
plt.close()
