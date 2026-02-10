#!/usr/bin/env Rscript
# Bar Chart Template
# Purpose: Create bar chart for categorical data

library(tidyverse)

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file <- "plot_data.csv"
category_var <- "category"      # Change to your category variable
value_var <- "value"            # Change to your value variable
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
p <- ggplot(df, aes(x = .data[[category_var]], y = .data[[value_var]])) +
  geom_col(fill = who_colors$blue, width = 0.7) +
  geom_text(aes(label = .data[[value_var]]), vjust = -0.5, size = 4) +
  scale_y_continuous(labels = scales::comma_format()) +
  labs(
    title = "Bar Chart Title",
    x = "Category Label",
    y = "Value Label"
  ) +
  theme_report() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# ============================================================================
# SAVE OUTPUT
# ============================================================================
ggsave(
  filename = "bar_chart.png",
  plot = p,
  width = 8,
  height = 6,
  dpi = 300
)

cat("Plot saved to: bar_chart.png\n")
