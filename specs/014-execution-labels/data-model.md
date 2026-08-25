# Data Model: Execution Harness and Routing Labels

## GenerationRecord (extended)

Existing Stage-1 entity in `hecate.data.records`. Stage-2 fields:

| Field | Type | Notes |
|-------|------|-------|
| patch_applied | bool \| None | From `patch_successfully_applied`; None = not yet executed |
| resolved | bool \| None | **NEW.** SWE-bench full resolution; None = not yet executed |
| fail_to_pass | list[str] \| None | Passing FAIL_TO_PASS test names |
| pass_to_pass | list[str] \| None | Passing PASS_TO_PASS test names |

`from_dict` treats missing `resolved` as `None` so older JSONL still loads.

## Prediction

Evaluator input row (not stored as a dataclass in records).

| Field | Type | Notes |
|-------|------|-------|
| instance_id | str | SWE-bench instance id |
| model_name_or_path | str | Hecate `model_slug` |
| model_patch | str | `extracted_patch` (empty string never sent; those pairs skip) |

## HarnessRequest / HarnessResult

In-memory harness protocol types (see contracts).

## ExecutionConfig / ExecutionResult

In-memory configuration and summary for `run_execution`.

| ExecutionConfig field | Type | Notes |
|-----------------------|------|-------|
| config_path | Path | `configs/execution.yaml` |
| input_path | Path | Stage-1 `generations.jsonl` |
| output_dir | Path | New run directory |
| run_id | str | Execution run id |
| model_slugs | tuple[str, ...] | Subset to evaluate |
| instance_ids | tuple[str, ...] \| None | Optional smoke filter |
| task_limit | int \| None | First N unique instance ids from input |
| dry_run | bool | |
| dataset_name | str | Default `SWE-bench/SWE-bench_Lite` |
| split | str | Default `test` |
| max_workers | int | |
| timeout | int | Seconds |
| namespace | str \| None | `None` means local build (`none`) |
| cache_level | str | |
| force_rebuild | bool | |
| modal | bool | |

## RoutingLabel

One row per task with both models present.

| Field | Type | Notes |
|-------|------|-------|
| instance_id | str | |
| repo | str | |
| m1_slug | str | Small tier |
| m2_slug | str | Large tier |
| m1_resolves | bool | Training label |
| m2_resolves | bool | |
| complementarity | str | `both` \| `only_m1` \| `only_m2` \| `neither` |

## PreflightReport

| Field | Type | Notes |
|-------|------|-------|
| n_tasks | int | Complete tasks (both models) |
| incomplete_instance_ids | list[str] | |
| m1_slug / m2_slug | str | |
| shared_scaffold | object | `{ok, mismatched_instance_ids}` |
| m1_resolve_rate | float | |
| m2_resolve_rate | float | |
| complementarity | object | counts for four buckets |
| always_m1_resolve_rate | float | Same as m1_resolve_rate |
| always_m2_resolve_rate | float | Same as m2_resolve_rate |
| oracle_routing_resolve_rate | float | m1 OR m2 |
| routing_headroom | float | oracle − always_m2 |
| m1_positive_rate | float | Same as m1_resolve_rate |
| m1_positive_rate_flag | bool | True if rate < 0.15 |

## ExecutionManifest

JSON written by the execution runner (and a smaller one by the label runner). Required: timestamp UTC, git commit, config snapshot, CLI overrides, `swebench` version, namespace, Stage-1 `run_id` (from input records), counts.

## State transitions (per pair)

```text
start
  → pair already in executions.jsonl with patch_applied bool? → skip
  → usable extracted_patch?
       no  → write applied=false, resolved=false, empty lists → done
       yes → write predictions → harness.run
              report.json present → merge fields → write record → done
              report.json missing → do not write (pending retry) → done
```
