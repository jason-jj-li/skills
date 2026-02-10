#!/usr/bin/env python3
# Box Plot Template
# Purpose: Create box plot for distribution comparison

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file = "data.csv"
numeric_var = "numeric_variable"   # Change to your numeric variable
group_var = "group_variable"       # Change to your grouping variable
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
    'blue': '#4D9DE0'
}

# ============================================================================
# CREATE PLOT
# ============================================================================
fig, ax = plt.subplots(figsize=(8, 6))

sns.boxplot(data=df, x=group_var, y=numeric_var,
            color=who_colors['blue'], ax=ax)

# Add jitter points
sns.stripplot(data=df, x=group_var, y=numeric_var,
              color='black', alpha=0.3, size=3, ax=ax)

ax.set_title("Box Plot Title")
ax.set_xlabel("Group Label")
ax.set_ylabel("Value Label")
ax.spines['top'].set_visible(True)
ax.spines['right'].set_visible(True)
ax.xaxis.grid(False)

plt.tight_layout()

# ============================================================================
# SAVE OUTPUT
# ============================================================================
plt.savefig("box_plot.png", dpi=300, bbox_inches='tight')
print("Plot saved to: box_plot.png")
plt.close()
