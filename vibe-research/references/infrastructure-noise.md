# Infrastructure Noise in Research Pipelines

## Typical Noise Sources

- API/search backend fluctuations
- transient network failures
- dependency/version drift
- hidden local state from prior runs
- model variance on ambiguous tasks

## Practical Mitigation

- persist run manifests and logs
- keep deterministic scripts for retrieval/screening/verification
- rerun critical steps and compare outputs
- pin tool versions when possible
- separate infra incidents from scientific interpretation

## Incident Triage

1. Did inputs change?
2. Did tool versions or endpoints change?
3. Is failure reproducible on retry?
4. If not reproducible, mark as infra noise with evidence.
