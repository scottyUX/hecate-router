# Implementation Plan: Caching Layer

**Branch**: `009-caching-layer` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-caching-layer/spec.md`

## Summary

Add a pure, offline, on-disk generation cache in `src/hecate/caching/cache.py`. The
cache is keyed by the full generation identity —
`(instance_id, model_slug, prompt_hash, prompt_version, decoding_fingerprint)` — so
a hit is only ever served for a byte-identical prompt under the same model, template
version, and decoding regime (protecting shared-scaffold fairness and
reproducibility). Entries persist under the gitignored `data/cache/generations/`
area so a crashed/resumed sweep reuses finished work instead of re-spending.

Two design decisions carry the spec's hardest requirements:
- **Success-only by construction (FR-011):** the store's `put` accepts a
  `CachedGeneration`, a type that can represent *only* a successful outcome — there
  is no code path to persist a provider failure or malformed response. The runner
  (S11) calls `put` solely on success; the module makes storing a failure impossible.
- **Atomic writes (FR-006):** entries are written to a temp file and `os.replace`d
  into place (atomic rename), so an interrupted write never surfaces as a hit; a
  corrupt/partial or schema-invalid file is read as a miss (FR-007), never a crash.

The OpenRouter client (S7) stays cache-unaware; lookup-before-call orchestration is
the runner's job (S11). Cost/budget (S10), the runner, distributed caching, and
eviction/TTL are out of scope.

## Technical Context

**Language/Version**: Python 3.10+ (`pyproject.toml` `requires-python = ">=3.10"`)

**Primary Dependencies**: Standard library only — `hashlib` (SHA-256 key/fingerprint), `json` (canonical serialization + entry format), `os`/`pathlib`/`tempfile` (atomic writes). Reuses S6 `hecate.scaffold.prompt.prompt_hash` / `PROMPT_VERSION`. **No new runtime dependency.**

**Storage**: JSON file per entry under `data/cache/generations/` (gitignored, `.gitignore:13`). Filename derived from the composite key hash. No database.

**Testing**: `pytest`, fully offline, zero provider spend. `tmp_path` cache dirs; provider avoidance verified with an injectable call counter / no client at all (the cache never calls a provider).

**Target Platform**: Local / CI Python package. `os.replace` gives atomic rename on POSIX and Windows.

**Project Type**: Library module in the Stage-1 `caching` package.

**Performance Goals**: Not a bottleneck — one lookup + at most one write per generation (≤1,200 in the full sweep). O(1) keyed file access.

**Constraints**: Deterministic key (FR-009); key binds all 5 identity dimensions (FR-001); atomic writes (FR-006); corrupt→miss, never crash (FR-007); success-only writes (FR-011); read-bypass mode (FR-008); offline/zero-spend (FR-010).

**Scale/Scope**: One store class + one entry dataclass + two key functions + one offline test module.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design. Evaluated against ratified constitution **v1.0.0**.*

| Principle | Verdict | Basis |
|-----------|---------|-------|
| I. Execution-Grounded Validity (invariants) | **PASS** | Rich storage upheld — `raw_response` stored verbatim, no truncation (FR-005). Full counterfactual matrix protected: FR-011 forbids caching failures, so a failed (task,model) cell is retried rather than permanently skipped. |
| II. Reproducibility by Manifest | **PASS (supports)** | The entry stores the decoding params used, and the key *binds* `decoding_fingerprint` + `prompt_version` + `prompt_hash`, so a cache hit cannot misreport the regime a result was produced under. The manifest itself is written by the runner (out of scope); the cache preserves everything the manifest needs. |
| III. Offline-Testable, Zero-Spend CI (NON-NEGOTIABLE) | **PASS** | Pure file I/O; the cache never opens a network connection or reads a credential. Suite passes with no `OPENROUTER_API_KEY` (FR-010, SC-005). A hit incurs zero spend (SC-001) — the feature's whole purpose. |
| IV. Spec-Driven Development | **PASS** | Full artifact set; every FR maps to a task in the forthcoming `tasks.md` (verified at the analyze gate); `spec.md` is source of truth. |
| V. Budget Discipline | **PASS (serves)** | Caching is the budget-protection mechanism — a hit costs nothing (SC-001), directly protecting the ~$38 target against accidental re-runs. |
| VI. Secrets Hygiene (NON-NEGOTIABLE) | **N/A** | No credential handling; the client stays cache-unaware. Cached files contain model output + decoding params only — never the API key. |
| VII. Shared-Scaffold Fairness | **PASS** | The 5-part key discriminates model slug, prompt content, template version, and decoding fingerprint, so a hit can never cross model/prompt/decoding regimes — comparability across the matrix is preserved. |

**Engineering-constraints check**: stdlib only (no new dependency); code lands in the existing `src/hecate/caching/` package per the README module map; small reviewable diff; frozen dataclass + `from __future__ import annotations`; `data/cache/` stays gitignored — run artifacts never committed.

**Result: GREEN — no violations.** Complexity Tracking has no violations to justify.

**Post-design re-check (after Phase 1)**: **PASS** — design adds only `cache.py` (store + entry dataclass + two key functions), re-exports from `hecate.caching`, one contract, and one offline test module. Success-only and atomicity are enforced structurally, so no principle is weakened.

## Project Structure

### Documentation (this feature)

```text
specs/009-caching-layer/
├── plan.md              # This file
├── research.md          # Phase 0 — storage/key/atomicity decisions
├── data-model.md        # Phase 1 — CachedGeneration + key + GenerationRecord mapping
├── quickstart.md        # Phase 1 — usage + offline verification matrix
├── contracts/
│   └── cache-api.md      # Phase 1 — caching module callable contract (K-1..)
├── checklists/
│   └── requirements.md  # PO output
└── tasks.md             # Phase 2 — created by /speckit-tasks (NOT this command)
```

### Source Code (repository root)

```text
src/hecate/caching/
├── __init__.py          # + re-export GenerationCache, CachedGeneration, cache_key, decoding_fingerprint
└── cache.py             # S9 — store (get/put), entry dataclass, key + fingerprint functions

tests/
└── test_caching.py      # S9 — offline tests (tmp_path); hit/miss, key discrimination, restart, atomicity, success-only, bypass
```

**Structure Decision**: New `cache.py` inside the existing `caching` package (README module map: "caching/ — content-hash keyed cache"), public surface re-exported from `hecate.caching`. The cache stores the *raw provider text* (not extracted patches — S8 runs after retrieval in the runner). Entries live under `data/cache/generations/`, a new subdirectory of the already-gitignored `data/cache/`.

## Complexity Tracking

> No constitution violations requiring justification.

Simplicity choices recorded for the review-plan gate:

| Decision | Why | Alternative rejected |
|----------|-----|----------------------|
| JSON file per entry, keyed by a composite-hash filename | Offline, human-inspectable, zero-dependency, O(1) keyed access, trivial restart survival | SQLite (adds concurrency/locking complexity for a write-once-per-key workload); single append JSONL (rewrite/scan contention). |
| `os.replace` temp-file atomic rename | Guarantees FR-006/SC-004 (no partial hit) and "last successful write wins" with no lock files | Advisory file locking — more moving parts, no benefit for write-once-per-key. |
| Success-only enforced by the `put` type (`CachedGeneration`) | Makes FR-011 structural — a failure literally cannot be stored — not a discipline the runner must remember | A boolean `ok` flag on a general entry — a caller could still persist `ok=False`; weaker guarantee. |
