# Implementation Plan: Cost Tracker & Hard Budget Guard

**Branch**: `010-cost-tracker` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-cost-tracker/spec.md`

## Summary

Add a pure, offline cost-accounting module in `src/hecate/cost/tracker.py` that
(1) prices token usage from Option A per-model rates, (2) maintains a running USD
total persisted under gitignored `data/outputs/cost/`, and (3) fail-closed
authorizes each proposed paid call against the hard ceiling ($100) using an
upper-bound estimate — refusing with a loggable `BudgetExceededError` before any
provider call would start.

The OpenRouter client (S7) stays cost-unaware; the generation runner (S11) will
call `authorize` → complete → `record`. Soft target (~$38) is status-only.
Operator ceiling override, multi-writer locking, and live price fetches are out
of scope.

## Technical Context

**Language/Version**: Python 3.10+ (`pyproject.toml` `requires-python = ">=3.10"`)

**Primary Dependencies**: Existing `pyyaml` for Option A config load; stdlib
`json` / `os` / `pathlib` / `tempfile` / `dataclasses` for ledger I/O. **No new
runtime dependency.**

**Storage**: Single JSON ledger at `data/outputs/cost/ledger.json` (gitignored).
Atomic write via temp + `os.replace`.

**Testing**: `pytest`, fully offline, zero provider spend. `tmp_path` ledgers;
over-budget simulated without a client.

**Target Platform**: Local / CI Python package.

**Project Type**: Library module in the Stage-1 `cost` package.

**Performance Goals**: Negligible — one authorize + one record per generation
(≤1,200).

**Constraints**: Fail closed on ceiling (FR-004), corrupt ledger (FR-008), missing
prices/tokens (FR-009); soft target non-blocking (FR-010); offline (FR-011).

**Scale/Scope**: One tracker module + errors + config/pricing loaders + one
offline test module; re-exports from `hecate.cost`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.
Evaluated against ratified constitution **v1.0.0**.*

| Principle | Verdict | Basis |
|-----------|---------|-------|
| I. Execution-Grounded Validity | **N/A / PASS** | No labeling or scaffold changes; does not weaken invariants. |
| II. Reproducibility by Manifest | **PASS (supports)** | Exposes `total_usd` / `status()` so S11 can put total cost on the run manifest; per-call USD feeds `GenerationRecord.cost_usd`. |
| III. Offline-Testable, Zero-Spend CI | **PASS** | No network/credentials (K-9); SC-005. |
| IV. Spec-Driven Development | **PASS** | Full artifact set; FRs map to tasks. |
| V. Budget Discipline | **PASS (delivers)** | Hard ceiling fail-closed authorize; soft target recorded; prices from committed S4 config. |
| VI. Secrets Hygiene | **N/A** | No credential handling. |
| VII. Shared-Scaffold Fairness | **PASS** | Pricing is per slug from shared config; no prompt/decoding mutation. |

**Engineering-constraints check**: code in `src/hecate/cost/` per README map;
frozen dataclasses + `from __future__ import annotations`; small reviewable diff;
`data/outputs/` stays gitignored.

**Result: GREEN — no violations.**

**Post-design re-check**: **PASS** — design adds `tracker.py` (+ thin errors if
kept in-module), re-exports, one contract, one offline test module. No client
wrapping; no constitution weakening.

## Project Structure

### Documentation (this feature)

```text
specs/010-cost-tracker/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cost-api.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/hecate/cost/
├── __init__.py          # re-export public API
└── tracker.py           # BudgetConfig, pricing load, estimate_cost, CostTracker, errors

tests/
└── test_cost.py         # offline: math, authorize, persist, corrupt, soft target
```

**Structure Decision**: Implement inside the existing stub package `hecate.cost`
(README: “token accounting + budget guard”). Single module keeps the surface
small; errors live alongside the tracker unless a split becomes necessary.

## Complexity Tracking

> No constitution violations requiring justification.

| Decision | Why | Alternative rejected |
|----------|-----|----------------------|
| Single JSON ledger (running total only) | Matches FR-007; simple restart story | Per-call JSONL audit log — useful later, not required for Done when |
| Authorize(estimate) separate from record(actual) | Clear fail-closed pre-call; honest ledger | Two-phase reservation ledger |
| Fail closed on corrupt ledger | Principle V | Silent reset to zero |
