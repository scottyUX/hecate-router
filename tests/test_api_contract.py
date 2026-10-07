"""Offline contract tests for the spec-035 `/v1/route` OpenAPI document.

US2 (swap the router without breaking callers) is a review criterion not an automated one.

"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_openapi

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = REPO_ROOT / "specs" / "035-router-api-contract"
OPENAPI_PATH = CONTRACT_DIR / "contracts" / "openapi.yaml"
EXAMPLES_DIR = CONTRACT_DIR / "examples"
OPTION_A_PATH = REPO_ROOT / "configs" / "option_a.yaml"

# examples/<prefix>.*.json validates against this component schema
SCHEMA_BY_PREFIX = {
    "request": "RouteRequest",
    "response": "RouteResponse",
    "error": "ErrorBody",
}

APP_CODES = {"400", "404", "413", "422", "429", "500", "503"}
FRONT_END_CODES = {"401", "403"}  # Cloud Run rejects before the app runs

CODE_BY_STATUS = {
    "400": "malformed_request",
    "404": "unknown_router_version",
    "413": "payload_too_large",
    "422": "validation_error",
    "429": "rate_limited",
    "500": "internal_error",
    "503": "router_unavailable",
}

BODY_MAX_BYTES = 4 * 1024 * 1024
WORST_CASE_BYTES_PER_CHAR = 12  # an emoji for example

TRACE_FIELDS = {"model_slug", "router_version", "request_id"}
VERSION_ALIASES = {"latest", "stable", "current", "newest"}


@pytest.fixture(scope="module")
def spec() -> dict:
    return yaml.safe_load(OPENAPI_PATH.read_text())


def _examples(pattern: str = "*.json") -> list[Path]:
    return sorted(EXAMPLES_DIR.glob(pattern))


def _operation(spec: dict) -> dict:
    return spec["paths"]["/v1/route"]["post"]


def _deref(spec: dict, node: dict) -> dict:
    """Follow a local `$ref` one level, if present."""
    ref = node.get("$ref")
    if not ref:
        return node
    target = spec
    for part in ref.removeprefix("#/").split("/"):
        target = target[part]
    return target


# --- US1: call the router without reading its source ---


def test_openapi_document_is_valid(spec: dict) -> None:
    # SC-001
    assert spec["openapi"].startswith("3.1")
    validate_openapi(spec)


def test_single_route_endpoint(spec: dict) -> None:
    # FR-001
    assert list(spec["paths"]) == ["/v1/route"]
    assert list(spec["paths"]["/v1/route"]) == ["post"]


def test_no_experiment_or_batch_paths(spec: dict) -> None:
    # SC-003 / FR-002: v1 is route-only
    offenders = [p for p in spec["paths"] if p.startswith(("/v1/experiment", "/v1/batch"))]
    assert offenders == []


def test_documented_status_codes(spec: dict) -> None:
    # FR-013 / SC-004: every application code is documented
    assert set(_operation(spec)["responses"]) == {"200"} | APP_CODES | FRONT_END_CODES
    assert {f"error.{code}.json" for code in APP_CODES} <= {p.name for p in _examples()} # <= means subset on sets as examples includes responses ad=nd requests too


def test_front_end_codes_declare_no_body(spec: dict) -> None:
    # FR-015: 401/403 are emitted by Cloud Run and do not use ErrorBody
    for code in sorted(FRONT_END_CODES):
        response = _deref(spec, _operation(spec)["responses"][code])
        assert "content" not in response, f"{code} must not declare a body schema"
        assert response["description"].strip()


def test_app_codes_declare_an_error_body(spec: dict) -> None:
    # SC-004 / FR-012: every application status returns the one error shape
    for code in sorted(APP_CODES):
        response = _deref(spec, _operation(spec)["responses"][code])
        schema = response["content"]["application/json"]["schema"]
        assert schema["$ref"] == "#/components/schemas/ErrorBody", code
        assert response["description"].strip()


def test_retryable_codes_declare_retry_after(spec: dict) -> None:
    # FR-014: a retryable status must tell the caller how long to wait
    for code in ("429", "503"):
        response = _deref(spec, _operation(spec)["responses"][code])
        header = response["headers"]["Retry-After"]
        assert header["schema"]["type"] == "integer", code


def test_ok_response_declares_request_id_header(spec: dict) -> None:
    # FR-011: request_id is returned in the body and as a response header
    ok = _operation(spec)["responses"]["200"]
    header = _deref(spec, ok["headers"]["X-Request-Id"])
    assert header["required"] is True
    body = ok["content"]["application/json"]["schema"]
    assert body["$ref"] == "#/components/schemas/RouteResponse"
    assert "request_id" in spec["components"]["schemas"]["RouteResponse"]["required"]


def test_documented_size_limits(spec: dict) -> None:
    # FR-006
    assert "4 MiB" in _operation(spec)["requestBody"]["description"]
    props = spec["components"]["schemas"]["RouteRequest"]["properties"]
    assert props["task_text"]["maxLength"] == 64000
    assert props["file_text"]["maxLength"] == 256000


def test_body_limit_dominates_field_limits(spec: dict) -> None:
    # FR-006: a body passing field validation can never trip the body cap
    props = spec["components"]["schemas"]["RouteRequest"]["properties"]
    total_chars = sum(prop["maxLength"] for prop in props.values())
    assert total_chars * WORST_CASE_BYTES_PER_CHAR <= BODY_MAX_BYTES


def test_examples_exist() -> None:
    # guards the parametrize below against silently collecting nothing
    assert _examples()


@pytest.mark.parametrize("path", _examples(), ids=lambda p: p.name)
def test_example_validates_against_schema(path: Path, spec: dict) -> None:
    # SC-002
    schema = dict(spec["components"]["schemas"][SCHEMA_BY_PREFIX[path.name.split(".")[0]]])
    schema["components"] = spec["components"]  # resolve #/components/... refs
    Draft202012Validator(schema).validate(json.loads(path.read_text()))


def test_code_enum_matches_status_map(spec: dict) -> None:
    # FR-012: the closed enum exists in the contract and CODE_BY_STATUS covers it
    error = spec["components"]["schemas"]["ErrorBody"]["properties"]["error"]
    enum = error["properties"]["code"]["enum"]
    assert set(CODE_BY_STATUS) == APP_CODES
    assert set(CODE_BY_STATUS.values()) == set(enum)


@pytest.mark.parametrize("path", _examples("error.*.json"), ids=lambda p: p.name)
def test_error_example_code_matches_its_status(path: Path) -> None:
    # FR-012: error.413.json must carry the 413 code, not merely a valid one
    status = path.name.split(".")[1]
    payload = json.loads(path.read_text())
    assert payload["error"]["code"] == CODE_BY_STATUS[status]


# --- US3: trace a decision from a stored response ---


@pytest.mark.parametrize("path", _examples("response.*.json"), ids=lambda p: p.name)
def test_response_carries_trace_fields(path: Path) -> None:
    # FR-010: a stored response identifies the artifact that produced it
    payload = json.loads(path.read_text())
    assert TRACE_FIELDS <= set(payload)
    assert payload["router_version"].lower() not in VERSION_ALIASES, (
        "router_version must be a concrete version"
    )


@pytest.mark.parametrize("path", _examples("response.*.json"), ids=lambda p: p.name)
def test_response_slug_matches_option_a(path: Path) -> None:
    # FR-009: model_slug is the configured slug for the chosen tier
    config = yaml.safe_load(OPTION_A_PATH.read_text())
    slug_by_tier = {model["tier"]: model["slug"] for model in config["models"]}

    payload = json.loads(path.read_text())
    assert payload["model_slug"] == slug_by_tier[payload["route"]]
