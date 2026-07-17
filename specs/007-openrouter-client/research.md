# Phase 0 Research: OpenRouter Client Wrapper

Decisions resolving the Technical Context unknowns for S7. No open NEEDS CLARIFICATION remain.

## 1. HTTP client library and sync vs async

**Decision**: Use `httpx.AsyncClient` with a module-level `OpenRouterClient` wrapper; async-first, concurrency capped by `asyncio.Semaphore`.

**Rationale**: `httpx` is already a declared dependency and `pytest-asyncio` is already in the dev extras, signalling async was the intended direction. `httpx.MockTransport` gives fully offline, deterministic tests (spec SC-005). A single async path with a semaphore is the simplest way to satisfy the bounded-concurrency requirement (FR-008).

**Alternatives considered**: `requests` + `ThreadPoolExecutor` (adds a dependency and a second concurrency model); `openai` SDK pointed at OpenRouter's base URL (heavier dependency, less control over retry/timeout semantics, harder to mock deterministically).

## 2. OpenRouter API surface

**Decision**: Call `POST {base_url}/chat/completions` with `Authorization: Bearer <key>`, body `{model, messages:[{role:"user", content: prompt}], temperature, max_tokens}`. Read `choices[0].message.content` for text and `usage.prompt_tokens` / `usage.completion_tokens` for counts.

**Rationale**: OpenRouter exposes an OpenAI-compatible chat-completions endpoint at the configured `base_url` (`https://openrouter.ai/api/v1` in `configs/option_a.yaml`). The single-shot v1 design (one prompt -> one response) maps to a single user message. `usage` is the standard token-accounting object.

**Alternatives considered**: Legacy `/completions` (not used by the configured instruct models); streaming responses (unnecessary for single-shot batch generation and complicates usage capture).

## 3. Which failures are transient vs permanent

**Decision**: Treat a response as transient (retry) when the status is `429` OR any 5xx (`500 <= status < 600`), and on `httpx.TimeoutException` / `httpx.TransportError` (connection errors). Fail fast (no retry) on all other 4xx (e.g. 400, 401, 403, 404, 422). Honor a `Retry-After` header when present on 429.

**Rationale**: Directly implements FR-005/FR-006. Matching the whole 5xx range (not an enumerated 500/502/503/504 list) means uncommon server errors like 507/520/524 are still retried, as issue #7 intends. 4xx (except 429) indicate a deterministic problem (bad request, missing/invalid key, unknown model) that will not resolve by retrying, so retrying wastes budget and time.

**Alternatives considered**: Enumerating specific 5xx codes (500/502/503/504) — misses other server errors the provider/CDN can emit; retry all non-2xx (wastes attempts on permanent 4xx); retry only 429 (misses transient 5xx and network blips that are common at sweep scale).

## 4. Back-off strategy and retry cap

**Decision**: Bounded exponential back-off with full jitter: `sleep = min(cap, base * 2**attempt)` then random in `[0, sleep]`, default `max_retries` small (e.g. 4 attempts) and configurable. `Retry-After` overrides computed back-off when larger.

**Rationale**: Full jitter avoids synchronized retry storms across concurrent calls; a bounded attempt count prevents infinite retry (spec edge case) and surfaces a distinct exhausted-retry error (FR-007).

**Alternatives considered**: Fixed-interval retry (thundering herd under concurrency); unbounded retry (violates the bounded-attempts edge case).

## 5. Decoding params source and reproducibility

**Decision**: Load `decoding.temperature` and `decoding.max_tokens` from `configs/option_a.yaml` at client construction; allow a per-call override dict but default to config; echo the exact params used on `CompletionResult.decoding_params`.

**Rationale**: Satisfies FR-003 and SC-006 (same inputs -> identically recorded params) and feeds `GenerationRecord.decoding_params` unchanged. Config is the single source of truth (S4 already verified the values).

**Alternatives considered**: Hard-coded defaults in code (drifts from S4 config, hurts reproducibility); requiring callers to pass params every time (error-prone, easy to diverge across models).

## 6. Credentials and safety

**Decision**: Resolve the key via `hecate.utils.env.get_openrouter_api_key(required=True)` at construction (or accept an explicit `api_key` for tests). Never include the key in logs, error messages, or `repr`.

**Rationale**: Reuses the S2 loader, gives an actionable error when the key is missing (FR-009 / spec edge case), and keeps secrets out of the codebase per repo rules.

**Alternatives considered**: Reading `os.environ` directly (bypasses the `.env` loading already centralized in S2).

## 7. Token usage missing from response

**Decision**: If `usage` (or a token field) is absent, set the corresponding counts to `None` rather than raising; the result is still returned with text.

**Rationale**: Matches the spec edge case and `GenerationRecord.prompt_tokens`/`completion_tokens` being `Optional[int]`. A missing usage field should not discard an otherwise-valid generation.

**Alternatives considered**: Raise on missing usage (loses a paid generation over a metadata gap); default to 0 (misleading — implies a measured zero).

## 8. Testing approach (offline, no spend)

**Decision**: Inject an `httpx.MockTransport` (or an explicit `transport`/`AsyncClient` parameter) so tests script responses for success, 429-then-success, exhausted retries, permanent 4xx, missing usage, and concurrency-cap enforcement. Any live smoke test is a separate, opt-in test skipped unless `OPENROUTER_API_KEY` is set.

**Rationale**: Satisfies FR-012 / SC-005 (CI passes with zero spend and no credential) while still exercising every behavior deterministically.

**Alternatives considered**: `respx` library (extra dependency; `MockTransport` is built into `httpx`); recording real responses (spend + flakiness + secret handling in CI).
