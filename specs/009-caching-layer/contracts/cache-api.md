# Contract: `hecate.caching` cache API

Public surface re-exported from `hecate.caching`, consumed by the S11 runner (which
orchestrates lookup-before-call and writes only on success). Signatures are the
contract; bodies are defined in implementation.

## Types

```python
@dataclass(frozen=True)
class CachedGeneration:
    raw_response: str
    prompt_tokens: int | None
    completion_tokens: int | None
    decoding_params: dict[str, Any]
    model_slug: str
```

`CachedGeneration` represents a **successful** outcome only — there is no failure
variant (FR-011).

## Functions

```python
def decoding_fingerprint(decoding_params: dict[str, Any]) -> str: ...

def cache_key(
    instance_id: str,
    model_slug: str,
    prompt_hash: str,
    prompt_version: str,
    decoding_fingerprint: str,
) -> str: ...
```

## Store

```python
class GenerationCache:
    def __init__(self, cache_dir: Path | str | None = None, *, read_bypass: bool = False) -> None: ...
    def get(self, key: str) -> CachedGeneration | None: ...
    def put(self, key: str, entry: CachedGeneration) -> None: ...
```

## Module constants & helpers

```python
CACHE_SCHEMA_VERSION: int         # on-disk entry format version; bump to invalidate all old entries
def default_cache_dir() -> Path:  # returns data/cache/generations/ (gitignored)
```

## Behavioral contract

| ID | Guarantee |
|----|-----------|
| K-1 | `cache_key` binds all five dimensions `(instance_id, model_slug, prompt_hash, prompt_version, decoding_fingerprint)`; changing any one yields a different key (FR-001, SC-003). |
| K-2 | `cache_key` and `decoding_fingerprint` are deterministic and pure: identical inputs → identical output, no I/O (FR-009). |
| K-3 | `decoding_fingerprint` depends only on the decoding-param values (order-independent via canonical sorted-key JSON), so a change to temperature / max-tokens / any decoding field changes it. Callers MUST supply consistently-typed values across runs (e.g. always `0.0`, never `0`): differing numeric types serialize differently and would cause a false miss — never a false hit (FR-001, FR-009). |
| K-4 | `get` returns the stored `CachedGeneration` for a present, valid key **without any provider call** (FR-003). The cache never opens a network connection or reads a credential. |
| K-5 | `get` returns `None` on miss (no file), on a corrupt/unparseable file, or on a schema-invalid entry — it never raises on read (FR-004, FR-007, SC-004). |
| K-6 | `put` writes atomically (temp file + `os.replace`); an interrupted write never produces a readable hit, and concurrent successful writes resolve to last-rename-wins (FR-006, SC-004). |
| K-7 | `put` persists **only** a `CachedGeneration` (a success); its `__post_init__` rejects an empty/whitespace `raw_response`, so there is no API to store a provider failure, exhausted-retry, or malformed/empty response (FR-011, SC-006). |
| K-8 | Entries persist under the gitignored cache area across process restarts; a new process with the same `cache_dir` retrieves prior entries by key (FR-002, SC-002). |
| K-9 | With `read_bypass=True`, `get` always returns `None` even when a valid entry exists, while `put` still writes successful entries (FR-008, SC-007). |
| K-10 | A stored entry preserves `raw_response` byte-for-byte (no truncation) plus token usage and decoding params — sufficient to populate a `GenerationRecord`'s generation portion (FR-005). |
| K-11 | `cache_dir` defaults to the gitignored `data/cache/generations/`; it is created on first write; all I/O is confined to it (FR-002). |
| K-12 | Each stored entry records `schema_version = CACHE_SCHEMA_VERSION`. `get` treats an entry whose `schema_version` is missing or ≠ the current `CACHE_SCHEMA_VERSION` as a **miss**, so a future on-disk format change auto-invalidates stale entries (mirrors `prompt_version` in the key). |

## Caller obligations (the S11 runner)

- **Fingerprint the resolved params.** `decoding_fingerprint` MUST be computed over the *same* fully-resolved decoding params that are stored as `CachedGeneration.decoding_params` — the params S7 echoes on `CompletionResult.decoding_params` — not a separately hand-built dict, so the key and the stored regime cannot diverge (avoids a false miss on the next run).
- **Consistent param typing.** Supply decoding params with stable value types across runs (e.g. always `0.0`, not `0`) so a byte-identical regime yields a byte-identical fingerprint (see K-3).
- **Write only on success.** Call `put` solely for a successful generation; the type prevents storing a failure, but the runner owns the lookup-before-call and success decision.

## Non-goals (contract explicitly excludes)

- Calling the provider or wrapping S7 (the client stays cache-unaware).
- Lookup-before-call orchestration and writing `GenerationRecord` / JSONL (runner, S11+).
- Cost accounting / budget guard (S10).
- Patch extraction of the cached text (S8 runs after retrieval, in the runner).
- Distributed/shared cache, eviction, or TTL.
