#!/usr/bin/env Rscript
# Box Plot Template
# Purpose: Create box plot for distribution comparison

library(tidyverse)

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file <- "data.csv"
numeric_var <- "numeric_variable"   # Change to your numeric variable
group_var <- "group_variable"       # Change to your grouping variable
# ============================================================================

# Load data
df <- read_csv(data_file)

# ============================================================================
# THEME
# ============================================================================
theme_report <- function() {
  theme_minimal(base_size = 11) +
    theme(
      plot.title = element_text(size = 14, face = "bold", hjust = 0.5),
      axis.title = element_text(size = 11, face = "bold"),
      axis.text = element_text(size = 10, color = "black"),
      panel.grid.major.x = element_blank(),
      panel.grid.major.y = element_line(color = "gray90", linewidth = 0.3),
      panel.grid.minor = element_blank(),
      panel.border = element_rect(fill = NA, color = "black", linewidth = 0.5),
      plot.margin = margin(10, 10, 10, 10)
    )
}

# WHO color scheme
who_colors <- list(
  blue = "#4D9DE0",
  navy = "#104E8B",
  gray = "#A8A8A8"
)

# ============================================================================
# CREATE PLOT
# ============================================================================
p <- ggplot(df, aes(x = .data[[group_var]], y = .data[[numeric_var]])) +
  geom_boxplot(fill = who_colors$blue, alpha = 0.8) +
  geom_point(position = position_jitter(width = 0.2), alpha = 0.3, size = 1) +
  labs(
    title = "Box Plot Title",
    x = "Group Label",
    y = "Value Label"
  ) +
  theme_report()

# ============================================================================
# SAVE OUTPUT
# ============================================================================
ggsave(
  filename = "box_plot.png",
  plot = p,
  width = 8,
  height = 6,
  dpi = 300
)

cat("Plot saved to: box_plot.png\n")
