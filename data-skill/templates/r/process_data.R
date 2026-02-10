#!/usr/bin/env Rscript
# Data Processing Template
# Purpose: Filter, recode, transform, and aggregate data

library(tidyverse)

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file <- "data.csv"
# ============================================================================

# Load data
df <- read_csv(data_file)

# ============================================================================
# DATA PROCESSING PIPELINE
# ============================================================================
plot_data <- df %>%
  # 1. Filter observations
  # filter(!is.na(variable_name)) %>%

  # 2. Mutate / Recode variables
  mutate(
    # Example: Chinese to English labels
    # new_var = case_when(
    #   variable_name == "中文值1" ~ "English Label 1",
    #   variable_name == "中文值2" ~ "English Label 2",
    #   TRUE ~ as.character(variable_name)
    # ),

    # Example: Create binary variable
    # binary_var = ifelse(variable_name == "是", 1, 0),

    # Example: Calculate derived variable
    # percentage = n / sum(n) * 100
  ) %>%

  # 3. Group and summarize
  # group_by(grouping_var) %>%
  # summarise(
  #   count = n(),
  #   mean_value = mean(numeric_var, na.rm = TRUE),
  #   .groups = "drop"
  # ) %>%

  # 4. Arrange
  # arrange(desc(count))

# ============================================================================
# VERIFY OUTPUT
# ============================================================================
cat("\n========================================\n")
cat("PROCESSED DATA\n")
cat("========================================\n\n")

print(plot_data)

cat("\nDimensions: ", nrow(plot_data), " rows x ", ncol(plot_data), " cols\n")
cat("Column names: ", names(plot_data), "\n")

# Export for plotting
# write_csv(plot_data, "plot_data.csv")

cat("\n========================================\n")
