# Tasks: Patch Extraction and Normalization

**Input**: Design documents from `/specs/008-patch-extraction/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, docs/contracts/patch-format.md

**Tests**: Required by SC-001–SC-005 / quickstart.md (offline synthetic fixture matrix).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 from spec.md
- Include exact file paths

## Phase 1: Setup

**Purpose**: Confirm package layout and public export path for S8

- [x] T001 Verify `src/hecate/generation/` exists with S7 modules; ensure `patch.py` is the planned home per `specs/008-patch-extraction/plan.md`
- [x] T002 Confirm `unidiff` is declared in `pyproject.toml` (no new dependency)

---

## Phase 2: Foundational

**Purpose**: Shared types and contract wiring before story behavior

**⚠️ CRITICAL**: Complete before user-story implementation

- [x] T003 Add frozen `ExtractionResult` dataclass in `src/hecate/generation/patch.py` per `specs/008-patch-extraction/data-model.md`
- [x] T004 [P] Confirm normative contract file `docs/contracts/patch-format.md` is present and referenced from `specs/008-patch-extraction/contracts/patch-api.md`
- [x] T005 Stub `extract_patch(raw_response: str) -> ExtractionResult` in `src/hecate/generation/patch.py` (pure sync; never raises on bad input)
- [x] T006 Re-export `extract_patch` and `ExtractionResult` from `src/hecate/generation/__init__.py` and update `__all__`

**Checkpoint**: Foundation ready — user stories can proceed

---

## Phase 3: User Story 1 — Extract a usable patch (Priority: P1) 🎯 MVP

**Goal**: Plain or single-fenced valid unified diffs become wrapper-free, byte-exact patches with `patch_parse_ok=True`.

**Independent Test**: Plain + fenced fixtures → same interior patch, parseable, paths/hunks unchanged.

- [x] T007 [US1] Implement Markdown fence candidate detection in `src/hecate/generation/patch.py` (``` / ~~~; fence only on non-hunk-body lines per contract §2)
- [x] T008 [US1] Implement unfenced region detection in `src/hecate/generation/patch.py` (start markers + prefix-precedence continuation per research D3)
- [x] T009 [US1] Validate candidates with `unidiff.PatchSet` as validator-only; emit exact substring (research D1) in `src/hecate/generation/patch.py`
- [x] T010 [US1] Wire success path: exactly one validating candidate → `patch_parse_ok=True`, `extracted_patch=slice`, `reason=None`, `raw_response` unchanged
- [x] T011 [P] [US1] Add success fixtures in `tests/test_patch_extraction.py` (plain, fenced+prose, multi-file, add/delete/rename/mod, non-ASCII, CRLF/mixed, missing final newline, blank context line, fence-in-hunk)

**Checkpoint**: US1 acceptance scenarios pass offline

---

## Phase 4: User Story 2 — Record malformed model behavior safely (Priority: P1)

**Goal**: Empty/ambiguous/malformed inputs return non-fatal failures with `extracted_patch=None` and preserved `raw_response`.

**Independent Test**: Empty, prose-only, bad headers, truncated hunks, multi-candidate → fail closed, no exception.

- [x] T012 [US2] Implement failure taxonomy (`empty`, `no_diff_found`, `invalid_structure`, `ambiguous`) in `src/hecate/generation/patch.py` per research D4
- [x] T013 [US2] Fail closed on >1 validating candidate region (`ambiguous`) without choosing one
- [x] T014 [US2] Ensure `extract_patch` never raises for bad input; always returns `ExtractionResult`
- [x] T015 [P] [US2] Add failure fixtures in `tests/test_patch_extraction.py` (empty/whitespace, BOM edge, prose-only, malformed/truncated, two fences, two unfenced regions)

**Checkpoint**: US2 acceptance scenarios pass offline

---

## Phase 5: User Story 3 — Share one cross-stage patch contract (Priority: P2)

**Goal**: Successful extractions conform to `docs/contracts/patch-format.md` with no further cleanup needed.

**Independent Test**: Every success fixture satisfies the shared contract; rejects classified consistently.

- [x] T016 [US3] Assert successful `extracted_patch` values need no extra wrapper/line-ending cleanup before apply (contract §5) via checks in `tests/test_patch_extraction.py`
- [x] T017 [P] [US3] Cross-check `specs/008-patch-extraction/contracts/patch-api.md` behavioral IDs P-1–P-11 against tests in `tests/test_patch_extraction.py`

**Checkpoint**: SC-006 covered

---

## Phase 6: Polish & Cross-Cutting

- [x] T018 Run `python -m pytest tests/test_patch_extraction.py -v` offline with no `OPENROUTER_API_KEY` (SC-005)
- [x] T019 [P] Update quickstart examples if signatures differ; keep `specs/008-patch-extraction/quickstart.md` accurate
- [x] T020 Mark completed tasks in `specs/008-patch-extraction/tasks.md`

---

## Dependencies

- Setup (T001–T002) → Foundational (T003–T006) → US1 (T007–T011) → US2 (T012–T015) → US3 (T016–T017) → Polish
- US1 and US2 are both P1; implement US1 success path first, then failure taxonomy (shared detector)
- US3 validates contract conformance on the US1/US2 suite

## Parallel opportunities

- T004 || T003 after T001–T002
- T011 || T010 after detector+validator exist
- T015 || T012–T014
- T017 || T016

## Implementation strategy

1. MVP = US1 (T003–T011): extract usable patches
2. Immediately add US2 failure paths (full counterfactual matrix)
3. US3 = contract conformance assertions on the same suite
4. Stop when `pytest tests/test_patch_extraction.py` is green offline

## MVP scope

T001–T011 (foundation + User Story 1). Do not ship without US2 before merge — malformed retention is a Stage-1 invariant.
