"""Merge SWE-bench ``report.json`` payloads onto generation records."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from hecate.data import GenerationRecord
from hecate.execution.harness import sanitize_model_slug

_REPORT_NAME = "report.json"


def load_instance_report(
    log_dir: Path, model_slug: str, instance_id: str
) -> dict[str, Any] | None:
    """Return the inner report object, or None if ``report.json`` is missing."""
    path = log_dir / sanitize_model_slug(model_slug) / instance_id / _REPORT_NAME
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    inner = payload.get(instance_id, payload)
    if not isinstance(inner, dict):
        return None
    return inner


def load_error_ids(report_dir: Path, model_slug: str, run_id: str) -> set[str]:
    """Return SWE-bench ``error_ids`` from the per-model summary JSON.

    SWE-bench writes ``{sanitized_slug}.{run_id}.json`` in the report dir.
    Instances listed there finished the harness with an EvaluationError
    (typically patch apply failed) and often have no ``report.json``.
    """
    path = report_dir / f"{sanitize_model_slug(model_slug)}.{run_id}.json"
    if not path.is_file():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return set()
    raw = payload.get("error_ids") or []
    return {str(item) for item in raw if item}


def apply_report(
    record: GenerationRecord, report: dict[str, Any]
) -> GenerationRecord:
    """Copy apply/resolved/test lists from a report body onto ``record``."""
    inner = report
    nested = report.get(record.instance_id)
    if isinstance(nested, dict) and (
        "patch_successfully_applied" in nested or "resolved" in nested
    ):
        inner = nested
    tests = inner.get("tests_status") or {}
    fail_block = tests.get("FAIL_TO_PASS") or {}
    pass_block = tests.get("PASS_TO_PASS") or {}
    fail_to_pass = list(fail_block.get("success") or [])
    pass_to_pass = list(pass_block.get("success") or [])
    return replace(
        record,
        patch_applied=bool(inner.get("patch_successfully_applied", False)),
        resolved=bool(inner.get("resolved", False)),
        fail_to_pass=fail_to_pass,
        pass_to_pass=pass_to_pass,
    )
