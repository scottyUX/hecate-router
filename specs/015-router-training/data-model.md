# Data Model: Router Training v1

## RouterExample

| Field | Type | Notes |
|-------|------|-------|
| instance_id | str | SWE-bench id |
| repo | str | Stratification key |
| text | str | Truncated issue + oracle context |
| truncated | bool | True if tokenizer hit 2048 |
| m1_resolves | bool | Training label |
| m2_resolves | bool | Needed for routing metrics |
| prompt_hash | str \| None | Scaffold identity |

Incomplete label pairs and rows with empty text after join are dropped (counted, not trained).

## FoldAssignment

| Field | Type | Notes |
|-------|------|-------|
| seed | int | |
| strategy | str | `label_repo` \| `repo` \| `round_robin` |
| fold_of | dict[str, int] | instance_id → fold 0..n_folds-1 |

## TrainMetrics

| Field | Type | Notes |
|-------|------|-------|
| always_m1 | float | Hold-out m1 resolve rate |
| always_m2 | float | Hold-out m2 resolve rate |
| random | float | Mean of always_m1 and always_m2 (coin-flip mix) |
| oracle | float | Fraction where m1 or m2 resolved |
| route_auc | float | ∫ (rate(λ) − always_m2) dλ |
| best_lambda | float | λ maximizing rate(λ) on hold-out |
| best_route_rate | float | rate(best_lambda) |
| n | int | Hold-out size |
| n_positive | int | m1_resolves true |

## TrainRun manifest

Timestamp, git commit, config snapshot, CLI overrides, seeds, n_folds, truncation_rate, split_strategy, per-seed per-fold metrics, mean Route-AUC, `go_nogo` (`go` if mean Route-AUC > 0 else `floor`).
