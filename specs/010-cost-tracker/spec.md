# Feature Specification: Cost Tracker & Hard Budget Guard

**Feature Branch**: `010-cost-tracker`

**Created**: 2026-08-03

**Status**: Draft

**Input**: GitHub issue #10, "S10 · Cost tracker & hard budget guard"

## User Scenarios & Testing

### User Story 1 - Refuse a call that would breach the ceiling (Priority: P1)

A Stage-1 operator (or automated runner) is about to spend provider budget on a
generation. Before the call starts, the system estimates the call's upper-bound
cost, compares it to the running total and the hard ceiling ($100), and refuses
to proceed when the call would push the total over the ceiling — logging a clear
reason so the operator knows why the run stopped.

**Why this priority**: The hard ceiling is a non-negotiable budget invariant.
Silent overspend would break Stage-1 cost discipline; refuse-before-call is the
only fail-closed guarantee that works before money leaves the account.

**Independent Test**: Seed a running total near the ceiling, request authorization
for a call whose estimate would exceed it, and confirm authorization is denied
with an explicit over-budget reason and that no provider call is attempted.

**Acceptance Scenarios**:

1. **Given** a running total and a proposed call whose estimated cost would make
   `total + estimate` exceed the hard ceiling, **When** authorization is checked,
   **Then** the call is refused and a clear over-budget reason is available to
   the caller/logger.
2. **Given** a running total and a proposed call whose estimated cost keeps
   `total + estimate` at or under the ceiling, **When** authorization is checked,
   **Then** the call is allowed to proceed.
3. **Given** a refused authorization, **When** the operator inspects the failure,
   **Then** the message includes enough context to act (at least: current total,
   ceiling, and the estimate that was refused).

---

### User Story 2 - Maintain an accurate running cost total (Priority: P1)

After each successful generation that incurred spend, the operator needs the
running USD total updated from actual token usage and the configured per-model
prices so later authorization checks and the run manifest reflect real spend —
not guesses.

**Why this priority**: The guard is only meaningful if the total matches what was
actually charged (within pricing-table fidelity). Under-counting would let runs
breach the ceiling; over-counting would halt early.

**Independent Test**: Record several known (model, prompt_tokens, completion_tokens)
outcomes against known prices; confirm the running total equals the sum of the
per-call USD costs computed from the pricing table.

**Acceptance Scenarios**:

1. **Given** configured per-model input/output prices and a completed call with
   known token counts, **When** the cost is recorded, **Then** the running total
   increases by the USD amount implied by those tokens and prices.
2. **Given** multiple recorded calls, **When** the total is read, **Then** it
   equals the sum of each call's recorded USD cost.
3. **Given** a model slug with no configured prices, **When** cost is estimated
   or recorded for that slug, **Then** the operation fails closed with a clear
   error (no silent zero-cost assumption).

---

### User Story 3 - Persist the total across restarts (Priority: P1)

A long sweep may stop mid-run. The spent total must survive process exit and
restart so a resumed run does not forget prior spend and accidentally authorize
calls that would breach the ceiling.

**Why this priority**: In-memory-only totals would reset on every crash/restart
and defeat the hard ceiling for multi-session sweeps.

**Independent Test**: Record spend in one process, start a fresh process pointed
at the same ledger location, and confirm the loaded total matches.

**Acceptance Scenarios**:

1. **Given** a non-zero running total persisted to the project's output/ledger
   area, **When** a new process starts with the same ledger location, **Then** it
   loads that total and uses it for subsequent authorization checks.
2. **Given** no prior ledger file, **When** a tracker starts, **Then** the
   running total is zero and writes create the ledger on first record.
3. **Given** a corrupt or unreadable ledger file, **When** a tracker starts,
   **Then** it fails closed (does not treat the total as zero) with a clear error
   so an operator must repair or explicitly reset.

---

### User Story 4 - Soft target is visible but not a hard stop (Priority: P2)

Operators plan around a ~$38 target for the 1,200-sample sweep. Crossing the
target should be observable (for reporting and go/no-go), but must not by itself
halt generation — only the hard ceiling refuses calls.

**Why this priority**: Useful for pilot reporting without conflating planning
guidance with the hard fail-closed guard.

**Independent Test**: Drive the total past the target but under the ceiling;
confirm authorization still succeeds and the tracker exposes that the target was
exceeded.

**Acceptance Scenarios**:

1. **Given** a total above the soft target and below the ceiling, **When** a
   call within the remaining ceiling headroom is authorized, **Then** it is
   allowed.
2. **Given** a total above the soft target, **When** status is inspected,
   **Then** the tracker reports the target value and that the target has been
   exceeded.

---

### Edge Cases

- Exact boundary: `total + estimate == ceiling` is allowed; only `>` refuses.
- Zero-token or missing usage on record: fail closed — do not record a silent
  zero-cost success when token counts needed for pricing are absent.
- Negative or non-finite token counts / costs: rejected.
- Concurrent writers to one ledger: Stage-1 assumes a single runner process; no
  multi-writer locking is required in this feature.
- Cache hits (S9) that skip the provider: the runner MUST NOT record spend for
  those identities (orchestration owned by S11; this module simply records what
  it is told).

## Requirements

### Functional Requirements

- **FR-001**: System MUST maintain a running USD cost total for a generation run.
- **FR-002**: System MUST compute per-call USD cost from prompt/completion token
  counts and the configured per-model input/output prices (USD per 1M tokens).
- **FR-003**: System MUST load the hard ceiling and soft target from the Stage-1
  budget configuration (defaults: ceiling $100, target ≈ $38).
- **FR-004**: Before a paid call starts, system MUST authorize against an
  upper-bound cost estimate and MUST refuse when `total + estimate > ceiling`.
- **FR-005**: On refusal, system MUST surface a clear reason including current
  total, ceiling, and refused estimate (suitable for operator logs).
- **FR-006**: After a paid call, system MUST record the actual USD cost into the
  running total (not the pre-call estimate).
- **FR-007**: System MUST persist the running total so a restarted process loads
  the same total from the same ledger location.
- **FR-008**: System MUST fail closed on corrupt/unreadable ledger data (never
  silently reset to zero).
- **FR-009**: System MUST fail closed when pricing is missing for a model slug
  or when token counts required for costing are absent/invalid.
- **FR-010**: Soft target MUST be readable for status/reporting and MUST NOT
  cause call refusal by itself.
- **FR-011**: All tracker behavior MUST be verifiable offline with zero provider
  spend (simulated over-budget runs, no live API key required).
- **FR-012**: Estimates used for authorization MUST be treated as upper bounds;
  callers are responsible for supplying conservative estimates (e.g. worst-case
  completion tokens).

### Key Entities

- **BudgetConfig**: Soft target and hard ceiling in USD, loaded from Stage-1
  config.
- **ModelPricing**: Per-model input and output USD cost per 1M tokens.
- **CostLedger**: Persisted running total (and enough metadata to reload safely).
- **BudgetStatus**: Snapshot of total, target, ceiling, remaining headroom, and
  whether the soft target has been exceeded.
- **BudgetExceeded**: Refusal outcome when a proposed estimate would breach the
  ceiling.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A simulated run that would exceed the $100 ceiling is halted before
  any further paid call is authorized, with an explicit over-budget reason.
- **SC-002**: After process restart, the loaded running total matches the total
  recorded before exit (same ledger location).
- **SC-003**: For a fixed set of (model, tokens) fixtures and the committed
  pricing table, recomputed totals match expected USD to at least 1e-9 relative
  tolerance on each line item.
- **SC-004**: Crossing the soft target alone never refuses a call that still fits
  under the ceiling.
- **SC-005**: The full cost-tracker test suite passes with no provider API key
  and no network access.

## Assumptions

- Stage-1 pricing and budget numbers live in the committed Option A config (S4)
  and are the source of truth for this feature.
- A single runner process owns one ledger file at a time (S11 orchestration).
- Pre-call authorization uses caller-supplied upper-bound estimates; this module
  does not tokenize prompts itself.
- Cache hits and other zero-spend paths are the runner's responsibility not to
  record (S11); the tracker records only explicit `record` calls.
- Operator override of the ceiling is out of scope for S10 (constitution requires
  an explicit future design if ever added).
- Wiring the tracker into the live OpenRouter client call path is owned by S11;
  S10 delivers the library API + offline simulation of over-budget halt.
