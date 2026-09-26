# Contract: `POST /v1/route`

Companion to [`openapi.yaml`](./openapi.yaml). This document is for meaning, versioning, and the auth boundary. Worked payloads are in [`examples/`](../examples/).

## Tier --> model slug

| `route` | `model_slug` |
|---------|--------------|
| `small` | `qwen/qwen-2.5-7b-instruct` |
| `large` | `qwen/qwen-2.5-72b-instruct` |

Resolved from [`configs/option_a.yaml`](../../../configs/option_a.yaml).

## Size limits

| Limit | Unit | Enforced | Exceeded |
|-------|------|----------|----------|
| Request body, 4 MiB | bytes | HTTP, before JSON parsing | 413 `payload_too_large` |
| `task_text`, 64,000 | characters | schema validation | 413 `payload_too_large` |
| `file_text`, 256,000 | characters | schema validation | 413 `payload_too_large` |
| Router input budget | tokens | tokenizer, inside the router | **nothing** - truncated, 200 OK |

Input longer than a router version's budget may be silently truncated and still scored, so a 200 response never tells you the whole input was read. Truncation is a routing-quality property, and per C-10 `/v1` makes no claim about routing quality.

Field-length violations (`maxLength`) return 413 `payload_too_large`; all other field validation failures return 422 `validation_error`.

## Errors

| Status | `error.code` | Retryable |
|--------|--------------|-----------|
| 400 | `malformed_request` | No - body is not valid JSON |
| 401 | *(none — see C-6)* | No - obtain a token |
| 403 | *(none — see C-6)* | No - request `roles/run.invoker` |
| 404 | `unknown_router_version` | No - version is not served here |
| 413 | `payload_too_large` | No - reduce the payload |
| 422 | `validation_error` | No - fix the request |
| 429 | `rate_limited` | Yes - follow `Retry-After` |
| 500 | `internal_error` | Maybe |
| 503 | `router_unavailable` | Yes - follow `Retry-After` |

404 and 503 are distinct: 404 means the version does not exist in the deployment and retrying never helps; 503 means a known version is not loaded yet, typically a cold start still fetching the checkpoint from GCS.

## Authentication

Cloud Run IAM. No application-level API key, no shared secret.

```bash
TOKEN="$(gcloud auth print-identity-token)"
curl -sS -X POST "${SERVICE_URL}/v1/route" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"task_text": "..."}'
```

The caller must hold `roles/run.invoker` on the service. Access is granted by adding an IAM binding, not by issuing a credential.

## Versioning

| | Versions | Where | Changes |
|---|---|---|---|
| **API version** | Wire contract - field names, types, status codes | URL path: `/v1/route` | Rarely |
| **Router version** | Packaged model artifact | Response body: `router_version` | Every retrain |

**Breaking - requires `/v2`:**

- Removing a response field, or making a required field optional
- Changing a field's type
- Adding a value to the `route` enum
- Changing or removing a documented status code
- Making an optional request field required

**Additive - stays on `/v1`:**

- New optional request fields; new response fields
- New `error.code` values for existing status codes
- Any change to `router_version`, its weights, or its threshold

## Behavioral contract

| ID | Guarantee |
|----|-----------|
| C-1 | `scores.small` is the estimated probability that the **small** tier produces a patch resolving the task, conditioned on `task_text` (and `file_text`, where the router version consumes it). `scores.large` is the same estimate for the large tier. |
| C-2 | `route` is the decision, `scores` the evidence. The threshold turning scores into a `route` belongs to the packaged `router_version` and is not a request parameter. |
| C-3 | `file_text` is accepted, but whether a given `router_version` consumes it is version-dependent and unspecified in v1. |
| C-4 | `model_slug` is a **configuration lookup, not a router output**: the router chooses a tier, the deployment maps it to a slug. |
| C-5 | `router_version` in the response is always the **concrete version**, never an alias, including when the request omitted the field. Requests accept concrete identifiers only. |
| C-6 | 401 and 403 are emitted by the Cloud Run front end **before this application executes**: the body is not `ErrorBody`, carries no `request_id`, and does not appear in this service's logs. Callers MUST check for 401/403 before parsing a body as `ErrorBody`, and debug them via Cloud Run / IAM audit logs. |
| C-7 | Every other documented status is emitted by the application and conforms to `ErrorBody`. |
| C-8 | Branch on `error.code` (a closed enum, part of the contract), never on `error.message` (human-readable, may change at any time). |
| C-9 | Retraining or swapping the router changes the `router_version` **value** only; request and response shapes are untouched and the API version does not bump. |
| C-10 | `/v1` refers to **interface stability only**. It makes no claim about routing quality; that is a property of the packaged `router_version`, evaluated separately. |

## Non-goals (contract explicitly excludes)

- Experiment, batch, or training endpoints - v1 is route-only.
- Serving implementation, deployment, and artifact packaging (separate issue).
- A caller-supplied decision threshold (C-2).
- Whether a given router version consumes `file_text` (C-3).
- Any claim about routing quality (C-10).
