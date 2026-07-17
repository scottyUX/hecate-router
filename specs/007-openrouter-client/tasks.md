# Tasks: OpenRouter Client Wrapper

**Input**: Design documents from `/specs/007-openrouter-client/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/client-api.md](./contracts/client-api.md)

**Tests**: Included. The spec explicitly requires offline verifiability with zero provider spend (FR-012, SC-005), so test tasks are first-class here.

**Organization**: Tasks are grouped by user story so each can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — reserved for tasks in **different files** with no dependency on incomplete tasks. Tasks that both edit `src/hecate/generation/client.py` or both edit `tests/test_generation.py` are NOT marked `[P]` (same-file writes serialize).
- **[Story]**: US1 / US2 / US3 (maps to spec.md user stories)
- All source paths are relative to repo root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the generation package for the client module.

- [ ] T001 [P] Add the error hierarchy in `src/hecate/generation/errors.py` (`OpenRouterError`, `MissingCredentialError`, `PermanentAPIError` with `status_code`, `RetryExhaustedError` with `attempts`/`last_status`), per [data-model.md](./data-model.md).
- [ ] T002 [P] Create `tests/test_generation.py` with the `pytest`/`pytest-asyncio` scaffold and a shared `httpx.MockTransport` helper (a `make_transport(handlers)` factory) so no test touches the network.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config loading, result type, and the client skeleton that every user story builds on.

**CRITICAL**: No user story work can begin until this phase is complete. All tasks in this phase edit `src/hecate/generation/client.py` (except T007), so they run sequentially — no `[P]`.

- [ ] T003 Implement `CompletionResult` frozen dataclass in `src/hecate/generation/client.py` with fields from [data-model.md](./data-model.md) (`model_slug`, `text`, `prompt_tokens`, `completion_tokens`, `decoding_params`, `finish_reason`, `raw_json`). Note: `raw_json` is a debugging dict; the generated `text` string is what maps to `GenerationRecord.raw_response` (I3).
- [ ] T004 Implement config loading in `src/hecate/generation/client.py`: read `base_url`, `decoding.temperature`, `decoding.max_tokens`, and `models[].slug` from `configs/option_a.yaml` (default path via a `_default_config_path()` helper mirroring `src/hecate/scaffold/context.py`). Depends on T003.
- [ ] T005 Implement `OpenRouterClient.__init__` in `src/hecate/generation/client.py`: resolve the API key by calling `hecate.utils.env.get_openrouter_api_key(required=True)` and **catching its `RuntimeError`, re-raising as `MissingCredentialError`** (G2, C-8) — or accept an explicit `api_key`; accept `timeout`/`max_retries`/`max_concurrency`/`backoff_base`/`backoff_cap`/`transport`/`validate_slug`; construct an `httpx.AsyncClient` (using `transport` when provided) with `base_url`; create the `asyncio.Semaphore`. Depends on T004.
- [ ] T006 Implement `aclose` + `__aenter__`/`__aexit__` async context management in `src/hecate/generation/client.py`. Depends on T005.
- [ ] T007 [P] Re-export the public surface (`OpenRouterClient`, `CompletionResult`, error types) from `src/hecate/generation/__init__.py`. Depends on T001, T006.

**Checkpoint**: Package imports cleanly and a client can be constructed with an injected transport.

---

## Phase 3: User Story 1 - Get one attempted fix for a task (Priority: P1) 🎯 MVP

**Goal**: A single call returns generated text plus token usage using the run's fixed decoding params, hitting the configured endpoint.

**Independent Test**: With a mock transport returning a chat-completion body, `complete(model_slug=..., prompt=...)` yields non-empty `text`, `prompt_tokens`, `completion_tokens`, and echoed `decoding_params`.

### Tests for User Story 1

> All edit `tests/test_generation.py` — write sequentially, not `[P]`.

- [ ] T008 [US1] Test happy-path `complete`: mock 200 chat-completion response → assert non-empty `text` and correct `prompt_tokens`/`completion_tokens` (C-1, C-2, SC-001).
- [ ] T009 [US1] Test decoding params: assert the request body carries config `temperature`/`max_tokens`, that `result.decoding_params` echoes them, and that a per-call override is honored (C-3, SC-006).
- [ ] T010 [US1] Test prompt fidelity + missing usage: assert the user message equals the prompt verbatim (C-9) and that a 200 response without `usage` yields `None` counts without raising and without fabricating counts (C-2, SC-001, spec edge case).
- [ ] T011 [US1] Test credential errors: `MissingCredentialError` is raised at construction when no key is present and none injected, and specifically that the loader's `RuntimeError` is translated to `MissingCredentialError` (C-8, G2). Assert no request is attempted.
- [ ] T012 [US1] Test timeout propagation: assert the configured `timeout` is applied to the outgoing request / `AsyncClient` (FR-004, C-4). (G1)
- [ ] T013 [US1] Test endpoint targeting: assert the request URL is `{base_url}/chat/completions` using the `base_url` from config (FR-011, C-4). (G1)
- [ ] T014 [US1] Test unknown-slug rejection: with `validate_slug=True`, an unconfigured slug raises before any request; with `validate_slug=False` it is allowed (FR-011, spec edge case). (G1)

### Implementation for User Story 1

> All edit `src/hecate/generation/client.py` — sequential, not `[P]`.

- [ ] T015 [US1] Implement the core request path in `OpenRouterClient.complete`: build `POST {base_url}/chat/completions` body `{model, messages:[{role:"user", content: prompt}], temperature, max_tokens}`, `Authorization: Bearer`, apply `timeout`, parse `choices[0].message.content` + optional `usage` (missing → `None` counts) into `CompletionResult` (`text` + `raw_json`). Depends on T006.
- [ ] T016 [US1] Add decoding resolution (config default, per-call `decoding` override) and echo params onto the result; validate non-empty prompt and (when `validate_slug`) known slug, raising before any request for an unknown slug. Depends on T015.
- [ ] T017 [US1] Ensure the API key never appears in `repr`, logs, or exception messages (C-10). Depends on T015.

**Checkpoint**: MVP — one real-shaped call returns text + usage offline; US1 tests pass, including FR-004/FR-011 coverage.

---

## Phase 4: User Story 2 - Survive transient provider failures (Priority: P1)

**Goal**: Transient failures retry with back-off; permanent failures fail fast; exhausted retries surface distinctly.

**Independent Test**: Mock 429-then-200 recovers; persistent 5xx raises `RetryExhaustedError`; 401/400 raises `PermanentAPIError` with a single attempt.

### Tests for User Story 2

> All edit `tests/test_generation.py` — sequential, not `[P]`.

- [ ] T018 [US2] Test 429-then-success and 503-then-success recover and return a result (C-5, SC-002).
- [ ] T019 [US2] Test that an uncommon 5xx (e.g. 520) is also treated as transient and retried, proving the `500 <= status < 600` rule rather than an enumerated list (I1, C-5).
- [ ] T020 [US2] Test persistent transient failure raises `RetryExhaustedError` with `attempts == max_retries + 1` (C-5, FR-007).
- [ ] T021 [US2] Test 400/401/403 raise `PermanentAPIError` on the first attempt (assert transport called exactly once) (C-6, SC-003).
- [ ] T022 [US2] Test timeout/connection errors are treated as transient and retried (C-5).

### Implementation for User Story 2

> All edit `src/hecate/generation/client.py` — sequential, not `[P]`.

- [ ] T023 [US2] Implement transient classification in a helper: transient iff status `== 429` OR `500 <= status < 600`, or the raised exception is `httpx.TimeoutException` / `httpx.TransportError`; otherwise a non-2xx is permanent → `PermanentAPIError` (I1, C-5, C-6). Depends on T015.
- [ ] T024 [US2] Implement bounded exponential back-off with full jitter (`backoff_base`, `backoff_cap`, `max_retries`), honoring `Retry-After` on 429, raising `RetryExhaustedError` when exhausted, in the `complete` retry loop. Make the sleep injectable/patchable so tests run fast. Depends on T023.

**Checkpoint**: US1 + US2 pass; reliability behavior fully covered offline.

---

## Phase 5: User Story 3 - Keep concurrency bounded (Priority: P2)

**Goal**: No more than `max_concurrency` calls are in flight at once.

**Independent Test**: Launch more concurrent `complete` calls than the cap using a gated mock transport and assert peak concurrency never exceeds the cap.

### Tests for User Story 3

- [ ] T025 [US3] Test concurrency cap: with `max_concurrency=N`, a transport that tracks in-flight count confirms peak ≤ N while all calls complete (C-7, SC-004), in `tests/test_generation.py`.

### Implementation for User Story 3

- [ ] T026 [US3] Wrap the request+retry path of `complete` in the shared `asyncio.Semaphore` so the cap holds across concurrent calls, in `src/hecate/generation/client.py`. Depends on T015, T024.

**Checkpoint**: All three stories independently testable and passing.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T027 [P] Add an opt-in live smoke test marked `@pytest.mark.live`, **skipped unless BOTH `RUN_LIVE_TESTS=1` and `OPENROUTER_API_KEY` are set** (I4) — a bare key on a dev machine must NOT trigger spend — hitting the cheapest configured slug, in `tests/test_generation.py`.
- [ ] T028 [P] Register the `live` marker in `pyproject.toml` `[tool.pytest.ini_options]` markers to avoid unknown-marker warnings.
- [ ] T029 Run `pytest tests/test_generation.py -v` offline (no key, `RUN_LIVE_TESTS` unset) and confirm all non-live tests pass with zero network access; then run any configured lint.
- [ ] T030 Execute the [quickstart.md](./quickstart.md) offline validation section and confirm the acceptance mapping (SC-001..SC-006).

---

## Dependencies & Execution Order

### Phase dependencies

- Setup (Phase 1) → Foundational (Phase 2) → User Stories (Phases 3–5) → Polish (Phase 6).
- Foundational blocks all user stories.

### User story dependencies

- US1 (P1): needs Foundational only — the MVP. Includes FR-004/FR-011 coverage (T012–T014).
- US2 (P1): builds on the `complete` request path from US1 (T015).
- US3 (P2): builds on the request+retry path (T015, T024).

### Within each story

- Tests are written first and expected to fail before implementation.
- `errors.py` and `CompletionResult`/config before the request path; request path before retry; retry before concurrency wrap.

### Parallel opportunities

- Phase 1: T001 (`errors.py`) and T002 (`tests/test_generation.py`) are different files → both `[P]`.
- T007 (`__init__.py`) is a different file from the Phase 2 client work → `[P]` once its deps are done.
- Phase 6: T027 (`tests/test_generation.py`) and T028 (`pyproject.toml`) are different files → both `[P]`.
- All other implementation/test tasks share `client.py` or `test_generation.py` respectively and are therefore sequential (T1).

---

## Implementation Strategy

### MVP first (User Story 1)

1. Phase 1 Setup → 2. Phase 2 Foundational → 3. Phase 3 US1 → STOP and validate one call returns text + usage offline, hitting the configured endpoint within the configured timeout.

### Incremental delivery

- Add US2 (reliability) → validate retries (429 + full 5xx range) / permanent / exhausted.
- Add US3 (concurrency) → validate cap.
- Polish: doubly-gated live smoke test + quickstart validation.

---

## Notes

- `[P]` = different files, no dependency on incomplete tasks. Same-file tasks are intentionally sequential (T1).
- Transient = `429` OR `500 <= status < 600` OR timeout/connection error (I1); everything else non-2xx is permanent.
- Token counts are `None` (never fabricated) when the provider omits `usage` (I2).
- `CompletionResult.text` (str) → `GenerationRecord.raw_response`; `raw_json` is debug-only (I3).
- Live tests require `RUN_LIVE_TESTS=1` AND `OPENROUTER_API_KEY` (I4).
- Wrap the loader's `RuntimeError` as `MissingCredentialError` (G2).
- Keep the API key out of all output (C-10); resolve via S2 env loader.
- Out of scope (do not implement here): cost/budget (`src/hecate/cost/`), patch extraction (S8), caching (S9), JSONL runner (S11+).
- Commit after each logical group; do not open a PR until requested.
