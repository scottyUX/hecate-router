# Quickstart: OpenRouter Client Wrapper

Validation guide for S7. Implementation details live in [contracts/client-api.md](./contracts/client-api.md) and [data-model.md](./data-model.md); this file shows how to prove the feature works.

## Prerequisites

- Repo installed in editable mode: `pip install -e ".[dev]"`
- Dependencies already declared: `httpx`, `pyyaml`, `python-dotenv`, `pytest`, `pytest-asyncio`
- Model config present at `configs/option_a.yaml` (S4)
- For the optional live check only: a real key in `.env` (`OPENROUTER_API_KEY=...`)

## Offline validation (no spend, no credential) — primary path

Run the feature's unit tests, which use `httpx.MockTransport`:

```bash
pytest tests/test_generation.py -v
```

Expected: all pass with no network access and no `OPENROUTER_API_KEY` set. Coverage should include:

- Success -> non-empty `text` + `prompt_tokens` / `completion_tokens` (C-1, C-2)
- Decoding params echoed on the result and taken from config, plus per-call override (C-3)
- Request targets `{base_url}/chat/completions` and carries the configured `timeout` (FR-004, FR-011, C-4)
- Unknown slug rejected before any request when `validate_slug=True` (FR-011)
- 429-then-success recovers and returns a result (C-5)
- An uncommon 5xx (e.g. 520) is also retried, proving `500 <= status < 600` (C-5)
- Persistent transient failure raises `RetryExhaustedError` (C-5)
- 401/400 raises `PermanentAPIError` with no retry (C-6)
- Response missing `usage` -> counts are `None`, no raise, no fabricated counts (C-2, SC-001)
- More than `max_concurrency` concurrent calls never exceed the cap (C-7)
- Missing credential raises `MissingCredentialError` before any call, translated from the loader's `RuntimeError` (C-8)

## Illustrative usage

```python
import asyncio
from hecate.generation import OpenRouterClient

async def main():
    async with OpenRouterClient(max_concurrency=4) as client:
        result = await client.complete(
            model_slug="meta-llama/llama-3.1-8b-instruct",
            prompt="<rendered S6 prompt string>",
        )
        print(result.text)
        print(result.prompt_tokens, result.completion_tokens)
        print(result.decoding_params)  # {"temperature": 0.0, "max_tokens": 4096}

asyncio.run(main())
```

## Optional live smoke test (incurs minimal spend)

Only when explicitly opted in; skipped in CI. Requires **two** signals so a bare key on a dev machine never triggers spend: `RUN_LIVE_TESTS=1` AND `OPENROUTER_API_KEY`. Without both, the test is skipped even when selected with `-m live`.

```bash
RUN_LIVE_TESTS=1 OPENROUTER_API_KEY=sk-... pytest tests/test_generation.py -v -m live
```

Expected: one real call to the cheapest configured slug returns text and non-zero token counts. Running the normal suite (no `RUN_LIVE_TESTS`) never issues a live call, even if `OPENROUTER_API_KEY` happens to be exported.

## Done / acceptance mapping

| Spec success criterion | Where proven |
|------------------------|--------------|
| SC-001 text + token counts | offline success test |
| SC-002 recover from transient | 429-then-success test |
| SC-003 permanent vs exhausted distinct | `PermanentAPIError` and `RetryExhaustedError` tests |
| SC-004 concurrency capped at N | concurrency test |
| SC-005 offline, zero spend in CI | whole suite runs without a key |
| SC-006 reproducible decoding params | decoding-params echo test |
