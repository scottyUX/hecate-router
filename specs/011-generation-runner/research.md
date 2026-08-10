# Research: Generation Runner

**Branch**: `011-generation-runner` | **Date**: 2026-08-10

## D1 — Orchestrator owns the loop; libraries stay unaware of each other

**Decision**: Implement `hecate.generation.runner` as the sole orchestrator that
calls scaffold → cache → cost → client → patch → records/manifest. Do not teach
the OpenRouter client about cache or cost.

**Rationale**: Matches S7–S10 contracts (each module is independently testable)
and keeps CI zero-spend.

**Alternatives considered**: Baking authorize into the client (rejected — couples
budget to HTTP); cache inside the client (rejected — S9 explicitly keeps client
cache-unaware).

## D2 — Upper-bound authorize before every paid call

**Decision**: Before `complete`, estimate with `completion_tokens = decoding.max_tokens`
(or equivalent upper bound from config) and call `CostTracker.authorize`. On
`BudgetExceededError`, stop that pair (and halt further paid pairs in the run).

**Rationale**: S10 FR / constitution hard ceiling. Worst-case estimate prevents
overshoot.

**Alternatives considered**: Authorize after the call (rejected — money already
spent); soft-target halt (rejected — soft target is status-only).

## D3 — Cache hit skips authorize and record_usage for provider spend

**Decision**: On cache hit, reuse `raw_response` / token fields from
`CachedGeneration`, extract patch, write a record, and do **not** call authorize
or `record_usage` (no new spend). Manifest total reflects ledger total (prior
paid spend only).

**Rationale**: Hits are not new charges; double-counting would halt early.

## D4 — Dry-run builds context/prompt and writes a stub record path without network

**Decision**: `--dry-run` loads tasks/config, builds context + prompt, computes
cache keys, skips provider and spend, and may write a manifest annotated
`dry_run: true`. It MUST NOT require `OPENROUTER_API_KEY`.

**Rationale**: Constitution III + FR-013; unblocks CI and operator wiring checks.

## D5 — Manifest via small utils helper

**Decision**: Add `hecate.utils.manifest.write_run_manifest(...)` writing JSON
under `data/outputs/runs/<run_id>/manifest.json` (or path supplied by runner).

**Rationale**: Constitution II; reusable by pilot and future sweep.

## D6 — Pilot script thin CLI over runner

**Decision**: `scripts/run_pilot.py` parses args and calls into the runner API;
business logic lives in the library module for tests.

**Rationale**: Matches prior script pattern; Done when is the script entry point.
