# Contract: `hecate.generation` client API

Public surface re-exported from `hecate.generation`. This is the interface downstream Stage-1 code (the runner, S8 patch extraction) depends on. Signatures are the contract; bodies are defined in implementation.

## Types

```python
@dataclass(frozen=True)
class CompletionResult:
    model_slug: str
    text: str
    prompt_tokens: int | None
    completion_tokens: int | None
    decoding_params: dict[str, Any]
    finish_reason: str | None = None
    raw_json: dict[str, Any] | None = None   # parsed body for debugging only; NOT GenerationRecord.raw_response
```

`GenerationRecord.raw_response` is `str | None`; the generated `text` (a string) is what populates it. `raw_json` is a separate optional debugging aid and is intentionally named to avoid that clash.

```python
class OpenRouterError(Exception): ...
class MissingCredentialError(OpenRouterError): ...
class PermanentAPIError(OpenRouterError):
    status_code: int
class RetryExhaustedError(OpenRouterError):
    attempts: int
    last_status: int | None
```

## Client

```python
class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,          # default: get_openrouter_api_key(required=True)
        config_path: Path | str | None = None,  # default: configs/option_a.yaml
        timeout: float = 60.0,
        max_retries: int = 4,
        max_concurrency: int = 8,
        backoff_base: float = 0.5,
        backoff_cap: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,  # test injection point
        validate_slug: bool = True,
    ) -> None: ...

    async def complete(
        self,
        *,
        model_slug: str,
        prompt: str,
        decoding: dict[str, Any] | None = None,  # default: config decoding params
    ) -> CompletionResult: ...

    async def aclose(self) -> None: ...

    async def __aenter__(self) -> "OpenRouterClient": ...
    async def __aexit__(self, *exc: object) -> None: ...
```

## Behavioral contract

| ID | Guarantee |
|----|-----------|
| C-1 | `complete` returns a `CompletionResult` with non-empty `text` on a 2xx response. |
| C-2 | `prompt_tokens` / `completion_tokens` reflect `usage`; both are `None` if `usage` is absent (no raise, no fabricated counts). |
| C-3 | `decoding_params` on the result equals what was sent (config values unless overridden). |
| C-4 | Every request carries the configured `timeout` (targeting the configured `base_url`). |
| C-5 | Transient responses — status `429` OR any 5xx (`500 <= status < 600`) — plus timeout / connection errors are retried with exponential back-off + full jitter, honoring `Retry-After` when present, up to `max_retries`; then `RetryExhaustedError` is raised. |
| C-6 | Any other 4xx (non-429) raises `PermanentAPIError` immediately with no retry. |
| C-7 | At most `max_concurrency` requests are in flight across concurrent `complete` calls (shared `asyncio.Semaphore`). |
| C-8 | Missing credential raises `MissingCredentialError` at construction, before any network call. The S2 loader `get_openrouter_api_key(required=True)` raises `RuntimeError`; the client MUST catch and re-raise it as `MissingCredentialError` so callers see the contract's error type. |
| C-9 | The request body's user message equals the provided `prompt` verbatim (no added solution/answer content). |
| C-10 | The API key never appears in `repr`, logs, or exception messages. |
| C-11 | A caller-supplied `transport` is used instead of a live network connection (enables offline tests). |

## Non-goals (contract explicitly excludes)

- Pricing / cost computation and budget enforcement (`hecate.cost`).
- Patch/diff extraction from `text` (S8).
- Response caching (S9).
- Building or writing `GenerationRecord` / JSONL (runner, S11+).
