# Results — E02 Specialist django

Status: **seed-0 smoke complete**. Early-stopped B/C/D rerun is not yet run.
This table is a §6.1 smoke, not a confirmatory result.

Canonical spec: [`spec.md`](spec.md)
Journal: `/journal/2026-09-15-e02-specialist-django-smoke`

Holdout (seed 0, 185/46): always-small 27/46 (0.587), always-large 33/46 (0.717),
oracle 37/46 (0.804). Complementarity on the 46: both 23, small-only 4,
large-only 10, neither 9. Oracle matched-quality cost is **10** Opus calls.

Headline numbers are the patched LoRA loop (shuffle, val-from-train, clip,
zero-init; `early_stopping: false`). Unshuffled k0/k1 are invalid for science
(§5.5 / label-order artifact) and are listed only so they are not quoted.

| run_id | arm | split | seed | route_auc | artifacts_uri |
| --- | --- | --- | ---: | ---: | --- |
| `exp-02_arm-frozen_split-specialist_seed-0` | A frozen logreg | specialist | 0 | 0.373 | `gs://hecate-506120-artifacts/runs/exp-02_arm-frozen_split-specialist_seed-0` |
| `exp-02_arm-k0_split-specialist_seed-0_run-2` | B K=0 LoRA | specialist | 0 | 0.482 | `gs://hecate-506120-artifacts/runs/exp-02_arm-k0_split-specialist_seed-0_run-2` |
| `exp-02_arm-k1_split-specialist_seed-0_run-2` | D K=1 LoRA | specialist | 0 | 0.625 | `gs://hecate-506120-artifacts/runs/exp-02_arm-k1_split-specialist_seed-0_run-2` |
| `exp-02_arm-k3_split-specialist_seed-0` | C K=3 LoRA | specialist | 0 | 0.574 | `gs://hecate-506120-artifacts/runs/exp-02_arm-k3_split-specialist_seed-0` |

MLP frozen Route-AUC is 0.690 and is **not** the arm-A headline (logreg is).

## Matched-quality Opus calls (locked 2026-09-15)

Among λ with holdout successes ≥ 33, minimum tasks sent to Opus. Same λ sweep
as Route-AUC. D is diagnostic (§5.4) and cannot headline.

| Policy | Opus calls | Successes | Notes |
| --- | ---: | ---: | --- |
| Always Qwen | 0 | 27 | −6 vs always-Opus |
| Oracle (match 33) | 10 | 33 | ceiling: only large-only need Opus |
| Always Opus | 46 | 33 | baseline |
| A frozen logreg | 46 | 33 | no cheaper 33 |
| B K=0 `_run-2` | 46 | 33 | no cheaper 33 |
| D K=1 `_run-2` | **26** | 33 | diagnostic; 8/10 large-only, 12/23 both-win still to Opus |
| C K=3 | — | **32** max (45 Opus) | never reaches 33 |

Q2.1 (B − A Route-AUC): +0.109 on one 46-task split — above frozen on this
seed, inside the §6.1 noise band, not a pass.
Q2.2 (C − B): +0.092.
Q2.3 (D − B): +0.143. Not a substitute for C.

## Validation CE (patched, ES off)

C dived: 0.657 → 0.637 → 0.892 → 1.461 → 2.902. Best checkpoint would have
been epoch 1. B stayed ~0.67; D ended 0.702. Next comparable set turns
`early_stopping: true` on B, C, and D together.

Invalid (do not quote): unshuffled k0 Route-AUC 0.757; unshuffled k1 0.500
(collapse). Adapters for those runs are still in GCS.

## Recorded API dollars (2025-08-02 mini-SWE-agent, this 46-task holdout)

Source: `per_instance_details.json` `cost` on the verified submissions (Qwen
traj `model_stats.instance_cost` matches 500/500). D and C priced from the
actual routed instance IDs in GCS holdout scores. Not Sep 2026 list prices.
Mean per task: $1.08 Opus vs $0.195 Qwen (~5.5×).

| Policy | Opus calls | Successes | Cost | Saved vs always-Opus |
| --- | ---: | ---: | ---: | --- |
| Always-Opus / A / B | 46 | 33 | $49.75 | — |
| D K=1 (diagnostic) | 26 | 33 | $31.88 | $17.87 (35.9%) |
| C K=3 (overfit) | 45 | 32 | $48.66 | $1.09 (2.2%) |
| Oracle (Opus-only only) | 10 | **37** | $19.72 | $30.03 (60.4%) |
| Always-Qwen | 0 | 27 | $8.97 | quality −6 |

Oracle at 10 Opus calls is not a 33-quality policy — sending everyone except
the 10 Opus-only tasks to Qwen also picks up the 4 Qwen-only tasks, so it
hits 37. A cheaper 33 exists as a label oracle: 6 Opus calls, $13.68
(72.5%), using Qwen-only wins as substitutes. That is not the pre-registered
10-call matched-quality read.

## Specialist vs generalist (signed gaps, not absolute Route-AUC)

Generalist is v3 leave-django-out: train 269 other-repo, test all 231 django
(`/journal/2026-08-26-v3-trajectory-router-spec`). Specialist is this smoke:
train 165 django, test 46 django. Do not stack 0.686 vs 0.482 as if
in-distribution ranking is worse — n and train sets differ. Frozen generalist
is v1 text 0.477 ± 0.030; frozen specialist is the E2 logreg refit (0.373).
K=1 has no generalist counterpart.

| Contrast | Generalist (n=231) | Specialist (n=46) |
| --- | --- | --- |
| Fine-tune lift (K=0 − frozen) | +0.209 (0.686 − 0.477) | +0.109 (0.482 − 0.373) |
| Trajectory gap (K=3 − K=0) | −0.099 (0.587 − 0.686) | +0.092 (0.574 − 0.482), C overfit |

Both regimes show a LoRA-over-frozen lift. The trajectory gap flipped sign,
which is the SWE-Router mix-1 vs repo-disjoint pattern — specialist K=3 is
the overfit checkpoint, so this is not a Q2.2 confirmation.

## Recorded-dollar ceilings on both protocols (2025-08-02)

Same `cost` / `instance_cost` files as the 46-task table. Oracle = Opus-only
→ Opus, everyone else → Qwen. Matched-quality frontier = cheapest
incremental Opus-only tasks (Opus $ − Qwen $) plus all Qwen-only to Qwen,
still hitting always-Opus’s own success count (29 calls on 231, 6 on 46).

| | Generalist (v3, n=231) | Specialist (E2, n=46) |
| --- | --- | --- |
| Always-Opus cost | $260.72 | $49.75 |
| Oracle ceiling | 38 calls, $82.01, 172/231 | 10 calls, $19.72, 37/46 |
| % saved at oracle | $178.71, 68.5% | $30.03, 60.4% |
| Frontier to match always-Opus | 29 calls, $62.43, 163 succ | 6 calls, $13.68, 33 succ |
| % saved at matched quality | $198.29, 76.1% | $36.07, 72.5% |
| Trained K=3 | 70.6% successes; call mix never written | 45 calls, 32 succ |
| Trained D K=1 | — | 26 calls, $31.88, save $17.87 (35.9% vs a possible 72.5%) |

The opportunity does not shrink under repo shift. Capture does. D is the
only trained mix we can price. Generalist K=3 `results.json` has
`best_lambda=0.67` and no `holdout_scores.jsonl`; that dollar % is unknown,
not zero. Do not say K=3 saved less than 35.9% as a measured fact — only
that K=1 banked a cheaper 33 and K=3 never showed a cheaper 163.

A run counts only if `artifacts_uri` is a `gs://hecate-506120-artifacts/runs/…`
path with adapter + `holdout_scores.jsonl` (frozen A: scores only).
