# Implementation Plan: Router API Contract (`POST /v1/route`)

**Branch**: `035-router-api-contract` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/035-router-api-contract/spec.md`

## Summary

Publish the `POST /v1/route` contract as `contracts/openapi.yaml` plus `contracts/router-api.md` for what the schema cannot express. Worked payloads live in `examples/`; `tests/test_api_contract.py` validates the document and every example offline so the contract cannot drift.

## Technical Context

**Language/Version**: Python 3.10+. Delivered artifacts are YAML, Markdown, and JSON.

**Primary Dependencies**: No new runtime dependency. Test-only additions to the
`[dev]` extra: `openapi-spec-validator` (OpenAPI 3.1 structural validation) and
`jsonschema` (example payload validation). Both are pure Python and run offline.

**Storage**: N/A.

**Testing**: `pytest`.

**Target Platform**: Targets GCP Cloud Run; this feature produces no deployable artifact.

**Project Type**: API contract documentation.

**Performance Goals**: N/A.

**Constraints**: Docs-only; no file under `deploy/` or `src/hecate/` is modified (SC-007). Contract scoped to one endpoint; no experiment or batch surfaces (FR-002).

**Scale/Scope**: One endpoint, 19 functional requirements, 7 success criteria, two contract documents, one test module.

## Constitution Check

*GATE: Evaluated against constitution **v1.0.0**.*

| Principle | Verdict | Basis |
|-----------|---------|-------|
| I. Execution-Grounded Validity | **PASS (N/A)** | No labels, generation, or matrix records. |
| II. Reproducibility by Manifest | **PASS (N/A)** | Feature runs nothing and consumes no provider budget, so no manifest. |
| III. Offline-Testable, Zero-Spend CI | **PASS** | Contract test parses local YAML/JSON; no network, no credentials, no spend. |
| IV. Spec-Driven Development | **PASS** | `spec.md` + `plan.md` + `tasks.md` present; every FR maps to at least one task. |
| V. Budget Discipline | **PASS (N/A)** | No provider calls issued or enabled by this feature. |
| VI. Secrets Hygiene | **PASS** | No credentials involved. The contract documents IAM auth by reference only; examples use placeholder identifiers and contain no tokens. |
| VII. Shared-Scaffold Fairness | **PASS (N/A)** | This feature defines a serving interface and issues no model requests. |

**Result: GREEN — no violations.**

**Post-design re-check**: **PASS** — `contracts/` and `examples/` ship documentation
only; the sole code change is `tests/test_api_contract.py` plus two `[dev]` extras.
`pytest` passes offline with no `OPENROUTER_API_KEY` (205 passed, 4 skipped).

## Project Structure

### Documentation (this feature)

```text
specs/035-router-api-contract/
├── spec.md              
├── plan.md              
├── tasks.md             
├── contracts/
│   ├── openapi.yaml     
│   └── router-api.md    
└── examples/
    ├── request.minimal.json
    ├── request.full.json
    ├── response.small.json
    ├── response.large.json
    └── error.<status>.json   # one per status code in FR-013
```

### Source Code (repository root)

```text
tests/
└── test_api_contract.py   # SC-001, SC-002, SC-003 as assertions

pyproject.toml             # [project.optional-dependencies]
```

**Structure Decision**: Contract artifacts live in the feature's `contracts/`
directory. The validation test lives in the repo's existing `tests/` directory
alongside `test_cost.py` and `test_runner.py`.

## Complexity Tracking

None.
