# Research: Caching Layer (S9)

Phase 0 decisions. Each resolves a spec unknown into a concrete, testable approach.
No new runtime dependencies (standard library only).

## D1 — JSON file per entry, keyed by a composite-hash filename

**Decision**: Persist each cache entry as one JSON file under
`data/cache/generations/`, with filename `{cache_key}.json` where `cache_key` is a
hex SHA-256 (D4). One key → one file.

**Rationale**: Offline, dependency-free, human-inspectable, O(1) keyed access, and
restart survival is automatic (the file is just there on the next process). Fits a
write-once-per-key workload (each generation identity is produced at most once).

**Alternatives rejected**: SQLite (adds a schema + connection + concurrency-lock
handling for no benefit here); a single append-only JSONL (readers must scan; writers
contend on one file).

## D2 — Atomic writes via temp file + `os.replace`

**Decision**: Write the entry to a temporary file in the same directory
(`{cache_key}.json.tmp-{unique}`), flush, then `os.replace(tmp, final)`. `os.replace`
is an atomic rename on the same filesystem (POSIX and Windows).

**Rationale**: A reader either sees the fully written file or no file at all — an
interrupted write leaves only an orphan temp file, never a readable partial hit
(FR-006, SC-004). Concurrent writers of the same successful outcome resolve to
"last completed rename wins" (spec edge case) with no lock files. Orphan temp files
from a crash are ignored by readers (they don't match `{key}.json`).

**Alternatives rejected**: advisory `flock` (more moving parts, platform-variable, no
gain for write-once-per-key).

## D3 — `decoding_fingerprint`: canonical-JSON SHA-256 of the decoding params

**Decision**: `decoding_fingerprint(decoding_params: dict) -> str` = hex SHA-256 of
the params serialized as **canonical JSON** — `json.dumps(params, sort_keys=True,
separators=(",", ":"), ensure_ascii=False)`. Deterministic and independent of dict
insertion order.

**Rationale**: FR-001 requires a change in temperature/max-tokens/etc. to change the
key; FR-009 requires determinism. Canonical JSON with sorted keys makes the
fingerprint depend only on the *values*, not on how the dict was built. The
fingerprint is computed over the params **as they will be sent** (post-config
resolution, matching what S7's `CompletionResult.decoding_params` echoes), so it
reflects the actual decoding regime.

**Edge note**: numeric type/format must be consistent across runs (e.g. always
`0.0`, not sometimes `0`). Since decoding params come from the single run config
(`configs/option_a.yaml`) via one resolution path, this holds; the contract records
the expectation so a future caller doesn't feed differently-typed params.

## D4 — `cache_key`: unambiguous composite of all five dimensions

**Decision**: `cache_key(instance_id, model_slug, prompt_hash, prompt_version,
decoding_fingerprint) -> str` = hex SHA-256 over a **canonical, unambiguous**
serialization of the 5-tuple (a JSON array of the five strings, not raw
concatenation).

**Rationale**: A naive `a + b + ...` concatenation would collide (`("ab","c")` vs
`("a","bc")`). Serializing as a JSON array delimits fields unambiguously, so
changing any single dimension changes the key (FR-001, US3.1–3.5, SC-003), and
identical inputs always produce the same key (FR-009, US3.6). `prompt_hash` and
`prompt_version` both feed the key (they are distinct: a byte-identical prompt under
a bumped template version must still miss — this is exactly the S6/S9 coupling the
spec closes, since `PROMPT_VERSION` is not embedded in the rendered prompt bytes).

**Alternatives rejected**: directory-per-dimension nesting (more filesystem surface;
discrimination is already guaranteed by hashing all dimensions into one key).

## D5 — Success-only writes enforced by type (FR-011)

**Decision**: The store's `put(key, entry: CachedGeneration)` accepts a
`CachedGeneration`, a frozen dataclass that represents **only** a successful outcome
(it requires usable `raw_response` text). There is no field or code path to persist a
provider failure, exhausted-retry, or malformed response. The runner constructs a
`CachedGeneration` and calls `put` **only** when the generation succeeded.

**Rationale**: Makes FR-011 / SC-006 structural rather than a rule the runner must
remember — a failure literally cannot be represented as an entry, so it can never be
served as a hit. A later re-run of a failed identity finds no entry and re-calls the
provider (US1.4).

## D6 — Read-bypass is a store flag (FR-008)

**Decision**: `GenerationCache(cache_dir=None, *, read_bypass=False)`. When
`read_bypass=True`, `get(key)` **always** returns `None` (miss), while `put` still
writes successful entries normally.

**Rationale**: FR-008 / US4 / SC-007 — an operator can force fresh provider calls
for debugging without deleting the cache tree, and freshly produced successful
outcomes are still recorded for later reuse.

## D7 — Corrupt / partial / missing → miss, never raise (FR-007)

**Decision**: `get(key)` returns `None` when: the file is absent; the JSON fails to
parse; or the parsed object is missing required entry fields (schema-invalid). It
never raises on a read. Orphan `*.tmp-*` files are never matched as entries.

**Rationale**: FR-007, SC-004, and the "corrupt cache files → miss, never crash"
edge case. The runner treats a miss as "re-fetch", so a damaged entry self-heals on
the next successful write.

## D8 — Determinism, purity, and I/O confinement

**Decision**: `cache_key` and `decoding_fingerprint` are pure functions (no I/O, no
clock, no randomness). The store's only side effects are reads/writes confined to its
`cache_dir`. Tests use a `tmp_path` cache dir; no global state.

**Rationale**: FR-009 determinism; Constitution III offline/zero-spend; makes the
whole suite reproducible and parallel-safe.
