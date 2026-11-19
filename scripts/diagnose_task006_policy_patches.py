#!/usr/bin/env python3
"""Authorized D1/D2 saved-source diagnostic grading; never regenerate agents."""
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
from pathlib import Path
import yaml
from hecate.execution.codex_artifacts import create_run, finish_run, checksums
from hecate.execution.task_environment import grade_patch, protected_test_path

IDS = [
    "jd__tenacity.0d40e76f.combine_file__s0bcdks5",
    "jd__tenacity.0d40e76f.combine_module__yjmtlc2r",
    "jd__tenacity.0d40e76f.func_basic__7azvfd3s",
]


def source_only(patch, rejected):
    kept = []
    removed = []
    for block in re.split(r"(?=^diff --git )", patch, flags=re.M):
        if not block:
            continue
        header = shlex.split(block.splitlines()[0])
        if len(header) != 4 or header[:2] != ["diff", "--git"]:
            raise ValueError("Unexpected patch boundary")
        old, new = header[2][2:], header[3][2:]
        if protected_test_path(old) or protected_test_path(new):
            if (
                old != new
                or new not in rejected
                or "\nnew file mode " not in block
                or "\n--- /dev/null\n" not in block
            ):
                raise ValueError(
                    "Only explicitly rejected newly added tests can be excluded"
                )
            removed.append(new)
        else:
            kept.append(block)
    if set(removed) != set(rejected):
        raise ValueError("Excluded files differ from recorded policy rejection")
    return "".join(kept), removed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument(
        "--scope", choices=["policy-three", "snapshot-eight"], default="policy-three"
    )
    ap.add_argument("--reuse-from", type=Path)
    args = ap.parse_args()
    cfg = yaml.safe_load(args.config.read_text())
    source = args.root / "runs/task006-qwen3-codex-pilot-run-01"
    selection = json.loads(Path("configs/codex_qwen_size_pilot_tasks.json").read_text())
    ids = IDS if args.scope == "policy-three" else selection["instance_ids"][:8]
    if args.reuse_from:
        recorded = json.loads((args.reuse_from / "checksums.json").read_text())
        if checksums(args.reuse_from) != recorded:
            raise ValueError("Prior diagnostic checksum mismatch")
        prior_manifest = json.loads((args.reuse_from / "manifest.json").read_text())
        if prior_manifest["config"] != cfg:
            raise ValueError("Prior diagnostic configuration differs")
    if (
        hashlib.sha256(args.dataset.read_bytes()).hexdigest()
        != selection["source_sha256"]
    ):
        raise ValueError("Dataset changed")
    rows = [
        json.loads(line)
        for line in args.dataset.read_text().splitlines()
        if line.strip()
    ]
    instances = {}
    for row in rows:
        instance = json.loads(row["reward_spec"]["ground_truth_json"])
        if instance["instance_id"] in ids:
            instances[instance["instance_id"]] = instance
    if set(instances) != set(ids):
        raise ValueError("Diagnostic task set incomplete")
    run = create_run(
        args.root / "diagnostic-runs",
        args.run_id,
        cfg,
        {
            "git_commit": os.environ["HECATE_CODE_SHA"],
            "purpose": "Diagnostic saved-source correctness; official policy rejections unchanged",
            "source_run": str(source),
            "instance_ids": ids,
            "scope": args.scope,
            "reuse_from": str(args.reuse_from) if args.reuse_from else None,
            "model_attempts_generated": 0,
        },
    )
    shutil.copy2(__file__, run / "diagnostic-source.py")
    results = []
    try:
        for iid in ids:
            directory = run / iid
            original = json.loads((source / iid / "result.json").read_text())
            if (
                args.scope == "policy-three"
                and original["status"] != "test_modification_rejected"
            ):
                raise ValueError("Source is not the named policy rejection")
            patch = (source / iid / "agent/patch.diff").read_text()
            derived, excluded = source_only(patch, original["test_modifications"])
            previous = args.reuse_from / iid if args.reuse_from else None
            if previous and (previous / "result.json").exists():
                result = json.loads((previous / "result.json").read_text())
                if (
                    result["original_sha256"]
                    != hashlib.sha256(patch.encode()).hexdigest()
                    or result["source_only_sha256"]
                    != hashlib.sha256(derived.encode()).hexdigest()
                ):
                    raise ValueError(
                        "Saved patch differs from the verified prior diagnostic"
                    )
                shutil.copytree(previous, directory)
                result.update(
                    reused_diagnostic_from=str(previous),
                    original_resolved=original.get("resolved"),
                    original_termination=original.get("termination_reason"),
                )
                (directory / "result.json").write_text(
                    json.dumps(result, indent=2) + "\n"
                )
                results.append(result)
                print(
                    json.dumps(
                        {
                            "instance_id": iid,
                            "diagnostic_resolved": result["resolved"],
                            "reused": True,
                        }
                    ),
                    flush=True,
                )
                continue
            directory.mkdir()
            (directory / "original.diff").write_text(patch)
            (directory / "source-only.diff").write_text(derived)
            image = cfg["sandbox"]["image"]
            instance = instances[iid]
            gold = grade_patch(
                image, instance, "", directory / "control-patched", gold=True
            )
            bug = grade_patch(
                image,
                instance,
                "",
                directory / "control-unpatched",
                verified_gold=gold.get("resolved") is True,
            )
            controls = (
                gold.get("status") == "completed"
                and gold.get("resolved") is True
                and bug.get("status") == "completed"
                and bug.get("resolved") is False
            )
            if not controls:
                raise RuntimeError("Independent grading controls failed")
            outcome = grade_patch(
                image,
                instance,
                derived,
                directory / "evaluation",
                validated_controls=True,
                verified_gold=True,
            )
            result = {
                "instance_id": iid,
                "diagnostic_only": True,
                "original_policy_status": original["status"],
                "original_resolved": original.get("resolved"),
                "original_termination": original.get("termination_reason"),
                "original_sha256": hashlib.sha256(patch.encode()).hexdigest(),
                "source_only_sha256": hashlib.sha256(derived.encode()).hexdigest(),
                "excluded_new_test_files": excluded,
                "controls": {"patched": gold, "unpatched": bug},
                "evaluation": outcome,
                "resolved": outcome["resolved"],
                "status": outcome["status"],
            }
            (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            results.append(result)
            print(
                json.dumps(
                    {
                        "instance_id": iid,
                        "diagnostic_resolved": outcome["resolved"],
                        "status": outcome["status"],
                    }
                ),
                flush=True,
            )
        finish_run(
            run,
            {
                "diagnostic_only": True,
                "model_attempts_generated": 0,
                "rows": results,
                "evaluable": sum(x["resolved"] is not None for x in results),
                "resolved": sum(x["resolved"] is True for x in results),
            },
        )
    except BaseException as exc:
        finish_run(run, {"diagnostic_only": True, "rows": results, "error": str(exc)})
        raise


if __name__ == "__main__":
    main()
