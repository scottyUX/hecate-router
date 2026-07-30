# Research: Patch Extraction and Normalization (S8)

Phase 0 decisions. Each resolves an unknown in the spec into a concrete,
testable approach. No new runtime dependencies are introduced.

## D1 — Validate with `unidiff`, emit the raw substring

**Decision**: Use `unidiff.PatchSet` **only to decide** whether a candidate region
is a structurally complete unified diff. The value returned in
`extracted_patch` is the **exact substring** of `raw_response` (the candidate
region with wrappers/prose removed), never `unidiff`'s re-serialization.

**Rationale**: FR-006/FR-007 require byte-exact preservation of paths, hunks, line
endings, and final-newline state, and forbid repair. `unidiff` re-serialization
normalizes newlines and can add/drop a trailing newline — using it as the output
would violate the invariant. Using it as a pure validator gives us a battle-tested
unified-diff grammar (already a declared dependency) without touching the bytes we
emit.

**Alternatives rejected**: (a) hand-rolled diff grammar — reinvents `unidiff`,
higher bug surface; (b) emitting `unidiff` output — breaks byte-exactness.

## D2 — Candidate detection: fenced first, then unfenced, else none

**Decision**: Detect exactly one candidate region in this order:

1. **Fenced**: scan for Markdown code fences (a line whose first non-space run is
   ` ``` ` or `~~~`, optional info string, matched by a closing fence of the same
   marker). A fenced region whose interior validates as a diff (D1) is a candidate.
2. **Unfenced**: if there are no fenced diff candidates, scan for a maximal
   contiguous run of unified-diff lines (D3) that validates.
3. **None**: if neither yields a validating candidate, it is a parse failure (D4).

**Ambiguity (fail closed, FR-011)**: if step 1 finds **>1** fenced region whose
interior validates as a diff, or step 2 finds **>1** separate validating unfenced
region, the result is `patch_parse_ok=False` with reason `ambiguous`. We never pick
"the first" or "the biggest".

**Rationale**: S6 instructs models to emit one fenced diff, so fenced-first matches
the dominant real shape; unfenced is the defensive fallback. Failing closed on
multiple candidates is mandated by FR-011 and avoids silently biasing the dataset.

## D3 — Precise unfenced region boundary (resolves QA finding #3)

**Decision**: Region membership is decided **by line prefix first**. An **unfenced
diff region** begins at the first line matching a diff-start marker — `diff --git `,
`--- `, or `Index: ` — and extends through every subsequent **diff line**: a header
line (`diff --git`, `index `, `--- `, `+++ `, `old mode`, `new mode`,
`similarity index`, `rename from`, `rename to`, `deleted file mode`,
`new file mode`), a hunk header (`@@ ... @@`), a **hunk-body line** — any line
beginning with a single ` ` (space), `+`, or `-` — or the marker
`\ No newline at end of file`.

**Prefix precedence (this is the fix for QA finding #3):** a line beginning with a
single space, `+`, or `-` **is** a hunk-body diff line and **continues** the region,
*including a blank context line* — a unified diff encodes a blank source line as a
single space followed by an empty/whitespace remainder (e.g. `" \n"`), so such a line
is **never** a region boundary. The region **ends only** at the first line that is
**not** a diff line: a truly empty (zero-width) line, or a prose line carrying no diff
prefix. Two validating regions separated by ≥1 such boundary line are two candidates
→ ambiguous. This same prefix precedence governs fence detection (D2 / contract §2):
a fence marker carried on a space/`+`/`-`-prefixed line is diff content, not a fence
delimiter.

**Rationale**: makes "one contiguous region" and "prose" precise enough that two
engineers classify the same fixture identically (QA finding #3). Diff-looking text
*inside* a hunk body is carried by the `+`/`-`/` ` prefix, so it cannot start a
second region (spec edge case).

## D4 — Failure taxonomy (non-fatal, FR-008/009)

**Decision**: `extract_patch` never raises for bad input. Every non-success path
returns `patch_parse_ok=False`, `extracted_patch=None`, and a diagnostic `reason`:

| reason | trigger |
|--------|---------|
| `empty` | input is empty or whitespace-only (resolves QA finding #4) |
| `no_diff_found` | no fenced or unfenced region validates as a diff |
| `invalid_structure` | a lone candidate region fails `unidiff` validation (bad header, truncated hunk, no complete hunk) |
| `ambiguous` | >1 validating candidate region (FR-011) |

`reason` is an in-memory diagnostic for tests and behavioral analysis; it is **not**
a `GenerationRecord` field and is not persisted by this feature (the record stores
only `patch_parse_ok` + `extracted_patch` + `raw_response`). Persisting a failure
reason is a possible future schema addition, out of scope here.

## D5 — Byte-exact interior; wrappers only (FR-007)

**Decision**: Extraction removes only (a) the opening/closing fence lines and their
info string, and (b) prose before/after the candidate. Everything **between** the
candidate's first and last diff line is returned unchanged, including original line
endings (LF/CRLF/mixed) and the presence/absence of a final newline. Validation is
performed on a **copy** if `unidiff` needs newline coercion; the emitted bytes are
the original slice.

**Rationale**: directly implements FR-006/FR-007 and SC-004. The fence info string
(e.g. ` ```diff `, ` ```patch `) is part of the removed wrapper and does not affect
acceptance (resolves QA finding #1). The recognized-wrapper set is **exhaustively**
`{one Markdown code fence (``` or ~~~)}` — nothing else (e.g. HTML tags, quote
markers) is stripped (resolves QA finding #5).

## D6 — Encoding edge cases (resolves QA finding #4)

**Decision**: Input is treated as an already-decoded `str`. A leading UTF-8 BOM
(`﻿`) is treated as prose on the line it occupies: if it precedes the first
diff marker it is excluded with surrounding prose; if it is glued to the first
diff-start line such that the marker no longer matches, that region does not start
and the result is `no_diff_found`/`empty` as applicable. Whitespace-only input →
`empty`. Non-ASCII paths/content are preserved byte-for-byte (they are ordinary
diff-body/header bytes to the scanner).

## D7 — Determinism & purity (Constitution III/VII)

**Decision**: `extract_patch` is a pure function of its single `str` argument: no
I/O, no clock, no randomness, no reliance on dict iteration order or locale.
Identical input always yields an identical `ExtractionResult`. This is what makes
the offline fixture suite reproducible and keeps extraction model-neutral.

## D8 — Cross-stage contract status (provisional)

**Decision**: `docs/contracts/patch-format.md` is published now, **marked
provisional**: its normalized-output and acceptance rules are ratified against
`git apply` / `unidiff` semantics as a proxy for the not-yet-specced Stage-2 apply
feature (E-M3, issue #17). When E-M3 is specced, the contract is confirmed or
amended via the constitution's amendment process. S8 artifacts reference it rather
than duplicating its rules.

**Rationale**: issue #8 explicitly requires coordinating the patch format with
Stage 2 early; `git apply` is the concrete consumer Stage 2 will use, so validating
against it now is the best available proxy without blocking S8 on E-M3.
