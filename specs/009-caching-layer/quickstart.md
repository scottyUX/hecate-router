# Quickstart: Caching Layer (S9)

How to use and verify the generation cache — fully offline, zero provider spend.

## Use (as the S11 runner will)

```python
from hecate.caching import (
    GenerationCache, CachedGeneration, cache_key, decoding_fingerprint,
)
from hecate.scaffold.prompt import prompt_hash, PROMPT_VERSION

# `decoding` must be the fully-resolved params that will actually be sent — identical to
# what S7 echoes as CompletionResult.decoding_params — so the key and stored entry stay consistent.
decoding = {"temperature": 0.0, "max_tokens": 1024}
key = cache_key(
    instance_id="psf__requests-1963",
    model_slug="qwen2.5-7b",
    prompt_hash=prompt_hash(rendered_prompt),
    prompt_version=PROMPT_VERSION,
    decoding_fingerprint=decoding_fingerprint(decoding),
)

cache = GenerationCache()                      # default data/cache/generations/
hit = cache.get(key)
if hit is None:                                # miss → call provider (runner does this)
    result = ...                               # S7 CompletionResult on success
    cache.put(key, CachedGeneration(
        raw_response=result.text,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        decoding_params=result.decoding_params,
        model_slug=result.model_slug,
    ))
else:
    result_text = hit.raw_response             # zero provider calls
```

Failures are never cached — the runner simply doesn't call `put` on a failure, and
`CachedGeneration` can't represent one, so a failed identity re-calls the provider on
the next run.

Force fresh calls without deleting the cache:

```python
cache = GenerationCache(read_bypass=True)      # get() always misses; put() still writes
```

## Verify offline

```bash
python -m pytest tests/test_caching.py -v
```

The suite (all offline, no `OPENROUTER_API_KEY`, `tmp_path` cache dir) covers:

**Hit / miss + zero-spend**
- write an entry → `get` returns it, and no provider is ever contacted (SC-001, US1)
- 10 entries → 10 hits, zero new calls

**Key discrimination (one dimension differs → miss)** — SC-003, US3
- differ only `instance_id` → miss; only `model_slug` → miss; only `prompt_hash` → miss
- only `prompt_version` → miss (byte-identical prompt, bumped template version)
- only `decoding_fingerprint` (e.g. temperature 0.0 → 0.7) → miss
- identical inputs computed twice → identical key (determinism, US3.6)

**Restart survival** — SC-002, US2
- write with one `GenerationCache`, construct a fresh `GenerationCache` on the same dir → entry still retrievable

**Atomicity / corruption → miss (never crash)** — SC-004, FR-007
- a truncated/garbage `{key}.json` → `get` returns `None`
- an orphan `{key}.json.tmp-*` → not matched as an entry
- a schema-invalid JSON object (missing `raw_response`) → miss

**Success-only** — SC-006, FR-011
- there is no API to store a failure; a failed identity has no entry → re-fetch

**Read-bypass** — SC-007, US4
- `read_bypass=True` → `get` misses even with a valid entry present; `put` still writes

## Expected acceptance evidence

- `pytest tests/test_caching.py` passes with no credential/network (SC-005).
- 100% hit on repeated successful identities, zero provider calls (SC-001).
- 100% miss when any one key dimension changes (SC-003).
- 100% of failure/malformed outcomes are unretrievable (SC-006).
- `raw_response` round-trips byte-for-byte (FR-005).
