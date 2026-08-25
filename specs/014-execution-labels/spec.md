# Feature Specification: Execution Harness and Routing Labels

**Feature Branch**: `014-execution-labels`

**Created**: 2026-08-20

**Status**: Draft

**Input**: GitHub issue #17 (E-M3 · Execution & labels) plus the Stage-4 pre-flight requirements from issue #18. Unblock first router training by applying generated patches, running project tests, and deriving execution-grounded routing labels.

## User Scenarios & Testing

### User Story 1 - Execute generated patches and record outcomes (Priority: P1)

An operator has a Stage-1 generation matrix (one attempted patch per task and model). They need each patch applied to the corresponding repository snapshot and evaluated against that task’s tests, with apply success, resolved status, and which tests passed written back onto every pair — without rewriting the original generation file.

**Why this priority**: Router training cannot start without execution outcomes. This story is the minimum path from patches to labels.

**Independent Test**: Feed a small generation JSONL (including at least one valid patch and one unparseable patch) through a harness stand-in that does not require live containers. Confirm a new execution run directory contains one output record per input pair, Stage-2 fields filled, and a run manifest.

**Acceptance Scenarios**:

1. **Given** a generation record with a structurally valid extracted patch, **When** execution runs, **Then** the output record has apply success, resolved status, and the lists of FAIL_TO_PASS / PASS_TO_PASS tests that passed, copied from the evaluation report.
2. **Given** a generation record with no extracted patch (parse failure or empty), **When** execution runs, **Then** the pair is not sent to the evaluator; the output record has apply success false, resolved false, and empty test lists.
3. **Given** a completed execution, **When** the original generation file is inspected, **Then** it is unchanged.

---

### User Story 2 - Preserve the full matrix and resume safely (Priority: P1)

Long evaluation runs stop. Operators restart the same output directory and must not drop failed pairs, must not re-run pairs that already have an execution outcome, and must refuse to start a full-matrix run if the input generations are missing any requested (task, model) pair.

**Why this priority**: Constitution requires a full counterfactual matrix. Interrupted Docker evals are expected.

**Independent Test**: Seed an output JSONL with one finished pair and an input matrix that omits a requested pair. Confirm resume skips the finished pair and that an incomplete input matrix fails closed before any evaluation.

**Acceptance Scenarios**:

1. **Given** an output record whose apply field is already true or false, **When** the same output directory is reused, **Then** that pair is not re-evaluated.
2. **Given** a requested set of tasks and models, **When** the input file is missing any of those pairs, **Then** execution refuses to start and reports the missing pairs.
3. **Given** a mix of valid and invalid patches, **When** the run finishes, **Then** the output JSONL contains exactly one record per input pair (no silent drops).

---

### User Story 3 - Construct routing labels and a training pre-flight report (Priority: P1)

Once execution outcomes exist for both the small (m1) and large (m2) models, the operator needs a binary label per task — whether m1 resolved it — plus a pre-flight report: shared-scaffold check, resolve rates, 2×2 complementarity, oracle-routing headroom versus always-m2, and a flag if the m1-positive rate is below about 15%.

**Why this priority**: Issue #18 blocks training until this report exists. Labels are the contract Stage 4 consumes.

**Independent Test**: Given a synthetic execution JSONL covering both models on several tasks, produce labels and pre-flight JSON and check the complementarity counts and headroom arithmetic.

**Acceptance Scenarios**:

1. **Given** execution records for m1 and m2 on the same task, **When** labels are built, **Then** the task is labeled m1-resolves only if m1’s patch applied and the evaluator marked the instance resolved; parse or apply failure is false.
2. **Given** a completed label run, **When** the pre-flight report is read, **Then** it includes shared-scaffold status, m1 and m2 resolve rates, counts for both / only-m1 / only-m2 / neither, oracle-routing resolve rate, always-m2 resolve rate, routing headroom (oracle minus always-m2), and the m1-positive rate with a low-rate flag.
3. **Given** two models on one task with different prompt hashes, **When** pre-flight runs, **Then** shared-scaffold is reported as failed for that task.

---

### Edge Cases

- Evaluator produces no report for a pair that was submitted (crash or timeout): leave apply/resolved unset so a later resume retries that pair.
- Patch applies but no tests_status is present: record apply from the report, resolved false, empty test lists.
- Input contains extra models beyond m1/m2: ignore them for labels; still execute if requested.
- Tasks present for only one model after execution: omit from label rows and list them as incomplete in pre-flight.
- Dry-run: validate config and matrix completeness, write a manifest annotated dry-run, and do not invoke the evaluator.

## Requirements

### Functional Requirements

- **FR-001**: Convert Stage-1 generation records into evaluator prediction files, one model per file, using instance id, model identity, and extracted patch text.
- **FR-002**: Invoke the SWE-bench Lite evaluation harness (or an injected stand-in) per model without reimplementing container apply/test logic.
- **FR-003**: Write execution outcomes to a new run directory; never mutate the Stage-1 generation file.
- **FR-004**: For every input pair, persist apply success, resolved status, FAIL_TO_PASS tests that passed, and PASS_TO_PASS tests that passed.
- **FR-005**: Pairs without a usable extracted patch skip evaluation and are recorded as not applied and not resolved.
- **FR-006**: Refuse to start when the input matrix is missing any requested (task, model) pair.
- **FR-007**: Resume by skipping pairs whose apply field is already true or false in the output JSONL.
- **FR-008**: Write a run manifest with timestamp, git commit, config snapshot, CLI overrides, evaluator version, docker namespace, Stage-1 run id, and per-model counts (evaluated, skipped-no-patch, resolved, pending-retry).
- **FR-009**: Offline automated tests MUST pass without Docker and without provider credentials.
- **FR-010**: Optional live evaluation is opt-in and skipped unless an explicit live-eval environment flag is set.
- **FR-011**: Derive a binary training label per task: m1 resolves if and only if the small-model patch applied and the instance is resolved.
- **FR-012**: Emit a pre-flight report with shared-scaffold check, m1/m2 resolve rates, 2×2 complementarity, oracle-routing minus always-m2 headroom, and an m1-positive-rate flag at a 15% threshold.
- **FR-013**: Evaluation logs MUST be written under the execution run directory, not the repository root.
- **FR-014**: Dry-run validates wiring and matrix completeness without starting containers.

### Key Entities

- **Generation record**: Stage-1 pair plus Stage-2 fields (apply, resolved, passing FAIL_TO_PASS tests, passing PASS_TO_PASS tests).
- **Prediction**: One evaluator input (instance id, model identity, patch text).
- **Evaluation report**: Per-instance apply/resolved/test-status payload produced by the harness.
- **Routing label**: Per-task m1/m2 resolve bits and complementarity bucket.
- **Pre-flight report**: Aggregate metrics that gate Stage-4 training.
- **Execution manifest**: Reproducibility snapshot for one execution or label run.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Operators can obtain execution outcomes for a requested matrix without altering Stage-1 artifacts.
- **SC-002**: 100% of input (task, model) pairs appear in the execution output; none are dropped because the patch failed to parse or apply.
- **SC-003**: An interrupted run can be resumed from the same output directory without re-evaluating pairs that already have apply true or false.
- **SC-004**: A missing pair in the input matrix is reported before any evaluation work starts.
- **SC-005**: From a completed two-model execution file, operators receive one label per complete task and a pre-flight report they can read without re-running tests.
- **SC-006**: The default automated test suite completes successfully on a machine with no container runtime and no cloud credentials.
- **SC-007**: A documented smoke path exists for one gold instance and one or two generated pairs when a container runtime is available.

## Assumptions

- Stage-1 sweep output for the Option A Qwen pair already exists and is the default input.
- v1 label scheme is binary “does the small model resolve?” as specified in issue #18; multiclass cheapest-resolver is deferred.
- m1 is the configured small-tier model (`qwen/qwen-2.5-7b-instruct`); m2 is the large-tier model (`qwen/qwen-2.5-72b-instruct`).
- Resolved means the evaluator’s full-resolution criterion (all FAIL_TO_PASS and all PASS_TO_PASS tests pass) after a successful apply.
- Full 600-pair Docker evaluation runs on an x86 host with sufficient disk (planned GCP VM); this feature ships the runner and offline tests even if that host is not used in the same session.
- S15 output-validation and S16 handoff remain separate issues; this feature only checks that the requested input matrix is complete.
- Patch text is never an input to the future router; this feature only stores it as already present on generation records.
