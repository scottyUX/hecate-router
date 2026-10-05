"""Offline tests for the three-model experiment analysis."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hecate.agent.experiment_analysis import (
    cohen_kappa,
    cross_model,
    feature_separation,
    load_runs,
    mcnemar_exact,
    per_model,
    render_markdown,
    wilson,
)

MODELS = ["a", "b", "c"]
TASKS = [
    {"instance_id": f"r__r-{i}", "repo": "r/r" if i < 4 else "s/s",
     "difficulty": "<15 min fix" if i % 2 == 0 else "15 min - 1 hour"}
    for i in range(6)
]
# resolved per model per task; None = no executions record (ungraded)
OUTCOMES = {
    "a": [True, True, True, False, False, True],
    "b": [True, False, True, False, True, None],
    "c": [True, False, False, False, False, False],
}
COST = {"a": 1.0, "b": 0.1, "c": 0.01}


def _write_traj(path: Path, iid: str, cost: float, steps: int) -> None:
    messages = [{"role": "system", "content": ""}, {"role": "user", "content": ""}]
    for s in range(steps):
        messages.append({
            "role": "assistant",
            "extra": {"actions": [], "timestamp": 100.0 + s,
                      "response": {"usage": {"prompt_tokens": 10, "cost": cost / steps}}},
        })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "instance_id": iid,
        "info": {"exit_status": "Submitted", "model_stats": {"instance_cost": cost, "api_calls": steps}},
        "messages": messages,
    }))


@pytest.fixture()
def run_root(tmp_path: Path) -> Path:
    for m in MODELS:
        d = tmp_path / m
        preds, execs = {}, []
        for i, task in enumerate(TASKS):
            iid = task["instance_id"]
            if m == "c" and i == 5:
                preds[iid] = {"model_patch": ""}  # infra failure: no trajectory
                continue
            preds[iid] = {"model_patch": "diff --git a/x b/x\n"}
            # resolved runs take fewer steps, so `steps` should separate
            res = OUTCOMES[m][i]
            _write_traj(d / iid / f"{iid}.traj.json", iid, COST[m], 3 if res else 9)
            if res is not None:
                execs.append({"instance_id": iid, "resolved": res, "patch_applied": True})
        d.mkdir(parents=True, exist_ok=True)
        (d / "preds.json").write_text(json.dumps(preds))
        (d / "executions.jsonl").write_text("".join(json.dumps(e) + "\n" for e in execs))
    return tmp_path


def test_wilson_known_value() -> None:
    lo, hi = wilson(5, 10)
    assert lo == pytest.approx(0.2366, abs=1e-3) and hi == pytest.approx(0.7634, abs=1e-3)
    assert wilson(0, 0) is None


def test_kappa_and_mcnemar() -> None:
    assert cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert cohen_kappa([True, True, False, False], [True, False, True, False]) == 0.0
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(0, 6) == pytest.approx(2 / 64)


def test_statuses_and_rates(run_root: Path) -> None:
    runs = load_runs(run_root, TASKS, MODELS)
    pm = per_model(runs, MODELS)
    assert pm["a"]["attempted"] == 6 and pm["a"]["resolved"] == 4 and pm["a"]["graded"] == 6
    # b's last task has a trajectory but no grade: ungraded, not unresolved
    assert pm["b"]["ungraded"] == 1 and pm["b"]["graded"] == 5 and pm["b"]["resolved"] == 3
    # c's last task never ran: infra failure, excluded from the denominator
    assert pm["c"]["infra_failures"] == 1 and pm["c"]["graded"] == 5 and pm["c"]["resolved"] == 1
    assert pm["a"]["by_difficulty"]["<15 min fix"]["resolved"] == 2
    assert pm["a"]["total_cost_usd"] == pytest.approx(6.0)
    assert pm["a"]["cost_per_resolved_usd"] == pytest.approx(1.5)


def test_cross_model_overlap(run_root: Path) -> None:
    xm = cross_model(load_runs(run_root, TASKS, MODELS), MODELS)
    # task 5 is ungraded for b and infra for c: only tasks 0-4 are common
    assert xm["n_common"] == 5
    assert xm["all_solved"] == 1  # task 0
    assert xm["none_solved"] == 1  # task 3
    assert xm["only_one"] == {"a": 1, "b": 1, "c": 0}  # task 1 (a), task 4 (b)
    assert xm["exactly_two"]["a+b"] == 1  # task 2
    ab = xm["pairwise"]["a vs b"]
    assert ab["a_only"] == 1 and ab["b_only"] == 1 and ab["agreement"] == 0.6
    # oracle: t0 c (0.01), t1 a (1.0), t2 b (0.1), t3 none -> cheapest c (0.01), t4 b (0.1)
    assert xm["oracle"]["resolved_rate"] == pytest.approx(0.8)
    assert xm["oracle"]["cost_usd"] == pytest.approx(1.22)


def test_feature_separation_finds_steps(run_root: Path) -> None:
    fs = feature_separation(load_runs(run_root, TASKS, MODELS), MODELS)
    steps = next(r for r in fs["pooled"] if r["feature"] == "steps")
    assert steps["auroc"] == 0.0  # fewer steps <-> resolved, perfectly
    assert fs["pooled"][0]["auroc"] in (0.0, 1.0)


def test_render_markdown_runs(run_root: Path) -> None:
    runs = load_runs(run_root, TASKS, MODELS)
    summary = {
        "generated": "t", "tasks_file": "f", "n_tasks": len(TASKS),
        "per_model": per_model(runs, MODELS),
        "cross_model": cross_model(runs, MODELS),
        "features": feature_separation(runs, MODELS),
    }
    md = render_markdown(summary, MODELS)
    assert "Oracle router" in md and "| a | 4/6" in md
