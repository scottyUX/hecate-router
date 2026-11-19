"""Offline contract tests for TASK-001; no model, Docker or provider calls."""
import json
import subprocess

import httpx
import pytest

from hecate.execution.codex_artifacts import create_run, finish_run, verify_mirror
from hecate.execution.codex_session import run_process
from hecate.execution.model_gateway import (
    Gateway,
    ProtocolError,
    response_events,
    translate_request,
    translate_response,
)
from hecate.execution.task_environment import (
    collect_patch,
    protected_test_path,
    validate_id,
)


def request():
    return {
        "instructions": "Local fixture",
        "input": [
            {"role": "user", "content": [{"type": "input_text", "text": "Fix source"}]}
        ],
        "tools": [
            {
                "type": "function",
                "name": "exec_command",
                "parameters": {
                    "type": "object",
                    "properties": {"cmd": {"type": "string"}},
                },
            },
            {"type": "custom", "name": "apply_patch", "description": "Patch tool"},
            {"type": "function", "name": "request_user_input"},
        ],
    }


def completion(name="exec_command", arguments='{"cmd":"echo hello"}'):
    return {
        "model": "local",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "function": {"name": name, "arguments": arguments},
                        }
                    ],
                },
            }
        ],
    }


def test_tool_history_and_custom_round_trip():
    body = request()
    payload, contract = translate_request(body, "Qwen/test", {"temperature": 0})
    assert payload["messages"][0]["role"] == "system"
    assert contract["removed"] == ["request_user_input"]
    result = translate_response(
        completion(
            "apply_patch", json.dumps({"input": "*** Begin Patch\n*** End Patch"})
        ),
        contract,
    )
    assert result["output"][0]["type"] == "custom_tool_call"
    assert result["usage"] is None
    body["input"] += result["output"] + [
        {"type": "custom_tool_call_output", "call_id": "call-1", "output": "Success"}
    ]
    payload, _ = translate_request(body, "Qwen/test", {})
    assert payload["messages"][-2]["tool_calls"][0]["id"] == "call-1"
    assert payload["messages"][-1] == {
        "role": "tool",
        "tool_call_id": "call-1",
        "content": "Success",
    }


def test_fragmented_sse_arguments_reconstruct_exactly():
    _, contract = translate_request(request(), "local", {})
    result = translate_response(
        completion(arguments=json.dumps({"cmd": "echo " + ("x" * 200)})), contract
    )
    wire = response_events(result).decode()
    events = [json.loads(x[6:]) for x in wire.splitlines() if x.startswith("data: ")]
    deltas = [
        e["delta"]
        for e in events
        if e["type"] == "response.function_call_arguments.delta"
    ]
    assert len(deltas) > 1
    assert "".join(deltas) == result["output"][0]["arguments"]
    assert events[-1]["response"] == result
    assert [e["sequence_number"] for e in events] == list(range(len(events)))
    assert "timeout --signal=TERM" in json.loads("".join(deltas))["cmd"]


@pytest.mark.parametrize(
    "change",
    [
        {"previous_response_id": "hidden"},
        {"input": [{"type": "input_image"}]},
        {
            "input": [
                {"type": "function_call_output", "call_id": "missing", "output": "oops"}
            ]
        },
    ],
)
def test_unsupported_requests_fail(change):
    with pytest.raises((ProtocolError, KeyError)):
        translate_request({**request(), **change}, "local", {})


def test_truncated_or_unadvertised_calls_fail():
    _, contract = translate_request(request(), "local", {})
    raw = completion()
    raw["choices"][0]["finish_reason"] = "length"
    with pytest.raises(ProtocolError):
        translate_response(raw, contract)
    with pytest.raises(ProtocolError):
        translate_response(completion("web_search", "{}"), contract)
    with pytest.raises(ProtocolError):
        translate_response(
            completion(
                arguments='{"cmd":"id","sandbox_permissions":"require_escalated"}'
            ),
            contract,
        )


def test_bounded_retries_usage_and_request_cap(tmp_path, monkeypatch):
    monkeypatch.setattr("hecate.execution.model_gateway.time.sleep", lambda _: None)
    calls = []

    def transport(payload):
        calls.append(payload)
        if len(calls) < 3:
            raise httpx.ConnectError("fixture")
        raw = completion()
        raw["usage"] = {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15}
        return raw

    gateway = Gateway(
        tmp_path / "socket",
        "http://127.0.0.1:8126/v1",
        "local",
        tmp_path,
        request_limit=1,
        sampling={},
        transport=transport,
    )
    result = gateway.complete(request())
    assert len(calls) == 3 and gateway.requests == 1
    assert result["usage"]["input_tokens"] == 12
    assert gateway.metrics[0]["retries"] == 2
    with pytest.raises(ProtocolError):
        gateway.complete(request())
    assert gateway.cap_hit


def test_permanent_failure_not_retried(tmp_path):
    calls = []

    def transport(_):
        calls.append(1)
        response = httpx.Response(
            400, request=httpx.Request("POST", "http://localhost")
        )
        raise httpx.HTTPStatusError(
            "bad request", request=response.request, response=response
        )

    gateway = Gateway(
        tmp_path / "s",
        "http://localhost:8000/v1",
        "local",
        tmp_path,
        request_limit=10,
        sampling={},
        transport=transport,
    )
    with pytest.raises(httpx.HTTPStatusError):
        gateway.complete(request())
    assert len(calls) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com/v1",
        "http://other-host/v1",
        "http://key:secret@localhost:8000/v1",
    ],
)
def test_hosted_or_credentialed_upstreams_rejected(tmp_path, url):
    with pytest.raises(ValueError):
        Gateway(tmp_path / "s", url, "local", tmp_path, request_limit=1, sampling={})


def test_process_timeout_and_final_event(tmp_path):
    result = run_process(
        ["python3", "-c", "import time; time.sleep(10)"], tmp_path, 0.15
    )
    assert (
        result["termination_reason"] == "budget_exhausted" and result["exit_code"] != 0
    )
    result = run_process(
        ["python3", "-c", 'print(\'{"type":"turn.completed"}\')'], tmp_path, 5
    )
    assert result["termination_reason"] == "completed"
    result = run_process(["python3", "-c", 'print("not-json")'], tmp_path, 5)
    assert result["termination_reason"] == "tool_protocol_failure"


def test_patch_includes_new_files_and_rejects_tests(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "source.py").write_text("value=1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=test@local",
            "commit",
            "-qm",
            "base",
        ],
        check=True,
    )
    (tmp_path / "new.py").write_text("value=2\n")
    (tmp_path / "test_new.py").write_text("assert True\n")
    patch, rejected = collect_patch(tmp_path)
    assert "new.py" in patch and rejected == ["test_new.py"]
    assert protected_test_path("tests/foo.py") and protected_test_path("conftest.py")
    with pytest.raises(ValueError):
        validate_id("../../escape")


def test_immutable_attempt_and_verified_copy(tmp_path):
    import shutil

    root = create_run(tmp_path, "attempt", {}, {})
    finish_run(root, {"verdict": "compatible"})
    with pytest.raises(FileExistsError):
        create_run(tmp_path, "attempt", {}, {})
    mirror = tmp_path / "mirror"
    shutil.copytree(root, mirror)
    with pytest.raises(ValueError):
        verify_mirror(root, mirror, off_spark=False)
    assert verify_mirror(root, mirror, off_spark=True)["status"] == "verified_off_spark"
    (mirror / "results.json").write_text("{}")
    with pytest.raises(ValueError):
        verify_mirror(root, mirror, off_spark=True)


def test_required_decoding_finish_is_explicit_and_not_a_tool_execution():
    payload, contract = translate_request(
        request(), "local", {}, "required_with_finish"
    )
    assert payload["tool_choice"] == "required"
    assert "hecate_finish" in contract["allowed"]
    raw = completion(
        "hecate_finish", json.dumps({"response": "Read the file successfully."})
    )
    result = translate_response(raw, contract)
    assert result["output"][0]["type"] == "message"
    assert result["output"][0]["content"][0]["text"] == "Read the file successfully."
    _, automatic = translate_request(request(), "local", {})
    with pytest.raises(ProtocolError):
        translate_response(raw, automatic)


def test_evaluator_missing_test_is_infrastructure_failure(tmp_path, monkeypatch):
    from hecate.execution import task_environment as environment

    calls = []

    def fake_docker(*args, **kwargs):
        calls.append(args)
        stdout = ""
        if args[0] == "exec" and "diff" in args:
            stdout = "tests/test_example.py\n"
        if args[0] == "exec" and "pytest" in args:
            stdout = "tests/test_example.py::test_other PASSED\n"
        return subprocess.CompletedProcess(args, 0, stdout, "")

    monkeypatch.setattr(environment, "docker", fake_docker)
    instance = {
        "instance_id": "fixture-1",
        "FAIL_TO_PASS": ["tests/test_example.py::test_fix"],
        "PASS_TO_PASS": [],
    }
    outcome = environment.grade_patch("fixture-image", instance, "", tmp_path / "eval")
    assert outcome["status"] == "evaluator_failure" and outcome["resolved"] is None
    assert any(args[:2] == ("rm", "-f") for args in calls)
    with pytest.raises(FileExistsError):
        environment.grade_patch("fixture-image", instance, "", tmp_path / "eval")


def test_evaluator_real_test_failure_is_unresolved(tmp_path, monkeypatch):
    from hecate.execution import task_environment as environment

    def fake_docker(*args, **kwargs):
        tests = args[0] == "exec" and "pytest" in args
        output = (
            "tests/test_example.py::test_fix FAILED\ntests/test_example.py::test_stable PASSED\n"
            if tests
            else ""
        )
        return subprocess.CompletedProcess(args, 1 if tests else 0, output, "")

    monkeypatch.setattr(environment, "docker", fake_docker)
    instance = {
        "instance_id": "fixture-1",
        "FAIL_TO_PASS": ["tests/test_example.py::test_fix"],
        "PASS_TO_PASS": ["tests/test_example.py::test_stable"],
    }
    outcome = environment.grade_patch("fixture-image", instance, "", tmp_path / "eval")
    assert outcome["status"] == "completed" and outcome["resolved"] is False


def test_cancelled_or_failed_session_preserves_evidence(tmp_path):
    result = run_process(["python3", "-c", "raise SystemExit(7)"], tmp_path, 5)
    assert (
        result["termination_reason"] == "process_failure" and result["exit_code"] == 7
    )
    result = run_process(
        ["python3", "-c", "import time;time.sleep(10)"],
        tmp_path,
        5,
        stop=lambda: "model_server_failure",
    )
    assert result["termination_reason"] == "model_server_failure"
    assert (tmp_path / "codex_stderr.log").exists()


def test_shell_fallback_is_explicit_and_patch_calls_are_rejected():
    payload, contract = translate_request(
        request(), "local", {}, "required_with_finish", "shell"
    )
    assert "apply_patch" in contract["removed"]
    assert "apply_patch" not in contract["allowed"]
    with pytest.raises(ProtocolError):
        translate_response(
            completion(
                "apply_patch", json.dumps({"input": "*** Begin Patch\n*** End Patch"})
            ),
            contract,
        )
    assert payload["tool_choice"] == "required"


def test_smoke_requires_matching_passing_fixture_gate(tmp_path):
    from hecate.execution.codex_session import require_fixture_gate

    config = {"model": {"id": "local"}}
    (tmp_path / "manifest.json").write_text(json.dumps({"config": config}))
    (tmp_path / "isolation.json").write_text(json.dumps({"passed": True}))
    (tmp_path / "results.json").write_text(
        json.dumps({"mode": "fixtures", "rows": [{"passed": True}] * 3})
    )
    require_fixture_gate(tmp_path, config)
    with pytest.raises(ValueError):
        require_fixture_gate(tmp_path, {"model": {"id": "different"}})
    (tmp_path / "results.json").write_text(
        json.dumps({"mode": "fixtures", "rows": [{"passed": False}] * 3})
    )
    with pytest.raises(ValueError):
        require_fixture_gate(tmp_path, config)


def test_timeout_wrapper_not_echoed_into_model_history(tmp_path):
    observed = []

    def transport(payload):
        observed.append(payload)
        return completion()

    gateway = Gateway(
        tmp_path / "s",
        "http://127.0.0.1:8126/v1",
        "local",
        tmp_path,
        request_limit=2,
        sampling={},
        transport=transport,
    )
    result = gateway.complete(request())
    body = request()
    body["input"] += result["output"] + [
        {"type": "function_call_output", "call_id": "call-1", "output": "hello"}
    ]
    gateway.complete(body)
    arguments = observed[1]["messages"][-2]["tool_calls"][0]["function"]["arguments"]
    assert json.loads(arguments) == {"cmd": "echo hello"}


def test_archive_retains_contained_file_link_and_blocks_escape(tmp_path):
    import io
    import tarfile
    from hecate.execution.task_environment import extract_task_archive

    def archive(link):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as tar:
            item = tarfile.TarInfo("doc/source/index.rst")
            content = b"Fixture readme\n"
            item.size = len(content)
            tar.addfile(item, io.BytesIO(content))
            item = tarfile.TarInfo("README.rst")
            item.type = tarfile.SYMTYPE
            item.linkname = link
            tar.addfile(item)
        return stream.getvalue()

    target = tmp_path / "safe"
    extract_task_archive(archive("doc/source/index.rst"), target)
    assert (target / "README.rst").is_symlink()
    assert (target / "README.rst").read_text() == "Fixture readme\n"
    for i, link in enumerate(["/etc/passwd", "../../outside", "absent-file"]):
        with pytest.raises(ValueError):
            extract_task_archive(archive(link), tmp_path / f"unsafe-{i}")
    assert not (tmp_path.parent / "outside").exists()


def test_patch_collection_error_is_unresolved_only_after_valid_controls(
    tmp_path, monkeypatch
):
    from hecate.execution import task_environment as environment

    def fake_docker(*args, **kwargs):
        tests = args[0] == "exec" and "pytest" in args
        return subprocess.CompletedProcess(
            args,
            2 if tests else 0,
            "Interrupted: 6 errors during collection" if tests else "",
            "",
        )

    monkeypatch.setattr(environment, "docker", fake_docker)
    instance = {
        "instance_id": "fixture-1",
        "FAIL_TO_PASS": ["tests/test_example.py::test_fix"],
        "PASS_TO_PASS": [],
    }
    failed = environment.grade_patch(
        "fixture", instance, "model patch", tmp_path / "unvalidated"
    )
    assert failed["status"] == "evaluator_failure" and failed["resolved"] is None
    scored = environment.grade_patch(
        "fixture",
        instance,
        "model patch",
        tmp_path / "validated",
        validated_controls=True,
    )
    assert scored["status"] == "completed" and scored["resolved"] is False
    assert scored["reason"] == "patch_broke_test_collection"


def test_artifact_checksums_never_follow_external_model_links(tmp_path):
    from hecate.execution.codex_artifacts import checksums

    outside = tmp_path / "outside"
    outside.write_text("harmless host-only marker")
    root = tmp_path / "run"
    root.mkdir()
    (root / "model-created-link").symlink_to(outside)
    digest = checksums(root)
    assert digest["model-created-link"].startswith("link:")
    with pytest.raises(ValueError):
        checksums(root, legacy_links=True)


def test_unpatched_collection_failure_needs_gold_and_empty_p2p(tmp_path, monkeypatch):
    from hecate.execution import task_environment as environment

    def fake_docker(*args, **kwargs):
        tests = args[0] == "exec" and "pytest" in args
        return subprocess.CompletedProcess(
            args,
            2 if tests else 0,
            "Interrupted: 4 errors during collection" if tests else "",
            "",
        )

    monkeypatch.setattr(environment, "docker", fake_docker)
    instance = {
        "instance_id": "fixture-1",
        "FAIL_TO_PASS": ["tests/test_example.py::test_fix"],
        "PASS_TO_PASS": [],
    }
    valid = environment.grade_patch(
        "fixture", instance, "", tmp_path / "validated", verified_gold=True
    )
    assert valid["status"] == "completed" and valid["resolved"] is False
    assert valid["reason"] == "unpatched_bug_broke_test_collection"
    unknown = environment.grade_patch("fixture", instance, "", tmp_path / "unknown")
    assert unknown["status"] == "evaluator_failure"
    requires_p2p = {**instance, "PASS_TO_PASS": ["tests/test_example.py::stable"]}
    missing = environment.grade_patch(
        "fixture", requires_p2p, "", tmp_path / "p2p", verified_gold=True
    )
    assert missing["status"] == "evaluator_failure"


def test_output_budget_failure_retains_raw_response_and_usage(tmp_path):
    from hecate.execution.model_gateway import OutputBudgetExceeded

    raw = completion()
    raw["choices"][0]["finish_reason"] = "length"
    raw["usage"] = {
        "prompt_tokens": 100,
        "completion_tokens": 2048,
        "total_tokens": 2148,
    }
    gateway = Gateway(
        tmp_path / "s",
        "http://127.0.0.1:8126/v1",
        "local",
        tmp_path,
        request_limit=1,
        sampling={},
        transport=lambda _: raw,
    )
    with pytest.raises(OutputBudgetExceeded):
        gateway.complete(request())
    assert gateway.metrics[0]["failed"] is True
    assert gateway.metrics[0]["usage"]["output_tokens"] == 2048
    records = [
        json.loads(line)
        for line in (tmp_path / "gateway.jsonl").read_text().splitlines()
    ]
    assert any(
        r.get("event") == "upstream_response"
        and r["response"]["choices"][0]["finish_reason"] == "length"
        for r in records
    )
