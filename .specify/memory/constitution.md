# Hecate Constitution

<!-- Execution-grounded LLM routing for coding tasks. Stage-1 patch generation. -->

## Core Principles

### I. Execution-Grounded Validity (NON-NEGOTIABLE)

Routing labels derive from execution outcomes, not model self-report or heuristic
proxies. The six Stage-1 invariants in `README.md` ("Non-negotiable invariants")
are binding on every feature and may not be weakened without a constitution
amendment:

1. **Shared scaffold** — every model receives identical issue text, file context,
   and prompt; the only variable across a matrix is the model slug.
2. **Single-shot generation (v1)** — one prompt yields one patch; no multi-turn
   or agentic loop.
3. **Oracle / retrieval context** — target files come from the gold patch (oracle)
   or BM25 retrieval, using the same method for all models.
4. **Full counterfactual matrix** — raw outcomes are persisted for every
   `(task, model)` pair; per-pair detail is never discarded.
5. **Store outputs richly; defer label scheme** — Stage 1 records raw patch +
   metadata so Stage 3 can derive binary or multiclass labels later.
6. **Reproducibility** — see Principle II.

**Enforcement**: A reviewer MUST be able to point to the code or test that upholds
each invariant a feature touches. A change that lets prompt/context vary by model,
introduces a multi-turn loop, or drops per-pair records is rejected.

### II. Reproducibility by Manifest

Any run that generates patches or consumes provider budget MUST write a run
manifest capturing, at minimum: the config snapshot, the model slugs used, a
timestamp, the git commit, and the total cost. Decoding parameters actually sent
MUST be recorded on each generation record (not assumed from defaults).

**Enforcement**: A run without a written manifest is a defect. A reviewer checks
that the manifest fields exist and that recorded decoding params reflect what was
sent, not a hard-coded constant. Library modules that do not themselves run a
sweep satisfy this by echoing the exact parameters used back to their caller so
the runner can persist them.

### III. Offline-Testable, Zero-Spend CI (NON-NEGOTIABLE)

Every behavior MUST be verifiable deterministically without live network access
and without incurring provider spend. The automated test suite MUST pass in CI
with no `OPENROUTER_API_KEY` present. Any test that makes a real provider call is
opt-in, marked `@pytest.mark.live`, and skipped unless BOTH `RUN_LIVE_TESTS=1`
and `OPENROUTER_API_KEY` are set — a bare key on a developer machine must never
trigger spend.

**Enforcement**: Reviewer runs `pytest` with no key set; it must pass. Network
calls in tests are made through injectable transports (e.g. `httpx.MockTransport`),
never a real endpoint. A live-marked test that is not doubly gated is rejected.

### IV. Spec-Driven Development

Features flow through the Spec Kit workflow: `specify → plan → tasks → implement`,
with the spec/plan review gates in `.specify/workflows/speckit/workflow.yml`
honored. Each feature lives under `specs/<NNN>-<slug>/` with, at minimum,
`spec.md`, `plan.md`, and `tasks.md`. The `spec.md` is the source of truth: every
functional requirement (FR) MUST map to at least one task in `tasks.md`, and code
that contradicts the spec is a defect in one or the other, to be reconciled before
merge.

**Enforcement**: Reviewer confirms the artifact set exists, that every FR has a
covering task, and that the `Constitution Check` section of `plan.md` was
evaluated against THIS constitution (not skipped as "template placeholder").

### V. Budget Discipline

Provider spend is bounded. The Stage-1 target is approximately **$38**, with a
hard ceiling of **$100** (per `README.md` / `configs/option_a.yaml`). Costs and
budget-relevant decisions (dry-run estimates, price changes) are recorded in the
repo. CI incurs zero spend (Principle III). Cost accounting and budget-guard code
must fail closed — refuse to proceed rather than silently exceed the ceiling.

**Enforcement**: Any feature that issues paid calls at scale must reference a
recorded cost estimate and respect the ceiling. A change that could exceed $100
without an explicit guard and an operator override is rejected.

### VI. Secrets Hygiene (NON-NEGOTIABLE)

Credentials are loaded from the environment only (via the centralized loader; not
`os.environ` reads scattered across modules). No credential, key, or token is
hard-coded, committed, logged, placed in an exception message, or exposed in a
`repr`. A missing credential produces a clear, actionable error before any network
call is attempted.

**Enforcement**: Reviewer greps the diff for literal keys and for the credential
appearing in logging/`repr`/error strings. A test MUST assert the key never
surfaces in output and that absence fails fast with an actionable message.

### VII. Shared-Scaffold Fairness

Because labels are comparative across a model matrix, nothing about a request may
advantage or disadvantage one model over another. Only the model slug varies. The
exact upstream-rendered prompt is sent verbatim — no appended solution, gold
patch, hint, or answer content — and decoding parameters are fixed by config and
applied uniformly across models.

**Enforcement**: A test MUST assert the request body's prompt equals the provided
prompt verbatim and that no solution/gold-patch content is appended. Reviewer
confirms decoding params come from config, not per-model overrides that would
break comparability.

## Engineering Constraints

- **Language/tooling**: Python ≥ 3.10; `pytest` + `pytest-asyncio` for tests
  (`pyproject.toml`). New runtime dependencies must be justified in the feature's
  `research.md`; prefer capabilities already declared over new packages.
- **Module boundaries**: Code lands in the `src/hecate/` package matching the
  README module map (`data/`, `scaffold/`, `generation/`, `caching/`, `cost/`,
  `utils/`). Features stay within their declared scope; out-of-scope concerns are
  named as such and deferred to their own feature.
- **Data hygiene**: `data/` (raw/, cache/, outputs/) is gitignored; run artifacts
  and provider responses are never committed.
- **Diff discipline**: Small, reviewable diffs that match existing patterns
  (frozen dataclasses, config helpers, `from __future__ import annotations`).

## Development Workflow & Quality Gates

- **Review gates**: The `review-spec` and `review-plan` gates in the Spec Kit
  workflow are mandatory; a rejected gate aborts the feature.
- **Constitution Check**: Every `plan.md` runs the Constitution Check gate against
  this document before Phase 0 and re-checks after Phase 1 design. Any violation
  must be either removed or recorded with justification in the plan's Complexity
  Tracking section.
- **Test-first for testable behavior**: Where a feature declares offline
  verifiability (the norm here), tests are written to fail first, then made to
  pass. FR → task → (ideally) success-criterion coverage is verified before merge.
- **Merge bar**: `pytest` passes offline with zero spend; no secrets in the diff;
  every touched invariant demonstrably upheld; manifest/reproducibility obligations
  met for any run-producing code.

## Governance

This constitution supersedes ad-hoc engineering practice for the Hecate project.
When guidance conflicts, the constitution wins; the `spec.md` for a feature is
authoritative for that feature's requirements within these bounds.

**Amendments** require: (a) a written rationale in the amending PR, (b) approval by
a project maintainer, and (c) a version bump per the policy below. Amending a
NON-NEGOTIABLE principle (I, III, VI) additionally requires an explicit note of the
validity or safety trade-off being accepted.

**Versioning policy** (semantic): MAJOR for a backward-incompatible change to a
principle's meaning or the removal/redefinition of a principle; MINOR for a new
principle or a materially expanded section; PATCH for clarifications and wording
that do not change obligations.

**Compliance**: All PRs and reviews MUST verify compliance with the principles
above; a reviewer cites the specific principle when requesting changes. Complexity
or deviation must be justified in the plan, not merged silently. Runtime and
feature-level guidance lives in each feature's `specs/<NNN>-*/` artifacts and in
`README.md`.

**Version**: 1.0.0 | **Ratified**: 2026-07-18 | **Last Amended**: 2026-07-18
