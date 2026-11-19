"""Checks for the genuine upstream loop and Hecate isolation/budget adapters."""

import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from hecate.execution.mini_harness import (
    AdapterConfig,
    EpisodeBudget,
    LocalChatModel,
    ShellSandbox,
)

VENDOR = Path(__file__).resolve().parents[1] / "vendor/mini-swe-agent-v1"
sys.path.insert(0, str(VENDOR))
from microsweagent.agents.default import DefaultAgent, FormatError, Submitted


def test_upstream_unchanged():
    provenance = json.loads((VENDOR / "provenance.json").read_text())
    assert provenance["commit"] == "a2b0efee5fd9c1d3bc9fdfc6fe88036a2235d74d"
    for name, digest in provenance["sha256"].items():
        assert hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() == digest


def test_upstream_bash_contract_and_submission():
    agent = DefaultAgent(
        SimpleNamespace(config=AdapterConfig()), SimpleNamespace(config=AdapterConfig())
    )
    assert (
        agent.parse_action({"content": "```bash\necho hello\n```"})["action"]
        == "echo hello"
    )
    with pytest.raises(FormatError):
        agent.parse_action({"content": "I am finished"})
    with pytest.raises(Submitted):
        agent.has_finished({"output": "MICRO_SWE_AGENT_FINAL_OUTPUT\nfixed"})


def test_expired_episode_never_sends_request(tmp_path):
    model = LocalChatModel({}, tmp_path, time.monotonic() - 1)
    with pytest.raises(EpisodeBudget):
        model.query([])
    assert model.n_calls == 0


def test_shell_immutable_bindings_and_timeout(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    (tmp_path / "test_example.py").write_text("assert True")
    calls = []

    def fake(*args, **kw):
        calls.append(args)
        return SimpleNamespace(
            stdout="", stderr="", returncode=124 if args[0] == "exec" else 0
        )

    monkeypatch.setattr("hecate.execution.mini_harness.docker", fake)
    sandbox = ShellSandbox("image", tmp_path, tmp_path, 120, time.monotonic() + 1000)
    import subprocess

    with sandbox:
        with pytest.raises(subprocess.TimeoutExpired):
            sandbox.execute("sleep 999")
    launch = calls[0]
    assert "none" in launch and "--read-only" in launch
    assert f"{tmp_path}/.git:/testbed/.git:ro" in launch
    assert f"{tmp_path}/test_example.py:/testbed/test_example.py:ro" in launch
    assert not any("docker.sock" in arg for arg in launch)
    assert "--kill-after=2s" in calls[1]


def test_parallel_launch_rejects_unexpected_gpu(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts/serve_codex_qwen7b.py"
    spec = importlib.util.spec_from_file_location("mini_serve", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.platform, "machine", lambda: "aarch64")
    monkeypatch.setattr(
        module.subprocess,
        "check_output",
        lambda args, **kw: "999\n" if args[0] == "nvidia-smi" else "PID\n123\n",
    )
    config = Path(__file__).resolve().parents[1] / "configs/mini_qwen7b_pilot.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "serve",
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--alongside-task002",
        ],
    )
    with pytest.raises(RuntimeError, match="Unexpected GPU process"):
        module.main()
