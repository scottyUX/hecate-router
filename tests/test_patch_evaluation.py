"""Regressions for correctness hidden by policy and execution failures."""
import importlib.util

import httpx
import pytest

from hecate.execution.codex_pilot import should_halt
from hecate.execution.model_gateway import failure_kind, ProtocolError
from hecate.execution.patch_evaluation import evaluation_patch, outcome_axes, correctness_summary

SOURCE = "diff --git a/source.py b/source.py\n--- a/source.py\n+++ b/source.py\n@@ -1 +1 @@\n-bug\n+fix\n"
TEST = "diff --git a/test_new.py b/test_new.py\nnew file mode 100644\n--- /dev/null\n+++ b/test_new.py\n@@ -0,0 +1 @@\n+assert True\n"


def runner():
    spec = importlib.util.spec_from_file_location("evaluation_runner", "scripts/run_codex_baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_projection_keeps_source_verbatim_and_omits_new_tests():
    patch, meta = evaluation_patch(SOURCE + TEST, ["test_new.py"])
    assert patch == SOURCE
    assert meta["excluded_new_test_files"] == ["test_new.py"]
    assert meta["original_sha256"] != meta["evaluation_sha256"]
    assert evaluation_patch(TEST, ["test_new.py"])[0] == ""
    assert evaluation_patch("", [])[0] == ""


@pytest.mark.parametrize("patch,paths", [
    (TEST.replace("new file mode 100644\n", ""), ["test_new.py"]),
    (TEST, []),
    (SOURCE, ["tests/missing.py"]),
    (SOURCE.replace("+++ b/source.py", "+++ b/tests/hidden.py"), []),
    (SOURCE.replace("source.py", "../outside.py"), []),
    (SOURCE.replace("source.py", ".git/config"), []),
    (SOURCE.replace("--- a/source.py", "rename from source.py\nrename to tests/x.py\n--- a/source.py"), []),
    ("not a diff", []),
])
def test_projection_fails_closed(patch, paths):
    with pytest.raises(ValueError):
        evaluation_patch(patch, paths)


@pytest.mark.parametrize("termination,added,status,resolved", [
    ("completed", True, "completed", True),
    ("tool_protocol_failure", False, "completed", True),
    ("model_server_failure", False, "completed", True),
    ("context_budget_exhausted", False, "completed", True),
    ("request_budget_exhausted", False, "completed", True),
    ("completed", False, "completed", False),
    ("completed", False, "evaluator_failure", None),
])
def test_runner_grades_patch_independent_of_termination(tmp_path, monkeypatch, termination, added, status, resolved):
    module = runner()
    seen = []
    def grade(image, instance, patch, output, **kwargs):
        if output.name == "control-patched":
            return {"status": "completed", "resolved": True}
        if output.name == "control-unpatched":
            return {"status": "completed", "resolved": False, "f2p": {"test": "FAILED"}, "p2p": {}}
        seen.append(patch)
        return {"status": status, "resolved": resolved}
    def execute(workspace, directory, *args, **kwargs):
        directory.mkdir()
        (directory / "patch.diff").write_text(SOURCE + (TEST if added else ""))
        return {"termination_reason": termination, "test_modifications": ["test_new.py"] if added else []}
    monkeypatch.setattr(module, "grade_patch", grade)
    monkeypatch.setattr(module, "export_task_tree", lambda *args: "base")
    row = module.run_task(tmp_path, {"sandbox": {"image": "fixture"}}, None, None,
                          {"instance_id": "example", "problem_statement": "fix"}, executor=execute)
    assert seen == [SOURCE] and row["resolved"] is resolved
    assert row["termination_reason"] == termination
    assert row["policy_compliant"] is (not added)
    assert row["clean_success"] is (resolved is True and termination == "completed" and not added)
    raw = tmp_path / "example/agent/patch.diff"
    assert raw.read_text() == SOURCE + (TEST if added else "")


def test_missing_patch_is_unknown_and_never_sent_to_evaluator(tmp_path, monkeypatch):
    module = runner()
    calls = []
    def grade(*args, **kwargs):
        calls.append(args[3].name)
        return {"status": "completed", "resolved": kwargs.get("gold", False)}
    def execute(*args, **kwargs):
        return {"termination_reason": "process_failure", "test_modifications": []}
    monkeypatch.setattr(module, "grade_patch", grade)
    monkeypatch.setattr(module, "export_task_tree", lambda *args: "base")
    row = module.run_task(tmp_path, {"sandbox": {"image": "fixture"}}, None, None,
                          {"instance_id": "example", "problem_statement": "fix"}, executor=execute)
    assert row["resolved"] is None and row["status"] == "patch_projection_failure"
    assert calls == ["control-patched", "control-unpatched"]


def test_passing_patches_do_not_disable_infrastructure_halt():
    row = {"resolved": True, "termination_reason": "model_server_failure", "status": "completed"}
    row.update(outcome_axes(row))
    assert should_halt([row] * 3, continue_on_error=True)
    budget = {**row, "termination_reason": "context_budget_exhausted"}
    budget.update(outcome_axes(budget))
    assert not should_halt([budget] * 3, continue_on_error=True)
    summary = correctness_summary([row, budget], 2)
    assert summary["resolved"] == 2 and summary["infrastructure_errors"] == 1
    assert summary["clean_successes"] == 0


@pytest.mark.parametrize("body,expected", [
    ("maximum context length is 16384 tokens", "context_budget_exhausted"),
    ('{"error":{"code":"context_length_exceeded"}}', "context_budget_exhausted"),
    ("Unsupported tool", "model_server_failure"),
])
def test_http400_is_not_always_context_exhaustion(body, expected):
    response = httpx.Response(400, text=body, request=httpx.Request("POST", "http://localhost"))
    exc = httpx.HTTPStatusError("error", request=response.request, response=response)
    assert failure_kind(exc) == expected
    assert failure_kind(ProtocolError("cap"), cap_hit=True) == "request_budget_exhausted"


@pytest.mark.parametrize("cap,kind,expected", [
    (True, "tool_protocol_failure", "request_budget_exhausted"),
    (False, "context_budget_exhausted", "context_budget_exhausted"),
    (False, "model_server_failure", "model_server_failure"),
])
def test_gateway_failure_survives_codex_exit_race(tmp_path, monkeypatch, cap, kind, expected):
    module = runner()
    class Gateway:
        cap_hit, failed, failure_kind = cap, not cap, kind
        requests, metrics = 1, []
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    class Sandbox:
        name = "fixture"
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def command(self, prompt): return []
    monkeypatch.setattr(module, "Gateway", Gateway)
    monkeypatch.setattr(module, "AgentSandbox", Sandbox)
    monkeypatch.setattr(module, "docker", lambda *args, **kwargs: None)
    monkeypatch.setattr(module.subprocess, "check_output", lambda *args, **kwargs: "base\n")
    monkeypatch.setattr(module, "model_catalog", lambda *args: {})
    monkeypatch.setattr(module, "collect_patch", lambda *args: (SOURCE, []))
    monkeypatch.setattr(module, "run_process", lambda *args, **kwargs: {"termination_reason": "tool_protocol_failure", "events": []})
    config = {"model": {"id": "fixture", "context_tokens": 16384, "sampling": {}},
              "serving": {"endpoint": "http://localhost:1234"}, "sandbox": {"image": "fixture"},
              "limits": {"task_model_requests": 40, "task_wall_s": 60, "request_timeout_s": 10, "retries": 0, "command_timeout_s": 10}}
    row = module.execute(tmp_path, tmp_path / "agent", "fix", config, tmp_path, tmp_path, fixture=False)
    assert row["termination_reason"] == expected


def test_replay_never_falls_back_to_inference(tmp_path, monkeypatch):
    module = runner()
    def grade(*args, **kwargs):
        return {"status": "completed", "resolved": kwargs.get("gold", False)}
    monkeypatch.setattr(module, "grade_patch", grade)
    def forbidden(*args, **kwargs):
        raise AssertionError("Replay attempted inference")
    monkeypatch.setattr(module, "execute", forbidden)
    with pytest.raises(ValueError, match="never generates"):
        module.run_task(tmp_path, {"sandbox": {"image": "fixture"}}, None, None,
                        {"instance_id": "example"}, reuse_agent_from=tmp_path / "missing")
