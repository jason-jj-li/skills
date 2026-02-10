# Matplotlib/Seaborn Publication Theme
# Source: WHO color scheme with clean styling

import matplotlib.pyplot as plt
import seaborn as sns

def apply_report_theme():
    """Apply publication-ready theme settings."""
    # Use seaborn whitegrid style as base
    sns.set_theme(style="whitegrid")

    # Set font sizes
    plt.rcParams['font.size'] = 11
    plt.rcParams['axes.labelsize'] = 11
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.titleweight'] = 'bold'
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    plt.rcParams['legend.fontsize'] = 10
    plt.rcParams['legend.title_fontsize'] = 11

    # Set figure quality
    plt.rcParams['figure.dpi'] = 100
    plt.rcParams['savefig.dpi'] = 300
    plt.rcParams['savefig.bbox'] = 'tight'

    # Show all borders
    plt.rcParams['axes.spines.top'] = True
    plt.rcParams['axes.spines.right'] = True
    plt.rcParams['axes.spines.top'] = True
    plt.rcParams['axes.spines.right'] = True


# WHO Color Palette
WHO_COLORS = {
    'blue': '#4D9DE0',
    'light_blue': '#A7D7F0',
    'navy': '#104E8B',
    'dark_blue': '#003366',
    'gray': '#A8A8A8'
}


# Usage:
# import matplotlib.pyplot as plt
# import seaborn as sns
# from theme_python import apply_report_theme, WHO_COLORS
#
# apply_report_theme()
#
# fig, ax = plt.subplots(figsize=(8, 6))
# sns.scatterplot(data=df, x='x', y='y', color=WHO_COLORS['blue'], ax=ax)
# plt.savefig("output.png")
