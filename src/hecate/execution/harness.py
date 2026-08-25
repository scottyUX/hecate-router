"""Injectable SWE-bench evaluation harness."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

def sanitize_model_slug(model_slug: str) -> str:
    """SWE-bench log dirs replace ``/`` with ``__``."""
    return model_slug.replace("/", "__")


@dataclass(frozen=True)
class HarnessRequest:
    predictions_path: Path
    run_id: str
    instance_ids: tuple[str, ...]
    dataset_name: str
    split: str
    max_workers: int
    timeout: int
    namespace: str | None
    report_dir: Path
    cache_level: str = "env"
    force_rebuild: bool = False
    modal: bool = False


@dataclass(frozen=True)
class HarnessResult:
    log_dir: Path


class Harness(Protocol):
    def run(self, request: HarnessRequest) -> HarnessResult: ...


@dataclass(frozen=True)
class ScriptedOutcome:
    """Synthetic per-(instance, model) eval result for tests."""

    patch_successfully_applied: bool = False
    resolved: bool = False
    fail_to_pass: tuple[str, ...] = ()
    pass_to_pass: tuple[str, ...] = ()
    omit_report: bool = False
    harness_error: bool = False


class ScriptedHarness:
    """Write synthetic ``report.json`` files without Docker."""

    def __init__(
        self,
        outcomes: dict[tuple[str, str], ScriptedOutcome] | None = None,
    ) -> None:
        self.outcomes = outcomes or {}
        self.calls: list[HarnessRequest] = []

    def run(self, request: HarnessRequest) -> HarnessResult:
        self.calls.append(request)
        log_dir = (
            request.report_dir / "logs" / "run_evaluation" / request.run_id
        )
        predictions = _read_predictions(request.predictions_path)
        error_ids_by_slug: dict[str, list[str]] = {}
        for pred in predictions:
            instance_id = pred["instance_id"]
            if request.instance_ids and instance_id not in request.instance_ids:
                continue
            model_slug = pred["model_name_or_path"]
            outcome = self.outcomes.get(
                (instance_id, model_slug), ScriptedOutcome()
            )
            if outcome.harness_error:
                error_ids_by_slug.setdefault(model_slug, []).append(instance_id)
                continue
            if outcome.omit_report:
                continue
            report_path = (
                log_dir / sanitize_model_slug(model_slug) / instance_id / "report.json"
            )
            report_path.parent.mkdir(parents=True, exist_ok=True)
            body = {
                instance_id: {
                    "patch_is_None": False,
                    "patch_exists": True,
                    "patch_successfully_applied": outcome.patch_successfully_applied,
                    "resolved": outcome.resolved,
                    "tests_status": {
                        "FAIL_TO_PASS": {
                            "success": list(outcome.fail_to_pass),
                            "failure": [],
                        },
                        "PASS_TO_PASS": {
                            "success": list(outcome.pass_to_pass),
                            "failure": [],
                        },
                    },
                }
            }
            report_path.write_text(
                json.dumps(body, indent=2) + "\n", encoding="utf-8"
            )
        for model_slug, error_ids in error_ids_by_slug.items():
            summary_path = (
                request.report_dir
                / f"{sanitize_model_slug(model_slug)}.{request.run_id}.json"
            )
            summary_path.write_text(
                json.dumps({"error_ids": error_ids}, indent=2) + "\n",
                encoding="utf-8",
            )
        return HarnessResult(log_dir=log_dir)


class SwebenchHarness:
    """Adapter around ``swebench.harness.run_evaluation.main``."""

    def run(self, request: HarnessRequest) -> HarnessResult:
        from swebench.harness.run_evaluation import main

        request.report_dir.mkdir(parents=True, exist_ok=True)
        predictions_path = request.predictions_path.resolve()
        cwd = Path.cwd()
        try:
            os.chdir(request.report_dir)
            main(
                dataset_name=request.dataset_name,
                split=request.split,
                instance_ids=list(request.instance_ids),
                predictions_path=str(predictions_path),
                max_workers=request.max_workers,
                force_rebuild=request.force_rebuild,
                cache_level=request.cache_level,
                clean=False,
                open_file_limit=4096,
                run_id=request.run_id,
                timeout=request.timeout,
                namespace=request.namespace,
                rewrite_reports=False,
                modal=request.modal,
                report_dir=str(request.report_dir.resolve()),
            )
        finally:
            os.chdir(cwd)
        return HarnessResult(
            log_dir=request.report_dir / "logs" / "run_evaluation" / request.run_id
        )


def _read_predictions(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(json.loads(stripped))
    return rows


# Imported by tests that want a round-trip through to_prediction.
__all__ = [
    "Harness",
    "HarnessRequest",
    "HarnessResult",
    "ScriptedHarness",
    "ScriptedOutcome",
    "SwebenchHarness",
    "sanitize_model_slug",
]
