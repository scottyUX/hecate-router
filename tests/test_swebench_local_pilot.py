from types import SimpleNamespace
import json
from pathlib import Path
import importlib.util
import subprocess

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
    assert config["serving"]["message_layout"] == "single_system_prefix"


def test_single_system_layout_preserves_instructions_and_conversation_order():
    from hecate.execution.model_gateway import translate_request
    body = {"instructions": "base policy", "input": [
        {"role": "developer", "content": "developer one"},
        {"role": "user", "content": "task"},
        {"role": "developer", "content": "developer two"},
        {"role": "assistant", "content": "working"},
    ]}
    original, _ = translate_request(body, "local", {})
    merged, _ = translate_request(body, "local", {}, message_layout="single_system_prefix")
    assert sum(m["role"] == "system" for m in original["messages"]) == 3
    assert merged["messages"][0] == {"role": "system", "content": "base policy\n\ndeveloper one\n\ndeveloper two"}
    assert merged["messages"][1:] == [m for m in original["messages"] if m["role"] != "system"]


def test_single_system_layout_preserves_tool_history():
    from hecate.execution.model_gateway import translate_request
    body = {"input": [{"role": "user", "content": "task"},
                      {"role": "developer", "content": "instructions"},
                      {"type": "function_call", "name": "exec_command", "call_id": "c", "arguments": '{"cmd":"ls"}'},
                      {"type": "function_call_output", "call_id": "c", "output": "source.py"}]}
    raw, _ = translate_request(body, "local", {})
    merged, _ = translate_request(body, "local", {}, message_layout="single_system_prefix")
    assert merged["messages"][1:] == [m for m in raw["messages"] if m["role"] != "system"]


@pytest.mark.parametrize("changed", [False, True])
def test_export_accepts_empty_setup_commit_but_rejects_source_changes(tmp_path, monkeypatch, changed):
    repository = tmp_path / "image-repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    (repository / "source.py").write_text("value=1\n")
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    commit = ["git", "-C", str(repository), "-c", "user.name=Fixture", "-c", "user.email=fixture@localhost", "commit", "-qm"]
    subprocess.run(commit + ["base"], check=True)
    base = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
    if changed:
        (repository / "source.py").write_text("value=2\n")
        subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(commit + ["setup", "--allow-empty"], check=True)
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    spec = importlib.util.spec_from_file_location("swe_pilot", "scripts/run_qwen36_swebench_pilot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = subprocess.check_output
    def docker(*args, **kwargs):
        stdout = ""
        if args[0] == "exec":
            stdout = original(["git", "-C", str(repository), *args[5:]], text=True)
        return subprocess.CompletedProcess(args, 0, stdout, "")
    def archive(command, **kwargs):
        if command[0] == "docker":
            return original(["git", "-C", str(repository), "archive", command[-1]], **kwargs)
        return original(command, **kwargs)
    monkeypatch.setattr(module, "docker", docker)
    monkeypatch.setattr(module.subprocess, "check_output", archive)
    workspace = tmp_path / "workspace"
    if changed:
        with pytest.raises(ValueError, match="source tree differs"):
            module.export_workspace(SimpleNamespace(instance_image_key="fixture"), base, workspace)
    else:
        result = module.export_workspace(SimpleNamespace(instance_image_key="fixture"), base, workspace)
        assert result["exported_revision"] == base and result["image_head"] != base
        assert (workspace / "source.py").read_text() == "value=1\n"
        assert original(["git", "-C", str(workspace), "rev-list", "--count", "HEAD"], text=True).strip() == "1"
