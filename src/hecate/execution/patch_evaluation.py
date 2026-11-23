"""Versioned source-patch scoring independent of agent termination."""
from __future__ import annotations

import hashlib
import re
import shlex
from pathlib import PurePosixPath

from hecate.execution.task_environment import protected_test_path

PROTOCOL = "source-patch-v2"
BUDGET_REASONS = {
    "completed", "budget_exhausted", "request_budget_exhausted",
    "context_budget_exhausted", "model_output_failure", "model_output_budget_exhausted",
}


def execution_infrastructure_failure(reason: str) -> bool:
    return reason not in BUDGET_REASONS


def evaluation_patch(patch: str, rejected: list[str]) -> tuple[str, dict]:
    """Exclude only newly added protected files; never rewrite source hunks."""
    kept, excluded = [], []
    for block in re.split(r"(?=^diff --git )", patch, flags=re.M):
        if not block:
            continue
        header = shlex.split(block.splitlines()[0])
        if len(header) != 4 or header[:2] != ["diff", "--git"]:
            raise ValueError("Unsupported or ambiguous patch header")
        if not header[2].startswith("a/") or not header[3].startswith("b/"):
            raise ValueError("Unexpected patch path prefix")
        old, new = header[2][2:], header[3][2:]
        for path in (old, new):
            parts = PurePosixPath(path).parts
            if not parts or PurePosixPath(path).is_absolute() or any(
                p in {"..", ".git"} for p in parts
            ):
                raise ValueError("Unsafe patch path")
        if re.search(r"^(?:rename|copy) (?:from|to) ", block, re.M):
            raise ValueError("Rename/copy patches require explicit review")
        # git apply may use unified headers instead of the diff --git paths.
        for prefix, expected in (("--- ", "a/" + old), ("+++ ", "b/" + new)):
            values = [line[len(prefix):] for line in block.splitlines() if line.startswith(prefix)]
            if len(values) > 1 or any(v not in {expected, "/dev/null"} for v in values):
                raise ValueError("Unified patch paths disagree with diff header")
        if protected_test_path(old) or protected_test_path(new):
            # An empty new file has no ---/+++ lines; git marks it with the empty blob.
            empty_new = re.search(r"^index 0+\.\.e69de29(?:bb2d1d6434b8b29ae775ad8c2e48c5391)?(?: 100(?:644|755))?$", block, re.M) \
                and not re.search(r"^(?:---|\+\+\+|@@) ", block, re.M)
            if (old != new or new not in rejected
                or not re.search(r"^new file mode 100(?:644|755)$", block, re.M)
                or ("\n--- /dev/null\n" not in block and not empty_new)):
                raise ValueError("Existing protected file change cannot be projected")
            excluded.append(new)
        else:
            kept.append(block)
    if len(excluded) != len(set(excluded)) or set(excluded) != set(rejected):
        raise ValueError("Protected paths differ from collected patch evidence")
    derived = "".join(kept)
    return derived, {
        "original_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "evaluation_sha256": hashlib.sha256(derived.encode()).hexdigest(),
        "excluded_new_test_files": excluded,
    }


def outcome_axes(result: dict) -> dict:
    """Never let a passing patch hide an execution or policy failure."""
    completed = result.get("termination_reason") == "completed"
    compliant = not result.get("test_modifications")
    return {
        "evaluation_protocol": PROTOCOL,
        "session_completed": completed,
        "policy_compliant": compliant,
        "execution_infrastructure_failure": execution_infrastructure_failure(
            result.get("termination_reason", "missing_agent_result")
        ),
        "clean_success": result.get("resolved") is True and completed and compliant,
    }


def correctness_summary(rows: list[dict], selected: int) -> dict:
    solved = sum(r.get("resolved") is True for r in rows)
    evaluable = sum(r.get("resolved") is not None for r in rows)
    return {
        "evaluation_protocol": PROTOCOL,
        "selected": selected,
        "evaluable": evaluable,
        "resolved": solved,
        "unresolved": sum(r.get("resolved") is False for r in rows),
        "ungraded": len(rows) - evaluable,
        "session_completed": sum(r.get("session_completed") is True for r in rows),
        "policy_violations": sum(r.get("policy_compliant") is False for r in rows),
        "clean_successes": sum(r.get("clean_success") is True for r in rows),
        "infrastructure_errors": sum(
            r.get("execution_infrastructure_failure", False)
            or r.get("status") in {"evaluator_failure", "infrastructure_failure"}
            for r in rows
        ),
        "resolved_fraction_of_selected": solved / selected if selected else None,
        "resolved_fraction_of_evaluable": solved / evaluable if evaluable else None,
    }
