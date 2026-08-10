# Feature Specification: Pilot Report & Go/No-Go

**Feature Branch**: `013-pilot-gonogo`

**Created**: 2026-08-10

**Status**: Draft

**Input**: GitHub issue #13, "S13 · Pilot report & go/no-go"

## User Scenarios & Testing

### User Story 1 - Decide whether to enter M2 (Priority: P1)

Advisors and the Stage-1 owner need a short report after the 20×1 pilot with
parse-clean fraction, extrapolated full-sweep cost and wall-clock, red flags, and
a clear go/no-go recommendation for the Stage-1 sweep (now 600 samples: 2 × 300).

**Why this priority**: M2 spend and calendar time must not start on a dirty pilot.

**Independent Test**: Report exists at `docs/pilot-report.md` with an explicit
GO or NO-GO and the supporting metrics from the S12 run.

## Requirements

- **FR-001**: Report parse-clean fraction from the S12 pilot records.
- **FR-002**: Extrapolate cost and wall-clock to a 300×2 sweep (with assumptions).
- **FR-003**: List red flags (context length, extract failures, etc.).
- **FR-004**: State a clear go/no-go for M2.
- **FR-005**: Defer Stage-3 label scheme (binary vs multiclass) to advisors.

## Success Criteria

- **SC-001**: A short report is committed and shareable.
- **SC-002**: Recommendation is unambiguous (GO or NO-GO).
