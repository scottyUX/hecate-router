# Tasks: Router API Contract (`POST /v1/route`)

**Input**: Design documents from `/specs/035-router-api-contract/`

**Prerequisites**: spec.md, plan.md

## Phase 1: Setup

- [x] T001 Add `openapi-spec-validator` + `jsonschema` to `[project.optional-dependencies] dev` in `pyproject.toml`
- [x] T002 [P] Confirm docs-only scope: nothing under `deploy/` or `src/hecate/` (SC-007)

## Phase 2: OpenAPI document

- [x] T003 [US1] `contracts/openapi.yaml` skeleton: `3.1.0`, `info`, single `POST /v1/route` path (FR-001, FR-002)
- [x] T004 [US1] `RouteRequest` schema: `task_text` required non-empty, `file_text` optional, `router_version` optional and concrete-only (FR-003, FR-004, FR-005)
- [x] T005 [US1] Request body size and field-length limits (FR-006)
- [x] T006 [US1] [US3] `RouteResponse` schema plus `X-Request-Id` / `request_id` headers (FR-007, FR-008, FR-009, FR-010, FR-011)
- [x] T007 [US1] `ErrorBody` schema and one response entry per status code, `Retry-After` on 503 (FR-012, FR-013, FR-014)

**Checkpoint**: `openapi.yaml` ready to validate

## Phase 3: Docs companion

- [x] T008 [P] [US1] `contracts/router-api.md`: what each `scores` value means (FR-008)
- [x] T009 [P] [US1] Tier --> `model_slug` resolution from `configs/option_a.yaml` (FR-009)
- [x] T010 [P] [US1] Cloud Run IAM auth; 401/403 bypass `ErrorBody` (FR-015)
- [x] T011 [P] [US2] Versioning policy: API vs router version, breaking vs additive, `/v1` is interface-only (FR-016, FR-017, FR-018, FR-019)

**Checkpoint**: versioning question answerable from the contract alone (SC-005)

## Phase 4: Examples

- [x] T012 [P] [US1] `examples/request.minimal.json` + `request.full.json`
- [x] T013 [P] [US1] [US3] `examples/response.small.json` + `response.large.json`, concrete `router_version` (FR-010)
- [x] T014 [P] [US1] `examples/error.<status>.json` per FR-013 code; placeholders only, no tokens (SC-004)

## Phase 5: Validation

- [x] T015 `tests/test_api_contract.py`: `openapi.yaml` validates as OpenAPI 3.1 (SC-001)
- [x] T016 Examples validate against their schemas (SC-002)
- [x] T017 No `/v1/experiment*` or `/v1/batch*` path (SC-003, FR-002)
- [x] T017a Every application status documents a body and an example; 401/403 declare none (SC-004, FR-013, FR-015)
- [x] T017b Body maximum and field maximum are documented, and the body maximum dominates the field maxima (FR-006)
- [x] T017c `Retry-After` is declared on 429 and 503 (FR-014)
- [x] T017d `X-Request-Id` is declared on the 200 response (FR-011)
- [x] T017e `error.code` is a closed enum and each example carries the code for its status (FR-012)
- [x] T017f Stored responses carry `model_slug` / `router_version` / `request_id`, with `router_version` concrete (FR-010)
- [x] T017g `model_slug` matches the tier's slug in `configs/option_a.yaml` (FR-009)

## Phase 6: Polish

- [x] T018 Run `pytest` offline with no API key set (Principle III)
- [x] T019 Post-design Constitution re-check in `plan.md`; review `contracts/` against SC-006

## Dependencies

Setup → OpenAPI document → docs + examples (parallel) → validation. Phase 5 depends on T003–T007 and T012–T014. Serving implementation is a separate issue.
