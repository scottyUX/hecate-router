# Feature Specification: Stage-1 Prompt Template

**Feature Branch**: `006-prompt-template`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "S6 · Prompt template (GitHub issue #6): Build the Stage-1 prompt template that turns issue text + file context into one frozen, versioned instruction string asking the model for a single unified diff. Shared across all models; single-shot v1; no gold patch in the prompt. Depends on S5 ContextBundle."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Render a fix-request prompt from task + context (Priority: P1)

A Stage-1 pipeline operator (or automated runner) has a SWE-bench Lite task and a file-context bundle for that task. They need one complete instruction string that presents the issue and relevant file contents and asks for a single unified-diff fix — so later steps can call any model with the same prompt.

**Why this priority**: Without a rendered prompt, generation (S7), patch extraction (S8), and the Stage-1 runner cannot proceed. This is the core deliverable of S6.

**Independent Test**: Given one Lite instance and a context bundle for it, call the prompt renderer and confirm a non-empty instruction string that includes the issue text, each provided file path and contents, and clear instructions to return one unified diff.

**Acceptance Scenarios**:

1. **Given** a SWE-bench Lite task and a context bundle with one or more files, **When** the prompt is rendered, **Then** the result is a single string containing the problem statement, each file’s path and contents, and instructions to respond with one unified diff only.
2. **Given** the same task and same context bundle, **When** the prompt is rendered twice (including as if for different models), **Then** both renders are byte-identical.
3. **Given** a task whose gold solution patch is available on the task record, **When** the prompt is rendered from that task and its context bundle, **Then** the gold patch text does not appear in the rendered prompt.

---

### User Story 2 - Freeze and version the template for reproducibility (Priority: P1)

Operators need every run to record which prompt wording was used so results are comparable and cache keys (S9) can include prompt identity. Changing wording accidentally across runs must be detectable.

**Why this priority**: Reproducibility and shared-scaffold invariants require an explicit, stable prompt version (or equivalent content identity) tied to the template.

**Independent Test**: Inspect the rendered prompt path or associated metadata for an explicit version identifier; re-render with the same inputs and confirm the version and prompt body remain stable.

**Acceptance Scenarios**:

1. **Given** the prompt template in its frozen form, **When** a prompt is rendered, **Then** a documented prompt version string (or content hash of the template/prompt) is available to record with the run.
2. **Given** fixed task + context inputs, **When** renders are produced on different days without intentional template changes, **Then** the rendered prompt bytes and version identity remain the same.

---

### User Story 3 - Support hashing / optional persistence for records and cache (Priority: P2)

Downstream generation records and cache layers need a stable content hash of the prompt, and optionally a reference to a stored full prompt rather than embedding huge strings everywhere.

**Why this priority**: Aligns with existing generation-record fields (`prompt`, `prompt_hash`, `prompt_ref`) and unblocks S9 caching; not required to demonstrate a correct render, but needed for clean Stage-1 plumbing.

**Independent Test**: Hash the same prompt twice and get the same digest; optionally write a prompt to the project’s cache/output area and obtain a reusable reference string.

**Acceptance Scenarios**:

1. **Given** a rendered prompt string, **When** a content hash is computed, **Then** the same string always yields the same hash.
2. **Given** a rendered prompt string and a request to persist it, **When** the prompt is written to the designated cache or outputs location, **Then** a `prompt_ref` (path or identifier) is returned that can later locate that prompt.

---

### Edge Cases

- Context bundle with zero files: prompt still renders with issue text and instructions; file section is empty or explicitly indicates no files.
- Very large file contents: full contents are included as provided by the context builder (no silent truncation in S6); size limits remain an S5/config concern.
- Special characters, backticks, or diff-like text inside issue or file contents: included verbatim without being treated as the model’s answer format.
- Missing or empty `problem_statement`: render still produces a deterministic string; empty issue body is allowed as input (invalid tasks are upstream).
- Optional metadata (`repo`, `instance_id`): may appear in the prompt when useful for the model; must remain minimal and must never include the gold patch or other solution leakage.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST render one prompt string from a SWE-bench Lite task’s issue text and a Stage-1 context bundle’s file paths and contents.
- **FR-002**: The rendered prompt MUST instruct the model to produce a single unified diff that applies the fix, with no multi-turn or tool-loop interaction in v1.
- **FR-003**: The same task + same context MUST produce identical prompt bytes for every model in a run (shared scaffold; model identity is not an input to rendering).
- **FR-004**: The prompt template wording MUST be frozen and versioned (explicit version string and/or content hash) so runs can record prompt identity for reproducibility and caching.
- **FR-005**: The rendered prompt MUST NOT include the gold solution patch (or equivalent solution text from the task record). Context may localize *which* files to include; contents MUST be pre-fix (base-commit) contents from the context bundle.
- **FR-006**: System MUST expose a deterministic render entry point usable by the Stage-1 pipeline (task + context → prompt string).
- **FR-007**: System MUST provide a content-hash helper for a prompt string suitable for generation-record and cache keys.
- **FR-008**: System MAY optionally persist the full prompt under the project’s cache or outputs area and return a reference for `prompt_ref`.
- **FR-009**: Minimal task metadata (e.g. repository name, instance id) MAY be included in the prompt; such metadata MUST NOT expand into solution leakage.
- **FR-010**: Automated tests MUST cover: at least one real Lite instance render; determinism (same inputs → same string); and assertion that gold patch text is not injected into the prompt.

### Key Entities

- **Task (issue text)**: A SWE-bench Lite instance providing the problem statement and identity metadata; gold patch exists on the record but is for evaluation/oracle file selection only, not for the prompt body.
- **Context bundle**: Ordered file context for one task (paths + base-commit contents) produced by the Stage-1 context builder (S5); identical across models for a given run configuration.
- **Rendered prompt**: The single frozen instruction string passed to the model call step; later stored on the generation record as prompt text and/or hash/ref.
- **Prompt version**: Stable identifier of the template wording used for a render, recorded with the run for reproducibility and cache keying.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any Lite instance that has a context bundle, operators can produce a complete fix-request prompt in one render step without manual editing.
- **SC-002**: 100% of repeated renders with identical task and context inputs yield byte-identical prompt strings (including across intended model targets).
- **SC-003**: In test coverage for a real Lite instance, the gold patch text never appears in the rendered prompt.
- **SC-004**: Every render is associated with an explicit prompt version (or equivalent template identity) that remains stable until the template is intentionally changed.
- **SC-005**: Downstream stages can rely on the prompt asking for exactly one unified-diff response (single-shot), matching the expected extractable format for the patch-parse step.

## Assumptions

- S5 context builder is available and supplies `ContextBundle` / file contents at `base_commit` (issue #5 is closed).
- Oracle vs BM25 file selection is out of scope; S6 consumes whatever context method the run already chose.
- HTTP/model client (S7), diff extraction (S8), cache key design details (S9), and JSONL generation runs (S11+) are out of scope.
- One shared template for the whole Stage-1 run; per-model prompt variants are explicitly out of scope for v1.
- Optional prompt persistence uses existing project conventions under `data/cache/` or `data/outputs/` when implemented.
- Exact English wording of the template may be chosen during implementation once, then frozen under a version id (e.g. `v1`); wording quality is secondary to freeze/version/determinism and “no gold patch” invariants.
