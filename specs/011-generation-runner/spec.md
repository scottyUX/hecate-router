# Feature Specification: Generation Runner (Orchestrator)

**Feature Branch**: `011-generation-runner`

**Created**: 2026-08-10

**Status**: Draft

**Input**: GitHub issue #11, "S11 · Generation runner (orchestrator)"

## User Scenarios & Testing

### User Story 1 - Run one (task, model) generation end-to-end (Priority: P1)

A Stage-1 operator wants to generate a patch for one SWE-bench Lite task with one
configured model. The system builds shared context and prompt, checks the cache,
authorizes spend against the hard budget ceiling, calls the model when needed,
extracts a unified diff, records cost, and appends a generation record — so the
pilot script can complete a single-task dry or live run.

**Why this priority**: Issue Done when requires `scripts/run_pilot.py` end-to-end
on 1 task. Without this path, S12 cannot start.

**Independent Test**: With a mocked provider (or `--dry-run` scaffolding that skips
network), run one task × one model and confirm a `GenerationRecord` is written
with prompt, tokens/cost fields as applicable, extraction outcome, and a run
manifest exists.

**Acceptance Scenarios**:

1. **Given** a valid config, one task, and one model slug, **When** the runner
   executes that pair without a cache hit, **Then** it produces one generation
   record and updates the cost ledger when a paid call occurred.
2. **Given** the same identity already cached successfully, **When** the runner
   executes again, **Then** it reuses the cached outcome with zero provider calls
   and still writes a generation record for the run.
3. **Given** a proposed call whose estimate would breach the hard ceiling, **When**
   authorization runs, **Then** the runner refuses that call, records why, and
   does not contact the provider.

---

### User Story 2 - Resume a interrupted matrix safely (Priority: P1)

A long run may stop mid-way. On restart, finished successful generations must not
be re-paid, and the cost ledger must still reflect prior spend so the ceiling
remains honest.

**Why this priority**: Pilot and full sweeps are expected to interrupt; resume is
the primary budget-safety mechanism alongside the hard ceiling.

**Independent Test**: Seed a cache hit and a non-zero ledger total; start a new
process for the same identities; confirm cache hits incur no provider calls and
authorization uses the restored total.

**Acceptance Scenarios**:

1. **Given** prior successful cache entries, **When** the runner is restarted,
   **Then** those identities are served from cache with zero new provider spend.
2. **Given** a persisted cost ledger, **When** a new runner process starts,
   **Then** authorization decisions use the restored running total.

---

### User Story 3 - Persist records and a reproducible run manifest (Priority: P1)

Operators and later stages need every (task, model) outcome in JSONL plus a run
manifest capturing config snapshot, model slugs, timestamp, git commit, and total
cost.

**Why this priority**: Constitution Principle II — a run without a manifest is a
defect; Stage-2/3 consume the records.

**Independent Test**: Complete a one-task run; open the JSONL and manifest; confirm
required fields are present and decoding params on the record match what was used.

**Acceptance Scenarios**:

1. **Given** a completed run of N pairs, **When** outputs are inspected, **Then**
   JSONL contains N generation records with Stage-2 placeholder fields present.
2. **Given** a completed run, **When** the manifest is read, **Then** it includes
   config snapshot, model slugs used, timestamp, git commit, and total cost.
3. **Given** two models in a matrix, **When** prompts/context are built, **Then**
   only the model slug differs (shared scaffold).

---

### User Story 4 - Operate the pilot CLI (Priority: P2)

An operator runs `scripts/run_pilot.py` with config, task count, model, and
optional `--dry-run` to validate wiring without spend.

**Why this priority**: The public entry point for M1; dry-run unblocks CI and local
checks without a key.

**Independent Test**: `--dry-run` completes without network and without requiring
`OPENROUTER_API_KEY`; a live one-task path works when the key is present (manual /
`@pytest.mark.live`).

**Acceptance Scenarios**:

1. **Given** `--dry-run`, **When** the pilot script runs for 1 task, **Then** it
   exits successfully without provider calls.
2. **Given** a live key and `--tasks 1` with a small model slug, **When** the
   pilot runs, **Then** it writes at least one generation record and a manifest.

---

### Edge Cases

- Unknown model slug relative to Option A config → fail closed before any call.
- Provider failure / retry exhaustion → no cache put; record failure fields
  honestly; do not record spend for unsuccessful calls.
- Empty or unparseable model output → record with `patch_parse_ok=False`; do not
  treat as a cacheable success.
- Missing API key on a live (non-dry-run) path → clear error before network.
- Task count larger than available Lite set → process available tasks only or fail
  with a clear bound error (fail closed).

## Requirements

### Functional Requirements

- **FR-001**: System MUST iterate a configured set of tasks and model slugs as a
  matrix of (task, model) pairs.
- **FR-002**: System MUST build context and render the Stage-1 prompt identically
  for every model on a given task (shared scaffold).
- **FR-003**: System MUST consult the generation cache before a paid call and MUST
  skip the provider on a hit.
- **FR-004**: System MUST authorize each proposed paid call against the hard
  budget ceiling using an upper-bound cost estimate; refuse rather than overspend.
- **FR-005**: System MUST call the OpenRouter client only when there is a cache
  miss, authorization succeeds, and the run is not in dry-run mode.
- **FR-006**: System MUST extract a unified diff from the raw response and persist
  extraction success/failure on the generation record.
- **FR-007**: System MUST put successful generations into the cache and MUST NOT
  cache failures.
- **FR-008**: System MUST record actual USD cost from token usage after a
  successful paid call.
- **FR-009**: System MUST append one `GenerationRecord` per attempted pair to a
  JSONL output, including Stage-2 placeholder fields.
- **FR-010**: System MUST write a run manifest with config snapshot, model slugs,
  timestamp, git commit, and total cost.
- **FR-011**: System MUST expose `scripts/run_pilot.py` that can run end-to-end on
  1 task (Done when).
- **FR-012**: Automated tests MUST verify orchestration offline with zero provider
  spend; any live test MUST be doubly gated (`RUN_LIVE_TESTS=1` and API key).
- **FR-013**: Dry-run mode MUST exercise wiring without network or credentials.

### Key Entities

- **RunConfig**: Paths and knobs for one runner invocation (config YAML, task
  limit, model slugs, dry-run, output/cache/ledger locations).
- **GenerationRecord**: Canonical per-(task, model) outcome (existing S3 schema).
- **RunManifest**: Reproducibility snapshot for one runner process.
- **CostTracker / GenerationCache / OpenRouterClient**: Existing S7–S10
  collaborators; runner orchestrates them and does not reimplement their rules.

## Success Criteria

- **SC-001**: `scripts/run_pilot.py --tasks 1` completes end-to-end (dry-run in CI;
  live optionally with key).
- **SC-002**: Re-running the same identity after a successful cache write performs
  zero provider calls.
- **SC-003**: A simulated near-ceiling ledger causes the runner to refuse the next
  paid call without contacting the provider.
- **SC-004**: Every completed run leaves a JSONL record set and a manifest with
  the constitution-required fields.
- **SC-005**: Offline test suite passes with no `OPENROUTER_API_KEY` and no network.

## Assumptions

- S5–S10 libraries on `dev` are the integration surface.
- Pilot default small model is `qwen/qwen-2.5-7b-instruct`.
- Single-process runner; no distributed locking.
- Full 4×300 sweep CLI remains a thin wrapper for S14; this feature delivers the
  orchestrator and makes the pilot script real.

## Out of Scope

- Stage-2 Docker apply / tests
- Full sweep completion (S14) and Stage-1 handoff packaging (S16)
- Changing prompt template, client retry policy, cache key formula, or cost
  accounting rules (owned by S6–S10)
- Multi-turn agent loops
