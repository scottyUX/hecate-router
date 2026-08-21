# Feature Specification: Router Training v1 (semantic-only baseline)

**Feature Branch**: `015-router-training`

**Created**: 2026-08-20

**Status**: Draft

**Input**: GitHub issue #18 (E-M4 · Router training v1). Fine-tune a small text encoder to predict whether the weak model resolves a SWE-bench Lite task, using Stage-3 execution-grounded labels. v1 is a measurable floor; low Route-AUC is documented, not a stop.

## User Scenarios & Testing

### User Story 1 - Build a training dataset from labels (Priority: P1)

An operator has Stage-3 `labels.jsonl` plus the Stage-1 generation records those labels came from. They need one training row per complete task: router input text (issue + oracle file context, not the patch), binary `m1_resolves`, repo id, and a truncation flag.

**Why this priority**: Nothing else can train without a deterministic, leak-free dataset.

**Independent Test**: Synthetic labels + generation records (including one over-long prompt) produce rows whose text excludes patch content, labels match `resolved is True` on m1, and truncation is counted.

**Acceptance Scenarios**:

1. **Given** a complete m1/m2 label pair and the m1 generation prompt, **When** the dataset is built, **Then** the row text is derived from issue/oracle prompt text, the label is m1 `resolved is True`, and extracted patch text is not in the input.
2. **Given** a prompt that exceeds the 2048-token budget, **When** the dataset is built, **Then** the text is truncated and the row is marked truncated.
3. **Given** a task missing m1 or m2, **When** the dataset is built, **Then** that task is omitted (incomplete pairs are not trained on).

---

### User Story 2 - Cross-validate the encoder router (Priority: P1)

The operator trains `answerdotai/ModernBERT-base` with a binary head P(m1 resolves), using stratified 5-fold splits by label and repo and 3 seeds. Live Hugging Face downloads are opt-in; CI uses a fake encoder.

**Why this priority**: This is the v1 experiment: a trained score and a serve rule (m1 if score ≥ λ, else m2).

**Independent Test**: A fake encoder on synthetic labels runs 5 folds × 1 seed offline, writes a manifest, and never downloads weights.

**Acceptance Scenarios**:

1. **Given** enough examples in both classes, **When** training runs, **Then** each fold trains on the complement and scores the hold-out with the same seed recorded in the manifest.
2. **Given** too few m1-positives to stratify by label and repo, **When** training runs, **Then** it falls back to repo-only or unstratified folds, records the fallback, and still completes.
3. **Given** default pytest, **When** router tests run, **Then** they pass without torch/transformers downloads and without GPU.

---

### User Story 3 - Report Route-AUC against baselines (Priority: P1)

After CV, the operator needs Route-AUC versus always-m1, always-m2, random, and oracle-routing, plus go/no-go: Route-AUC > 0 on held-out folds. If not, document the floor and continue.

**Why this priority**: Issue #18 done-when is the comparison report, not a strong router.

**Independent Test**: Synthetic scores and m1/m2 resolve bits produce baseline rates and a Route-AUC that matches a hand-computed integral of (routed resolve − always-m2) over λ.

**Acceptance Scenarios**:

1. **Given** hold-out scores and labels, **When** metrics are computed, **Then** the report includes always-m1, always-m2, random, oracle-routing resolve rates, and Route-AUC.
2. **Given** Route-AUC ≤ 0, **When** the run finishes, **Then** training still writes artifacts and marks go/no-go as floor/no-go rather than failing closed.
3. **Given** a completed train run, **When** the manifest is read, **Then** it has timestamp, git commit, config snapshot, seeds, fold fallback (if any), truncation rate, and metrics.

---

### Edge Cases

- All m1 labels false: ROC-AUC undefined; Route-AUC near 0; still write the report.
- Shared-scaffold mismatch tasks: still trainable if both labels exist; pre-flight already flagged them.
- Missing generation prompt: skip the row and count it in the manifest.
- Operator waives the 15% m1-positive pre-flight flag: training proceeds.

## Requirements

### Functional Requirements

- **FR-001**: Build one training example per complete labeled task from `labels.jsonl` and Stage-1 generation records.
- **FR-002**: Router input is issue text plus oracle file context; patch text MUST NOT be an input.
- **FR-003**: Truncate input at 2048 tokens and log the truncation rate.
- **FR-004**: Label is `m1_resolves` iff the small-model record has `resolved is True`.
- **FR-005**: Default backbone is `answerdotai/ModernBERT-base` with a binary P(m1 resolves) head.
- **FR-006**: Serve rule: m1 if score ≥ λ, else m2.
- **FR-007**: Cross-validate with 5 folds × 3 seeds, stratified by label and repo when possible.
- **FR-008**: If stratification is impossible, fall back and record the strategy.
- **FR-009**: Report Route-AUC vs always-m1, always-m2, random, and oracle-routing.
- **FR-010**: Go/no-go is Route-AUC > 0 on held-out folds; ≤ 0 is documented floor, not a crash.
- **FR-011**: Default pytest MUST pass without downloading ModernBERT and without GPU.
- **FR-012**: Live training is opt-in via an extra install and CLI; write a run manifest.
- **FR-013**: Torch/transformers are optional extras, not default runtime dependencies.

### Key Entities

- **Router example**: instance id, repo, input text, truncated flag, m1_resolves, m2_resolves.
- **Fold assignment**: instance id → fold index for a seed.
- **Train run**: config snapshot, metrics per fold/seed, truncation rate, go/no-go.
- **Route-AUC**: integral over λ ∈ [0, 1] of (resolve rate of the λ-policy − always-m2 resolve rate).

## Success Criteria

### Measurable Outcomes

- **SC-001**: From labels + generations, operators obtain a training JSONL with no patch text in inputs.
- **SC-002**: Offline tests cover dataset join, truncation, splits fallback, and Route-AUC arithmetic.
- **SC-003**: A live train command produces fold metrics and a go/no-go bit in a gitignored run directory.
- **SC-004**: Default CI does not download Hugging Face weights.

## Assumptions

- Stage-3 labels exist (20-task waiver allowed; full 300 preferred).
- m1 = `qwen/qwen-2.5-7b-instruct`; m2 = `qwen/qwen-2.5-72b-instruct`.
- Prompt text on the m1 generation record is the shared issue + oracle context.
- AST, BM25, multi-turn, Llama, and 8k context are out of scope.
