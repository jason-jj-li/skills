# Exemplar Alignment

Legacy note: this file describes the older automation path that emits `.json + .md` artifact pairs. For new MD-first projects, keep exemplar findings in Markdown unless a script specifically requires structured export.

Use published near-neighbor papers to convert journal benchmarking from vague style mimicry into executable constraints.

## Why This Gate Exists

Guidelines (PRISMA/MOOSE/Cochrane) define minimum reporting standards, but top-tier acceptance also depends on how papers are actually structured and argued in the target venue.

## Required Outputs

- `process/exemplar_benchmark.json`
- `process/exemplar_benchmark.md`
- `process/writing_blueprint.json`
- `process/writing_outline.md`

Minimum contents:
- query tiers and hit counts
- exemplar list (pmid/title/journal/year)
- common abstract section labels
- method signal counts (registration, random-effects, heterogeneity, bias tool, certainty)
- planning hints translated into concrete task constraints
- style-profile to outline mapping (journal style -> section-level writing constraints)

## Query Strategy

1. Target journal + method + topic cues
2. Target journal + method
3. Neighbor journals + method + topic cues
4. Neighbor journals + method

Stop once enough exemplars are collected (typically 5-8).

## How to Use Results

Convert exemplar patterns into plan requirements, for example:
- abstract heading template
- mandatory heterogeneity and sensitivity reporting
- mandatory risk-of-bias and certainty sections
- registration/protocol disclosure style
- section-by-section manuscript outline for the target journal

## Gate Rule

For top-tier targets, if exemplar artifacts are missing, planning is incomplete and execution should not proceed.
