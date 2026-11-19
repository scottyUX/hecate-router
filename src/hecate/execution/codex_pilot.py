"""Scope and failure accounting for the explicitly authorized TASK-002 pilot."""

from __future__ import annotations


def validate_scope(mode: str, config: dict, selection: dict) -> int:
    ids = selection.get("instance_ids", [])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate selected task IDs")
    if mode == "fixtures":
        return 3
    if mode == "smoke":
        if len(ids) != 3:
            raise ValueError("Smoke requires exactly three selected tasks")
        return 3
    if mode != "pilot":
        raise ValueError("Unknown run mode")
    pilot = config.get("pilot", {})
    if (
        pilot.get("task_id") not in {"TASK-002", "TASK-006"}
        or selection.get("task_id") != "TASK-002"
        or pilot.get("task_count") != 20
        or len(ids) != 20
    ):
        raise ValueError("TASK-002 pilot requires exactly 20 fixed selected tasks")
    if (
        pilot.get("task_id") == "TASK-006"
        and config.get("model", {}).get("id") != "Qwen/Qwen3-Coder-30B-A3B-Instruct"
    ):
        raise ValueError("TASK-006 requires its explicitly authorized model")
    if set(ids) & set(selection.get("excluded_instance_ids", [])):
        raise ValueError("Pilot includes previously exposed smoke tasks")
    return 20


def infrastructure_failure(row: dict) -> bool:
    return row.get("resolved") is None


def should_halt(
    rows: list[dict], *, continue_on_error: bool, consecutive_limit: int = 3
) -> bool:
    if not rows or not infrastructure_failure(rows[-1]):
        return False
    if not continue_on_error:
        return True
    if consecutive_limit < 1:
        raise ValueError("Consecutive error limit must be positive")
    return len(rows) >= consecutive_limit and all(
        infrastructure_failure(r) for r in rows[-consecutive_limit:]
    )
