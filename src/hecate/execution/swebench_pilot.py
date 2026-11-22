"""Strict one-task scope and required-test coverage for the local paper pilot."""
from __future__ import annotations


def validate_pilot(config: dict, selection: dict, instance: dict) -> None:
    if (
        config["model"]["id"] != "Qwen/Qwen3.6-35B-A3B"
        or config["model"]["revision"] != "345d467b117d1fd5eda9b879a5988de9ae5f47a7"
        or config["model"]["precision"] != "bfloat16"
        or config["codex"]["version"] != "0.164.0"
        or config["evaluator"]["task_id"] != "TASK-009"
        or config["evaluator"]["task_count"] != 1
        or config["evaluator"]["arch"] != "arm64"
        or instance["instance_id"] != "django__django-16560"
        or config["evaluator"]["instance_id"] != instance["instance_id"]
        or instance["instance_id"] not in selection["instance_ids"]
    ):
        raise ValueError("Pilot scope differs from the approved one-task Qwen3.6 configuration")


def required_outcomes(spec, statuses: dict, found: bool, timed_out: bool = False) -> dict:
    required = list(spec.FAIL_TO_PASS) + list(spec.PASS_TO_PASS)
    missing = [name for name in required if name not in statuses]
    if not found or timed_out or not spec.FAIL_TO_PASS or missing:
        return {"status": "evaluator_failure", "resolved": None,
                "missing_required_tests": missing, "test_markers_found": found,
                "timed_out": timed_out}
    return {"status": "completed", "resolved": all(statuses[t] == "PASSED" for t in required),
            "f2p": {t: statuses[t] for t in spec.FAIL_TO_PASS},
            "p2p": {t: statuses[t] for t in spec.PASS_TO_PASS}}
