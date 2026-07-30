# Feature Specification: Caching Layer

**Feature Branch**: `009-caching-layer`

**Created**: 2026-07-30

**Status**: Draft (QA findings addressed)

**Input**: GitHub issue #9, "S9 · Caching layer"

## User Scenarios & Testing

### User Story 1 - Skip completed generations on re-run (Priority: P1)

A Stage-1 operator re-runs a sweep or resumes after interruption. For every
generation identity that already finished successfully, the run must reuse the
stored outcome instead of calling the provider again.

**Why this priority**: Accidental re-runs are the primary budget risk. The Stage-1
target (~$38) depends on zero duplicate API calls for work already done.

**Independent Test**: Complete one successful generation, then request the same
identity again; confirm the second request returns the cached outcome and
performs zero provider calls (verified by an injectable call counter or transport
mock).

**Acceptance Scenarios**:

1. **Given** a successfully completed generation for one cache identity, **When**
   the same identity is requested again, **Then** the cached outcome is returned
   and no provider call is made.
2. **Given** a sweep with 10 successfully completed identities, **When** the
   sweep is re-run with caching enabled, **Then** all 10 are served from cache
   with zero new provider calls for those identities.
3. **Given** a cache hit, **When** the outcome is consumed, **Then** it includes
   enough fields to populate a generation record (generated text and token usage)
   without a live call.
4. **Given** a provider error, timeout exhaustion, or malformed response for an
   identity, **When** that outcome is considered for caching, **Then** it is
   **not** stored as a hit, and a later re-run may call the provider again.

---

### User Story 2 - Survive crashes and restarts (Priority: P1)

A long sweep may stop mid-run because of a crash, operator interrupt, or machine
restart. Cached completions must remain on disk so a later process can resume
without repeating finished work.

**Why this priority**: Restarts are expected during pilot and full sweeps. An
in-memory-only cache would silently re-spend on every restart.

**Independent Test**: Write one cache entry, terminate the process, start a new
process with the same cache directory, and confirm the entry is still readable.

**Acceptance Scenarios**:

1. **Given** a cache entry written to the project's cache area, **When** the
   process exits and a new process starts, **Then** the entry is still present and
   retrievable by the same cache key.
2. **Given** a partially written entry interrupted mid-save, **When** a reader
   looks up that key, **Then** it treats the entry as a miss (not a corrupt hit)
   so the runner can safely re-fetch.

---

### User Story 3 - Key by full generation identity (Priority: P1)

Operators must not get a cache hit when any dimension of the generation identity
changes. The cache is cross-run and on disk, so the key must bind every factor
that would make two generations non-comparable: task instance, model, prompt
content, prompt-template version, and decoding regime.

**Why this priority**: A wrong cache hit would poison the counterfactual matrix
(shared-scaffold fairness) or silently reuse a response produced under different
prompt wording or decoding settings.

**Independent Test**: Store an entry for identity A; request identity B where only
one key dimension differs; confirm B is a miss.

**Acceptance Scenarios**:

1. **Given** a cached entry, **When** only `prompt_hash` differs, **Then** the
   lookup is a miss.
2. **Given** a cached entry, **When** only `model_slug` differs, **Then** the
   lookup is a miss.
3. **Given** a cached entry, **When** only `instance_id` differs, **Then** the
   lookup is a miss.
4. **Given** a cached entry, **When** only `prompt_version` differs, **Then** the
   lookup is a miss.
5. **Given** a cached entry, **When** only the decoding-params fingerprint
   differs (e.g. temperature or max tokens changed), **Then** the lookup is a
   miss.
6. **Given** identical key inputs, **When** a cache key is computed twice,
   **Then** the key is identical (deterministic).

---

### User Story 4 - Explicit cache control for operators (Priority: P2)

An operator may need to force fresh provider calls (e.g. for debugging). The
cache layer must support bypassing reads while still allowing writes of
successful outcomes.

**Why this priority**: Supports controlled re-generation without deleting the
cache tree by hand; secondary to the default "always reuse when present" behavior.

**Independent Test**: Populate cache, run with read-bypass enabled, confirm
lookups miss and a successful new outcome can still be written.

**Acceptance Scenarios**:

1. **Given** a populated cache entry, **When** a lookup runs with read-bypass
   enabled, **Then** the lookup behaves as a miss even though an entry exists.
2. **Given** read-bypass is off (default), **When** a populated entry exists,
   **Then** lookups use the cache normally.

### Edge Cases

- Empty or missing cache directory on first run — treated as all misses; directory
  is created on first write.
- Corrupt or schema-invalid cache files — treated as misses (never crash the run).
- Concurrent writers to the same key — last completed atomic write of a
  **successful** outcome wins; partial writes never surface as hits.
- Very large raw responses — stored verbatim; no truncation.
- Cache entries are local to the machine/repo workspace under the project's
  gitignored cache area; not committed to git.
- Changing decoding parameters between runs with the same cache tree must miss
  (key includes a decoding fingerprint), not serve a stale hit from the prior
  decoding regime.
- A byte-identical rendered prompt under a different declared prompt-template
  version must miss (key includes prompt version).

## Requirements

### Functional Requirements

- **FR-001**: System MUST define a cache key from
  `(instance_id, model_slug, prompt_hash, prompt_version, decoding_fingerprint)`
  where `prompt_hash` is the content hash of the rendered prompt (S6),
  `prompt_version` is the declared prompt-template version identity (S6), and
  `decoding_fingerprint` uniquely identifies the decoding parameters that would
  be sent with the call (so a change in temperature, max tokens, or other
  decoding fields yields a different key).
- **FR-002**: System MUST persist cache entries on disk under the project's
  gitignored cache area so they survive process restarts.
- **FR-003**: System MUST return a cache hit for an existing key without invoking
  the provider.
- **FR-004**: System MUST return a cache miss when no valid entry exists for the
  key.
- **FR-005**: System MUST store, at minimum, the generated text and token usage
  fields needed to populate `GenerationRecord` (`raw_response`, `prompt_tokens`,
  `completion_tokens`) plus the decoding parameters used for the call.
- **FR-006**: System MUST write entries atomically so interrupted writes never
  produce readable hits.
- **FR-007**: System MUST treat corrupt or unreadable cache files as misses.
- **FR-008**: System MUST support an optional read-bypass mode for forced
  re-generation.
- **FR-009**: Cache key computation MUST be deterministic: identical key inputs
  always yield the same key.
- **FR-010**: Automated tests MUST verify cache hit/miss behavior, key
  discrimination (including prompt version and decoding fingerprint), restart
  survival, success-only writes, and atomic-write safety without live network
  access or provider spend.
- **FR-011**: System MUST persist a cache hit **only** for a successful
  generation outcome (usable generated text suitable to record as
  `raw_response`). Provider failures, exhausted retries, and malformed responses
  MUST NOT be written as cache hits.

### Key Entities

- **Cache key**: Stable identifier for one generation identity —
  `(instance_id, model_slug, prompt_hash, prompt_version, decoding_fingerprint)`.
- **Cache entry**: Persisted **successful** provider outcome for one key —
  generated text, token counts, decoding parameters, and metadata sufficient to
  rebuild the generation portion of a record.
- **Cache store**: The on-disk collection of entries under the project's
  gitignored cache area, managed by the caching module.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Re-running a successfully completed generation identity performs
  zero provider API calls (100% cache-hit rate on repeated successful work).
- **SC-002**: After a simulated process restart, 100% of previously written valid
  entries are retrievable.
- **SC-003**: Changing any one of `{instance_id, model_slug, prompt_hash,
  prompt_version, decoding_fingerprint}` produces a miss 100% of the time in
  tests.
- **SC-004**: Interrupted/partial writes produce misses 100% of the time (never
  corrupt hits).
- **SC-005**: Full test suite passes offline with no `OPENROUTER_API_KEY` and no
  network access.
- **SC-006**: In tests, provider-failure and malformed-response outcomes are never
  retrievable as cache hits (0% of failure outcomes become hits).
- **SC-007**: With read-bypass enabled, lookups miss 100% of the time even when a
  valid entry exists for that key.

## Assumptions

- `prompt_hash` comes from S6 and captures rendered prompt bytes; content changes
  invalidate via hash. `prompt_version` is still required in the key so a
  declared template-version bump invalidates even if rendered bytes happen to
  match.
- Decoding parameters are uniform across models for a given run (constitution
  VII). Because the cache is cross-run, their fingerprint is part of the key so
  a later run with different decoding settings cannot hit earlier entries.
- The OpenRouter client (S7) remains cache-unaware; the runner (S11+) orchestrates
  lookup-before-call and only writes on success. This feature delivers the cache
  module and the success-only write rule.
- Patch extraction (S8) runs after cache retrieval in the runner; the cache stores
  the raw provider text, not extracted patches.
- Exact on-disk path layout under the gitignored cache area is a planning
  decision; this spec requires only persistence under that area.

## Dependencies

- **S3** (merged): `GenerationRecord` schema and instance identifiers.
- **S6** (merged): `prompt_hash` helper, `PROMPT_VERSION`, and frozen prompt
  rendering.
- **S7** (merged): successful completion field shapes inform cached payload
  contents (consumer only; client unchanged).

## Out of Scope

- Cost accounting and budget guard (S10).
- Run orchestration / JSONL runner (S11+), except that the success-only write
  rule and key dimensions defined here bind that future runner.
- Distributed or shared cache across machines.
- Cache eviction/TTL policies (entries persist until manually removed or key
  dimensions change).
- Caching patch extraction results separately from raw responses.

## Process note (for implementers)

Branch `009-caching-layer` was cut from the #8 tip. Before implementation,
rebase onto `dev` (especially after PR #32 merges) so #9 is not coupled to
unmerged #8 work.
