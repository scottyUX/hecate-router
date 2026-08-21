# Implementation Plan: Router Training v1

**Branch**: `014-execution-labels` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-router-training/spec.md`

## Summary

Add a Stage-4 router package that joins Stage-3 labels with Stage-1 prompts, truncates to 2048 tokens, cross-validates a binary P(m1 resolves) head, and reports Route-AUC against always-m1 / always-m2 / random / oracle. Live ModernBERT is an optional extra; CI uses a scripted encoder.

## Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**: stdlib for dataset/splits/metrics. Optional extra `train`: `torch`, `transformers`. No new default runtime packages.

**Storage**: JSONL/JSON under `data/outputs/runs/<train-run-id>/` (gitignored).

**Testing**: `pytest`; scripted encoder; no Hugging Face download in default CI.

**Target Platform**: Local Mac (MPS/CPU) for v1 live train; library + CLI.

**Project Type**: Library modules + thin CLI script.

**Performance Goals**: 300 examples × 5 folds × 3 seeds on CPU/MPS in one sitting.

**Constraints**: Patch text never in input; optional deps; constitution manifests; zero-spend CI.

**Scale/Scope**: `src/hecate/router/`, `configs/router.yaml`, `scripts/run_train.py`, `tests/test_router.py`.

## Constitution Check

*GATE: Evaluated against constitution **v1.0.0**.*

| Principle | Verdict | Basis |
|-----------|---------|-------|
| I. Execution-Grounded Validity | **PASS** | Labels from Stage 3 `resolved`; patch not an input. |
| II. Reproducibility by Manifest | **PASS (delivers)** | Train manifest: config, SHA, seeds, folds, metrics. |
| III. Offline-Testable, Zero-Spend CI | **PASS** | Scripted encoder; live train extra-gated. |
| IV. Spec-Driven Development | **PASS** | Full artifact set; FRs map to tasks. |
| V. Budget Discipline | **PASS / N/A** | No OpenRouter spend; local fine-tune. |
| VI. Secrets Hygiene | **PASS** | HF downloads use public weights; no new secrets. |
| VII. Shared-Scaffold Fairness | **PASS** | Input is the shared prompt; model slug is not a feature. |

**New module path**: constitution lists `data/ scaffold/ generation/ caching/ cost/ utils/`. `src/hecate/router/` matches the README Stage-4 map and is recorded here.

**Result: GREEN — no violations.**

**Post-design re-check**: **PASS** — injectable encoder backend; metrics have no torch dependency.

## Project Structure

### Documentation (this feature)

```text
specs/015-router-training/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/router-api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
configs/router.yaml
src/hecate/router/
├── __init__.py
├── dataset.py
├── splits.py
├── metrics.py
├── backends.py
└── runner.py
scripts/run_train.py
tests/test_router.py
```

**Structure Decision**: Same single-package layout as Stage 2/3.

## Complexity Tracking

None.
