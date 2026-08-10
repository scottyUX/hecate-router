# Feature Specification: Run the Pilot (20 × 1)

**Feature Branch**: `012-pilot-run`

**Created**: 2026-08-10

**Status**: Draft

**Input**: GitHub issue #12, "S12 · Run the pilot (20 tasks × 1 model)"

## User Scenarios & Testing

### User Story 1 - Execute a 20-task single-model pilot (Priority: P1)

A Stage-1 operator runs the generation runner on 20 SWE-bench Lite tasks with one
small model, producing generation records, a manifest with cost and wall-clock
metrics, so the team can judge scaffold quality before a full sweep.

**Why this priority**: This is the M1 day-2 evidence gate.

**Independent Test**: Run the pilot command; confirm 20 records exist and the
manifest includes total cost, cost-per-sample, and per-task wall-clock.

**Acceptance Scenarios**:

1. **Given** a working S11 runner and API key, **When** the pilot runs for 20
   tasks × one small model, **Then** 20 generation records are written.
2. **Given** a completed pilot, **When** the manifest is inspected, **Then** it
   includes total cost, cost-per-sample, and per-pair wall-clock timings.
3. **Given** generated patches, **When** an operator samples a few, **Then** they
   are human-readable unified diffs or clearly marked parse failures.

### Edge Cases

- Day-2 gate: if patches largely fail to parse, stop and debug scaffold (S6/S8)
  rather than proceeding to S14.
- Budget refuse mid-pilot must be visible in manifest counters.

## Requirements

- **FR-001**: Execute 20 tasks × 1 small model (`qwen/qwen-2.5-7b-instruct`).
- **FR-002**: Persist 20 generation records and a run manifest.
- **FR-003**: Record cost-per-sample and per-task/pair wall-clock.
- **FR-004**: Capture reproducibility fields (config snapshot, git commit, slugs).
- **FR-005**: Document inspection notes for a sample of patches.

## Success Criteria

- **SC-001**: 20 records produced for the pilot model.
- **SC-002**: Manifest contains cost and wall-clock metrics.
- **SC-003**: Operator can open records and inspect diffs.

## Assumptions

- Uses live OpenRouter spend under the $100 ceiling.
- Runner timing fields from S11 are acceptable for wall-clock recording.
