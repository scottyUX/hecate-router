# Quickstart: Patch Extraction (S8)

How to use and verify `extract_patch` — fully offline, zero provider spend.

## Use

```python
from hecate.generation import extract_patch

raw = "Here's the fix:\n```diff\n--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n-x = 1\n+x = 2\n para\n```\n"
result = extract_patch(raw)

result.patch_parse_ok   # True
result.extracted_patch  # "--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n-x = 1\n+x = 2\n para\n"
result.reason           # None
result.raw_response     # == raw, byte-for-byte
```

Failure is data, never an exception:

```python
bad = extract_patch("Sorry, I couldn't produce a patch.")
bad.patch_parse_ok      # False
bad.extracted_patch     # None
bad.reason              # "no_diff_found"
bad.raw_response        # == the input, unchanged
```

## The runner does the persistence (not this feature)

```python
# Illustrative — the S11 runner maps a result onto the existing record fields:
record.raw_response    = result.raw_response
record.extracted_patch = result.extracted_patch
record.patch_parse_ok  = result.patch_parse_ok
# result.reason is diagnostic only and is not persisted.
```

## Verify offline

```bash
# From the repo root, no OPENROUTER_API_KEY needed, no network:
python -m pytest tests/test_patch_extraction.py -v
```

The suite exercises the acceptance matrix from `spec.md` / the shared
`docs/contracts/patch-format.md`:

**Success fixtures** (→ `patch_parse_ok=True`, byte-exact):
- plain single-file diff; fenced diff (` ```diff ` and bare ` ``` `) with prose around it
- multi-file diff in one region (order preserved)
- add (`/dev/null` → file), delete (file → `/dev/null`), rename, modification
- non-ASCII paths/content; CRLF and mixed line endings; missing final newline
- **unfenced** diff whose hunk contains a blank context line (a single-space line) →
  still one region, `parse_ok=True` (regression guard for the region-boundary rule, DEF-1)
- a Markdown-file diff whose hunk body contains a ` ``` ` fence line → the inner fence
  does not close the outer fence; still one patch (regression guard, DEF-3)

**Failure fixtures** (→ `patch_parse_ok=False`, `extracted_patch=None`, raw preserved):
- empty / whitespace-only (`empty`), leading BOM, prose-only (`no_diff_found`)
- malformed header, truncated hunk, no complete hunk (`invalid_structure`)
- two fenced diffs, two separate unfenced regions (`ambiguous`)
- diff-looking text inside a hunk body (still one candidate → success, not a second region)

## Expected acceptance evidence

- `pytest tests/test_patch_extraction.py` passes with no credential/network (SC-005).
- Each success fixture round-trips byte-for-byte through `extracted_patch` (SC-004).
- Each failure fixture preserves `raw_response` byte-for-byte (SC-003).
- 100% of the valid corpus is `parse_ok=True`; 100% of the invalid/ambiguous corpus
  is `parse_ok=False` with `extracted_patch=None` (SC-001/002).
