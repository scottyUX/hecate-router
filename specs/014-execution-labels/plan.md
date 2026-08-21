# Implementation Plan: Execution Harness and Routing Labels

**Branch**: `014-execution-labels` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-execution-labels/spec.md`

## Summary

Add a Stage-2 execution orchestrator that converts Stage-1 `generations.jsonl` into per-model SWE-bench prediction files, calls `swebench.harness.run_evaluation.main` through an injectable harness, merges `report.json` back onto `GenerationRecord` Stage-2 fields (including new `resolved`), and writes a new run directory (Stage-1 artifacts stay immutable). Add Stage-3 label construction and the E-M4 pre-flight report. Offline tests use a fake harness; Docker is opt-in.

## Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**: Existing `swebench==4.1.0` (already in `pyproject.toml`); `pyyaml`; stdlib dataclasses/json/pathlib. No new runtime package.

**Storage**: JSONL + JSON under `data/outputs/runs/<exec-run-id>/` (gitignored). Harness logs under that run dir (`logs/run_evaluation/`), never repo root.

**Testing**: `pytest`; fake harness for CI; optional `@pytest.mark.live_eval` gated on `RUN_LIVE_EVAL=1`.

**Target Platform**: Local/CI Python package + CLI; live eval on x86 Docker (GCP `n2-standard-8`) or ARM with `--namespace none`.

**Project Type**: Library modules + thin CLI scripts.

**Performance Goals**: Support smoke (1–2 instances), 20-task pilot, and 300×2=600-pair sweep with resume.

**Constraints**: Full matrix; no silent drops; zero Docker in default CI; constitution manifests; do not mutate Stage-1 files.

**Scale/Scope**: New `src/hecate/execution/` package, two scripts, config YAML, schema field `resolved`, offline tests, smoke docs.

## Constitution Check

*GATE: Evaluated against constitution **v1.0.0**.*

| Principle | Verdict | Basis |
|-----------|---------|-------|
| I. Execution-Grounded Validity | **PASS** | Labels from harness resolved/apply only; full matrix; Stage-1 file unchanged; no new prompting. |
| II. Reproducibility by Manifest | **PASS (delivers)** | Execution and label runs write manifests (config, SHA, timestamp, counts, swebench version). |
| III. Offline-Testable, Zero-Spend CI | **PASS** | Fake harness; live eval doubly gated; no OpenRouter calls. |
| IV. Spec-Driven Development | **PASS** | Full artifact set; FRs map to tasks. |
| V. Budget Discipline | **PASS / N/A** | No provider spend; compute-bound eval is operator-triggered. |
| VI. Secrets Hygiene | **PASS** | No new credentials; Modal path unused unless operator opts in later. |
| VII. Shared-Scaffold Fairness | **PASS** | Execution applies existing patches only; pre-flight reports prompt-hash mismatches. |

**Result: GREEN — no violations.**

**Post-design re-check**: **PASS** — adapter + harness protocol + merge + labels; no Docker in pytest default path.

## Project Structure

### Documentation (this feature)

```text
specs/014-execution-labels/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── execution-api.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
configs/execution.yaml
src/hecate/
├── data/records.py              # add resolved
├── execution/
│   ├── __init__.py
│   ├── predictions.py
│   ├── harness.py
│   ├── merge.py
│   ├── labels.py
│   └── runner.py
scripts/
├── run_execution.py
└── run_labels.py
tests/
├── test_data.py                 # resolved field
└── test_execution.py
```

**Structure Decision**: Single-package layout matching Stage 1 (`src/hecate/<stage>/` + thin `scripts/`).

## Complexity Tracking

No constitution violations requiring justification.
