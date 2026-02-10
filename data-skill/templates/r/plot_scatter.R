#!/usr/bin/env Rscript
# Scatter Plot Template
# Purpose: Create scatter plot with proper styling

library(tidyverse)

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file <- "plot_data.csv"
x_var <- "x_variable"    # Change to your x-axis variable
y_var <- "y_variable"    # Change to your y-axis variable
color_var <- NULL        # Optional: variable for color grouping
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
      plot.subtitle = element_text(size = 11, color = "gray40", hjust = 0.5),
      axis.title = element_text(size = 11, face = "bold"),
      axis.text = element_text(size = 10, color = "black"),
      panel.grid.major = element_line(color = "gray90", linewidth = 0.3),
      panel.grid.minor = element_blank(),
      panel.border = element_rect(fill = NA, color = "black", linewidth = 0.5),
      plot.margin = margin(10, 10, 10, 10),
      legend.position = "right"
  )
}

# WHO color scheme
who_colors <- list(
  blue = "#4D9DE0",
  light_blue = "#A7D7F0",
  navy = "#104E8B",
  gray = "#A8A8A8"
)

# ============================================================================
# CREATE PLOT
# ============================================================================
p <- ggplot(df, aes(x = .data[[x_var]], y = .data[[y_var]])) +
  geom_point(size = 3, alpha = 0.7, color = who_colors$blue) +

  # Optional: Add color grouping
  # aes(color = .data[[color_var]]) +
  # geom_point(size = 3, alpha = 0.7) +
  # scale_color_manual(values = who_colors$blue) +

  # Optional: Add trend line
  # geom_smooth(method = "lm", se = TRUE, color = who_colors$navy) +

  labs(
    title = "Scatter Plot Title",
    x = "X Axis Label",
    y = "Y Axis Label"
  ) +
  theme_report()

# ============================================================================
# SAVE OUTPUT
# ============================================================================
ggsave(
  filename = "scatter_plot.png",
  plot = p,
  width = 8,
  height = 6,
  dpi = 300
)

cat("Plot saved to: scatter_plot.png\n")
