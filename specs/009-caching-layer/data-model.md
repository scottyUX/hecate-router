# Data Model: Caching Layer (S9)

One entry type, two key functions, and a store. Maps onto the **existing**
`GenerationRecord` fields; no record-schema change.

## Entity: `CachedGeneration`

A persisted **successful** provider outcome for one cache key. By construction it can
represent only a success (FR-011 / D5) — there is no failure variant.

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class CachedGeneration:
    raw_response: str                    # generated text, verbatim (maps to GenerationRecord.raw_response)
    prompt_tokens: int | None            # None if provider omitted usage
    completion_tokens: int | None        # None if provider omitted usage
    decoding_params: dict[str, Any]      # the params actually sent (regime the result was produced under)
    model_slug: str                      # self-describing; aids debugging + record rebuild
    # __post_init__ rejects empty/whitespace raw_response (success-only, FR-011)
    # serialization: to_dict / from_dict / to_json / from_json (JSON object, ensure_ascii=False)
```

**Invariants** (enforced/asserted):
- `raw_response` is required and MUST be non-empty and not whitespace-only —
  `__post_init__` rejects `""` / whitespace-only text, so a non-success (e.g. an empty
  completion) literally cannot be constructed as a `CachedGeneration` (FR-011).
- Round-trips losslessly through JSON (verbatim `raw_response`, no truncation — FR-005).
- Frozen (immutable) — a cached outcome is never mutated in place.
- `from_dict` returns a miss signal (store treats it as `None`) if required fields are
  absent — schema-invalid file → miss (FR-007).
- Serialized entries carry `schema_version = CACHE_SCHEMA_VERSION`; `from_dict` returns
  a miss when it is missing or mismatched, so an on-disk format bump auto-invalidates
  stale entries (contract K-12).

## Key functions

```python
def decoding_fingerprint(decoding_params: dict[str, Any]) -> str: ...
    # hex SHA-256 of canonical JSON (sort_keys=True) of the params as they will be sent

def cache_key(
    instance_id: str,
    model_slug: str,
    prompt_hash: str,       # from hecate.scaffold.prompt.prompt_hash (S6)
    prompt_version: str,    # hecate.scaffold.prompt.PROMPT_VERSION (S6)
    decoding_fingerprint: str,
) -> str: ...
    # hex SHA-256 of a canonical JSON array of the five strings (unambiguous, deterministic)
```

Both are pure and deterministic (FR-009). Changing any one input changes `cache_key`
(FR-001, SC-003).

## Entity: `GenerationCache` (the store)

```python
class GenerationCache:
    def __init__(self, cache_dir: Path | str | None = None, *, read_bypass: bool = False) -> None: ...
        # default cache_dir: data/cache/generations/  (gitignored)

    def get(self, key: str) -> CachedGeneration | None: ...
        # None on miss / corrupt / schema-invalid / read_bypass; never raises on read
    def put(self, key: str, entry: CachedGeneration) -> None: ...
        # atomic write (temp + os.replace); creates cache_dir on first write
```

## Mapping onto `GenerationRecord` (existing schema, `src/hecate/data/records.py`)

The S11 runner maps a hit onto a record; the cache stores exactly what a record's
*generation portion* needs:

| `GenerationRecord` field | source on a hit |
|--------------------------|-----------------|
| `raw_response` | `CachedGeneration.raw_response` |
| `prompt_tokens` | `CachedGeneration.prompt_tokens` |
| `completion_tokens` | `CachedGeneration.completion_tokens` |
| `decoding_params` | `CachedGeneration.decoding_params` |
| `model_slug` | `CachedGeneration.model_slug` |

`extracted_patch` / `patch_parse_ok` are populated **after** retrieval by S8 in the
runner (the cache stores raw text, not extracted patches — spec Assumptions). No new
record field; no schema change.

## Non-entities (explicitly not modeled)

- No failure entry (a failed generation is simply absent — FR-011).
- No eviction/TTL metadata, no distributed-cache coordination (out of scope).
- No change to `GenerationRecord`, its serialization, or JSONL I/O.
- The client (S7) is unchanged and cache-unaware.
