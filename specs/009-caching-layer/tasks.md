# Tasks: Caching Layer

**Input**: Design documents from `/specs/009-caching-layer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cache-api.md

**Tests**: Required by SC-001–SC-007 / quickstart.md (offline, `tmp_path` cache dirs, zero provider spend). Test-first within each story.

**Organization**: Tasks grouped by user story (US1–US4) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files / independent, no incomplete deps)
- **[Story]**: US1 / US2 / US3 / US4 from spec.md
- Include exact file paths

## Phase 1: Setup

**Purpose**: Confirm package layout and dependencies

- [x] T001 Confirm `src/hecate/caching/` exists (currently `__init__.py` docstring only) and that `cache.py` is the planned home per `plan.md`
- [x] T002 Confirm stdlib-only (`hashlib`, `json`, `os`, `pathlib`, `tempfile`) — no new dependency added to `pyproject.toml`; confirm `data/cache/` is gitignored (`.gitignore:13`)
- [x] T003 Confirm S6 hooks importable: `hecate.scaffold.prompt.prompt_hash` and `PROMPT_VERSION`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Key functions, entry type, and store skeleton before any story behavior

**⚠️ CRITICAL**: Complete before user-story implementation

- [x] T004 [P] Implement `decoding_fingerprint(decoding_params) -> str` in `src/hecate/caching/cache.py` — hex SHA-256 of canonical JSON (`sort_keys=True, separators=(",",":")`) per research D3 (FR-001, K-3)
- [x] T005 [P] Implement `cache_key(instance_id, model_slug, prompt_hash, prompt_version, decoding_fingerprint) -> str` — hex SHA-256 over a canonical JSON **array** of the five strings (collision-proof) per research D4 (FR-001, FR-009, K-1/K-2)
- [x] T006 Add frozen `CachedGeneration` dataclass in `src/hecate/caching/cache.py` per data-model.md, with `to_dict`/`from_dict`/`to_json`/`from_json` (JSON, `ensure_ascii=False`)
- [x] T007 Add `__post_init__` to `CachedGeneration` rejecting empty/whitespace-only `raw_response` (**review-plan MINOR-1**; makes success-only structural — FR-011, K-7)
- [x] T008 Implement `GenerationCache.__init__(cache_dir=None, *, read_bypass=False)` in `src/hecate/caching/cache.py`; default `cache_dir = data/cache/generations/`; create dir lazily on first write (FR-002, K-11)
- [x] T009 Re-export `GenerationCache`, `CachedGeneration`, `cache_key`, `decoding_fingerprint` from `src/hecate/caching/__init__.py` and set `__all__`

**Checkpoint**: Foundation ready — user stories can proceed

---

## Phase 3: US1 — Skip completed generations on re-run (P1)

**Goal**: A cache hit returns the stored outcome with zero provider calls; failures are never cached.

- [x] T010 [US1] Test (failing first): `put` then `get` on the same key returns the `CachedGeneration` and performs **zero** provider calls (assert via a call counter / no client involved) — `tests/test_caching.py` (FR-003, SC-001)
- [x] T011 [P] [US1] Test: `get` on an absent key returns `None` (miss) — `tests/test_caching.py` (FR-004)
- [x] T012 [P] [US1] Test: a hit carries `raw_response` + `prompt_tokens` + `completion_tokens` + `decoding_params` + `model_slug` sufficient to populate a `GenerationRecord` (FR-005, K-10)
- [x] T013 [P] [US1] Test: `raw_response` (incl. non-ASCII + very large text) round-trips byte-for-byte, no truncation (FR-005)
- [x] T014 [US1] Test: a failure/empty outcome cannot be stored — constructing `CachedGeneration(raw_response="")` (or whitespace) raises; so a failed identity has no entry and re-fetches (FR-011, SC-006)
- [x] T015 [US1] Implement `GenerationCache.get`/`put` happy path (read JSON entry; atomic write) to make T010–T014 pass (FR-003, FR-005, FR-011)

**Checkpoint**: Re-run reuse works; failures excluded

---

## Phase 4: US2 — Survive crashes and restarts (P1)

**Goal**: Entries persist on disk across processes; interrupted/corrupt writes are misses, never hits.

- [x] T016 [US2] Test: write with one `GenerationCache`, construct a **fresh** `GenerationCache` on the same dir, entry still retrievable (simulates restart) — `tests/test_caching.py` (FR-002, SC-002)
- [x] T017 [US2] Test: a truncated/garbage `{key}.json` → `get` returns `None` (never raises); a schema-invalid JSON object (missing `raw_response`) → miss (FR-007, SC-004)
- [x] T018 [US2] Test: an orphan `{key}.json.tmp-*` file is never returned as a hit (FR-006)
- [x] T019 [US2] Implement atomic write in `put`: serialize to `{cache_key}.json.tmp-{unique}` in the **same directory**, then `os.replace` to `{cache_key}.json` per research D2 (FR-006, K-6)
- [x] T020 [US2] Implement `get` corrupt/missing/schema-invalid handling → return `None`, never raise (FR-007, D7)

**Checkpoint**: Restart-safe and corruption-safe

---

## Phase 5: US3 — Key by full generation identity (P1)

**Goal**: Changing any one key dimension is a miss; identical inputs are deterministic.

- [x] T021 [P] [US3] Test: differ only `instance_id` → miss (SC-003, US3.3)
- [x] T022 [P] [US3] Test: differ only `model_slug` → miss (US3.2)
- [x] T023 [P] [US3] Test: differ only `prompt_hash` → miss (US3.1)
- [x] T024 [P] [US3] Test: differ only `prompt_version` (byte-identical prompt, bumped template version) → miss (US3.4, FR-001)
- [x] T025 [P] [US3] Test: differ only decoding fingerprint (e.g. temperature `0.0`→`0.7`) → miss (US3.5)
- [x] T026 [P] [US3] Test: identical inputs → identical `cache_key` twice (determinism, US3.6, FR-009)
- [x] T027 [US3] Test: `decoding_fingerprint` is order-independent (same dict, keys inserted in different orders → same fingerprint) and value-sensitive (K-3)
- [x] T028 [US3] Confirm T021–T027 pass against the T004/T005 implementations; add a canonical-serialization regression assertion that `("ab","c")` and `("a","bc")` dimension pairs do **not** collide (K-1)

**Checkpoint**: Key discrimination proven on all five dimensions

---

## Phase 6: US4 — Explicit cache control (P2)

**Goal**: Read-bypass forces misses while still writing successful outcomes.

- [x] T029 [US4] Test: with `read_bypass=True`, `get` misses even when a valid entry exists; `put` still writes; with bypass off (default), the same entry hits — `tests/test_caching.py` (FR-008, SC-007, US4)
- [x] T030 [US4] Implement `read_bypass` in `GenerationCache.get` (short-circuit to `None`) leaving `put` unaffected (FR-008, K-9)

---

## Phase 7: Polish & cross-cutting

- [x] T031 [P] Add module docstring + type hints; ensure `from __future__ import annotations`; match existing `src/hecate` style
- [x] T032 Docs alignment (**review-plan MINOR-2/3**): ensure the quickstart derives `decoding_fingerprint` from the fully-resolved params that are stored (not a separate hand-built dict), and that the K-3 consistent-typing note is reflected in a test comment; no runner code added (S11 owns orchestration)
- [x] T033 Run full offline suite `pytest tests/test_caching.py -v` and `pytest tests/ -q` — confirm pass with no `OPENROUTER_API_KEY` and no network (FR-010, SC-005)

---

## Dependencies

- Setup (T001–T003) → Foundational (T004–T009) → user stories.
- Within Foundational: T004/T005 (keys) and T006/T007 (entry) are independent [P]; T008 (store) after T006; T009 after all symbols exist.
- US1/US2/US3 are all P1 and independent once Foundational is done; US4 (P2) last.
- Test tasks precede their implementation task within each story (test-first).

## FR → task coverage (for the analyze gate)

| FR | Tasks |
|----|-------|
| FR-001 5-dim key | T004, T005, T021–T027 |
| FR-002 persist/gitignored | T008, T016 |
| FR-003 hit, no provider | T010, T015 |
| FR-004 miss | T011, T015 |
| FR-005 store text+usage+decoding | T006, T012, T013, T015 |
| FR-006 atomic write | T018, T019 |
| FR-007 corrupt→miss | T017, T020 |
| FR-008 read-bypass | T029, T030 |
| FR-009 deterministic key | T005, T026, T027 |
| FR-010 offline tests | T010–T033 (whole suite), T033 |
| FR-011 success-only | T007, T014, T015 |

Every FR maps to ≥1 task; every user story has test-first coverage; the K-* contract clauses each trace to a task (K-1→T028, K-2→T005/T026, K-3→T004/T027, K-4→T010, K-5→T017/T020, K-6→T018/T019, K-7→T007/T014, K-8→T016, K-9→T029/T030, K-10→T012, K-11→T008).
