# Stage-2/3 GCP execution pilot (20 × 2)

**Date**: 2026-08-20
**Run id**: `exec-pilot-20`
**Stage-1 input**: `data/outputs/runs/sweep-2x300-qwen/generations.jsonl`
**Config**: `configs/execution.yaml` (`namespace: swebench`)
**Code on the VM**: `a6b9387`
**Journal**: `2026-08-20-gcp-exec-pilot-20`

## Recommendation

**Do not start E-M4 router training on this slice.**

The 20-task pre-flight has no routing headroom: the small model resolved nothing,
and an oracle that picks the better model per task matches always-72B. This is a
front-of-file sample, not a verdict on the full 300. Execution itself worked.

Router training did **not** run. Labels exist; the encoder was not fine-tuned.

## Setup

Local ARM Mac cannot pull SWE-bench prebuilt `linux/x86_64` images. Eval ran on
GCP project `hecate-506120`.

| | |
|---|---|
| Instance | `hecate-exec` |
| Machine | `e2-standard-8` (8 vCPU / 32 GB; `n2-standard-8` sold out in `us-central1`) |
| Zone | `us-central1-a` |
| Disk | 200 GB pd-balanced, Ubuntu 22.04 |
| Harness | SWE-bench `4.1.0`, Docker namespace `swebench` |
| Models | `qwen/qwen-2.5-7b-instruct` (m1) · `qwen/qwen-2.5-72b-instruct` (m2) |

Runbook: [`docs/EXECUTION_GCP.md`](EXECUTION_GCP.md). The VM was **stopped** after
the pilot (disk still bills; CPU does not).

## Method

1. Gold smoke: official patch for `astropy__astropy-12907`.
2. Hecate smoke: both models on `astropy__astropy-14182` (both Stage-1 patches
   parsed).
3. Pilot: first 20 unique instance ids from the Stage-1 sweep × both models
   (`--tasks 20 --max-workers 4 --run-id exec-pilot-20`).
4. `scripts/run_labels.py` → `labels.jsonl` + `preflight.json`.

**Resolved** means SWE-bench FULL resolution: patch applied, all FAIL_TO_PASS
tests pass, all PASS_TO_PASS tests still pass.

Six pairs finished the harness as SWE-bench `error_ids` (patch apply failed, no
per-instance `report.json`). Those were recorded as `patch_applied=False`,
`resolved=False` so the 20-task matrix is complete. Resume would re-run Docker
and likely hit the same apply errors.

## Results

### Smokes

| Check | Instance | Outcome |
|-------|----------|---------|
| Gold | `astropy__astropy-12907` | 1/1 resolved |
| Hecate | `astropy__astropy-14182` × both models | both patches applied; neither resolved |

### Pilot matrix (40 pairs)

| Count | Value |
|-------|------:|
| Pairs attempted | 40 |
| No executable patch (parse fail / empty) | 9 |
| Docker-evaluated | 25 |
| SWE-bench apply/eval errors (filled not-applied) | 6 |
| Resolved | **1** |

The one resolve: **72B** on `django__django-10914`. 7B did not resolve that task.

### Pre-flight (`preflight.json`)

| Metric | Value |
|--------|------:|
| Tasks with both models | 20 |
| Shared scaffold | ok (prompt hashes match) |
| 7B resolve rate | **0%** (0/20) |
| 72B resolve rate | **5%** (1/20) |
| Complementarity | both 0 · only-m1 0 · only-m2 1 · neither 19 |
| Oracle routing resolve rate | 5% |
| Routing headroom (oracle − always-72B) | **0** |
| `m1_positive_rate_flag` (< 15%) | **true** |

Artifacts (gitignored; on the VM at `/opt/hecate`):
`data/outputs/runs/exec-pilot-20/` and `data/outputs/runs/exec-smoke/`.
Share them on the disk, do not commit `data/outputs/`.

## Interpretation

Stage-2 Docker eval on GCP is viable: gold resolved, Hecate patches apply, labels
write. The 20-task slice is mostly Astropy then Django from the start of SWE-bench
Lite, so rates are not the full-300 estimate.

Issue #18 still needs either the remaining 280 tasks × 2 models, or an explicit
weak-floor waiver. Headroom 0 means a router cannot beat “always use 72B” on
this labeled set.

## Next

- Start `hecate-exec` and run `scripts/run_execution.py` without `--tasks` (full
  600), then rebuild pre-flight.
- Or accept a weak m1-positive floor and scaffold E-M4 anyway.
- Do not commit `data/outputs/` or eval logs.
