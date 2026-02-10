# ggplot2 Publication Theme
# Source: WHO color scheme with minimal styling

theme_report <- function() {
  theme_minimal(base_size = 11) +
    theme(
      # Title styling
      plot.title = element_text(size = 14, face = "bold", hjust = 0.5),
      plot.subtitle = element_text(size = 11, color = "gray40", hjust = 0.5),

      # Axis styling
      axis.title = element_text(size = 11, face = "bold"),
      axis.text = element_text(size = 10, color = "black"),

      # Panel styling
      panel.grid.major = element_line(color = "gray90", linewidth = 0.3),
      panel.grid.minor = element_blank(),
      panel.border = element_rect(fill = NA, color = "black", linewidth = 0.5),

      # Margins
      plot.margin = margin(10, 10, 10, 10),

      # Legend
      legend.position = "right",
      legend.text = element_text(size = 10),
      legend.title = element_text(size = 11, face = "bold")
    )
}

# WHO Color Palette
who_colors <- list(
  blue = "#4D9DE0",
  light_blue = "#A7D7F0",
  navy = "#104E8B",
  dark_blue = "#003366",
  gray = "#A8A8A8"
)

# Usage:
# library(ggplot2)
# source("theme_r.R")
#
# ggplot(data, aes(x, y)) +
#   geom_*() +
#   theme_report()
