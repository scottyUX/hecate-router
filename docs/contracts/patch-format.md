# Cross-Stage Patch-Format Contract

**Status: PROVISIONAL** — ratified against `git apply` / `unidiff` semantics as a
proxy for the Stage-2 apply feature. To be confirmed or amended (per the
constitution's amendment process) when **E-M3 · Execution & labels** (issue #17) is
specced. Consumers MUST treat the normalized-output section as stable enough to
build against, and flag any Stage-2 apply mismatch as a contract defect.

**Owners / consumers**: produced by **S8** (patch extraction, issue #8); consumed
by **S8** and by the future **Stage-2 apply** step (E-M3). This is the single
normative definition of accepted inputs and normalized output shared by both
stages. Feature-local contracts reference this file rather than restating its rules.

---

## 1. Scope

Defines, for one model response:

1. what raw shapes are **accepted** as containing a unified diff,
2. how the diff is **normalized** (what is removed, what is preserved), and
3. what shapes are **rejected** (fail closed), and how.

It does **not** define patch application, test execution, or record persistence.

## 2. Accepted input shapes

A response is accepted iff it contains **exactly one** validating *candidate region*
(§4). A candidate region is one of:

- **Fenced**: the interior of a single Markdown code fence — an opening fence line
  whose content is a bare fence marker (` ``` ` or `~~~`), optionally followed by an
  info string such as `diff` or `patch`, through the matching closing fence of the
  same marker. A fence delimiter (open or close) is recognized **only** on a line that
  does **not** begin with a diff-body prefix (` `, `+`, or `-`); a fence marker carried
  inside a hunk body — on a space-prefixed context line, or on an added/removed line —
  is diff content, not a delimiter (see §7).
- **Unfenced**: a maximal contiguous run of unified-diff lines (§4.2) not enclosed
  in a fence.

Arbitrary prose may appear before and/or after the one candidate region; it is
never part of the extracted patch.

## 3. Recognized wrappers (exhaustive)

The **only** recognized wrapper is **one Markdown code fence** (` ``` ` or `~~~`),
including its info string. No other decoration (HTML tags, blockquote `>` markers,
numbered-list prefixes, "Here is the patch:" prose) is stripped — if such decoration
is glued into the diff lines so they no longer match §4.2, the region simply does
not validate and the response is rejected. Extraction removes wrappers; it never
rewrites diff content.

## 4. Structural validity

### 4.1 Validator

A candidate region is **structurally valid** iff `unidiff.PatchSet` parses it into
**≥1 file change**, each retained file containing **≥1 complete hunk** (a well-formed
`@@ -a,b +c,d @@` header followed by its hunk body). Validation may operate on a
newline-coerced copy; the **emitted** patch is always the original bytes (§5).

### 4.2 Unified-diff line grammar (for unfenced region detection)

A *diff line* is any of:

- header: `diff --git `, `index `, `--- `, `+++ `, `old mode `, `new mode `,
  `deleted file mode `, `new file mode `, `similarity index `, `rename from `,
  `rename to `, `copy from `, `copy to `
- hunk header: `@@ ` … ` @@` (optionally trailed by a section heading)
- hunk body: a line beginning with a single ` ` (space), `+`, or `-`
- the marker `\ No newline at end of file`

A region **starts** at the first line matching `diff --git `, `--- `, or `Index: `.
**Membership is decided by prefix precedence:** any line beginning with a single ` `
(space), `+`, or `-` (or the `\ No newline at end of file` marker) **is** a hunk-body
diff line and **continues** the region — this **includes a blank context line**, which
a unified diff encodes as a single space followed by an empty/whitespace remainder
(`" \n"`) and which is therefore **never** a boundary. The region **ends only** at the
first line that is not a diff line: a truly empty (zero-width) line, or a prose line
with no diff prefix. `/dev/null` headers for added/deleted files are valid. Optional
`diff --git`/`index`/mode/similarity/rename metadata is accepted.

## 5. Normalized output (what a consumer receives on success)

On acceptance, the normalized patch is the candidate region with **only** the
wrapper (§3) and surrounding prose removed. Everything between the first and last
diff line is **byte-for-byte identical** to the input, specifically preserving:

- file paths and their order (including non-ASCII paths),
- all header/metadata lines and hunk content,
- every line-ending sequence exactly (LF, CRLF, or mixed — never re-encoded), and
- the presence or absence of a final newline.

A consumer (Stage 2) MUST be able to feed the normalized output to `git apply`
without any further wrapper removal or line-ending normalization (SC-006).

## 6. Rejection rules (fail closed)

The response is rejected — no patch, non-fatal — in these cases:

| condition | classification |
|-----------|----------------|
| empty or whitespace-only input | reject (`empty`) |
| leading BOM / decoration that breaks the first diff marker | reject (`empty`/`no_diff_found`) |
| no fenced or unfenced region validates (§4) | reject (`no_diff_found`) |
| the single candidate region fails structural validation (bad header, truncated hunk, no complete hunk) | reject (`invalid_structure`) |
| **more than one** validating candidate region (multiple fenced diffs, or ≥2 separate unfenced regions) | reject (`ambiguous`) — never choose one |

Rejection is data, not an error: the raw response is retained unchanged and no
patch is fabricated or partially accepted.

## 7. Edge cases (normative examples)

- Diff-looking or fence-looking text **inside** a hunk body (carried by a ` `/`+`/`-`
  prefix) does not start a second region or close a fence.
- Empty fenced blocks, unmatched fences, and nested fences do not yield a candidate.
- A valid patch preceded/followed by arbitrary prose is accepted; the prose is
  excluded.
- Non-ASCII file paths and content are preserved exactly.
- Mixed LF/CRLF within one candidate is preserved as-is (not unified).

## 8. Compatibility notes (provisional ratification basis)

The rules above are chosen so a normalized patch is directly consumable by
`git apply` and structurally valid under `unidiff>=0.7`, and so they align with the
S6 prompt (which asks each model for exactly one unified diff) and the existing
`GenerationRecord` patch fields (`raw_response`, `extracted_patch`, `patch_parse_ok`).

**Line-ending caveat:** the emitted patch preserves the candidate's *original* line
endings (§5); S8 may validate on a newline-normalized copy, so the "valid under
`unidiff`" property is asserted for that normalized form. A consumer that re-parses a
CRLF or mixed-ending patch afresh may need to apply the same newline handling before
`unidiff` will accept it — `git apply` itself tolerates these endings.

When E-M3 is specced, verify a corpus of normalized outputs applies cleanly in the
Stage-2 Docker harness and amend §5/§6 if any mismatch surfaces.
