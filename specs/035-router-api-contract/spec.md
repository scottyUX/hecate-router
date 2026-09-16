# Feature Specification: Router API Contract (`POST /v1/route`)

**Feature Branch**: `035-router-api-contract`

**Created**: 2026-08-28

**Status**: Draft

**Input**: GitHub issue #35, "Router API: contracts for /v1/route (request/response, errors, versioning)"

## Context

Hecate needs a versioned, route-only inference contract so callers can depend on a stable
interface while the routers behind it keep changing. Multiple routers are expected
(E-M4 and successors); `router_version` is the field that lets them be swapped without
breaking callers.

Scope for this branch is **documentation only**. No serving code is written or modified
here; the implementation is a separate issue. 

**Tiers for v1** are the Option A pair in `configs/option_a.yaml`:

| Tier | OpenRouter slug |
|---|---|
| `small` | `qwen/qwen-2.5-7b-instruct` |
| `large` | `qwen/qwen-2.5-72b-instruct` |

## User Scenarios & Testing

### User Story 1 - Call the router without reading its source (Priority: P1)

A lab member or downstream pipeline (Stage 5 evaluation, E-M5 #19) sends a task and gets
back a tier decision plus the model slug to use. They need a document stating every field,
its type, whether it is required, and every failure response without reading Python.

**Why this priority**: Without it, each caller re-derives the interface from source with implementation details that are free to change.

**Independent Test**: A reader who has never opened the serving code can construct a valid
request and interpret every response field using only `contracts/openapi.yaml` and
`contracts/router-api.md`.

**Acceptance Scenarios**:

1. **Given** the contract, **When** a caller sends a request built only from it, **Then** the documented 200 response shape is returned.
2. **Given** the contract, **When** a caller sends an empty `task_text`, **Then** the documented 422 error body is returned.

---

### User Story 2 - Swap or retrain the router without breaking callers (Priority: P2)

Routers will be retrained and replaced. Callers need to know which parts of the response
are stable across those changes and which are expected to differ.

**Why this priority**: Versioning policy is the longest lived part of this contract, and
the reason `/v1` is worth declaring at all.

**Independent Test**: The versioning section answers, without reference to code, whether
swapping the router bumps the API version.

**Acceptance Scenarios**:

1. **Given** a new packaged router artifact, **When** it is deployed, **Then** `/v1` is unchanged and only `router_version` in the response differs.
2. **Given** a change that removes or retypes a response field, **Then** the policy classifies it as breaking and requires `/v2`.

---

### User Story 3 - Trace a specific routing decision (Priority: P3)

A surprising decision is reported. The reviewer must identify which router version and
which model produced it, from the stored response alone.

**Why this priority**: Research results must be reproducible; a score with no history of where it came from
cannot be audited months later.

**Independent Test**: A stored 200 response contains enough information about source to reproduce the
call without external notes.

**Acceptance Scenarios**:

1. **Given** a stored response, **When** a reviewer inspects it, **Then** `router_version`, `model_slug`, and `request_id` are all present.

### Edge Cases

- `task_text` present but whitespace only --> 422.
- Request body exceeds the documented byte limit --> 413.
- `task_text` or `file_text` exceeds its documented character limit --> 413.
- `router_version` requested that this deployment does not serve --> 404, distinct from a known version whose artifact is unavailable or still loading (503).
- Cold start: the artifact is still downloading from GCS --> 503 with `Retry-After`.
- Caller lacks `roles/run.invoker` --> 403 emitted by Cloud Run **before** the application runs, so it does not use this contract's error body.

## Requirements

### Endpoint

- **FR-001**: The contract MUST define exactly one inference endpoint, `POST /v1/route`.
- **FR-002**: The contract MUST NOT define experiment, batch, or training endpoints (no `/v1/experiments`, `/v1/batch`, or equivalent) in v1.

### Request

- **FR-003**: `task_text` (string) MUST be required, and MUST be rejected when empty or whitespace-only.
- **FR-004**: `file_text` (string) MUST be accepted as optional oracle/context input.
- **FR-005**: `router_version` (string) MUST be accepted as optional, defaulting to the latest artifact packaged in the deployment (for example `em4-v1`). Only concrete version identifiers are accepted; v1 defines no `latest` or other alias as an input value.
- **FR-006**: The contract MUST state a maximum request body size **in bytes**, and the maximum accepted length of `task_text` and `file_text` **in characters**, with 413 as the documented response for exceeding either. The body maximum MUST be large enough that any body passing field validation also passes it.

### Response (200)

- **FR-007**: `route` MUST be returned as one of `small` | `large`.
- **FR-008**: `scores` MUST be returned as an object keyed by tier (`small`, `large`), each an independent per-model estimate expressed as a float in 0.0–1.0. The contract MUST state precisely what each number means so callers do not invent an interpretation.
- **FR-009**: `model_slug` MUST be returned as the OpenRouter slug mapped to the chosen tier, resolved from `configs/option_a.yaml`.
- **FR-010**: `router_version` MUST be returned as the resolved concrete version, including when the request omitted the field.
- **FR-011**: `request_id` MUST be returned in both the response body and a response header. The service MUST echo a caller-supplied `X-Request-Id` when present and generate a UUIDv4 otherwise.

### Errors

- **FR-012**: The contract MUST define one error body shape used by every error the application emits, and that shape MUST include `request_id`.
- **FR-013**: The contract MUST document at minimum: 400 malformed body, 422 validation failure, 404 unknown `router_version`, 413 payload too large, 429 rate limited, 500 internal error, 503 router unavailable or still loading.
- **FR-014**: 503 responses for a warming or unavailable router MUST document `Retry-After`.
- **FR-015**: The contract MUST document that authentication is Cloud Run IAM, and that 401/403 are produced by Google's front end before the application executes and therefore do **not** conform to the FR-012 error shape.

### Versioning

- **FR-016**: The contract MUST distinguish the API version (`/v1`) from the router version (`router_version`).
- **FR-017**: The contract MUST state explicitly that retraining or swapping the router does NOT bump the API version.
- **FR-018**: The contract MUST classify changes as breaking (removing a response field, retyping a field, adding a value to the `route` enum, changing a documented status code) or additive (new optional request fields, new response fields), and state that breaking changes require `/v2`.
- **FR-019**: The contract MUST state that `/v1` addresses interface stability only and makes no claim about routing quality.

### Key Entities

- **RouteRequest**: `task_text` (required), `file_text` (optional), `router_version` (optional).
- **RouteResponse**: `route`, `scores`, `model_slug`, `router_version`, `request_id`.
- **RouterVersion**: a packaged artifact identified by a version string (e.g. `em4-v1`).
- **ErrorBody**: the single error shape from FR-012.

## Success Criteria

- **SC-001**: `contracts/openapi.yaml` exists and parses as a valid OpenAPI 3.1 document under an automated validator.
- **SC-002**: Every file in `examples/` validates against its schema in `contracts/openapi.yaml`.
- **SC-003**: The contract defines no path matching `/v1/experiment*` or `/v1/batch*`, verified by an automated check.
- **SC-004**: Every status code in FR-013 has a documented body and at least one example.
- **SC-005**: A reader can answer "does swapping the router bump the API version?" from the contract alone.
- **SC-006**: A reader can construct a valid request and interpret every response field without reading any Python.
- **SC-007**: No file under `deploy/` or `src/hecate/` is modified on this branch.

## Assumptions

- Serving implementation is a separate issue; this branch ships documentation only.
- The routed tiers are the Option A Qwen pair (`configs/option_a.yaml`). Other routers and other model pairs are expected later and are accommodated via `router_version` rather than by changing `/v1`.
- Authentication is Cloud Run IAM (`roles/run.invoker`); no application-level API key is introduced.
- The decision threshold is a property of the packaged `router_version`, not a request parameter. v1 exposes no caller-supplied threshold.
- Router artifacts are packaged with the deployment or fetched from GCS at startup; the contract does not constrain which.