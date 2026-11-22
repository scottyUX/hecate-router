# Implemented Alpha components

- [Telemetry Collector](telemetry-collector.md): canonical events, causal counters,
  safe replay checkpoints, source adapters and historical coverage limitations.
- [State Builder](state-builder.md): 22-feature observations, masks, train-only
  normalization, frozen reload and readiness modes.

Both were implemented and verified offline in
[TASK-004](../tasks/e7-telemetry-and-routing-state-builder.md). Live routing
integration and validated advisor/test producers remain subsequent work.
