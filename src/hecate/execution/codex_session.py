"""Codex lifecycle and pinned model metadata, independent of model providers.

The embedded-catalog extraction/configuration approach is adapted from
Advisor Models' eval_codex.py (Apache-2.0). See docs/tasks/task-001-reuse-and-runbook.md
and docs/licenses/advisor-models-APACHE-2.0.txt for provenance and license.
"""
from __future__ import annotations
import copy
import json
import os
import signal
import subprocess
import time
from pathlib import Path

INSTRUCTIONS = """You are a coding agent working inside /testbed. Use native function calls, not fenced code blocks. Call exec_command with a JSON cmd string to inspect files and run visible tests. Call apply_patch to edit source when available. You must actually execute requested actions rather than print tool calls or patches as text. Use apply_patch when available; otherwise edit with shell commands. Do not modify test files. Never request sandbox escalation. Do not access the network or reference solutions. After completing the work, provide a concise final report based on observed command results."""


def model_catalog(binary: Path, model: str, context: int) -> dict:
    data = binary.read_bytes()
    index = data.find(b'"models": [')
    if index < 0:
        raise ValueError("Pinned Codex binary has no embedded model catalog")
    start = data.rfind(b"{", 0, index)
    catalog, _ = json.JSONDecoder().raw_decode(
        data[start : start + 4_000_000].decode("utf8", "replace")
    )
    base = next((x for x in catalog["models"] if x["slug"] == "gpt-5.5"), None)
    if base is None:
        raise ValueError("Expected metadata template absent from pinned Codex")
    entry = copy.deepcopy(base)
    entry.update(
        slug=model,
        display_name=model,
        description="Hecate local Qwen compatibility; metadata template gpt-5.5, explicit no-reasoning overrides",
        context_window=context,
        max_context_window=context,
        supported_reasoning_levels=[],
        supports_reasoning_summaries=False,
        supports_reasoning_summary_parameter=False,
        supports_reasoning_effort_updates=False,
        default_reasoning_level=None,
        supports_search_tool=False,
        input_modalities=["text"],
        supports_image_detail_original=False,
        prefer_websockets=False,
        service_tiers=[],
        additional_speed_tiers=[],
        upgrade=None,
        visibility="list",
    )
    return {"models": [entry]}


def config_text(model: str, context: int, *, native_instructions: bool = False) -> str:
    text = f"""model = {json.dumps(model)}
model_provider = "hecate"
model_context_window = {context}
model_catalog_json = "/opt/hecate-config/catalog.json"
model_instructions_file = "/opt/hecate-config/instructions.md"
web_search = "disabled"
[features]
multi_agent = false
goals = false
image_generation = false
computer_use = false
in_app_browser = false
browser_use = false
browser_use_external = false
apps = false
memories = false
[model_providers.hecate]
name = "Hecate local gateway"
base_url = "http://127.0.0.1:8127/v1"
wire_api = "responses"
request_max_retries = 0
stream_max_retries = 0
stream_idle_timeout_ms = 600000
"""
    if native_instructions:
        text = text.replace('model_instructions_file = "/opt/hecate-config/instructions.md"\n', '')
    return text


def run_process(
    command: list[str], directory: Path, timeout_s: float, *, stop=None
) -> dict:
    started = time.monotonic()
    reason = None
    with (directory / "codex_events.jsonl").open("w") as output, (
        directory / "codex_stderr.log"
    ).open("w") as error:
        proc = subprocess.Popen(
            command,
            stdout=output,
            stderr=error,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            while proc.poll() is None:
                reason = stop() if stop else None
                if time.monotonic() - started >= timeout_s:
                    reason = "budget_exhausted"
                if reason:
                    break
                time.sleep(0.1)
        except BaseException:
            reason = "cancelled"
            raise
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)
    events = []
    malformed = 0
    for line in (directory / "codex_events.jsonl").read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            malformed += 1
    if not reason:
        if malformed or any(e.get("type") == "turn.failed" for e in events):
            reason = "tool_protocol_failure"
        elif proc.returncode:
            reason = "process_failure"
        elif not any(e.get("type") == "turn.completed" for e in events):
            reason = "tool_protocol_failure"
        else:
            reason = "completed"
    return {
        "termination_reason": reason,
        "exit_code": proc.returncode,
        "episode_wall_s": time.monotonic() - started,
        "malformed_events": malformed,
        "events": events,
    }


def require_fixture_gate(path: Path, config: dict) -> None:
    """Do not run benchmark tasks with an unvalidated effective configuration."""
    results = json.loads((path / "results.json").read_text())
    manifest = json.loads((path / "manifest.json").read_text())
    isolation = json.loads((path / "isolation.json").read_text())
    if (
        results.get("mode") != "fixtures"
        or len(results.get("rows", [])) != 3
        or not all(r.get("passed") for r in results["rows"])
    ):
        raise ValueError(
            "All three capability fixtures must pass before benchmark smoke"
        )
    if not isolation.get("passed") or manifest.get("config") != config:
        raise ValueError("Isolation/configuration gate mismatch")
