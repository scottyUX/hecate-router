#!/usr/bin/env python3
"""TASK-003: real upstream mini-SWE-agent v1 with matched TASK-002 grading."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml
from hecate.execution.codex_artifacts import create_run, finish_run
from hecate.execution.codex_pilot import should_halt
from hecate.execution.mini_harness import (
    EpisodeBudget,
    LocalChatModel,
    ModelContextExceeded,
    ShellSandbox,
)
from hecate.execution.task_environment import collect_patch, docker
from run_codex_baseline import init_fixture, load_tasks, run_task


def execute(
    workspace, directory, prompt, config, tools=None, binary=None, *, fixture=False
):
    from microsweagent.agents.default import DefaultAgent

    directory.mkdir(parents=True, exist_ok=False)
    original = subprocess.check_output(
        ["git", "-C", str(workspace), "rev-parse", "HEAD"], text=True
    ).strip()
    (directory / "prompt.txt").write_text(prompt)
    upstream = yaml.safe_load(
        (
            Path(config["harness"]["vendor_path"]) / "microsweagent/config/default.yaml"
        ).read_text()
    )["agent"]
    limits = config["limits"]
    kind = "fixture" if fixture else "task"
    upstream.update(step_limit=limits[kind + "_model_requests"], cost_limit=0.0)
    (directory / "agent-config.json").write_text(json.dumps(upstream, indent=2) + "\n")
    deadline = time.monotonic() + limits[kind + "_wall_s"]
    model = LocalChatModel(config, directory, deadline)
    agent = None
    status, error = "infrastructure_failure", None
    with ShellSandbox(
        config["sandbox"]["image"],
        workspace,
        directory,
        limits["command_timeout_s"],
        deadline,
    ) as env:
        try:
            agent = DefaultAgent(model, env, **upstream)
            status, message = agent.run(prompt)
            (directory / "submission.txt").write_text(message)
        except EpisodeBudget:
            status = "WallLimitExceeded"
        except ModelContextExceeded as exc:
            status, error = "ContextExceeded", str(exc)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        finally:
            if agent:
                (directory / "messages.json").write_text(
                    json.dumps(agent.messages, indent=2) + "\n"
                )
    patch, rejected = collect_patch(workspace, original)
    (directory / "patch.diff").write_text(patch)
    result = {
        "termination_reason": (
            "completed"
            if status == "Submitted"
            else (
                "budget_exhausted"
                if status in {"LimitsExceeded", "WallLimitExceeded", "ContextExceeded"}
                else status
            )
        ),
        "mini_exit_status": status,
        "error": error,
        "model_requests": model.n_calls,
        "usage_records": model.metrics,
        "inference_wall_s": sum(x["inference_wall_s"] for x in model.metrics),
        "tool_calls": env.calls,
        "test_modifications": rejected,
    }
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def fixtures(run, cfg):
    workspace = run / "fixture-workspace"
    init_fixture(
        workspace,
        {
            "answer.py": "VALUE = 41\n",
            "test_answer.py": "from answer import VALUE\ndef test_answer():\n    assert VALUE == 42\n",
        },
    )
    probe = run / "isolation"
    probe.mkdir()
    with ShellSandbox(
        cfg["sandbox"]["image"], workspace, probe, 30, time.monotonic() + 60
    ) as env:
        result = env.execute(
            "test ! -S /var/run/docker.sock && test ! -d /host && test ! -w /testbed/test_answer.py && test ! -w /testbed/.git && test ! -w / && echo ISOLATED"
        )
        if result["returncode"] or result["output"].strip() != "ISOLATED":
            raise RuntimeError("Shell isolation probe failed")
        info = json.loads(docker("inspect", env.name).stdout)[0]
        if info["HostConfig"]["NetworkMode"] != "none":
            raise RuntimeError("Shell network isolation failed")
        (probe / "container-inspection.json").write_text(
            json.dumps(info, indent=2) + "\n"
        )
    result = execute(
        workspace,
        run / "fixture-agent",
        "Read answer.py. Change VALUE to 42, then run python -m pytest -q. Do not modify test files. Finish using the required final-output command.",
        cfg,
        fixture=True,
    )
    check = run / "fixture-check"
    check.mkdir()
    with ShellSandbox(
        cfg["sandbox"]["image"], workspace, check, 30, time.monotonic() + 60
    ) as env:
        verification = env.execute("python -m pytest -q")
    if (
        verification["returncode"]
        or result["test_modifications"]
        or result["termination_reason"] != "completed"
    ):
        raise RuntimeError(
            "Mini capability fixture failed; preserve evidence and inspect"
        )
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument(
        "--config", type=Path, default=Path("configs/mini_qwen7b_pilot.yaml")
    )
    ap.add_argument("--dataset", type=Path, required=True)
    args = ap.parse_args()
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        ap.error("Live runs are restricted to Spark ARM64 Linux")
    cfg = yaml.safe_load(args.config.read_text())
    vendor = Path(cfg["harness"]["vendor_path"])
    provenance = json.loads((vendor / "provenance.json").read_text())
    for name, digest in provenance["sha256"].items():
        if hashlib.sha256((vendor / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Vendored upstream source hash mismatch")
    sys.path.insert(0, str(vendor.resolve()))
    os.environ["MICRO_SWE_AGENT_SILENT_STARTUP"] = "1"
    os.environ["MICRO_SWE_AGENT_GLOBAL_CONFIG_DIR"] = str(args.root / "mini-global")
    selection = json.loads(Path(cfg["selection_manifest"]).read_text())
    if (
        len(selection["instance_ids"]) != 20
        or len(set(selection["instance_ids"])) != 20
    ):
        raise ValueError("Expected the fixed 20 unique paired tasks")
    tasks = load_tasks(args.dataset, selection)
    run = create_run(
        args.root / "runs",
        args.run_id,
        cfg,
        {
            "git_commit": os.environ.get("HECATE_CODE_SHA"),
            "argv": sys.argv,
            "upstream": provenance,
            "selection": selection,
            "dependencies": {
                d: importlib.metadata.version(d)
                for d in [
                    "httpx",
                    "PyYAML",
                    "Jinja2",
                    "MarkupSafe",
                    "python-dotenv",
                    "platformdirs",
                    "rich",
                ]
            },
        },
    )
    snapshot = run / "source"
    snapshot.mkdir()
    for p in [
        args.config,
        Path(cfg["selection_manifest"]),
        Path(__file__),
        Path("scripts/run_codex_baseline.py"),
        Path("scripts/serve_codex_qwen7b.py"),
        Path("configs/mini_harness_requirements.txt"),
        Path("docs/tasks/qwen25-coder-7b-mini-swe-agent-pilot.md"),
        *Path("src/hecate/execution").glob("*.py"),
    ]:
        shutil.copy2(p, snapshot / p.name)
    shutil.copytree(vendor, snapshot / "vendor")
    rows = []
    try:
        fixture = fixtures(run, cfg)
        (run / "fixture-result.json").write_text(json.dumps(fixture, indent=2) + "\n")
        for instance in tasks:
            try:
                result = run_task(run, cfg, None, None, instance, executor=execute)
            except Exception as exc:
                result = {
                    "instance_id": instance["instance_id"],
                    "status": "infrastructure_failure",
                    "resolved": None,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            rows.append(result)
            directory = run / instance["instance_id"]
            directory.mkdir(exist_ok=True)
            (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            summary = {
                "records": len(rows),
                "resolved": sum(r.get("resolved") is True for r in rows),
                "errors": sum(r.get("resolved") is None for r in rows),
            }
            (run / "progress.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(
                json.dumps(
                    {
                        "instance_id": instance["instance_id"],
                        **summary,
                        "status": result["status"],
                    }
                ),
                flush=True,
            )
            if should_halt(rows, continue_on_error=True, consecutive_limit=3):
                break
        finish_run(
            run,
            {
                "mode": "pilot",
                "harness": cfg["harness"],
                "rows": rows,
                "tasks_considered": len(rows),
                "resolved": sum(r.get("resolved") is True for r in rows),
                "evaluable": sum(r.get("resolved") is not None for r in rows),
                "expected_tasks": 20,
                "infrastructure_errors": sum(r.get("resolved") is None for r in rows),
            },
        )
    except BaseException as exc:
        finish_run(
            run,
            {
                "rows": rows,
                "error": str(exc),
                "error_type": type(exc).__name__,
                "tasks_considered": len(rows),
            },
        )
        raise
    return (
        0 if len(rows) == 20 and all(r.get("resolved") is not None for r in rows) else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
