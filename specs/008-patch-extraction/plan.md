# Implementation Plan: Patch Extraction and Normalization

**Branch**: `008-patch-extraction` | **Date**: 2026-07-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-patch-extraction/spec.md`

## Summary

Add a pure, offline patch-extraction step in `src/hecate/generation/patch.py`:
`extract_patch(raw_response) -> ExtractionResult` converts one raw model response
into **either** one wrapper-free, byte-exact unified diff (`patch_parse_ok=True`)
**or** an explicit non-fatal parse failure (`patch_parse_ok=False`,
`extracted_patch=None`) — always preserving `raw_response` verbatim.

Structural validity is checked with the already-declared `unidiff` library used
as a **validator only**. The emitted patch is the exact candidate substring of the
raw response, never a re-serialization, so line endings, final-newline state, and
non-ASCII content are preserved exactly and malformed content is never repaired.
One normative cross-stage contract (`docs/contracts/patch-format.md`) defines
accepted inputs and normalized output for both S8 extraction and the future
Stage-2 apply step (E-M3). Applying patches, model calls, orchestration, caching,
and cost are out of scope.

## Technical Context

**Language/Version**: Python 3.10+ (`pyproject.toml` `requires-python = ">=3.10"`)

**Primary Dependencies**: `unidiff>=0.7,<1` — **already declared** (`pyproject.toml:18`), used only to validate that a candidate parses as a structurally complete unified diff. No new runtime dependency. Standard library otherwise (single-pass string scanning; no regex-heavy parsing required).

**Storage**: None. `extract_patch` returns an in-memory `ExtractionResult`; mapping onto `GenerationRecord.{raw_response, extracted_patch, patch_parse_ok}` is done later by the S11 runner. This feature does not write records or JSONL.

**Testing**: `pytest`, fully offline, zero provider spend. Fixtures are **synthetic hand-authored raw responses** (no live model output exists yet — the pilot, S12, has not run), covering the success and failure matrix from the spec.

**Target Platform**: Local / CI Python package. No network, no async (pure sync function).

**Project Type**: Library module inside the Stage-1 `generation` package.

**Performance Goals**: Not a bottleneck — one call per generated response (≤1,200 in the full sweep). Linear single-pass scan of one response string.

**Constraints**: Deterministic (identical input → identical output; no randomness, no locale/dict-order dependence); byte-exact interior preservation (FR-006/007); fail closed on ambiguity (FR-011); non-fatal on any malformed input (FR-008); never repair (FR-006).

**Scale/Scope**: Single pure function + one small result dataclass + one shared format contract + one offline test module.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design. Evaluated against the ratified constitution **v1.0.0** (`.specify/memory/constitution.md`), not the former placeholder template.*

| Principle | Verdict | Basis |
|-----------|---------|-------|
| I. Execution-Grounded Validity (invariants) | **PASS** | Upholds "store outputs richly; defer label scheme" and "full counterfactual matrix": malformed responses are stored as data (FR-008/009/010), `raw_response` is never discarded or mutated. Shared-scaffold, single-shot, oracle-context invariants are N/A (no prompting/model call here). |
| II. Reproducibility by Manifest | **N/A** | Pure transformer; runs no sweep and consumes no budget, so the manifest obligation does not apply. (Determinism — which supports reproducibility — is covered separately under Principle VII and research D7; persisting results is the runner's responsibility, not this feature's.) |
| III. Offline-Testable, Zero-Spend CI (NON-NEGOTIABLE) | **PASS** | No network, no credential, no async. Entire behavior verified offline with synthetic fixtures; `pytest` passes with no `OPENROUTER_API_KEY` (FR-013, SC-005). |
| IV. Spec-Driven Development | **PASS** | Full artifact set (spec, plan, research, data-model, contracts, quickstart); every FR maps to a task in the forthcoming `tasks.md` (verified at the analyze gate). `spec.md` is source of truth. |
| V. Budget Discipline | **N/A** | No paid calls. |
| VI. Secrets Hygiene (NON-NEGOTIABLE) | **N/A** | No credential handling. |
| VII. Shared-Scaffold Fairness | **PASS** | Extraction is model-agnostic: identical rules for every model, no per-model branching, so it cannot advantage one model over another in the comparative matrix. |

**Engineering-constraints check**: New capability reuses an already-declared dependency (`unidiff`) — no `research.md` justification for a new package needed; code lands in `src/hecate/generation/` per the README module map; small reviewable diff; frozen dataclass + `from __future__ import annotations` matching existing modules; `data/` untouched.

**Result: GREEN — no violations.** Complexity Tracking is empty of violations.

**Post-design re-check (after Phase 1)**: **PASS** — design adds only `patch.py` (pure function + `ExtractionResult` dataclass), re-exports from `hecate.generation`, one shared contract doc, and one offline test module. `unidiff` is used strictly as a validator; the byte-exact substring is what is emitted, so no principle is weakened.

## Project Structure

### Documentation (this feature)

```text
specs/008-patch-extraction/
├── plan.md              # This file
├── research.md          # Phase 0 — parsing/validation decisions
├── data-model.md        # Phase 1 — ExtractionResult + GenerationRecord mapping
├── quickstart.md        # Phase 1 — how to run/verify offline
├── contracts/
│   └── patch-api.md     # Phase 1 — S8 callable contract (references the shared format contract)
├── checklists/
│   └── requirements.md  # PO output
└── tasks.md             # Phase 2 — created by /speckit-tasks (NOT this command)

docs/contracts/
└── patch-format.md      # Phase 1 — NORMATIVE cross-stage contract (S8 + Stage-2 E-M3)
```

### Source Code (repository root)

```text
src/hecate/generation/
├── __init__.py          # + re-export extract_patch, ExtractionResult
├── client.py            # S7 (existing, unchanged)
├── errors.py            # S7 (existing, unchanged)
└── patch.py             # S8 — extract_patch(), ExtractionResult, candidate detection + unidiff validation

tests/
└── test_patch_extraction.py  # S8 — offline synthetic-fixture matrix (success + failure)
```

**Structure Decision**: New `patch.py` inside the existing `generation` package, public surface re-exported from `hecate.generation` so callers use one import path (matches the README module map: "generation/ = OpenRouter client, patch extraction", and the S7 contract's own non-goal note that patch extraction is "S8"). The normative format contract lives in `docs/contracts/` rather than under `specs/008-*/contracts/` because it is **consumed by two stages** (S8 and E-M3); the feature-local `contracts/patch-api.md` references it instead of duplicating its rules.

## Complexity Tracking

> No constitution violations requiring justification.

Two deliberate simplicity choices, recorded for the review-plan gate:

| Decision | Why | Alternative rejected |
|----------|-----|----------------------|
| `unidiff` used as a *validator only*; emit the raw substring | Guarantees byte-exact preservation + "never repair" (FR-006/007) in one stroke — the library's re-serialization would normalize whitespace/newlines and defeat the invariant. | Emitting `unidiff`'s serialized output: rejected — it can alter line endings and final-newline state. |
| Pure sync function, inline fixtures | Deterministic, reviewable, no I/O; mirrors S6/S7 test style. | A fixtures directory adds file I/O and hides test inputs from review; deferred unless the corpus outgrows inline strings. |
