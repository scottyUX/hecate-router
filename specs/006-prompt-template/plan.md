# Implementation Plan: Stage-1 Prompt Template

**Branch**: `006-prompt-template` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-prompt-template/spec.md`

## Summary

Add a Stage-1 shared prompt template in `src/hecate/scaffold/` that deterministically renders one frozen, versioned instruction string from a `SwebenchTask` and S5 `ContextBundle`, asking the model for a single unified diff. Expose `render_prompt`, `PROMPT_VERSION`, `prompt_hash`, and optional prompt persistence for `prompt_ref`. Reuse the existing S5 context types — do not redefine `ContextBundle`.

## Technical Context

**Language/Version**: Python 3.11+ (matches project `pyproject.toml`)

**Primary Dependencies**: Existing `hecate.data.tasks.SwebenchTask`, `hecate.scaffold.context.ContextBundle` / `ContextFile`; stdlib `hashlib` for hashing

**Storage**: Optional prompt files under `data/cache/prompts/` or `data/outputs/prompts/` (gitignored via existing `data/cache/`, `data/outputs/`)

**Testing**: pytest (extend `tests/test_scaffold.py` or add adjacent prompt tests)

**Target Platform**: Local / CI Python package (no HTTP in this feature)

**Project Type**: Library module within the Hecate Stage-1 scaffold package

**Performance Goals**: Deterministic in-memory string build; fine for full Lite file contexts

**Constraints**: Shared scaffold (no model_slug in render); single-shot v1; never inject gold patch; freeze wording under `PROMPT_VERSION`

**Scale/Scope**: One template for the whole Stage-1 run; ~300 Lite instances downstream

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution file is still a placeholder template — no project-specific gates to enforce. Apply repo engineering defaults: small reviewable diff, match existing scaffold patterns, no secrets, stay within S6 scope.

**Post-design re-check**: Pass — design stays inside `scaffold/`, reuses S5 types, adds only prompt helpers + tests.

## Project Structure

### Documentation (this feature)

```text
specs/006-prompt-template/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── prompt-api.md
└── tasks.md
```

### Source Code (repository root)

```text
src/hecate/scaffold/
├── __init__.py          # Re-export prompt API alongside context API
├── context.py           # S5 (existing) — ContextBundle, build_context
└── prompt.py            # S6 — PROMPT_VERSION, render_prompt, prompt_hash, optional write

tests/
└── test_scaffold.py     # Extend with prompt tests (or add tests/test_prompt.py)
```

**Structure Decision**: New `prompt.py` next to `context.py`; public surface re-exported from `hecate.scaffold` so callers use one package. Matches issue home `src/hecate/scaffold/`.

## Complexity Tracking

> No constitution violations requiring justification.
