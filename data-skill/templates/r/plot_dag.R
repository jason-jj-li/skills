#!/usr/bin/env Rscript
# DAG (Directed Acyclic Graph) Template
# Purpose: Visualize causal relationships and identify confounders

library(ggplot2)
library(dagitty)
library(ggdag)

# ============================================================================
# USER INPUT: Define your DAG
# ============================================================================
# Format: "parent -> child; parent -> child"
dag_definition <- "dag {
    treatment -> outcome
    confounder -> treatment
    confounder -> outcome
    mediator -> outcome
    treatment -> mediator
    collider -> outcome
}"

# Alternative: Build programmatically
# dag <- dagitty::dagitty("dag {
#     treatment -> outcome
#     confounder -> treatment
#     confounder -> outcome
# }")

# ============================================================================
# PLOT DAG
# ============================================================================
dag <- dagitty::dagitty(dag_definition)

# Basic plot
ggdag(dag) +
  theme_dag() +
  labs(title = "Causal DAG")

# Colored by variable type
ggdag(dag) +
  theme_dag() +
  labs(title = "Causal DAG") +
  scale_gdag_d(fill = "variable")  # Color by variable type

# With adjustment sets highlighted
adjustments <- adjustmentSets(dag, exposure = "treatment", outcome = "outcome")
ggdag(dag) +
  theme_dag() +
  labs(title = "Causal DAG with Adjustment Sets") +
  geom_dag_node(aes(color = after_adjustment))

# ============================================================================
# OUTPUT ANALYSIS
# ============================================================================
cat("\n========================================\n")
cat("DAG ANALYSIS RESULTS\n")
cat("========================================\n\n")

# Show parents and children
cat("Parents of 'treatment':\n")
print(parents(dag, "treatment"))

cat("\nChildren of 'treatment':\n")
print(children(dag, "treatment"))

cat("\nAdjustment sets for 'treatment' -> 'outcome':\n")
print(adjustments)

cat("\nPaths from treatment to outcome:\n")
print(paths(dag, from = "treatment", to = "outcome"))

cat("\n========================================\n")

# Save plot
ggsave("dag_plot.png", width = 8, height = 6, dpi = 300)
cat("DAG plot saved to: dag_plot.png\n")
