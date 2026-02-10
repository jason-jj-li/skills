#!/usr/bin/env Rscript
# Target Trial Emulation - Cloning Template
# Purpose: Emulate multiple treatment strategies using cloning

library(tidyverse)

# ============================================================================
# USER INPUT: Define your trial
# ============================================================================
data_file <- "data.csv"

# Trial components
# 1. Eligibility
eligibility_filter <- "age >= 18"

# 2. Index date (time zero)
index_date_var <- "baseline_date"

# 3. Treatment strategies to compare
# Strategy A: Always treat
# Strategy B: Never treat
# Strategy C: As observed

# 4. Follow-up (days)
follow_up_days <- 365  # 1 year follow-up

# Outcome variable
outcome_var <- "outcome"
# ============================================================================

# Load data
df <- read_csv(data_file)

# ============================================================================
# STEP 1: Define eligibility
# ============================================================================
eligible <- df %>%
  filter(age >= 18) %>%
  filter(!is.na(baseline_covariate))

cat("Eligible population:", nrow(eligible), "subjects\n")

# ============================================================================
# STEP 2: Create cloned dataset
# ============================================================================
# Create multiple copies of each person under different strategies

# Strategy A: Everyone gets treatment
strategy_A <- eligible %>%
  select(id, all_of(index_date_var), treatment, all_of(outcome_var), matches_eligible) %>%
  mutate(
    strategy = "A",
    assigned_treatment = 1,
    assigned_outcome = outcome_var  # Use observed outcome
  )

# Strategy B: No one gets treatment
strategy_B <- eligible %>%
  select(id, all_of(index_date_var), treatment, all_of(outcome_var), matches_eligible) %>%
  mutate(
    strategy = "B",
    assigned_treatment = 0,
    assigned_outcome = outcome_var  # Use observed outcome
  )

# Strategy C: As actually observed
strategy_C <- eligible %>%
  select(id, all_of(index_date_var), treatment, all_of(outcome_var), matches_eligible) %>%
  mutate(
    strategy = "C",
    assigned_treatment = treatment,
    assigned_outcome = outcome_var  # Use observed outcome
  )

# Combine all strategies
tte_data <- bind_rows(strategy_A, strategy_B, strategy_C)

# ============================================================================
# STEP 3: Calculate follow-up time
# ============================================================================
tte_data <- tte_data %>%
  mutate(
    index_date = as.Date(!!index_date_var),
    follow_up_days = as.numeric(as.Date(end_date) - index_date)
  ) %>%
  # Filter to valid follow-up window
  filter(follow_up_days >= 0, follow_up_days <= follow_up_days) %>%
  # Censor at end of follow-up
  mutate(
    event = ifelse(is.na(event), 0, 1),
    censored = ifelse(follow_up_days < follow_up_days, 1, 0)
  )

# ============================================================================
# STEP 4: Analyze outcomes by strategy
# ============================================================================
results <- tte_data %>%
  group_by(strategy) %>%
  summarise(
    n = n(),
    event_count = sum(event),
    person_time = sum(follow_up_days, na.rm = TRUE),
    cumulative_incidence = sum(event) / n(),
    .groups = "drop"
  )

cat("\n========================================\n")
cat("TARGET TRIAL EMULATION RESULTS\n")
cat("========================================\n\n")

print(results)

cat("\nIncidence rates (per 1000 person-years):\n")
results %>%
  mutate(
    rate_per_1000_py = (event_count / person_time) * 1000 * 365
  ) %>%
  select(strategy, rate_per_1000_py) %>%
  print()

cat("\n========================================\n")

# Risk comparison
risk_A <- results$cumulative_incidence[results$strategy == "A"]
risk_B <- results$cumulative_incidence[results$strategy == "B"]

if (!is.na(risk_A) && !is.na(risk_B)) {
  risk_ratio <- risk_A / risk_B
  risk_difference <- risk_A - risk_B

  cat("Risk Ratio (A vs B):", round(risk_ratio, 3), "\n")
  cat("Risk Difference (A vs B):", round(risk_difference, 3), "\n")
}

# ============================================================================
# SAVE RESULTS
# ============================================================================
write_csv(results, "tte_results.csv")
ggsave("tte_comparison.png", width = 8, height = 6, dpi = 300)
