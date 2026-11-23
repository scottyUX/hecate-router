#!/usr/bin/env python3
"""TASK-001 local Codex compatibility runner. GPU/model work is Spark-only.

Example on Spark:
  PYTHONPATH=src python scripts/run_codex_baseline.py fixtures --root ~/work/hecate-task001 --run-id task001-fixtures-<attempt>
  PYTHONPATH=src python scripts/run_codex_baseline.py smoke --root ~/work/hecate-task001 --run-id task001-smoke-<attempt> --dataset <training-jsonl>
"""
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
import tempfile
from pathlib import Path

import yaml
from hecate.execution.codex_pilot import validate_scope, should_halt
from hecate.execution.codex_artifacts import create_run, finish_run, checksums
from hecate.execution.codex_session import (
    INSTRUCTIONS,
    config_text,
    model_catalog,
    run_process,
    require_fixture_gate,
)
from hecate.execution.model_gateway import Gateway
from hecate.execution.patch_evaluation import evaluation_patch, outcome_axes, correctness_summary
from hecate.execution.task_environment import (
    AgentSandbox,
    collect_patch,
    docker,
    export_task_tree,
    grade_patch,
)


def load_tasks(dataset: Path, selection: dict) -> list[dict]:
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != selection["source_sha256"]:
        raise ValueError("Dataset hash differs from preselected source")
    rows = [json.loads(x) for x in dataset.read_text().splitlines() if x.strip()]
    rows = [
        json.loads(x["reward_spec"]["ground_truth_json"]) if "reward_spec" in x else x
        for x in rows
    ]
    selected = {r["instance_id"]: r for r in rows}
    return [selected[i] for i in selection["instance_ids"]]


def execute(
    workspace: Path,
    directory: Path,
    prompt: str,
    config: dict,
    tools: Path,
    binary: Path,
    *,
    fixture: bool,
    transport=None,
) -> dict:
    directory.mkdir(parents=True, exist_ok=False)
    original_commit = subprocess.check_output(
        ["git", "-C", str(workspace), "rev-parse", "HEAD"], text=True
    ).strip()
    config_dir = directory / "codex-config"
    config_dir.mkdir()
    (config_dir / "catalog.json").write_text(
        json.dumps(
            model_catalog(
                binary, config["model"]["id"], config["model"]["context_tokens"]
            ),
            indent=2,
        )
    )
    instructions = INSTRUCTIONS
    if config["serving"].get("editing_mode") == "shell":
        instructions = instructions.replace(
            "Call apply_patch to edit source when available.",
            "Use exec_command with sed, a Python script or a heredoc to edit source. The apply_patch function is not available in this declared shell-edit mode.",
        )
    (config_dir / "instructions.md").write_text(instructions)
    (config_dir / "config.toml").write_text(
        config_text(config["model"]["id"], config["model"]["context_tokens"],
                    native_instructions=config["serving"].get("prompt_profile") == "native")
    )
    (directory / "prompt.txt").write_text(prompt)
    limit = config["limits"]
    kind = "fixture" if fixture else "task"
    # Keep the Unix socket path short (Linux sun_path maximum is 108 bytes).
    with tempfile.TemporaryDirectory(prefix="hecate-task001-") as temp:
        with Gateway(
            Path(temp) / "gateway.sock",
            config["serving"]["endpoint"],
            config["model"]["id"],
            directory,
            request_limit=limit[kind + "_model_requests"],
            tool_decoding=config["serving"].get("tool_decoding", "auto"),
            editing_mode=config["serving"].get("editing_mode", "patch"),
            message_layout=config["serving"].get("message_layout", "native"),
            sampling=config["model"]["sampling"],
            timeout_s=limit["request_timeout_s"],
            retries=limit["retries"],
            command_timeout_s=limit["command_timeout_s"],
            recover_model_outputs=config['serving'].get('recover_model_outputs', False),
            max_response_recoveries=config['serving'].get('max_response_recoveries', 3),
            transport=transport,
        ) as gateway:
            try:
                with AgentSandbox(
                    config["sandbox"]["image"], workspace, tools, config_dir, Path(temp)
                ) as sandbox:
                    docker(
                        "exec",
                        sandbox.name,
                        "/opt/miniconda3/envs/testbed/bin/python",
                        "-c",
                        "import urllib.request,time; time.sleep(.3)",
                        timeout=10,
                    )
                    result = run_process(
                        sandbox.command(prompt),
                        directory,
                        limit[kind + "_wall_s"],
                        stop=lambda: (
                            "budget_exhausted"
                            if gateway.cap_hit
                            else gateway.failure_kind if gateway.failed else None
                        ),
                    )
            except Exception as exc:
                result = {
                    "termination_reason": "sandbox_failure",
                    "error": str(exc),
                    "events": [],
                }
            # Codex may exit before run_process polls stop(); preserve gateway truth.
            if gateway.cap_hit:
                result["termination_reason"] = "request_budget_exhausted"
            elif gateway.failed and gateway.failure_kind:
                result["termination_reason"] = gateway.failure_kind
            result["model_requests"] = gateway.requests
            result["usage_records"] = gateway.metrics
            result["tool_calls"] = sum(
                e.get("item", {}).get("type") in {"command_execution", "file_change"}
                for e in result["events"]
                if e.get("type") == "item.completed"
            )
            result["inference_wall_s"] = sum(
                x["inference_wall_s"] for x in gateway.metrics
            )
    patch, rejected = collect_patch(workspace, original_commit)
    (directory / "patch.diff").write_text(patch)
    result["test_modifications"] = rejected
    result["events_file"] = "codex_events.jsonl"
    result.pop("events", None)
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def init_fixture(path: Path, files: dict) -> None:
    path.mkdir()
    for name, content in files.items():
        (path / name).write_text(content)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.name=Hecate",
            "-c",
            "user.email=fixture@localhost",
            "commit",
            "-qm",
            "Fixture base",
        ],
        check=True,
    )


def check_isolation(run: Path, config: dict, tools: Path, binary: Path) -> dict:
    workspace = run / "workspace-isolation"
    init_fixture(
        workspace, {"source.py": "value=1\n", "test_readonly.py": "assert True\n"}
    )
    cfgdir = run / "isolation-config"
    cfgdir.mkdir()
    (cfgdir / "config.toml").write_text(
        config_text(config["model"]["id"], config["model"]["context_tokens"])
    )
    marker = run / "host-only-marker.txt"
    marker.write_text("Harmless TASK-001 isolation probe")
    with tempfile.TemporaryDirectory(prefix="hecate-task001-") as sockdir:
        with Gateway(
            Path(sockdir) / "gateway.sock",
            config["serving"]["endpoint"],
            config["model"]["id"],
            run,
            request_limit=1,
            sampling={},
        ):
            with AgentSandbox(
                config["sandbox"]["image"], workspace, tools, cfgdir, Path(sockdir)
            ) as box:
                script = """import pathlib,socket,subprocess
assert not pathlib.Path(%r).exists(), 'host marker exposed'
assert subprocess.check_output(['git','rev-list','--count','HEAD'],text=True).strip()=='1'
assert not subprocess.check_output(['git','remote'],text=True).strip()
for protected in ('.git/config','test_readonly.py'):
 try:
  with open(protected,'a') as f: f.write('UNEXPECTED WRITE')
 except OSError:
  pass
 else:
  raise AssertionError('protected path writable: '+protected)
try:
 socket.create_connection(('198.51.100.1',9),timeout=1)
except OSError:
 print('PASS: external networking denied; host marker absent; one-commit repository')
else:
 raise AssertionError('network access unexpectedly available')
""" % str(
                    marker.resolve()
                )
                probe = docker(
                    "exec",
                    box.name,
                    "/opt/miniconda3/envs/testbed/bin/python",
                    "-c",
                    script,
                    timeout=10,
                    check=False,
                )
                inspection = json.loads(docker("inspect", box.name).stdout)[0]
                passed = (
                    probe.returncode == 0
                    and inspection["HostConfig"]["NetworkMode"] == "none"
                )
                result = {
                    "passed": passed,
                    "probe_stdout": probe.stdout,
                    "probe_stderr": probe.stderr,
                    "network_mode": inspection["HostConfig"]["NetworkMode"],
                    "mount_destinations": [
                        m["Destination"] for m in inspection["Mounts"]
                    ],
                }
    (run / "isolation.json").write_text(json.dumps(result, indent=2) + "\n")
    if not passed:
        raise RuntimeError("Isolation gate failed")
    return result


def fixtures(run: Path, config: dict, tools: Path, binary: Path) -> list[dict]:
    check_isolation(run, config, tools, binary)
    specs = [
        (
            "read",
            {"source.py": 'COMPATIBILITY_MARKER = "violet-heron-731"\n'},
            'Call the exec_command function with {"cmd":"cat source.py"}, then report the exact value of COMPATIBILITY_MARKER from the actual tool result. Do not edit files.',
        ),
        (
            "edit",
            {"source.py": "def add(a, b):\n    return a - b\n"},
            "Inspect source.py and fix add so it returns the sum of a and b. Actually edit the file, preferably with apply_patch. Do not add tests.",
        ),
        (
            "repair",
            {
                "source.py": "def add(a, b):\n    return a - b\n",
                "test_source.py": "from source import add\ndef test_add():\n    assert add(2, 3) == 5\n",
            },
            "Run python3 -m pytest -q test_source.py and observe the failure. The implementation in source.py subtracts a and b; change return a - b to return a + b. The tests are correct and read-only. Do not edit tests. Run the same test again and confirm it passes.",
        ),
    ]
    rows = []
    for name, files, prompt in specs:
        workspace = run / ("workspace-" + name)
        init_fixture(workspace, files)
        result = execute(
            workspace, run / name, prompt, config, tools, binary, fixture=True
        )
        event_file = run / name / "codex_events.jsonl"
        events = (
            [json.loads(x) for x in event_file.read_text().splitlines() if x.strip()]
            if event_file.exists()
            else []
        )
        commands = [
            e["item"]
            for e in events
            if e.get("type") == "item.completed"
            and e.get("item", {}).get("type") == "command_execution"
        ]
        if name == "read":
            evidence = any(
                "violet-heron-731" in c.get("aggregated_output", "") for c in commands
            )
        else:
            assertion = docker(
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--memory",
                "512m",
                "--pids-limit",
                "64",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "-v",
                f"{workspace.resolve()}:/testbed:ro",
                "-w",
                "/testbed",
                config["sandbox"]["image"],
                "/opt/miniconda3/envs/testbed/bin/python",
                "-B",
                "-c",
                "from source import add; assert add(2,3)==5; assert add(-1,3)==2",
                timeout=15,
                check=False,
            )
            evidence = assertion.returncode == 0
            if name == "repair":
                tests = [c for c in commands if "pytest" in c.get("command", "")]
                evidence = (
                    evidence
                    and any(c.get("exit_code") == 1 for c in tests)
                    and any(c.get("exit_code") == 0 for c in tests)
                )
        result.update(
            fixture=name,
            passed=bool(
                evidence
                and commands
                and result["termination_reason"] == "completed"
                and not result["test_modifications"]
            ),
        )
        rows.append(result)
        print(
            json.dumps(
                {
                    "fixture": name,
                    "passed": result["passed"],
                    "termination": result["termination_reason"],
                }
            ),
            flush=True,
        )
        if not result["passed"]:
            break
    return rows


def run_task(
    run: Path,
    config: dict,
    tools: Path,
    binary: Path,
    instance: dict,
    reuse_agent_from: Path | None = None,
    *,
    executor=None,
) -> dict:
    iid = instance["instance_id"]
    directory = run / iid
    directory.mkdir()
    image = config["sandbox"]["image"]
    # Controls must pass before any model attempt on this task.
    gold = grade_patch(image, instance, "", directory / "control-patched", gold=True)
    bug = grade_patch(
        image,
        instance,
        "",
        directory / "control-unpatched",
        verified_gold=gold.get("status") == "completed"
        and gold.get("resolved") is True,
    )
    controls = (
        bug["status"] == "completed"
        and not bug["resolved"]
        and (
            bug.get("reason") == "unpatched_bug_broke_test_collection"
            or all(s in {"FAILED", "ERROR"} for s in bug.get("f2p", {}).values())
        )
        and gold["status"] == "completed"
        and gold["resolved"]
        and all(s == "PASSED" for s in bug.get("p2p", {}).values())
    )
    if not controls:
        failed = {
            "instance_id": iid,
            "status": "evaluator_failure",
            "resolved": None,
            "controls": {"unpatched": bug, "patched": gold},
        }
        return {**failed, **outcome_axes(failed)}
    previous = reuse_agent_from / iid / "agent" if reuse_agent_from else None
    if previous and not (previous / "result.json").exists():
        raise ValueError("Saved agent result missing; replay never generates a replacement attempt")
    if previous and (previous / "result.json").exists():
        shutil.copytree(previous, directory / "agent", symlinks=True)
        result = json.loads((previous / "result.json").read_text())
        original_row = json.loads((previous.parent / "result.json").read_text())
        if result.get("termination_reason") == "tool_protocol_failure":
            events = [
                json.loads(line)
                for line in (previous / "gateway.jsonl").read_text().splitlines()
                if line.strip()
            ]
            failures = [
                e
                for e in events
                if e.get("event") == "gateway_error"
                and e.get("message") == "Missing, ambiguous or truncated completion"
            ]
            if failures:
                failure = failures[-1]
                requests = [
                    e
                    for e in events
                    if e.get("event") == "request"
                    and e["timestamp"] <= failure["timestamp"]
                ]
                result.update(
                    original_termination_reason=result["termination_reason"],
                    termination_reason="model_output_failure",
                    failure_evidence=failure["message"],
                    historical_failed_output_not_retained=True,
                )
                if requests:
                    last = requests[-1]
                    if last["request"] not in {
                        m["request"] for m in result.get("usage_records", [])
                    }:
                        duration = failure["timestamp"] - last["timestamp"]
                        result.setdefault("usage_records", []).append(
                            {
                                "request": last["request"],
                                "retries": 0,
                                "inference_wall_s": duration,
                                "usage": None,
                                "failed": True,
                                "timing_source": "gateway_log_timestamps",
                            }
                        )
                        result["inference_wall_s"] = sum(
                            m["inference_wall_s"] for m in result["usage_records"]
                        )
            if any(e.get("event") == "gateway_error"
                   and e.get("message") == "Model request budget exhausted" for e in events):
                result.update(original_termination_reason=result["termination_reason"],
                              termination_reason="request_budget_exhausted")
        result.update(
            instance_id=iid,
            base_revision=original_row.get("base_revision"),
            reused_agent_artifacts_from=str(previous),
            previous_outcome={key: original_row.get(key) for key in (
                "status", "resolved", "termination_reason"
            )},
        )
    else:
        workspace = directory / "workspace"
        base = export_task_tree(image, iid, workspace)
        result = (executor or execute)(
            workspace,
            directory / "agent",
            instance["problem_statement"]
            + "\n\nFix non-test source files in /testbed. Do not modify tests.",
            config,
            tools,
            binary,
            fixture=False,
        )
        result.update(instance_id=iid, base_revision=base)
    try:
        patch = (directory / "agent/patch.diff").read_text()
        projected, projection = evaluation_patch(patch, result["test_modifications"])
        (directory / "evaluation.diff").write_text(projected)
        result["patch_projection"] = projection
    except (OSError, ValueError) as exc:
        result.update(status="patch_projection_failure", resolved=None, projection_error=str(exc))
    else:
        evaluation = grade_patch(
            image,
            instance,
            projected,
            directory / "evaluation",
            validated_controls=True,
            verified_gold=True,
        )
        result["evaluation"] = evaluation
        result.update(status=evaluation["status"], resolved=evaluation["resolved"])
    result.update(outcome_axes(result))
    return result


def smoke(
    run: Path,
    config: dict,
    tools: Path,
    binary: Path,
    tasks: list[dict],
    reuse_agent_from: Path | None = None,
    *,
    continue_on_error: bool = False,
    consecutive_limit: int = 3,
) -> list[dict]:
    rows = []
    for instance in tasks:
        try:
            result = run_task(run, config, tools, binary, instance, reuse_agent_from)
        except Exception as exc:
            result = {
                "instance_id": instance["instance_id"],
                "status": "infrastructure_failure",
                "resolved": None,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
            result.update(outcome_axes(result))
        rows.append(result)
        directory = run / instance["instance_id"]
        directory.mkdir(exist_ok=True)
        (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        (run / "progress.json").write_text(
            json.dumps(
                {
                    "records": len(rows),
                    "resolved": sum(r.get("resolved") is True for r in rows),
                    "ungraded": sum(r.get("resolved") is None for r in rows),
                    "errors": sum(
                        bool(r.get("execution_infrastructure_failure"))
                        or r.get("status") in {"evaluator_failure", "infrastructure_failure"}
                        for r in rows
                    ),
                    "session_completed": sum(r.get("session_completed") is True for r in rows),
                    "clean_successes": sum(r.get("clean_success") is True for r in rows),
                },
                indent=2,
            )
            + "\n"
        )
        print(
            json.dumps(
                {
                    "record": len(rows),
                    "instance_id": instance["instance_id"],
                    "status": result["status"],
                    "resolved": result.get("resolved"),
                }
            ),
            flush=True,
        )
        # Replay generates no inference: old execution faults do not stop grading.
        halt_rows = [
            {**r, "execution_infrastructure_failure": False}
            if reuse_agent_from and "evaluation_protocol" in r else r for r in rows
        ]
        if should_halt(
            halt_rows,
            continue_on_error=continue_on_error,
            consecutive_limit=consecutive_limit,
        ):
            break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["fixtures", "smoke", "pilot"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/codex_qwen7b.yaml")
    )
    parser.add_argument("--dataset", type=Path)
    parser.add_argument(
        "--reuse-agent-from",
        type=Path,
        help="Reuse immutable saved agent attempts; only re-evaluate their patches",
    )
    parser.add_argument(
        "--fixtures-run", type=Path, help="Required passing fixture run for smoke"
    )
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        parser.error("Live execution is restricted to ARM64 Linux Spark")
    cfg = yaml.safe_load(args.config.read_text())
    if args.mode in {"smoke", "pilot"}:
        if not args.fixtures_run:
            parser.error("--fixtures-run is required for smoke")
        require_fixture_gate(args.fixtures_run, cfg)
        if args.reuse_agent_from:
            old_manifest = json.loads(
                (args.reuse_agent_from / "manifest.json").read_text()
            )
            if old_manifest["config"] != cfg:
                raise ValueError("Cannot reuse an attempt with different configuration")
            expected = json.loads(
                (args.reuse_agent_from / "checksums.json").read_text()
            )
            legacy = (
                old_manifest.get("checksum_scheme")
                != "sha256-files-and-link-targets-v2"
            )
            if checksums(args.reuse_agent_from, legacy_links=legacy) != expected:
                raise ValueError("Saved attempt checksum mismatch")
    binary = args.root / cfg["codex"]["binary"]
    version = subprocess.check_output([str(binary), "--version"], text=True).strip()
    if cfg["codex"]["version"] not in version:
        raise ValueError("Codex version mismatch")
    tools = binary.parent.parent
    selection = json.loads(Path(cfg["selection_manifest"]).read_text())
    tasks = (
        load_tasks(args.dataset, selection)
        if args.mode in {"smoke", "pilot"} and args.dataset
        else []
    )
    expected_count = validate_scope(args.mode, cfg, selection)
    if args.mode != "fixtures" and len(tasks) != expected_count:
        parser.error("Run requires the exact authorized task selection")
    run = create_run(
        args.root / "runs",
        args.run_id,
        cfg,
        {
            "codex_version": version,
            "runner_dependencies": {
                name: importlib.metadata.version(name) for name in ("httpx", "PyYAML")
            },
            "platform": platform.uname()._asdict(),
            "memory_before": subprocess.check_output(["free", "-b"], text=True),
            "codex_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "git_commit": os.environ.get("HECATE_CODE_SHA"),
            "task_selection": selection,
            "argv": sys.argv,
            "mode": args.mode,
            "fixtures_run": str(args.fixtures_run) if args.fixtures_run else None,
            "reuse_agent_from": (
                str(args.reuse_agent_from) if args.reuse_agent_from else None
            ),
            "model_attempts_generated": 0 if args.reuse_agent_from else None,
            "source_hashes": {
                str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(Path("src/hecate/execution").glob("*.py"))
            },
        },
    )
    snapshot = run / "source_snapshot"
    snapshot.mkdir()
    for source in [
        Path(__file__),
        args.config,
        Path(cfg["selection_manifest"]),
        Path("configs/codex_compat_requirements.txt"),
        *Path("src/hecate/execution").glob("*.py"),
    ]:
        destination = snapshot / source.name
        shutil.copy2(source, destination)
    try:
        rows = (
            fixtures(run, cfg, tools, binary)
            if args.mode == "fixtures"
            else smoke(
                run,
                cfg,
                tools,
                binary,
                tasks,
                args.reuse_agent_from,
                continue_on_error=args.mode == "pilot",
                consecutive_limit=cfg.get("pilot", {}).get(
                    "max_consecutive_infrastructure_errors", 3
                ),
            )
        )
        ok = len(rows) == expected_count and all(
            r["passed"] if args.mode == "fixtures" else r.get("resolved") is not None
            for r in rows
        )
        results = {
            "mode": args.mode,
            "verdict": ("compatible_with_declared_limitations" if ok else "blocked")
            if args.mode == "fixtures" else ("grading_complete" if ok else "incomplete_grading"),
            "limitations": [
                ("Schema-constrained required tools with explicit finish action"
                 if cfg["serving"].get("tool_decoding") == "required_with_finish"
                 else "Native parser with automatic tool choice"),
                "Shell editing; no validated apply_patch support",
            ],
            "attempted": (
                len(rows)
                if args.mode == "fixtures"
                else sum("termination_reason" in r for r in rows)
            ),
            "tasks_considered": len(rows),
            "expected_tasks": expected_count,
            "rows": rows,
        }
        if args.mode in {"smoke", "pilot"}:
            results.update(correctness_summary(rows, expected_count))
        finish_run(run, results)
        return 0 if ok else 1
    except BaseException as exc:
        finish_run(
            run,
            {
                "mode": args.mode,
                "verdict": "blocked",
                "error": str(exc),
                "type": type(exc).__name__,
            },
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
