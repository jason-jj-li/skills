#!/usr/bin/env Rscript
# Variable Exploration Template
# Purpose: Understand variable types, distributions, and patterns

library(tidyverse)

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file <- "data.csv"
variable_name <- "your_variable"  # Change to your variable name
# ============================================================================

# Load data
df <- read_csv(data_file)

cat("\n========================================\n")
cat("VARIABLE EXPLORATION:", variable_name, "\n")
cat("========================================\n\n")

# 1. Check class/type
cat("Variable class:\n")
cat("  ", class(df[[variable_name]]), "\n\n")

# 2. Check unique values
cat("Unique values (n=", n_distinct(df[[variable_name]]), "):\n")
print(table(df[[variable_name]], useNA = "ifany"))

# 3. Check for missing values
missing_count <- sum(is.na(df[[variable_name]]))
missing_pct <- missing_count / nrow(df) * 100
cat("\nMissing values:\n")
cat("  Count: ", missing_count, "\n")
cat("  Percentage: ", sprintf("%.1f%%", missing_pct), "\n\n")

# 4. Check first few values
cat("First 10 values:\n")
print(head(df[[variable_name]], 10))

# 5. Summary statistics (if numeric)
if (is.numeric(df[[variable_name]]) || is.integer(df[[variable_name]])) {
  cat("\nSummary statistics:\n")
  print(summary(df[[variable_name]]))
  cat("\nMean: ", mean(df[[variable_name]], na.rm = TRUE), "\n")
  cat("SD:   ", sd(df[[variable_name]], na.rm = TRUE), "\n")
}

cat("\n========================================\n")
