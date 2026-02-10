#!/usr/bin/env Rscript
# Data Cleaning Template
# Purpose: Handle missing values, duplicates, and outliers

library(tidyverse)

# ============================================================================
# USER INPUT: Modify these variables
# ============================================================================
data_file <- "data.csv"
# ============================================================================

# Load data
df <- read_csv(data_file)

cat("\n========================================\n")
cat("DATA CLEANING REPORT\n")
cat("========================================\n\n")

# Initial dimensions
cat("Original dimensions: ", nrow(df), " rows x ", ncol(df), " cols\n\n")

# ============================================================================
# 1. Remove Duplicates
# ============================================================================
df_clean <- df %>% distinct()
removed_dup <- nrow(df) - nrow(df_clean)
cat("Duplicates removed: ", removed_dup, "\n")

# ============================================================================
# 2. Handle Missing Values
# ============================================================================
missing_by_col <- df_clean %>%
  summarise(across(everything(), ~ sum(is.na(.)))) %>%
  pivot_longer(cols = everything(), names_to = "variable", values_to = "missing_count") %>%
  filter(missing_count > 0) %>%
  arrange(desc(missing_count))

if (nrow(missing_by_col) > 0) {
  cat("\nMissing values by column:\n")
  print(missing_by_col)
} else {
  cat("\nNo missing values found.\n")
}

# Option: Drop rows with missing values
# df_clean <- df_clean %>% drop_na()

# Option: Fill missing values
# df_clean <- df_clean %>% mutate(across(where(is.numeric), ~ifelse(is.na(.), mean(., na.rm = TRUE), .)))

# ============================================================================
# 3. Detect Outliers (for numeric columns)
# ============================================================================
numeric_cols <- names(df_clean)[sapply(df_clean, is.numeric)]

if (length(numeric_cols) > 0) {
  cat("\nOutlier detection (IQR method):\n")
  for (col in numeric_cols) {
    Q1 <- quantile(df_clean[[col]], 0.25, na.rm = TRUE)
    Q3 <- quantile(df_clean[[col]], 0.75, na.rm = TRUE)
    IQR <- Q3 - Q1
    lower <- Q1 - 1.5 * IQR
    upper <- Q3 + 1.5 * IQR
    outliers <- sum(df_clean[[col]] < lower | df_clean[[col]] > upper, na.rm = TRUE)
    if (outliers > 0) {
      cat("  ", col, ": ", outliers, " outliers\n")
    }
  }
}

# Final dimensions
cat("\nClean dimensions: ", nrow(df_clean), " rows x ", ncol(df_clean), " cols\n")
cat("Data removed: ", round((1 - nrow(df_clean)/nrow(df)) * 100, 1), "%\n")

cat("\n========================================\n")

# Save cleaned data
# write_csv(df_clean, "data_cleaned.csv")
