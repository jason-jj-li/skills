#!/usr/bin/env python3
# DAG (Directed Acyclic Graph) Template
# Purpose: Visualize causal relationships and identify confounders

import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd

# ============================================================================
# USER INPUT: Define your DAG edges
# ============================================================================
# Format: (parent, child) tuples
dag_edges = [
    ("treatment", "outcome"),
    ("confounder", "treatment"),
    ("confounder", "outcome"),
    ("mediator", "outcome"),
    ("treatment", "mediator"),
    ("collider", "outcome")  # WARNING: Don't condition on collider!
]

# ============================================================================
# CREATE DAG
# ============================================================================
dag = nx.DiGraph()
dag.add_edges_from(dag_edges)

# Check for cycles
if not nx.is_directed_acyclic_graph(dag):
    print("Warning: Graph contains cycles - not a valid DAG!")

# ============================================================================
# PLOT DAG
# ============================================================================
plt.figure(figsize=(8, 6))

# Layout options
pos = nx.spring_layout(dag)  # Force-directed
# pos = nx.circular_layout(dag)  # Circular
# pos = nx.shell_layout(dag)      # Hierarchical

nx.draw(dag, pos,
        with_labels=True,
        arrows=True,
        node_size=2000,
        node_color='lightblue',
        edge_color='gray',
        font_size=10,
        arrowsize=20)

plt.title("Causal DAG")
plt.axis('off')
plt.tight_layout()

# Save plot
plt.savefig("dag_plot.png", dpi=300, bbox_inches='tight')
print("DAG plot saved to: dag_plot.png")

# ============================================================================
# OUTPUT ANALYSIS
# ============================================================================
print("\n" + "="*40)
print("DAG ANALYSIS RESULTS")
print("="*40 + "\n")

# Find parents and children
print("Parents of 'treatment':")
for parent in dag.predecessors('treatment'):
    print(f"  - {parent}")

print("\nChildren of 'treatment':")
for child in dag.successors('treatment'):
    print(f"  - {child}")

# Find all paths between two nodes
try:
    paths = list(nx.all_simple_paths(dag, 'treatment', 'outcome', cutoff=5))
    print(f"\nPaths from 'treatment' to 'outcome' (max 5 shown):")
    for i, path in enumerate(paths[:5], 1):
        print(f"  Path {i}: {' -> '.join(path)}")
except:
    print("\nNo paths found between 'treatment' and 'outcome'")

# Find adjustment sets (manual approach)
# In R use dagitty::adjustmentSets()
print("\n" + "="*40)
print("ADJUSTMENT SETS")
print("="*40 + "\n")
print("Note: For full adjustment sets, use R's dagitty package")
print("Minimum adjustment set for treatment -> outcome:")

# Find minimal adjustment set
confounders = []
for parent in dag.predecessors('treatment'):
    if parent != 'outcome':  # Not a mediator
        if parent in dag.predecessors('outcome'):
            confounders.append(parent)

if confounders:
    print(f"  {', '.join(confounders)}")
else:
    print("  (none needed - no common confounders)")

print("\n" + "="*40)
