# Research: Cost Tracker & Hard Budget Guard (S10)

Phase 0 decisions. Each resolves a spec unknown into a concrete, testable approach.

## D1 — USD cost from tokens × per-1M prices

**Decision**:  
`cost_usd = (prompt_tokens / 1e6) * input_cost_per_1m + (completion_tokens / 1e6) * output_cost_per_1m`

Prices and slugs come from `configs/option_a.yaml` (`models[].input_cost_per_1m` /
`output_cost_per_1m`). Budget numbers from `budget.target_usd` / `budget.ceiling_usd`.

**Rationale**: Matches the S4 pricing table already used for dry-run estimates; no
live price fetch (offline, reproducible).

**Alternatives rejected**: Live OpenRouter price API (network + non-determinism in
CI); hard-coded price constants in Python (duplicates YAML).

## D2 — Authorize on upper-bound estimate; record actuals

**Decision**: Public flow is `authorize(estimate_usd)` then later
`record(actual_usd)`. Authorization refuses iff `total + estimate > ceiling`.
Recording adds the **actual** USD (from real token usage), not the estimate.

**Rationale**: FR-004/FR-006/FR-012. Worst-case estimates (e.g. completion =
`max_tokens`) keep the guard fail-closed before spend; actuals keep the ledger
honest for manifests.

**Alternatives rejected**: Deducting the estimate up front and reconciling later
(two-phase ledger complexity for a single-writer Stage-1 runner); checking only
after the call (cannot prevent breach).

## D3 — Single JSON ledger file with atomic replace

**Decision**: Persist `{schema_version, total_usd, target_usd, ceiling_usd, updated_at}`
as one JSON file under `data/outputs/cost/` (gitignored via `data/outputs/`).
Writes use temp file + `os.replace` (same pattern as S9).

**Rationale**: Restart survival (FR-007), human-inspectable, stdlib, matches
existing gitignore. Atomic rename avoids partial reads looking like a valid zero
or truncated total.

**Alternatives rejected**: SQLite; append-only JSONL of every call (useful later
for audit, but S10 only requires the running total); storing under `data/cache/`
(outputs/cost better matches “run spend state”).

## D4 — Corrupt ledger fails closed

**Decision**: Unreadable JSON, missing `total_usd`, wrong `schema_version`, or
non-finite/negative total → raise on load. Never treat as zero.

**Rationale**: FR-008 / constitution Principle V. Silent reset would authorize
overspend after corruption.

**Alternatives rejected**: Auto-reset with a warning (unsafe); backup-and-continue
heuristics (out of scope).

## D5 — `BudgetExceededError` carries loggable context

**Decision**: Refusal raises a dedicated exception whose message/attributes include
`total_usd`, `ceiling_usd`, `estimate_usd`, and remaining headroom.

**Rationale**: FR-005 / SC-001 (“logs why”). Callers (tests today; S11 later) log
`str(exc)` or attributes without needing a separate logging framework in S10.

**Alternatives rejected**: Returning a status enum only (easy to ignore; weaker
fail-closed); printing inside the library (S10 stays a library).

## D6 — Soft target is status-only

**Decision**: `BudgetStatus.target_exceeded` is derived (`total > target`);
`authorize` ignores the target.

**Rationale**: FR-010 / SC-004 / US4.

## D7 — Missing prices or tokens fail closed

**Decision**: Unknown `model_slug` in the pricing table, or `None`/negative token
counts when computing/recording from tokens → raise. No silent $0.

**Rationale**: FR-009. Under-counting is a ceiling bypass.

## D8 — Scope boundary with S7/S11

**Decision**: S10 does not call OpenRouter and does not wrap `OpenRouterClient`.
It exposes pure helpers + `CostTracker` for the runner. Offline tests simulate
over-budget halt without a client.

**Rationale**: Matches S7 contract (“cost deferred to `hecate.cost`”) and issue
Done-when (“simulated over-budget run”).
