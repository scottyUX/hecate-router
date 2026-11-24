# Implemented Alpha components

- [Telemetry Collector](telemetry-collector.md): canonical events, causal counters,
  safe replay checkpoints, source adapters and historical coverage limitations.
- [State Builder](state-builder.md): 22-feature observations, masks, train-only
  normalization, frozen reload and readiness modes.

Both were implemented and verified offline in
[TASK-004](../tasks/e7-telemetry-and-routing-state-builder.md). Live routing
integration and validated advisor/test producers remain subsequent work.

- [Saved-source patch evaluator](patch-evaluator.md): independent patch correctness,
  separate completion/policy outcomes, grading-only replay and protocol comparisons.
  Implemented and verified on all20 saved TASK-006 attempts in
  [TASK-007](../tasks/task-007-evaluation-correctness.md).
