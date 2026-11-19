"""Offline guards for the paired TASK-002 pilot."""
import json
from pathlib import Path
import pytest
import yaml
from hecate.execution.codex_pilot import validate_scope, should_halt


def test_fixed_selection_and_shared_arm_settings():
    selection = json.loads(Path("configs/codex_qwen_size_pilot_tasks.json").read_text())
    ids = selection["instance_ids"]
    assert len(ids) == len(set(ids)) == 20
    assert not set(ids) & set(selection["excluded_instance_ids"])
    assert len(selection["bug_type_counts"]) == 9
    assert sum(selection["bug_type_counts"].values()) == 20
    small = yaml.safe_load(Path("configs/codex_qwen_size_pilot_7b.yaml").read_text())
    large = yaml.safe_load(Path("configs/codex_qwen_size_pilot_14b.yaml").read_text())
    assert validate_scope("pilot", small, selection) == 20
    assert validate_scope("pilot", large, selection) == 20
    for key in ("serving", "codex", "sandbox", "limits", "selection_manifest", "pilot"):
        assert small[key] == large[key]
    assert {k: v for k, v in small["model"].items() if k not in {"id", "revision"}} == {
        k: v for k, v in large["model"].items() if k not in {"id", "revision"}
    }


def test_scope_does_not_silently_expand_legacy_smoke():
    selection = json.loads(Path("configs/codex_qwen_size_pilot_tasks.json").read_text())
    config = yaml.safe_load(Path("configs/codex_qwen_size_pilot_7b.yaml").read_text())
    with pytest.raises(ValueError):
        validate_scope("smoke", config, selection)
    with pytest.raises(ValueError):
        validate_scope("pilot", {}, selection)
    with pytest.raises(ValueError):
        validate_scope(
            "pilot",
            config,
            {**selection, "instance_ids": selection["instance_ids"][:19]},
        )
    legacy = json.loads(Path("configs/codex_qwen7b_tasks.json").read_text())
    assert validate_scope("smoke", {}, legacy) == 3
    assert validate_scope("fixtures", {}, legacy) == 3


def test_failures_are_retained_but_systematic_errors_halt():
    failure = {"resolved": None, "status": "model_server_failure"}
    unresolved = {"resolved": False, "status": "completed"}
    assert not should_halt([failure], continue_on_error=True)
    assert not should_halt(
        [failure, failure, unresolved, failure], continue_on_error=True
    )
    assert should_halt([failure, failure, failure], continue_on_error=True)
    assert should_halt([failure], continue_on_error=False)
    assert not should_halt([unresolved] * 20, continue_on_error=True)
    assert not should_halt(
        [{"resolved": False, "status": "test_modification_rejected"}],
        continue_on_error=True,
    )


def test_pilot_runner_retains_isolated_failures_and_continues(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "pilot_runner_under_test", Path("scripts/run_codex_baseline.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fake_task(run, config, tools, binary, instance, reuse_agent_from):
        if instance["instance_id"] == "task-0":
            raise RuntimeError("isolated sandbox fixture failure")
        return {
            "instance_id": instance["instance_id"],
            "resolved": False,
            "status": "completed",
        }

    monkeypatch.setattr(module, "run_task", fake_task)
    tasks = [{"instance_id": f"task-{i}"} for i in range(20)]
    rows = module.smoke(tmp_path, {}, tmp_path, tmp_path, tasks, continue_on_error=True)
    assert len(rows) == 20 and rows[0]["resolved"] is None
    assert len(list(tmp_path.glob("task-*/result.json"))) == 20
    assert json.loads((tmp_path / "progress.json").read_text())["errors"] == 1
