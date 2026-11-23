#!/usr/bin/env python3
"""TASK-009: official task build/controls, then one isolated local Codex attempt."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import uuid

import yaml
from hecate.execution.codex_artifacts import create_run, finish_run, checksums
from hecate.execution.patch_evaluation import evaluation_patch, outcome_axes
from hecate.execution.swebench_pilot import validate_pilot, required_outcomes
from hecate.execution.task_environment import docker, extract_task_archive
from run_codex_baseline import execute, fixtures


def load_inputs(config_path, parquet_path):
    import pyarrow.parquet as pq
    config = yaml.safe_load(config_path.read_text())
    selection = json.loads(Path(config["selection_manifest"]).read_text())
    if hashlib.sha256(parquet_path.read_bytes()).hexdigest() != selection["parquet_sha256"]:
        raise ValueError("Dataset hash differs from the pinned Verified snapshot")
    instance = next(r for r in pq.read_table(parquet_path).to_pylist()
                    if r["instance_id"] == config["evaluator"]["instance_id"])
    validate_pilot(config, selection, instance)
    return config, selection, instance


def spec_for(instance):
    from swebench.harness.test_spec.test_spec import make_test_spec
    return make_test_spec(instance, arch="arm64", base_image_tag="task009",
                          env_image_tag="task009", instance_image_tag="task009")


def grade(spec, patch, directory, timeout, *, wheelhouse=None):
    """Run the official eval script/parser in a fresh networkless container."""
    from swebench.harness.grading import get_eval_report, get_logs_eval
    directory.mkdir()
    (directory / "patch.diff").write_text(patch)
    (directory / "eval.sh").write_text(spec.eval_script)
    name = "hecate-task009-grade-" + uuid.uuid4().hex[:10]
    outcome = {"status": "evaluator_failure", "resolved": None}
    try:
        offline = ["-v", str(Path(wheelhouse).resolve()) + ":/opt/hecate-wheels:ro",
                   "-e", "PIP_NO_INDEX=1", "-e", "PIP_FIND_LINKS=file:///opt/hecate-wheels"] if wheelhouse else []
        docker("run", "-d", "--name", name, "--network", "none", *offline, "--memory", "8g",
               "--pids-limit", "512", spec.instance_image_key, "sleep", "1200")
        if patch:
            applied = docker("exec", "-i", "-w", "/testbed", name, "git", "apply", "-",
                             input=patch, check=False)
            (directory / "apply.log").write_text(applied.stdout + applied.stderr)
            if applied.returncode:
                outcome.update(status="patch_application_failure", error="Saved patch did not apply")
                return outcome
        docker("cp", str(directory / "eval.sh"), name + ":/eval.sh")
        try:
            result = docker("exec", name, "bash", "/eval.sh", timeout=timeout, check=False)
            log = result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired as exc:
            (directory / "test_output.txt").write_text(str(exc))
            outcome.update(error="Evaluator timeout", timed_out=True)
            return outcome
        path = directory / "test_output.txt"
        path.write_text(log)
        if wheelhouse and any(marker in log for marker in (
            "ERROR: No matching distribution found", "ERROR: Failed to build",
            "error: subprocess-exited-with-error",
        )):
            outcome.update(error="Offline setup step failed; inspect test_output.txt")
            return outcome
        statuses, found = get_logs_eval(spec, str(path))
        (directory / "test_statuses.json").write_text(json.dumps(statuses, indent=2) + "\n")
        official = get_eval_report(spec, {"instance_id": spec.instance_id,
                                  "model_name_or_path": "hecate-task009", "model_patch": patch},
                                  str(path), include_tests_status=True)
        (directory / "official_report.json").write_text(json.dumps(official, indent=2) + "\n")
        outcome.update(required_outcomes(spec, statuses, found), exit_code=result.returncode,
                       official_resolved=official[spec.instance_id]["resolved"])
        if outcome["resolved"] is not None and outcome["resolved"] != outcome["official_resolved"]:
            outcome.update(status="evaluator_failure", resolved=None,
                           error="Strict required-test outcome differs from official report")
        return outcome
    finally:
        docker("rm", "-f", name, check=False)
        (directory / "outcome.json").write_text(json.dumps(outcome, indent=2) + "\n")


def export_workspace(spec, base_commit, workspace):
    name = "hecate-task009-export-" + uuid.uuid4().hex[:10]
    try:
        docker("run", "-d", "--name", name, "--network", "none",
               spec.instance_image_key, "sleep", "600")
        revision = docker("exec", "-w", "/testbed", name, "git", "rev-parse", "HEAD").stdout.strip()
        actual_tree = docker("exec", "-w", "/testbed", name, "git", "rev-parse", "HEAD^{tree}").stdout.strip()
        expected_tree = docker("exec", "-w", "/testbed", name, "git", "rev-parse", base_commit + "^{tree}").stdout.strip()
        # Official setup adds an empty SWE-bench commit; compare source trees,
        # then export the dataset's exact base, never later history.
        setup_pin = None
        if actual_tree != expected_tree:
            # SWE-bench's Astropy build recipes (5.0 and later, TASK-012) commit this
            # dependency pin. Accept precisely that blob change, while exporting the original base.
            if getattr(spec, 'repo', None) == 'astropy/astropy':
                changed = docker('exec', '-w', '/testbed', name, 'git', 'diff', '--name-only', base_commit, 'HEAD').stdout.splitlines()
                before = docker('exec', '-w', '/testbed', name, 'git', 'show', base_commit + ':pyproject.toml').stdout
                after = docker('exec', '-w', '/testbed', name, 'git', 'show', 'HEAD:pyproject.toml').stdout
                old = 'requires = ["setuptools",'
                new = 'requires = ["setuptools==68.0.0",'
                if changed == ['pyproject.toml'] and before.count(old) == 1 and after == before.replace(old, new):
                    setup_pin = {'path': 'pyproject.toml', 'before': old, 'after': new}
            if setup_pin is None:
                raise ValueError("Task image source tree differs from the prescribed base")
        archive = subprocess.check_output(["docker", "exec", "-w", "/testbed", name,
                                           "git", "archive", base_commit], timeout=120)
        extract_task_archive(archive, workspace)
        subprocess.run(["git", "init", "-q", str(workspace)], check=True)
        subprocess.run(["git", "-C", str(workspace), "add", "."], check=True)
        subprocess.run(["git", "-C", str(workspace), "-c", "user.name=Hecate",
                        "-c", "user.email=fixture@localhost", "commit", "-qm", "Public task base"], check=True)
        return {"prescribed_base": base_commit, "image_head": revision,
                "source_tree": expected_tree, "exported_revision": base_commit,
                "image_setup_pin": setup_pin}
    finally:
        docker("rm", "-f", name, check=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["controls", "attempt"])
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=Path("configs/qwen36_local_evaluator.yaml"))
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--controls-run", type=Path)
    args = ap.parse_args()
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        ap.error("Live pilot is restricted to Spark ARM64")
    args.root, args.dataset, args.config = args.root.resolve(), args.dataset.resolve(), args.config.resolve()
    config, selection, instance = load_inputs(args.config, args.dataset)
    if importlib.metadata.version("swebench") != config["evaluator"]["version"]:
        raise ValueError("SWE-bench version mismatch")
    source = Path(__file__).resolve().parents[1]
    run = create_run(args.root / "runs", args.run_id, config, {
        "git_commit": os.environ["HECATE_CODE_SHA"], "mode": args.mode,
        "instance_id": instance["instance_id"], "dataset_revision": selection["revision"],
        "dataset_sha256": selection["parquet_sha256"], "argv": list(__import__("sys").argv),
        "controls_run": str(args.controls_run) if args.controls_run else None,
        "provider_api_cost_usd": 0,
    })
    snapshot = run / "source_snapshot"
    snapshot.mkdir()
    for path in [Path(__file__), args.config, source / config["selection_manifest"],
                 source / "scripts/run_codex_baseline.py", source / "scripts/serve_codex_qwen7b.py",
                 *sorted((source / "src/hecate/execution").glob("*.py"))]:
        shutil.copy2(path, snapshot / path.name)
    (run / "dependencies.txt").write_text(subprocess.check_output(
        [__import__("sys").executable, "-m", "pip", "freeze"], text=True))
    os.chdir(run)
    try:
        spec = spec_for(instance)
        (run / "test-spec.json").write_text(json.dumps(spec.__dict__, indent=2) + "\n")
        if args.mode == "controls":
            import docker as docker_sdk
            from swebench.harness.docker_build import build_env_images, build_instance_image
            client = docker_sdk.from_env()
            _, failed = build_env_images(client, [spec], max_workers=1)
            if failed:
                raise RuntimeError("Official ARM environment build failed; inspect retained build logs")
            build_instance_image(spec, client, logger=None, nocache=False)
            image = json.loads(docker("image", "inspect", spec.instance_image_key).stdout)[0]
            (run / "image.json").write_text(json.dumps(image, indent=2) + "\n")
            bug = grade(spec, "", run / "unpatched", config["evaluator"]["timeout_s"])
            gold = grade(spec, instance["patch"], run / "gold", config["evaluator"]["timeout_s"])
            if not (bug["status"] == gold["status"] == "completed"
                    and bug["resolved"] is False and gold["resolved"] is True
                    and all(v == "PASSED" for v in bug.get("p2p", {}).values())):
                raise RuntimeError("Independent evaluator controls did not validate")
            finish_run(run, {"controls_passed": True, "instance_id": spec.instance_id,
                             "unpatched": bug, "gold": gold, "image_id": image["Id"],
                             "provider_api_cost_usd": 0, "model_attempts_generated": 0})
        else:
            if not args.controls_run:
                raise ValueError("A verified controls run is required")
            controls = args.controls_run.resolve()
            if checksums(controls) != json.loads((controls / "checksums.json").read_text()):
                raise ValueError("Control artifact checksum mismatch")
            if json.loads((controls / "manifest.json").read_text())["config"] != config:
                raise ValueError("Control configuration differs")
            control = json.loads((controls / "results.json").read_text())
            if not control.get("controls_passed"):
                raise ValueError("Controls did not pass")
            image_id = json.loads(docker("image", "inspect", spec.instance_image_key).stdout)[0]["Id"]
            if control["image_id"] != image_id:
                raise ValueError("Task image changed after controls")
            binary = args.root / config["codex"]["binary"]
            if subprocess.check_output([str(binary), "--version"], text=True).strip() != "codex-cli 0.164.0":
                raise ValueError("Codex binary version mismatch")
            (run / "codex-sha256.txt").write_text(hashlib.sha256(binary.read_bytes()).hexdigest() + "\n")
            toolchain = binary.parent.parent
            fixture_run = run / "fixtures"
            fixture_run.mkdir()
            fixture_rows = fixtures(fixture_run, config, toolchain, binary)
            (fixture_run / "results.json").write_text(json.dumps(fixture_rows, indent=2) + "\n")
            if len(fixture_rows) != 3 or not all(r["passed"] for r in fixture_rows):
                raise RuntimeError("Codex capability fixtures did not pass")
            workspace = run / "workspace"
            provenance = export_workspace(spec, instance["base_commit"], workspace)
            (run / "public-task-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
            agent_config = {**config, "sandbox": {"image": image_id}}
            result = execute(workspace, run / "agent", instance["problem_statement"]
                             + "\n\nFix non-test source files in /testbed. Do not modify tests.",
                             agent_config, toolchain, binary, fixture=False)
            patch = (run / "agent/patch.diff").read_text()
            projected, projection = evaluation_patch(patch, result["test_modifications"])
            (run / "evaluation.diff").write_text(projected)
            evaluated = grade(spec, projected, run / "evaluation", config["evaluator"]["timeout_s"])
            result.update(instance_id=spec.instance_id, patch_projection=projection,
                          evaluation=evaluated, status=evaluated["status"], resolved=evaluated["resolved"])
            result.update(outcome_axes(result))
            finish_run(run, {"rows": [result], "provider_api_cost_usd": 0,
                             "model_attempts_generated": 1, "fixtures_passed": True})
    except BaseException as exc:
        finish_run(run, {"error": str(exc), "error_type": type(exc).__name__, "provider_api_cost_usd": 0})
        raise


if __name__ == "__main__":
    main()
