# Implementation Plan: OpenRouter Client Wrapper

**Branch**: `007-openrouter-client` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-openrouter-client/spec.md`

## Summary

Add the Stage-1 OpenRouter client wrapper in `src/hecate/generation/`: an async client that sends one rendered prompt (S6) to a configured model slug and returns generated text plus token usage, using the run's fixed decoding params. It enforces a per-request timeout, retries transient failures (429/5xx/timeout/connection) with bounded exponential back-off + jitter, fails fast on deterministic 4xx, and caps concurrency with an `asyncio.Semaphore`. The result maps directly onto `GenerationRecord` fields. Cost/budget, patch extraction, caching, and the run loop are out of scope.

## Technical Context

**Language/Version**: Python 3.10+ (matches project `pyproject.toml` `requires-python = ">=3.10"`)

**Primary Dependencies**: `httpx` (already declared) for async HTTP; stdlib `asyncio` for concurrency; `pyyaml` (already declared) to read `configs/option_a.yaml`; existing `hecate.utils.env.get_openrouter_api_key`

**Storage**: None. Client returns in-memory results; persistence to JSONL / `GenerationRecord` is a downstream feature

**Testing**: `pytest` + `pytest-asyncio` (both declared); offline via `httpx.MockTransport` — no live network in unit tests

**Target Platform**: Local / CI Python package (async I/O)

**Project Type**: Library module within the Hecate Stage-1 `generation` package

**Performance Goals**: Support a full Stage-1 sweep (1,200 calls) without overwhelming the provider; throughput bounded by a configurable concurrency cap rather than maximized

**Constraints**: Fixed decoding params sourced from config and echoed on each result (reproducibility); API key from env only, never logged; send exactly the S6 prompt (no solution leakage); bounded retry attempts (no infinite retry)

**Scale/Scope**: One client reused for all 4 models across ~300 Lite tasks; single-shot generation (one prompt in, one response out)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution file is still the placeholder template — no project-specific gates to enforce. Apply repo engineering defaults: small reviewable diff, match existing `src/hecate` module patterns (dataclasses, config helpers, `from __future__ import annotations`), no secrets in code, stay within S7 scope.

**Post-design re-check**: Pass — design stays inside `src/hecate/generation/`, reuses S2 env + S4 config, adds only the client + result dataclass + offline tests. No new runtime dependencies.

## Project Structure

### Documentation (this feature)

```text
specs/007-openrouter-client/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── client-api.md
├── checklists/
│   └── requirements.md
└── tasks.md            # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/hecate/generation/
├── __init__.py          # Re-export client API (OpenRouterClient, CompletionResult, errors)
├── client.py            # S7 — OpenRouterClient, CompletionResult, config loading, retry/backoff, concurrency
└── errors.py            # S7 — OpenRouterError hierarchy (transient-exhausted vs permanent)

configs/option_a.yaml    # S4 (existing) — base_url, decoding, model slugs (read-only here)

tests/
└── test_generation.py   # S7 — offline tests via httpx.MockTransport
```

**Structure Decision**: New `client.py` (and small `errors.py`) inside the existing `generation` package; public surface re-exported from `hecate.generation` so callers use one import path. Matches the issue's stated home `src/hecate/generation/` and the README module map ("generation/ = OpenRouter client, patch extraction"). Patch extraction (S8) lands later in the same package.

## Complexity Tracking

> No constitution violations requiring justification. Async is chosen over threads because it pairs with the already-declared `pytest-asyncio` and gives a simple `asyncio.Semaphore` concurrency cap; a thin sync wrapper may be added only if a caller needs it, keeping one source of truth in the async path.
