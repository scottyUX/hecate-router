# Implementation Plan: Generation Runner (Orchestrator)

**Branch**: `011-generation-runner` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-generation-runner/spec.md`

## Summary

Add a Stage-1 generation orchestrator in `src/hecate/generation/runner.py` that
ties S5–S10 into a resumable (task × model) loop: shared context/prompt → cache
lookup → budget authorize → OpenRouter complete → patch extract → cache/cost
update → JSONL record, plus a run manifest. Expose `scripts/run_pilot.py` so a
1-task dry-run (CI) and live path (operator) both work. Libraries remain
unaware of each other; the runner is the only integrator.

## Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**: Existing stack — `httpx`/`yaml` via S7, S5–S10 packages;
stdlib `asyncio`, `json`, `dataclasses`, `uuid`, `subprocess` (git SHA). **No new
runtime dependency.**

**Storage**: JSONL records + manifest under `data/outputs/runs/<run_id>/`
(gitignored); reuses S9 cache dir and S10 ledger.

**Testing**: `pytest` + `pytest-asyncio`; offline with injectable/mocked client;
live tests doubly gated.

**Target Platform**: Local / CI Python package + CLI scripts.

**Project Type**: Library module + thin pilot CLI.

**Performance Goals**: Support pilot (20 × 1) and later 1,200-pair sweeps; throughput
bounded by existing client concurrency semaphore.

**Constraints**: Shared scaffold; fail-closed budget; zero-spend CI; no secrets in
logs; dry-run without credentials.

**Scale/Scope**: One runner module, manifest helper, pilot script wiring, offline
tests; sweep script may call the same runner later (S14).

## Constitution Check

*GATE: Evaluated against constitution **v1.0.0**.*

| Principle | Verdict | Basis |
|-----------|---------|-------|
| I. Execution-Grounded Validity | **PASS** | Shared scaffold; single-shot; full matrix records; no label scheme. |
| II. Reproducibility by Manifest | **PASS (delivers)** | Writes manifest with config, slugs, timestamp, git commit, cost. |
| III. Offline-Testable, Zero-Spend CI | **PASS** | Mocked client / dry-run; live doubly gated. |
| IV. Spec-Driven Development | **PASS** | Full artifact set; FRs map to tasks. |
| V. Budget Discipline | **PASS** | Authorize before paid calls via S10. |
| VI. Secrets Hygiene | **PASS** | Credentials only via `get_openrouter_api_key`; never logged. |
| VII. Shared-Scaffold Fairness | **PASS** | Context/prompt identical across models; only slug varies. |

**Result: GREEN — no violations.**

**Post-design re-check**: **PASS** — orchestrator + manifest + pilot CLI only;
no changes to S6–S10 algorithms.

## Project Structure

### Documentation (this feature)

```text
specs/011-generation-runner/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── runner-api.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/hecate/
├── generation/
│   ├── runner.py          # NEW orchestrator
│   └── __init__.py        # re-export RunConfig, RunResult, run_generation
├── utils/
│   ├── manifest.py        # NEW write_run_manifest, git_commit_sha
│   └── __init__.py
scripts/
└── run_pilot.py           # wire to runner
tests/
└── test_runner.py         # NEW offline orchestration tests
```

## Complexity Tracking

No constitution violations requiring justification. Complexity is orchestration
glue only.
