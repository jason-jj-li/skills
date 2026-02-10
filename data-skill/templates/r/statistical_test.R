#!/usr/bin/env Rscript
# Statistical Test Template
# Purpose: Run common hypothesis tests

library(tidyverse)

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file <- "data.csv"

# Test type: "t_test", "correlation", "chisquare"
test_type <- "t_test"

# For t-test
group_var <- "group"       # Binary grouping variable
numeric_var <- "outcome"   # Numeric outcome variable

# For correlation
var1 <- "variable1"
var2 <- "variable2"
# ============================================================================

# Load data
df <- read_csv(data_file)

cat("\n========================================\n")
cat("STATISTICAL TEST RESULTS\n")
cat("========================================\n\n")

if (test_type == "t_test") {
  # Independent samples t-test
  cat("Independent Samples t-test\n")
  cat("--------------------------------------\n")
  cat("Grouping variable: ", group_var, "\n")
  cat("Outcome variable: ", numeric_var, "\n\n")

  # Group means
  group_means <- df %>%
    group_by(.data[[group_var]]) %>%
    summarise(
      n = n(),
      mean = mean(.data[[numeric_var]], na.rm = TRUE),
      sd = sd(.data[[numeric_var]], na.rm = TRUE),
      .groups = "drop"
    )
  print(group_means)

  # Run t-test
  test_result <- t.test(df[[numeric_var]] ~ df[[group_var]])
  cat("\nt-statistic: ", test_result$statistic, "\n")
  cat("Degrees of freedom: ", test_result$parameter, "\n")
  cat("p-value: ", test_result$p.value, "\n")
  cat("95% CI: [", test_result$conf.int[1], ", ", test_result$conf.int[2], "]\n")

} else if (test_type == "correlation") {
  # Pearson correlation
  cat("Pearson Correlation\n")
  cat("--------------------------------------\n")
  cat("Variable 1: ", var1, "\n")
  cat("Variable 2: ", var2, "\n\n")

  # Run correlation
  test_result <- cor.test(df[[var1]], df[[var2]], method = "pearson")
  cat("Correlation: ", test_result$estimate, "\n")
  cat("t-statistic: ", test_result$statistic, "\n")
  cat("Degrees of freedom: ", test_result$parameter, "\n")
  cat("p-value: ", test_result$p.value, "\n")
  cat("95% CI: [", test_result$conf.int[1], ", ", test_result$conf.int[2], "]\n")

} else if (test_type == "chisquare") {
  # Chi-square test of independence
  cat("Chi-Square Test of Independence\n")
  cat("--------------------------------------\n")
  cat("Variables: ", var1, ", ", var2, "\n\n")

  # Create contingency table
  contingency_table <- table(df[[var1]], df[[var2]])
  print(contingency_table)

  # Run chi-square test
  test_result <- chisq.test(contingency_table)
  cat("\nChi-square: ", test_result$statistic, "\n")
  cat("Degrees of freedom: ", test_result$parameter, "\n")
  cat("p-value: ", test_result$p.value, "\n")
}

cat("\n========================================\n")
