# Feature Specification: Patch Extraction and Normalization

**Feature Branch**: `008-patch-extraction`

**Created**: 2026-07-18

**Status**: Draft

**Input**: GitHub issue #8, "S8 · Patch extraction & normalization"

## User Scenarios & Testing

### User Story 1 - Extract a usable patch (Priority: P1)

A Stage-1 operator has a raw model response that contains one valid unified
diff. They need the response converted into one stable patch representation
that a later execution stage can consume without model-specific cleanup.

**Why this priority**: A usable extracted patch is the primary outcome of S8.
Without it, generated responses cannot advance to execution-based evaluation.

**Independent Test**: Supply a plain valid unified diff and a valid diff inside
one Markdown fence; confirm both produce the same wrapper-free patch, marked as
parseable, without changing file paths, metadata, or hunks.

**Acceptance Scenarios**:

1. **Given** a raw response containing one plain valid unified diff, **When**
   extraction runs, **Then** it returns that diff in the shared normalized
   format and marks the result parseable.
2. **Given** a raw response containing one valid unified diff inside a Markdown
   code fence with optional prose outside the fence, **When** extraction runs,
   **Then** it removes the wrapper and prose, returns only the normalized diff,
   and marks the result parseable.
3. **Given** a valid multi-file patch, **When** extraction runs, **Then** every
   file change remains present and in its original order.
4. **Given** a valid add, delete, rename, or modification patch, **When**
   extraction runs, **Then** its paths, metadata, and hunks are semantically
   unchanged.

---

### User Story 2 - Record malformed model behavior safely (Priority: P1)

A Stage-1 operator receives output that is empty, ambiguous, or malformed. They
need the outcome recorded as a parse failure without crashing the run, losing
the original response, or inventing a patch.

**Why this priority**: Malformed responses are part of the comparative model
data. Dropping them would bias later labels, while raising a fatal error would
prevent collection of the full counterfactual matrix.

**Independent Test**: Supply empty text, prose-only text, invalid headers,
truncated hunks, and multiple patch candidates; confirm every case produces a
non-fatal parse failure, no extracted patch, and leaves the raw response
available unchanged for storage.

**Acceptance Scenarios**:

1. **Given** an empty or prose-only response, **When** extraction runs, **Then**
   it marks parsing unsuccessful and returns no extracted patch.
2. **Given** a response with malformed headers or a truncated hunk, **When**
   extraction runs, **Then** it marks parsing unsuccessful rather than
   repairing or partially accepting the patch.
3. **Given** a response containing multiple patch candidates, **When**
   extraction runs, **Then** it fails closed as ambiguous instead of choosing
   one candidate.
4. **Given** any unsuccessful extraction, **When** the generation outcome is
   recorded, **Then** the original raw response is retained byte-for-byte,
   `patch_parse_ok` is false, and `extracted_patch` is `None`/`null`.

---

### User Story 3 - Share one cross-stage patch contract (Priority: P2)

The Stage-1 extraction owner and the Stage-2 execution owner need one normative
definition of accepted inputs and normalized patch output so the two stages do
not silently diverge.

**Why this priority**: Extraction can be demonstrated independently first, but
its output is only useful if the execution stage can consume it without another
undocumented transformation.

**Independent Test**: Evaluate a shared fixture corpus against the published
patch-format contract and confirm every successful extraction satisfies that
contract while every rejected fixture is classified consistently.

**Acceptance Scenarios**:

1. **Given** the approved patch-format decisions, **When** the extraction and
   execution stages are designed, **Then** both reference the same shared
   normative contract.
2. **Given** a successful extraction, **When** its output is checked against the
   shared contract, **Then** no additional wrapper removal or line-ending
   normalization is required before patch application.

### Edge Cases

- Inputs may use LF, CRLF, or mixed line endings; extraction preserves the
  candidate region's line-ending bytes exactly.
- A successful output may omit its final newline; extraction preserves that
  state rather than adding or removing a newline.
- Valid patches may include optional `diff --git`, index, mode, similarity, and
  rename metadata.
- Added and deleted files may use `/dev/null` headers.
- Changed file content may itself contain diff-looking lines or Markdown fence
  markers; these do not create a second candidate.
- Empty fenced blocks, unmatched fences, nested fences, and multiple fenced or
  unfenced patch candidates fail closed.
- One candidate is one contiguous diff region: either the contents of one
  Markdown fence or one unfenced run of diff headers and hunks uninterrupted by
  prose or a fence boundary. Multiple file-change blocks inside that region are
  one multi-file candidate; two or more separate regions are ambiguous.
- Arbitrary prose may appear before or after one unambiguous patch candidate,
  but never inside the extracted patch.
- Inputs may contain non-ASCII file content and paths.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST accept a raw model-response string and identify
  exactly one unified-diff candidate when one is present. A candidate is one
  contiguous fenced or unfenced diff region; multiple file-change blocks within
  the same region form one multi-file candidate.
- **FR-002**: The system MUST accept a valid plain unified diff.
- **FR-003**: The system MUST accept a valid unified diff enclosed in one
  Markdown code fence and MUST exclude the fence and surrounding prose from the
  extracted patch.
- **FR-004**: The system MUST validate that a candidate contains at least one
  structurally valid file change with at least one complete hunk.
- **FR-005**: The system MUST support valid single-file and multi-file patches,
  including modifications, additions, deletions, and renames.
- **FR-006**: The system MUST preserve the order and semantics of file paths,
  patch metadata, and hunk content, including non-ASCII paths and content; it
  MUST NOT repair malformed patch content.
- **FR-007**: The system MUST preserve every line-ending sequence and the final
  newline state inside the extracted candidate exactly. Normalization is limited
  to removing content outside the candidate and MUST NOT reinterpret carriage
  returns as either document separators or hunk payload.
- **FR-008**: The system MUST return a non-fatal unsuccessful result for empty,
  non-diff, malformed, truncated, or ambiguous input.
- **FR-009**: An unsuccessful result MUST set `patch_parse_ok` to false and MUST
  set `extracted_patch` to `None`/`null` rather than returning partial or
  fabricated patch content.
- **FR-010**: The original `raw_response` MUST remain byte-for-byte available
  for storage regardless of extraction success or failure.
- **FR-011**: The system MUST classify an input with multiple patch candidates
  as ambiguous and fail closed rather than choosing a candidate.
- **FR-012**: This feature MUST publish accepted variants and normalized output
  in one normative cross-stage patch-format contract and MUST reference it from
  S8 extraction artifacts so the future Stage-2 patch-application feature can
  consume the same contract.
- **FR-013**: All extraction and validation behavior MUST be deterministically
  verifiable offline without a provider credential, network access, or spend.

### Key Entities

- **Raw response**: The verbatim text returned by one model call. It remains
  unchanged and is retained even when no patch can be extracted.
- **Patch candidate**: A contiguous region of the raw response that appears to
  contain one unified diff before structural validation.
- **Extraction result**: The outcome containing normalized patch text when
  successful and an explicit parse-success flag; unsuccessful outcomes contain
  no patch.
- **Shared patch-format contract**: The cross-stage definition of accepted
  wrappers, valid unified-diff structure, normalization, and rejection rules.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of valid fixtures in the approved corpus—including plain,
  fenced, single-file, multi-file, add, delete, rename, and modification
  patches—are extracted and marked parseable.
- **SC-002**: 100% of invalid or ambiguous fixtures—including empty,
  prose-only, malformed-header, truncated-hunk, and multiple-candidate
  responses—produce a non-fatal parse failure with `extracted_patch` set to
  `None`/`null`.
- **SC-003**: For every failure fixture, the stored raw response is byte-for-byte
  identical to the supplied input.
- **SC-004**: For every success fixture, paths, file ordering, metadata, and hunk
  content—including line endings and final-newline state—are unchanged; only
  documented wrappers and surrounding prose are removed.
- **SC-005**: The full acceptance fixture suite passes with network access and
  provider credentials absent, incurring zero provider spend.
- **SC-006**: Every successful fixture conforms to the shared patch-format
  contract without additional cleanup before the Stage-2 application step.

## Assumptions

- S6's merged prompt asks every model to return one unified diff without
  explanations, but extraction remains defensive because model output may not
  comply.
- S7 supplies generated text as the raw extraction input; orchestration that
  copies it into a generation record is handled by a later feature.
- Existing generation records already provide `raw_response`,
  `extracted_patch`, and `patch_parse_ok`; this feature does not redesign the
  record schema.
- Exactly one patch candidate is required. Ambiguous responses fail closed.
- Multiple file-change blocks in one contiguous diff region are one multi-file
  candidate; separate fenced or unfenced regions are multiple candidates.
- Recognized wrappers may be removed, but malformed patch content is never
  repaired.
- Patch application, test execution, orchestration, caching, and cost accounting
  remain out of scope.
