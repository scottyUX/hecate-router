# Phase 1 Data Model: OpenRouter Client Wrapper

In-memory types only; nothing is persisted by this feature. Fields are named to map cleanly onto the existing `hecate.data.records.GenerationRecord`.

## CompletionResult (frozen dataclass)

The output of one model call.

| Field | Type | Notes |
|-------|------|-------|
| `model_slug` | `str` | Slug that was called (one of the S4 config slugs). |
| `text` | `str` | Generated text (`choices[0].message.content`). Non-empty on success. |
| `prompt_tokens` | `int \| None` | From `usage.prompt_tokens`; `None` if provider omitted usage. |
| `completion_tokens` | `int \| None` | From `usage.completion_tokens`; `None` if omitted. |
| `decoding_params` | `dict[str, Any]` | Exact params sent (e.g. `{"temperature": 0.0, "max_tokens": 4096}`). |
| `finish_reason` | `str \| None` | Optional; `choices[0].finish_reason` when present. |
| `raw_json` | `dict[str, Any] \| None` | Optional parsed JSON body, for debugging only. Deliberately named `raw_json` (not `raw_response`) to avoid confusion with the string field on `GenerationRecord`. |

**Mapping to `GenerationRecord`** (note the field types — `GenerationRecord.raw_response` is `str | None`, see `src/hecate/data/records.py`):

| `CompletionResult` | `GenerationRecord` | Notes |
|--------------------|--------------------|-------|
| `text` | `raw_response` (`str`) | Per issue #7, the generated text populates the record's `raw_response`. |
| `model_slug` | `model_slug` | |
| `prompt_tokens` | `prompt_tokens` | `None` passes through unchanged. |
| `completion_tokens` | `completion_tokens` | `None` passes through unchanged. |
| `decoding_params` | `decoding_params` | |
| `raw_json` | (not stored) | Debugging aid only; the record stores the string text, not the JSON object. |

This feature does not build the record; it returns the values the runner will copy in. The generated text is a plain string so it maps directly onto `GenerationRecord.raw_response` without a type mismatch.

## GenerationRequest (implicit — method arguments)

Not a stored entity; the inputs to `OpenRouterClient.complete`.

| Field | Type | Notes |
|-------|------|-------|
| `model_slug` | `str` | Required; must be a configured slug. |
| `prompt` | `str` | Required; the S6 rendered prompt, sent verbatim as a single user message. |
| `decoding` | `dict \| None` | Optional per-call override; defaults to config decoding params. |

## ClientConfig (loaded from configs/option_a.yaml)

Resolved once at client construction.

| Field | Type | Source |
|-------|------|--------|
| `base_url` | `str` | `base_url` (e.g. `https://openrouter.ai/api/v1`). |
| `temperature` | `float` | `decoding.temperature`. |
| `max_tokens` | `int` | `decoding.max_tokens`. |
| `model_slugs` | `list[str]` | `models[].slug` (for optional slug validation). |

Client-behavior settings (constructor args, with defaults; not from the model config): `timeout`, `max_retries`, `max_concurrency`, `backoff_base`, `backoff_cap`.

## Error hierarchy

| Type | Meaning | Retried? |
|------|---------|----------|
| `OpenRouterError` | Base class for all client errors. | — |
| `PermanentAPIError` | Deterministic 4xx (400/401/403/404/422). Carries status code. | No — fail fast (FR-006). |
| `RetryExhaustedError` | Transient failures persisted past `max_retries`. Carries last status/exception and attempt count. | No — surfaced after retries (FR-007). |
| `MissingCredentialError` | API key absent at construction. | No — raised before any network call (FR-009). |

`RetryExhaustedError` and `PermanentAPIError` are distinct types so callers/tests can tell exhausted-retry from permanent failure (SC-003).

## Validation rules

- `prompt` must be non-empty.
- `model_slug` should match a configured slug when validation is enabled; unknown slugs raise before the call.
- `max_concurrency`, `max_retries`, `timeout` must be positive.
- Credential resolved (or explicitly provided) before any request is attempted.
