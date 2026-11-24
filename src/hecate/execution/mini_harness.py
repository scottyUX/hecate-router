"""Adapters for the unmodified, vendored upstream mini-SWE-agent v1 core."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx

from hecate.execution.task_environment import docker, protected_test_path


@dataclass
class AdapterConfig:
    cwd: str = "/testbed"


class EpisodeBudget(Exception):
    """The pre-registered episode wall budget expired."""


class ModelContextExceeded(Exception):
    """The trajectory exceeded the declared context window."""


class ShellSandbox:
    """Same isolation as the Codex arm, without its inference relay or tools."""

    config = AdapterConfig()

    def __init__(
        self,
        image: str,
        workspace: Path,
        directory: Path,
        timeout: int,
        deadline: float,
    ):
        self.image, self.workspace, self.directory = image, workspace, directory
        self.timeout, self.deadline = timeout, deadline
        self.name = "task003-agent-" + uuid.uuid4().hex[:10]
        self.calls = 0

    def __enter__(self):
        immutable = ["-v", f"{self.workspace.resolve()}/.git:/testbed/.git:ro"]
        for path in self.workspace.rglob("*"):
            rel = path.relative_to(self.workspace)
            if (
                ".git" not in rel.parts
                and path.is_file()
                and protected_test_path(str(rel))
            ):
                immutable.extend(["-v", f"{path.resolve()}:/testbed/{rel}:ro"])
        docker(
            "run",
            "-d",
            "--name",
            self.name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "256",
            "--memory",
            "8g",
            "--cpus",
            "4",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--tmpfs",
            "/tmp:rw,exec,size=512m,mode=1777",
            "-v",
            f"{self.workspace.resolve()}:/testbed:rw",
            *immutable,
            "-w",
            "/testbed",
            "-e",
            "HOME=/tmp/home",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-e",
            "PATH=/opt/miniconda3/envs/testbed/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            self.image,
            "bash",
            "-lc",
            "mkdir -p /tmp/home && exec sleep infinity",
        )
        return self

    def execute(self, command: str, cwd: str = "") -> dict:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise EpisodeBudget()
        timeout = max(0.1, min(self.timeout, remaining))
        started = time.monotonic()
        result = docker(
            "exec",
            "-w",
            cwd or "/testbed",
            self.name,
            "timeout",
            "--signal=TERM",
            "--kill-after=2s",
            f"{timeout}s",
            "bash",
            "-lc",
            command,
            timeout=int(timeout) + 15,
            check=False,
        )
        output = {
            "output": result.stdout + result.stderr,
            "returncode": result.returncode,
        }
        self.calls += 1
        with (self.directory / "commands.jsonl").open("a") as stream:
            stream.write(
                json.dumps(
                    {"command": command, "wall_s": time.monotonic() - started, **output}
                )
                + "\n"
            )
        if result.returncode in {124, 137}:
            raise subprocess.TimeoutExpired(
                command, timeout, output=output["output"].encode()
            )
        return output

    def __exit__(self, *_):
        docker("rm", "-f", self.name, check=False)


class LocalChatModel:
    """Plain chat, no tool schema; record raw responses before interpreting them."""

    config = AdapterConfig()
    cost = 0.0

    def __init__(self, cfg: dict, directory: Path, deadline: float):
        self.cfg, self.directory, self.deadline = cfg, directory, deadline
        self.n_calls = 0
        self.metrics = []

    def query(self, messages: list[dict], **kwargs) -> dict:
        if time.monotonic() >= self.deadline:
            raise EpisodeBudget()
        self.n_calls += 1
        payload = {
            "model": self.cfg["model"]["id"],
            "messages": messages,
            "stream": False,
            **self.cfg["model"]["sampling"],
        }
        started = time.monotonic()
        record = {"request": self.n_calls, "messages": messages, "attempts": []}
        try:
            for attempt in range(self.cfg["limits"]["retries"] + 1):
                remaining = self.deadline - time.monotonic()
                if remaining <= 0:
                    raise EpisodeBudget()
                try:
                    with httpx.Client(
                        timeout=min(self.cfg["limits"]["request_timeout_s"], remaining),
                        trust_env=False,
                    ) as client:
                        response = client.post(
                            self.cfg["serving"]["endpoint"] + "/chat/completions",
                            json=payload,
                        )
                    record["attempts"].append(
                        {"status_code": response.status_code, "body": response.text}
                    )
                    if response.status_code == 400 and any(
                        s in response.text.lower()
                        for s in ("context length", "maximum context", "max_model_len")
                    ):
                        raise ModelContextExceeded(response.text)
                    response.raise_for_status()
                    raw = response.json()
                    metric = {
                        "request": self.n_calls,
                        "inference_wall_s": time.monotonic() - started,
                        "usage": raw.get("usage"),
                        "finish_reason": raw["choices"][0].get("finish_reason"),
                    }
                    self.metrics.append(metric)
                    record.update(metric)
                    content = raw["choices"][0]["message"].get("content")
                    # Empty/truncated output gets native agent format-error feedback.
                    return {"content": content or ""}
                except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                    record["attempts"].append({"error": str(exc)})
                    if (
                        isinstance(exc, httpx.HTTPStatusError)
                        and exc.response.status_code < 500
                    ):
                        raise
                    if attempt == self.cfg["limits"]["retries"]:
                        raise
            raise AssertionError("Unreachable retry exit")
        finally:
            record["total_wall_s"] = time.monotonic() - started
            with (self.directory / "model.jsonl").open("a") as stream:
                stream.write(json.dumps(record) + "\n")
