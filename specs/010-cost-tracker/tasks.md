# Tasks: Cost Tracker & Hard Budget Guard

**Input**: Design documents from `/specs/010-cost-tracker/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cost-api.md

**Tests**: Required by SC-001–SC-005 / quickstart.md (offline, `tmp_path` ledgers, zero provider spend). Test-first within each story.

**Organization**: Tasks grouped by user story (US1–US4) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files / independent, no incomplete deps)
- **[Story]**: US1 / US2 / US3 / US4 from spec.md
- Include exact file paths

## Phase 1: Setup

**Purpose**: Confirm package layout and dependencies

- [x] T001 Confirm `src/hecate/cost/` exists (stub `__init__.py`) and that `tracker.py` is the planned home per `plan.md`
- [x] T002 Confirm no new dependency needed beyond existing `pyyaml`; confirm `data/outputs/` is gitignored (`.gitignore`)
- [x] T003 Confirm Option A exposes `budget.target_usd`, `budget.ceiling_usd`, and per-model `input_cost_per_1m` / `output_cost_per_1m` in `configs/option_a.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Types, errors, config/pricing load, cost formula before tracker behavior

**⚠️ CRITICAL**: Complete before user-story implementation

- [x] T004 [P] Add exception hierarchy in `src/hecate/cost/tracker.py`: `CostError`, `BudgetExceededError` (with total/ceiling/estimate attrs + message), `CostConfigError`, `CostLedgerError`, `CostAccountingError` (contract)
- [x] T005 [P] Add frozen `BudgetConfig`, `ModelPricing`, `BudgetStatus` dataclasses in `src/hecate/cost/tracker.py` per data-model.md
- [x] T006 Implement `load_budget_config` / `load_model_pricing` from Option A YAML (default path `configs/option_a.yaml`); invalid/missing → `CostConfigError` (FR-003)
- [x] T007 Implement `estimate_cost(model_slug, prompt_tokens, completion_tokens, pricing=None)` per D1; unknown slug / invalid tokens → `CostAccountingError` (FR-002, FR-009)
- [x] T008 Implement `default_ledger_path()` → `data/outputs/cost/ledger.json` and `LEDGER_SCHEMA_VERSION` constant (K-8, D3)
- [x] T009 Re-export public API from `src/hecate/cost/__init__.py` and set `__all__`

**Checkpoint**: Foundation ready — user stories can proceed

---

## Phase 3: US2 — Accurate running total from token usage (P1)

**Goal**: Pricing math and `record` update the running total correctly.

- [x] T010 [US2] Test: `estimate_cost` for a known Option A slug matches hand-computed USD (SC-003) — `tests/test_cost.py`
- [x] T011 [P] [US2] Test: unknown slug raises `CostAccountingError` (FR-009)
- [x] T012 [P] [US2] Test: negative / non-int-like token rejection (FR-009)
- [x] T013 [US2] Test: multiple `record` calls sum into `total_usd` (FR-001, FR-006)
- [x] T014 [US2] Implement `CostTracker.__init__` / `total_usd` / `record` / `record_usage` happy path (in-memory first; persist in US3) to make T010–T013 pass

**Checkpoint**: Totals match pricing math

---

## Phase 4: US1 — Refuse over-ceiling calls (P1) 🎯 MVP Done-when

**Goal**: `authorize` fail-closed before spend; loggable reason.

- [x] T015 [US1] Test: when `total + estimate > ceiling`, `authorize` raises `BudgetExceededError` with total/ceiling/estimate in message (FR-004, FR-005, SC-001) — `tests/test_cost.py`
- [x] T016 [P] [US1] Test: `total + estimate == ceiling` is allowed (edge case)
- [x] T017 [P] [US1] Test: estimate under remaining headroom is allowed
- [x] T018 [US1] Test: simulated multi-step run halts on the first over-budget authorize and never “continues” (SC-001)
- [x] T019 [US1] Implement `CostTracker.authorize` per K-1/K-2 (FR-004, FR-005)

**Checkpoint**: Done-when satisfied offline

---

## Phase 5: US3 — Persist across restarts (P1)

**Goal**: Ledger survives process boundaries; corrupt → fail closed.

- [x] T020 [US3] Test: record with one tracker, fresh tracker on same path loads same total (FR-007, SC-002) — `tests/test_cost.py`
- [x] T021 [US3] Test: missing ledger → start at 0 (K-4)
- [x] T022 [US3] Test: corrupt / schema-invalid ledger → `CostLedgerError` on init, not zero (FR-008)
- [x] T023 [US3] Implement atomic ledger load/save in `CostTracker` (temp + `os.replace`, D3/D4, K-3/K-5)

**Checkpoint**: Restart-safe and corruption-safe

---

## Phase 6: US4 — Soft target status only (P2)

**Goal**: Target visible; does not block authorize.

- [x] T024 [US4] Test: total above target and below ceiling → `authorize` succeeds and `status().target_exceeded` is True (FR-010, SC-004)
- [x] T025 [US4] Implement `CostTracker.status` → `BudgetStatus` (remaining headroom, target_exceeded)

**Checkpoint**: Soft vs hard distinction clear

---

## Phase 7: Polish

- [x] T026 [P] Module docstring + type hints; `from __future__ import annotations`; match `src/hecate` style
- [x] T027 Docs alignment: quickstart matches public API; no runner wiring added (S11 owns orchestration)
- [x] T028 Run `pytest tests/test_cost.py -v` and `pytest tests/ -q` — confirm pass with no `OPENROUTER_API_KEY` and no network (FR-011, SC-005)

## Dependency graph (stories)

```text
Phase 1 → Phase 2 → US2 (totals) → US1 (authorize) → US3 (persist) → US4 (status) → Polish
```

US1 depends on a working `total_usd` (US2). Persist (US3) layers onto record.
US4 only needs `status` + authorize semantics.

## FR coverage

| FR | Tasks |
|----|-------|
| FR-001 | T013, T014 |
| FR-002 | T007, T010 |
| FR-003 | T003, T006 |
| FR-004 | T015–T019 |
| FR-005 | T015, T019 |
| FR-006 | T013, T014 |
| FR-007 | T020, T023 |
| FR-008 | T022, T023 |
| FR-009 | T007, T011, T012 |
| FR-010 | T024, T025 |
| FR-011 | T028 |
| FR-012 | documented in authorize/estimate tests (T018 uses upper-bound estimates) |
