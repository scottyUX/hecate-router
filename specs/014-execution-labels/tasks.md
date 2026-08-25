# Tasks: Execution Harness and Routing Labels

**Input**: Design documents from `/specs/014-execution-labels/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required (constitution III; FR-009). Write tests first where noted.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [x] T001 Create package stub `src/hecate/execution/__init__.py`
- [x] T002 [P] Add `configs/execution.yaml` with dataset, input path, workers, timeout, namespace, cache_level
- [x] T003 [P] Add `logs/` to `.gitignore`; add `live_eval` pytest marker in `pyproject.toml`

---

## Phase 2: Foundational

- [x] T004 Add `resolved: bool | None = None` to `GenerationRecord` in `src/hecate/data/records.py` (older payloads load as None)
- [x] T005 Update `tests/test_data.py` so Stage-2 serialization includes `resolved`

**Checkpoint**: Record schema round-trips with `resolved`

---

## Phase 3: User Story 1 - Execute patches and record outcomes (Priority: P1) 🎯 MVP

**Goal**: Predictions adapter, injectable harness, merge, execution runner, CLI.

**Independent Test**: `pytest tests/test_execution.py` with `ScriptedHarness`; Stage-1 file unchanged.

### Tests for User Story 1

- [x] T006 [P] [US1] Tests for `has_executable_patch` / `to_prediction` / `write_predictions` in `tests/test_execution.py`
- [x] T007 [P] [US1] Tests for `apply_report` / missing report in `tests/test_execution.py`
- [x] T008 [US1] Tests for `run_execution` with `ScriptedHarness` (valid patch, no-patch skip, immutable input) in `tests/test_execution.py`

### Implementation for User Story 1

- [x] T009 [P] [US1] Implement `src/hecate/execution/predictions.py`
- [x] T010 [P] [US1] Implement harness protocol, `ScriptedHarness`, and `SwebenchHarness` in `src/hecate/execution/harness.py`
- [x] T011 [P] [US1] Implement `src/hecate/execution/merge.py`
- [x] T012 [US1] Implement `load_execution_config` / `run_execution` in `src/hecate/execution/runner.py` (dry-run, no-patch short-circuit, harness merge, manifest)
- [x] T013 [US1] Implement `scripts/run_execution.py` and export public API from `src/hecate/execution/__init__.py`

**Checkpoint**: US1 offline path works end-to-end

---

## Phase 4: User Story 2 - Full matrix and resume (Priority: P1)

**Goal**: Completeness check, resume skip, pending-missing-report.

**Independent Test**: Incomplete matrix raises; resume does not re-invoke harness for finished pairs.

### Tests for User Story 2

- [x] T014 [US2] Tests for incomplete matrix, resume skip, and pending missing report in `tests/test_execution.py`

### Implementation for User Story 2

- [x] T015 [US2] Enforce matrix completeness, resume via `patch_applied is not None`, and pending-on-missing-report in `src/hecate/execution/runner.py`

**Checkpoint**: US1 + US2 hold

---

## Phase 5: User Story 3 - Labels and pre-flight (Priority: P1)

**Goal**: Binary m1 labels + pre-flight JSON.

**Independent Test**: Synthetic two-model JSONL produces expected complementarity and headroom.

### Tests for User Story 3

- [x] T016 [US3] Tests for labels, complementarity, headroom, scaffold mismatch, incomplete tasks in `tests/test_execution.py`

### Implementation for User Story 3

- [x] T017 [US3] Implement `src/hecate/execution/labels.py`
- [x] T018 [US3] Implement `scripts/run_labels.py` and wire exports

**Checkpoint**: All stories independently testable

---

## Phase 6: Polish

- [x] T019 [P] Update README module map and Stage-2/3 quick start
- [x] T020 [P] Optional `live_eval` skip-unless-`RUN_LIVE_EVAL=1` test in `tests/test_execution.py`
- [x] T021 Run `pytest` (offline) and confirm quickstart dry-run path

---

## Dependencies & Execution Order

- Setup → Foundational (schema) → US1 → US2 (extends runner) → US3 → Polish
- T006–T008 should fail until T009–T013 exist
- T014 depends on US1 runner
- T016/T017 independent of Docker

### Parallel opportunities

- T002 / T003 with T001
- T009 / T010 / T011 after tests T006–T007
- T019 / T020 after labels

## Implementation Strategy

MVP is US1 (execute + record with fake harness). US2 makes 600-pair runs safe. US3 unblocks E-M4 pre-flight. Full Docker 600 is operator/GCP, not required to close the coding tasks.
