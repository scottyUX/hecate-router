# Tasks: Stage-1 Prompt Template

**Input**: Design documents from `/specs/006-prompt-template/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required by spec FR-010 / Done when (real instance render, determinism, no gold patch).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm S5 landing surface before adding S6

- [x] T001 Verify S5 exports (`ContextBundle`, `ContextFile`, `build_context`) in `src/hecate/scaffold/__init__.py` and `src/hecate/scaffold/context.py` — no duplicate context types for S6

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create prompt module shell and public exports

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Create `src/hecate/scaffold/prompt.py` with `PROMPT_VERSION = "v1"` and module docstring describing shared-scaffold / single-shot invariants
- [x] T003 Re-export `PROMPT_VERSION`, `render_prompt`, `prompt_hash`, and `write_prompt` from `src/hecate/scaffold/__init__.py` without breaking existing context exports

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 - Render fix-request prompt (Priority: P1) 🎯 MVP

**Goal**: Deterministic `render_prompt(task, context)` producing issue + files + unified-diff instructions

**Independent Test**: Synthetic task + `ContextBundle` → non-empty prompt with issue, paths, contents; gold patch absent; two renders identical

### Tests for User Story 1

- [x] T004 [P] [US1] Add synthetic prompt tests in `tests/test_scaffold.py`: contains issue/files; determinism; does not leak gold patch
- [x] T005 [P] [US1] Add real Lite instance prompt test in `tests/test_scaffold.py` using `build_context` + `render_prompt` (e.g. `psf__requests-1963`)

### Implementation for User Story 1

- [x] T006 [US1] Implement `render_prompt` in `src/hecate/scaffold/prompt.py` using S5 `ContextBundle.files` order, frozen v1 wording, optional `version` kwarg (unsupported → `ValueError`)
- [x] T007 [US1] Run `pytest tests/test_scaffold.py -k prompt -q` and fix until US1 tests pass

**Checkpoint**: User Story 1 fully functional and testable

---

## Phase 4: User Story 2 - Freeze and version template (Priority: P1)

**Goal**: Explicit stable `PROMPT_VERSION` tied to renders

**Independent Test**: Assert `PROMPT_VERSION == "v1"` and default render uses that version

### Tests for User Story 2

- [x] T008 [P] [US2] Add version stability / unsupported-version tests in `tests/test_scaffold.py`

### Implementation for User Story 2

- [x] T009 [US2] Ensure `render_prompt` defaults to `PROMPT_VERSION` and documents version freeze in `src/hecate/scaffold/prompt.py`
- [x] T010 [US2] Run version-related pytest selectors and confirm pass

**Checkpoint**: User Stories 1 and 2 both work

---

## Phase 5: User Story 3 - Hashing and optional persistence (Priority: P2)

**Goal**: `prompt_hash` + optional `write_prompt` → `prompt_ref`

**Independent Test**: Same prompt → same hash; write under temp/`data/cache/prompts` returns locatable ref

### Tests for User Story 3

- [x] T011 [P] [US3] Add `prompt_hash` and `write_prompt` tests in `tests/test_scaffold.py` (use `tmp_path` for write)

### Implementation for User Story 3

- [x] T012 [US3] Implement `prompt_hash` (SHA-256 hex) in `src/hecate/scaffold/prompt.py`
- [x] T013 [US3] Implement `write_prompt` defaulting to `data/cache/prompts/` in `src/hecate/scaffold/prompt.py`
- [x] T014 [US3] Run hash/persist pytest selectors and confirm pass

**Checkpoint**: All user stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full validation against quickstart

- [x] T015 Run full `pytest tests/test_scaffold.py -q` (context + prompt)
- [x] T016 [P] Confirm `.gitignore` already covers `data/cache/` and `data/outputs/` (no secret/prompt cache commits)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Immediate
- **Foundational (Phase 2)**: After Setup — BLOCKS all stories
- **US1 (Phase 3)**: After Foundational — MVP
- **US2 (Phase 4)**: After Foundational; naturally follows US1 render
- **US3 (Phase 5)**: After Foundational; can follow US1
- **Polish (Phase 6)**: After desired stories complete

### User Story Dependencies

- **US1**: No dependency on US2/US3
- **US2**: Uses same `PROMPT_VERSION` / `render_prompt` as US1
- **US3**: Operates on rendered strings from US1; independently testable with any string

### Parallel Opportunities

- T004 / T005 can be drafted in parallel before implementation (TDD)
- T008 / T011 can be drafted in parallel once render exists
- T016 independent of test runs once ignore verified

---

## Parallel Example: User Story 1

```bash
# Draft tests together:
Task: "Add synthetic prompt tests in tests/test_scaffold.py"
Task: "Add real Lite instance prompt test in tests/test_scaffold.py"

# Then implement render_prompt and run pytest
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001–T003 foundation
2. T004–T007 render + tests
3. Validate MVP before US2/US3

### Incremental Delivery

1. Setup + Foundational
2. US1 render → demo MVP
3. US2 versioning asserts
4. US3 hash + write
5. Full scaffold pytest

---

## Notes

- Spec FR-010 requires tests — included above
- Do not redefine `ContextBundle` / `ContextFile`
- Do not implement S7/S8/S9/S11
- Suggested MVP: Phase 1–3 only
