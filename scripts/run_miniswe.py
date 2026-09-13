#!/usr/bin/env python3
"""Run one SWE-bench instance via mini-SWE-agent (optional agent scaffold).

Usage:
    python scripts/run_miniswe.py --help
    python scripts/run_miniswe.py --dry-run
    python scripts/run_miniswe.py --instance django__django-10914 \\
        --model openrouter/qwen/qwen-2.5-7b-instruct

Does not use Hecate Stage-1 patch extraction. Install with:
    pip install -e ".[agent]"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Hecate mini-SWE-agent single-instance runner"
    )
    parser.add_argument(
        "--config",
        default="configs/miniswe.yaml",
        help="Path to miniswe config YAML",
    )
    parser.add_argument(
        "--instance",
        default=None,
        help="SWE-bench instance id or index (default from config)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model slug for mini-SWE / litellm (default from config)",
    )
    parser.add_argument(
        "--subset",
        default=None,
        help="SWE-bench subset (default: lite from config)",
    )
    parser.add_argument(
        "--split",
        default=None,
        help="Dataset split (default: test from config)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Trajectory output path passed to mini-extra",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="If set without --output, write <output-dir>/<instance>.traj.json",
    )
    parser.add_argument(
        "--cost-limit",
        type=float,
        default=None,
        help="Per-instance cost limit (USD) for mini-SWE",
    )
    parser.add_argument(
        "--environment-class",
        default=None,
        help="mini-SWE environment (e.g. docker)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate wiring and print argv; no Docker/API",
    )
    args = parser.parse_args(argv)

    from hecate.agent.miniswe import (
        MinisweNotInstalledError,
        load_miniswe_config,
        run_swebench_single,
    )
    from hecate.utils.env import load_env

    load_env()
    config = load_miniswe_config(args.config)

    defaults = config.get("defaults") or {}
    scaffold = config.get("scaffold") or {}
    instance = args.instance or str(defaults.get("instance") or "0")
    model = args.model or str(defaults.get("model") or "")
    if not model.strip():
        print(
            "error: model is required (pass --model or set defaults.model)",
            file=sys.stderr,
        )
        return 2

    output = args.output
    if output is None and args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = str(instance).replace("/", "__")
        output = str(out_dir / f"{safe}.traj.json")

    cost_limit = args.cost_limit
    if cost_limit is None and defaults.get("cost_limit") is not None:
        cost_limit = float(defaults["cost_limit"])

    try:
        result = run_swebench_single(
            instance=instance,
            model=model,
            subset=args.subset or str(scaffold.get("subset") or "lite"),
            split=args.split or str(scaffold.get("split") or "test"),
            output=output,
            cost_limit=cost_limit,
            environment_class=args.environment_class
            or defaults.get("environment_class"),
            exit_immediately=bool(defaults.get("exit_immediately", True)),
            dry_run=args.dry_run,
        )
    except MinisweNotInstalledError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"dry_run={result.dry_run} returncode={result.returncode} "
        f"argv={' '.join(result.argv)}"
    )
    return 0 if result.dry_run else int(result.returncode)


if __name__ == "__main__":
    sys.exit(main())
