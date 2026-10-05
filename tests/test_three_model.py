"""Offline tests for the three-model Verified experiment runner."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # @dataclass resolves its module via sys.modules.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUN = _load("run_three_model")
SELECT = _load("select_three_model_tasks")


def test_task_file_has_100_unique_ids() -> None:
    ids = RUN.load_task_ids(ROOT / RUN.TASKS_FILE)
    assert len(ids) == 100
    assert len(set(ids)) == 100


def test_selection_is_deterministic_and_order_independent() -> None:
    rows = [
        {"instance_id": f"r__r-{i}", "repo": "r/r", "difficulty": "<15 min fix"}
        for i in range(300)
    ]
    forward = SELECT.select(rows)
    backward = SELECT.select(list(reversed(rows)))
    assert forward == backward
    assert len(forward) == SELECT.N_TASKS


def test_global_caps_sum_to_experiment_budget() -> None:
    assert sum(s.global_cost_limit_usd for s in RUN.MODELS.values()) == 250.0


def test_filter_spec_matches_exactly_the_set() -> None:
    pattern = re.compile(RUN.filter_spec_for(("a__a-1", "b__b-2")))
    assert pattern.match("a__a-1")
    assert not pattern.match("a__a-10")
    assert not pattern.match("c__c-3")


def test_overrides_set_provider_order_per_model() -> None:
    spec = RUN.MODELS["minimax"]
    overrides = RUN.config_overrides_for(spec, Path("cfg.yaml"))
    assert overrides[0] == "cfg.yaml"
    key, value = overrides[1].split("=", 1)
    assert key == "model.model_kwargs.extra_body.provider.order"
    assert json.loads(value) == ["minimax"]


def test_shared_config_has_no_per_task_cap_and_same_prompt_as_sanity() -> None:
    three = yaml.safe_load((ROOT / "configs/miniswe_three_model.yaml").read_text())
    sanity = yaml.safe_load((ROOT / "configs/miniswe_verified_single.yaml").read_text())
    assert three["agent"]["cost_limit"] == 0
    assert three["agent"]["step_limit"] == sanity["agent"]["step_limit"]
    assert three["agent"]["instance_template"] == sanity["agent"]["instance_template"]
    assert three["environment"] == sanity["environment"]


def test_prune_infra_failures_drops_only_trajectoryless(tmp_path: Path) -> None:
    (tmp_path / "ran").mkdir()
    (tmp_path / "ran" / "ran.traj.json").write_text("{}")
    (tmp_path / "preds.json").write_text(
        json.dumps({"ran": {"model_patch": "x"}, "never": {"model_patch": ""}})
    )
    assert RUN.prune_infra_failures(tmp_path) == ["never"]
    assert set(json.loads((tmp_path / "preds.json").read_text())) == {"ran"}
    assert list(tmp_path.glob("preds.json.bak-*"))


def test_prune_requeues_cost_tracking_crash_and_keeps_its_trajectory(tmp_path: Path) -> None:
    (tmp_path / "crashed").mkdir()
    (tmp_path / "crashed" / "crashed.traj.json").write_text(
        json.dumps({"info": {"exit_status": "RuntimeError",
                             "traceback": "RuntimeError: Error calculating cost for model x"}})
    )
    (tmp_path / "ok").mkdir()
    (tmp_path / "ok" / "ok.traj.json").write_text(
        json.dumps({"info": {"exit_status": "Submitted"}})
    )
    (tmp_path / "preds.json").write_text(json.dumps({"crashed": {}, "ok": {}}))
    assert RUN.prune_infra_failures(tmp_path) == ["crashed"]
    assert set(json.loads((tmp_path / "preds.json").read_text())) == {"ok"}
    assert not (tmp_path / "crashed").exists()
    assert len(list((tmp_path / "_infra_failed").glob("crashed-*/crashed.traj.json"))) == 1


def test_only_gemini_ignores_cost_tracking_errors() -> None:
    for key, spec in RUN.MODELS.items():
        overrides = RUN.config_overrides_for(spec, Path("cfg.yaml"))
        assert ("model.cost_tracking=ignore_errors" in overrides) == (key == "gemini")
