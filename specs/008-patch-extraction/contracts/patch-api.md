# Contract: `hecate.generation` patch-extraction API

Public surface re-exported from `hecate.generation`, consumed by the S11 runner.
Signatures are the contract; bodies are defined in implementation. Structural
acceptance/rejection rules are defined **normatively** in
[`docs/contracts/patch-format.md`](../../../docs/contracts/patch-format.md); this
file specifies only the callable surface and its behavioral guarantees.

## Types

```python
@dataclass(frozen=True)
class ExtractionResult:
    raw_response: str
    patch_parse_ok: bool
    extracted_patch: str | None
    reason: str | None = None   # diagnostic only; not a GenerationRecord field
```

## Function

```python
def extract_patch(raw_response: str) -> ExtractionResult: ...
```

Pure, synchronous, offline. One `str` in, one `ExtractionResult` out.

## Behavioral contract

| ID | Guarantee |
|----|-----------|
| P-1 | Given a raw response containing exactly one validating unified-diff candidate (plain, or inside one Markdown fence), returns `patch_parse_ok=True` with `extracted_patch` set to the wrapper-free diff. |
| P-2 | `extracted_patch` on success is a **byte-exact** slice of `raw_response` with only the recognized wrapper (one Markdown code fence) and surrounding prose removed — file paths, metadata, hunk content, line-ending sequences, and final-newline state are unchanged (FR-006/007). |
| P-3 | The single recognized wrapper is one Markdown code fence (` ``` ` or `~~~`); its info string (e.g. `diff`, `patch`) is part of the removed wrapper and does not affect acceptance. No other wrapper is stripped. |
| P-4 | A multi-file patch inside one contiguous candidate region is preserved whole, files in original order (FR-005). |
| P-5 | Structural validity is decided per `docs/contracts/patch-format.md` (via `unidiff`): a candidate must contain ≥1 file change with ≥1 complete hunk. Content is never repaired (FR-004/006). |
| P-6 | Empty, whitespace-only, non-diff, malformed, truncated, or BOM-corrupted input returns `patch_parse_ok=False`, `extracted_patch=None`, and never raises (FR-008). |
| P-7 | Input with >1 validating candidate region (multiple fenced diffs, or multiple separate unfenced regions) returns `patch_parse_ok=False` with `reason="ambiguous"` — it fails closed and does not choose a candidate (FR-011). |
| P-8 | On every failure, `extracted_patch is None` and `reason` is one of `{empty, no_diff_found, invalid_structure, ambiguous}`; no partial or fabricated patch is returned (FR-009). |
| P-9 | `result.raw_response` equals the input byte-for-byte in all cases, success or failure (FR-010). |
| P-10 | `extract_patch` is deterministic and pure: identical input → identical result; no network, credential, file, clock, or randomness (FR-013). |
| P-11 | `ExtractionResult` is frozen (immutable). |

## Public surface

`hecate.generation.__init__` additionally re-exports:

```python
from .patch import ExtractionResult, extract_patch
```

added to `__all__` alongside the existing S7 exports.

## Non-goals (contract explicitly excludes)

- Applying patches or running tests (Stage 2 / E-M3).
- Building/writing `GenerationRecord` or JSONL (runner, S11+) — this returns a result; the runner persists it.
- Persisting `reason` (record schema is unchanged).
- Selecting among multiple candidates, or repairing malformed diffs.
- Prompt construction or model calls (S6/S7).
