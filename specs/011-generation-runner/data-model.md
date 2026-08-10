# Data Model: Generation Runner

## RunConfig

In-memory configuration for one runner invocation.

| Field | Type | Notes |
|-------|------|-------|
| config_path | Path | Default `configs/option_a.yaml` |
| task_limit | int | e.g. 1 or 20 for pilot |
| model_slugs | list[str] | Subset of Option A slugs |
| dry_run | bool | Skip network + spend |
| output_dir | Path | Default `data/outputs/runs/<run_id>/` |
| cache_dir | Path | Default `data/cache/generations/` |
| ledger_path | Path | Default cost ledger path |
| run_id | str | Unique per process (uuid / timestamp) |

## RunManifest

Persisted JSON reproducibility snapshot.

| Field | Type | Notes |
|-------|------|-------|
| run_id | str | |
| timestamp | str | ISO-8601 UTC |
| git_commit | str \| null | `git rev-parse HEAD` when available |
| config_path | str | |
| config_snapshot | object | Parsed YAML (or hash + embedded subset) |
| model_slugs | list[str] | |
| task_limit | int | |
| dry_run | bool | |
| records_path | str | JSONL path |
| total_cost_usd | float | From cost tracker at end |
| pairs_attempted | int | |
| pairs_cache_hit | int | |
| pairs_generated | int | Paid or dry synthetic |
| pairs_refused_budget | int | |

## PairOutcome (internal)

| Field | Type | Notes |
|-------|------|-------|
| record | GenerationRecord | Always produced when pair is processed |
| cache_hit | bool | |
| refused_budget | bool | |
| error | str \| null | Provider/orchestrator error summary (no secrets) |

## Existing entities (unchanged)

- `SwebenchTask` — `hecate.data`
- `ContextBundle` — `hecate.scaffold`
- `GenerationRecord` — `hecate.data.records`
- `CachedGeneration` / `GenerationCache` — `hecate.caching`
- `CostTracker` / `BudgetStatus` — `hecate.cost`
- `CompletionResult` — `hecate.generation.client`
- `ExtractionResult` — `hecate.generation.patch`

## State transitions (per pair)

```text
start
  → build context + prompt
  → cache lookup
       hit  → extract → write record → done (no spend)
       miss → dry_run? → write dry record/manifest bookkeeping → done
              else authorize
                   refuse → write refused record / halt paid work → done
                   allow  → complete → extract
                            success → cache put → record_usage → write record
                            failure → write record (no cache put, no spend)
```
