# Data Model: Patch Extraction and Normalization (S8)

This feature introduces one in-memory result type and maps it onto the **existing**
`GenerationRecord` fields. No record-schema change is made.

## Entity: `ExtractionResult`

The outcome of `extract_patch(raw_response)`.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ExtractionResult:
    raw_response: str            # the input, byte-for-byte (never mutated)
    patch_parse_ok: bool         # True iff exactly one candidate validated
    extracted_patch: str | None  # wrapper-free, byte-exact diff on success; None on failure
    reason: str | None = None    # diagnostic on failure ("empty" | "no_diff_found"
                                 #   | "invalid_structure" | "ambiguous"); None on success.
                                 #   In-memory only — NOT persisted to GenerationRecord.
```

**Invariants** (enforced by construction; asserted in tests):

- `patch_parse_ok is True` ⟹ `extracted_patch is not None` **and** `reason is None`.
- `patch_parse_ok is False` ⟹ `extracted_patch is None` **and** `reason is not None`.
- `result.raw_response == input` byte-for-byte in **every** case (success or failure).
- On success, `extracted_patch` is a substring-derived slice of `raw_response` with
  only wrapper/prose removed — no added, removed, or altered interior bytes.
- Frozen: results are immutable, reinforcing "never mutate raw output".

## Field: `reason` value set

Closed set (from research D4). Stable string literals so tests and later behavioral
analysis can rely on them:

| value | meaning |
|-------|---------|
| `empty` | input empty or whitespace-only |
| `no_diff_found` | no fenced/unfenced region validated as a diff |
| `invalid_structure` | the single candidate failed structural validation |
| `ambiguous` | more than one validating candidate region (fail closed) |

## Mapping onto `GenerationRecord` (existing schema, `src/hecate/data/records.py`)

The S11 runner (not this feature) copies an `ExtractionResult` onto a record:

| `GenerationRecord` field | source | notes |
|--------------------------|--------|-------|
| `raw_response` | `result.raw_response` | already the verbatim S7 `text`; unchanged |
| `extracted_patch` | `result.extracted_patch` | `str` on success, `None` on failure |
| `patch_parse_ok` | `result.patch_parse_ok` | `bool` |

`ExtractionResult.reason` has **no** target field — it is intentionally not
persisted (the record schema was frozen in S3 with exactly these three patch
fields; adding a `parse_reason` column is a future, out-of-scope schema decision).

## Entity: Patch candidate (internal, not exported)

A transient value used during detection: a contiguous region of `raw_response`
(fenced interior or unfenced run) plus its char offsets, before structural
validation. Not part of the public API; documented here only to fix terminology
shared with `docs/contracts/patch-format.md`.

## Non-entities (explicitly not modeled here)

- No persisted store, cache, or file. Extraction is a pure function.
- No change to `GenerationRecord`, its serialization, or JSONL I/O.
- No Stage-2 apply state (`patch_applied`, `fail_to_pass`, `pass_to_pass`) — those
  remain the untouched Stage-2 placeholders.
