---
name: research-repro
description: Make experiment and batch runs reproducible with config snapshots, versions, and manifests. Use when adding runners, sweeps, pilots, benchmarks, training jobs, or any scripted experiment that should be re-runnable.
---

# Research reproducibility

## Goal

Every meaningful run should be reconstructible later: what config, what code, when, and what it cost or produced.

## Minimum manifest fields

Record (as JSON/YAML alongside outputs):

| Field | Why |
|-------|-----|
| Timestamp (UTC) | When the run happened |
| Git commit SHA | Exact code version |
| Config snapshot or path + hash | Inputs and hyperparameters |
| CLI args / overrides | Anything not in the config file |
| Dependency or environment note | Python version, key package versions if relevant |
| Status / counts | Completed, failed, skipped |
| Cost or resource metrics | Tokens, USD, GPU hours — if applicable |

## Workflow

1. Load config from a file; avoid hardcoding model IDs, paths, or budgets in code.
2. Before work starts, create a `run_id` and write a manifest stub.
3. Append or finalize the manifest when the run ends (success or halt).
4. Prefer content-addressed or deterministic caches so resumed runs do not silently diverge.
5. Keep raw outputs; do not overwrite previous runs without an explicit resume/replace policy.

## Checklist

```
- [ ] Config loaded from file (not hardcoded)
- [ ] Manifest written with commit + config + timestamp
- [ ] Outputs tied to run_id
- [ ] Failures recorded, not silently dropped
```

## Anti-patterns

- Mutating config mid-run without recording the change
- Discarding failed trials that are needed for a full matrix
- “Best effort” logs instead of a structured manifest
