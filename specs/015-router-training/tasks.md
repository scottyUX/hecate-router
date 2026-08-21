# Tasks: Router Training v1

**Input**: Design documents from `/specs/015-router-training/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup

- [x] T001 Add optional `[project.optional-dependencies] train` (torch, transformers) in `pyproject.toml`
- [x] T002 [P] Add `configs/router.yaml` (backbone, max_tokens, n_folds, seeds, lambda grid)
- [x] T003 [P] Create `src/hecate/router/__init__.py` package exports

## Phase 2: Foundational

- [x] T004 Tokenizer protocol + whitespace tokenizer in `src/hecate/router/dataset.py`
- [x] T005 `RouterExample` dataclass in `src/hecate/router/dataset.py`

## Phase 3: User Story 1 — Dataset (P1) 🎯 MVP

- [x] T006 [P] [US1] Tests for join, truncation, and no-patch-leak in `tests/test_router.py`
- [x] T007 [US1] `build_examples` in `src/hecate/router/dataset.py` (depends on T004–T006)

**Checkpoint**: Synthetic labels produce truncated, leak-free rows

## Phase 4: User Story 2 — CV loop (P1)

- [x] T008 [P] [US2] Tests for label×repo / repo / round-robin fallback in `tests/test_router.py`
- [x] T009 [US2] `assign_folds` in `src/hecate/router/splits.py`
- [x] T010 [P] [US2] `EncoderBackend` + `ScriptedBackend` in `src/hecate/router/backends.py`
- [x] T011 [US2] `run_train` in `src/hecate/router/runner.py` + `scripts/run_train.py` using ScriptedBackend by default
- [x] T012 [US2] `ModernBertBackend` gated on the train extra (import inside methods)

**Checkpoint**: `pytest tests/test_router.py` passes without torch

## Phase 5: User Story 3 — Metrics (P1)

- [x] T013 [P] [US3] Tests for Route-AUC integral and baselines in `tests/test_router.py`
- [x] T014 [US3] `route_metrics` in `src/hecate/router/metrics.py`
- [x] T015 [US3] Manifest fields: split_strategy, truncation_rate, go_nogo, mean Route-AUC

## Phase 6: Polish

- [x] T016 [P] README pointer to `scripts/run_train.py` and quickstart
- [x] T017 Run `pytest tests/test_router.py tests/test_execution.py` (offline)

## Dependencies

Setup → Foundational → US1 → US2/US3 (metrics can land before the full runner). Live ModernBERT fit waits on Stage-3 labels from the GCP 600-eval.
