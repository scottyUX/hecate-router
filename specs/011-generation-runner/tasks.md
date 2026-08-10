# Tasks: Generation Runner (Orchestrator)

**Input**: Design documents from `/specs/011-generation-runner/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/runner-api.md

**Tests**: Required by SC-001–SC-005 / quickstart.md (offline first; live doubly gated).

**Organization**: Tasks grouped by user story (US1–US4).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [x] T001 Confirm S5–S10 imports resolve on branch (`scaffold`, `generation`, `caching`, `cost`, `data`)
- [x] T002 Create `tests/test_runner.py` skeleton with asyncio mode already enabled in pyproject
- [x] T003 [P] Update `.specify/feature.json` to `specs/011-generation-runner`

## Phase 2: Foundational

- [x] T004 [P] Add `src/hecate/utils/manifest.py` with `git_commit_sha` + `write_run_manifest`
- [x] T005 [P] Re-export manifest helpers from `src/hecate/utils/__init__.py`
- [x] T006 Add frozen `RunConfig` / `RunResult` dataclasses in `src/hecate/generation/runner.py`
- [x] T007 Implement `load_run_config` (defaults, model slug validation against Option A)

**Checkpoint**: Config + manifest helpers ready

## Phase 3: User Story 1 — One pair end-to-end (P1)

- [x] T008 [US1] Test (failing): mocked complete path writes JSONL record with extraction fields — `tests/test_runner.py`
- [x] T009 [P] [US1] Test: cache hit skips provider (call counter = 0)
- [x] T010 [P] [US1] Test: near-ceiling ledger ⇒ authorize refuse, no provider call
- [x] T011 [US1] Implement async pair loop in `run_generation`: context → prompt → cache → authorize → complete → extract → cache/cost → append_jsonl
- [x] T012 [US1] Inject optional client factory / complete callable for tests

**Checkpoint**: US1 offline scenarios green

## Phase 4: User Story 2 — Resume (P1)

- [x] T013 [US2] Test: new process with same cache dir + ledger serves hit and restores total
- [x] T014 [US2] Ensure runner constructs `GenerationCache` / `CostTracker` from config paths (no in-memory-only store)

## Phase 5: User Story 3 — Manifest + records (P1)

- [x] T015 [US3] Test: manifest contains config snapshot, slugs, timestamp, git commit, total_cost_usd
- [x] T016 [US3] Test: shared scaffold — two model slugs get identical prompt_hash for same task (when both processed with mocks)
- [x] T017 [US3] Write manifest at end of `run_generation`; include pair counters

## Phase 6: User Story 4 — Pilot CLI (P2)

- [x] T018 [US4] Wire `scripts/run_pilot.py` to `load_run_config` + `asyncio.run(run_generation(...))`
- [x] T019 [US4] Test or manual: `--dry-run --tasks 1` exits 0 without key
- [x] T020 [P] [US4] Re-export runner API from `src/hecate/generation/__init__.py`

## Phase 7: Polish

- [x] T021 [P] Module docstrings + type hints; match `src/hecate` style
- [x] T022 Docs: quickstart commands match CLI flags
- [x] T023 Run `pytest tests/test_runner.py -v` and `pytest tests/ -q` — offline pass (FR-012, SC-005)

## Dependency graph

```text
Phase 1 → Phase 2 → US1 → US2 → US3 → US4 → Polish
```

## FR coverage

| FR | Tasks |
|----|-------|
| FR-001 | T007, T011 |
| FR-002 | T011, T016 |
| FR-003 | T009, T011 |
| FR-004 | T010, T011 |
| FR-005 | T011, T018 |
| FR-006 | T008, T011 |
| FR-007 | T009, T011 |
| FR-008 | T011 |
| FR-009 | T008, T011 |
| FR-010 | T015, T017 |
| FR-011 | T018, T019 |
| FR-012 | T008–T010, T023 |
| FR-013 | T019 |
