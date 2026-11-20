from types import SimpleNamespace
import json
from pathlib import Path

import pytest
import yaml
from hecate.execution.swebench_pilot import validate_pilot, required_outcomes


def test_exact_paper_model_and_task_scope():
    config = yaml.safe_load(Path("configs/qwen36_local_evaluator.yaml").read_text())
    manifest = json.loads(Path(config["selection_manifest"]).read_text())
    instance = {"instance_id": "django__django-16560"}
    validate_pilot(config, manifest, instance)
    config["model"]["id"] = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
    with pytest.raises(ValueError):
        validate_pilot(config, manifest, instance)


@pytest.mark.parametrize("change", ["checkpoint", "precision", "codex", "task", "count", "arch"])
def test_scope_rejects_unapproved_changes(change):
    config = yaml.safe_load(Path("configs/qwen36_local_evaluator.yaml").read_text())
    manifest = json.loads(Path(config["selection_manifest"]).read_text())
    section, key, value = {"checkpoint": ("model", "revision", "new"),
                           "precision": ("model", "precision", "fp8"),
                           "codex": ("codex", "version", "new"),
                           "task": ("evaluator", "instance_id", "other"),
                           "count": ("evaluator", "task_count", 45),
                           "arch": ("evaluator", "arch", "x86_64")}[change]
    config[section][key] = value
    with pytest.raises(ValueError):
        validate_pilot(config, manifest, {"instance_id": "django__django-16560"})


def test_missing_test_and_missing_markers_are_unknown_not_pass():
    spec = SimpleNamespace(FAIL_TO_PASS=["fix"], PASS_TO_PASS=["stable"])
    assert required_outcomes(spec, {"fix": "PASSED"}, True)["resolved"] is None
    statuses = {"fix": "PASSED", "stable": "PASSED"}
    assert required_outcomes(spec, statuses, False)["resolved"] is None
    assert required_outcomes(spec, statuses, True, timed_out=True)["resolved"] is None
    assert required_outcomes(spec, statuses, True)["resolved"] is True
    assert required_outcomes(spec, {**statuses, "fix": "FAILED"}, True)["resolved"] is False
    assert required_outcomes(spec, {**statuses, "stable": "ERROR"}, True)["resolved"] is False


def test_qwen36_serving_configuration_is_explicit():
    config = yaml.safe_load(Path("configs/qwen36_local_evaluator.yaml").read_text())
    assert config["serving"]["reasoning_parser"] == "qwen3"
    assert config["serving"]["language_model_only"] is True
    assert config["serving"]["parser"] == "qwen3_coder"
    assert config["model"]["context_tokens"] == 32768
