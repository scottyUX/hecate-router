"""TASK-012 paper-comparable SWE-bench-45 aggregates (arXiv:2610.32483v1 eqs. 6-7)."""
from __future__ import annotations

import hashlib
import random

EMPTY_PATCH_SHA = hashlib.sha256(b"").hexdigest()


def schedule(instance_ids: list[str], repetitions: int) -> list[tuple[str, int]]:
    """Repetition-major order: a partial run still covers every task at r=0."""
    return [(iid, rep) for rep in range(repetitions) for iid in instance_ids]


def attempt_tokens(row: dict) -> int | None:
    records = row.get("usage_records")
    if records is None:
        return None
    total = 0
    for record in records:
        usage = record.get("usage") or {}
        if "total_tokens" in usage:
            total += usage["total_tokens"]
        else:
            total += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    return total


def labels(row: dict) -> dict:
    """Paper label: official verifier, any missing outcome counts as unresolved.

    Strict label keeps our evaluator unknowns separate (None)."""
    evaluation = row.get("evaluation") or {}
    official = evaluation.get("official_resolved")
    sha = (row.get("patch_projection") or {}).get("original_sha256")
    nonempty = sha is not None and sha != EMPTY_PATCH_SHA
    applied = evaluation.get("status") not in {None, "patch_application_failure"}
    return {
        "paper_resolved": official is True,
        "strict_resolved": row.get("resolved"),
        # A.3: recognized normal stop plus a non-empty patch the evaluator applied.
        "valid_completion": row.get("termination_reason") == "completed" and nonempty and applied,
        "tokens": attempt_tokens(row),
    }


def aggregate(rows: dict[tuple[str, int], dict], instance_ids: list[str], repetitions: int) -> dict:
    """Every scheduled attempt enters the denominators; missing rows score zero."""
    scored = {key: labels(rows[key]) if key in rows else None for key in schedule(instance_ids, repetitions)}
    n = len(scored)
    present = [v for v in scored.values() if v is not None]
    paper = sum(v["paper_resolved"] for v in present)
    strict_known = [v["strict_resolved"] for v in present if v["strict_resolved"] is not None]
    tokens = [v["tokens"] for v in present if v["tokens"] is not None]
    best = sum(any(scored[(iid, r)] and scored[(iid, r)]["paper_resolved"] for r in range(repetitions))
               for iid in instance_ids)
    return {
        "tasks": len(instance_ids),
        "scheduled_attempts": n,
        "recorded_attempts": len(present),
        "mean_paper": 100 * paper / n,
        "best_paper": 100 * best / len(instance_ids),
        "vcr": 100 * sum(v["valid_completion"] for v in present) / n,
        "strict_resolved": sum(x is True for x in strict_known),
        "strict_unresolved": sum(x is False for x in strict_known),
        "strict_unknown": len(present) - len(strict_known),
        "token_load_m": (sum(tokens) / len(tokens) / 1e6) if tokens else None,
        "tokens_per_success_m": (sum(tokens) / paper / 1e6) if tokens and paper else None,
        "token_coverage": 100 * len(tokens) / n,
    }


def bootstrap(rows: dict, instance_ids: list[str], repetitions: int,
              replicates: int = 2000, seed: int = 0) -> dict:
    """Task-cluster bootstrap 95% intervals for Mean-of-R and Best-of-R."""
    rng = random.Random(seed)
    per_task = {}
    for iid in instance_ids:
        hits = [bool(rows.get((iid, r)) and labels(rows[(iid, r)])["paper_resolved"]) for r in range(repetitions)]
        per_task[iid] = (sum(hits), any(hits))
    means, bests = [], []
    for _ in range(replicates):
        sample = [per_task[rng.choice(instance_ids)] for _ in instance_ids]
        means.append(100 * sum(s for s, _ in sample) / (len(sample) * repetitions))
        bests.append(100 * sum(b for _, b in sample) / len(sample))

    def interval(values):
        values = sorted(values)
        return [values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]]

    return {"mean_paper_ci95": interval(means), "best_paper_ci95": interval(bests),
            "replicates": replicates, "seed": seed}
