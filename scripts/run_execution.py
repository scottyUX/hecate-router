#!/usr/bin/env python3
"""Run Stage-2 SWE-bench execution over Stage-1 generation records.

Usage:
    python scripts/run_execution.py --dry-run --tasks 2
    python scripts/run_execution.py --tasks 1 --instance-ids astropy__astropy-12907
    python scripts/run_execution.py --namespace none
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hecate Stage 2 execution runner")
    parser.add_argument(
        "--config",
        default="configs/execution.yaml",
        help="Path to execution config YAML",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        default=None,
        help="Stage-1 generations JSONL (default: path in execution.yaml)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for executions + manifest (stable for resume)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Execution run id (default: random)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Evaluate a single model slug",
    )
    parser.add_argument(
        "--tasks",
        type=int,
        default=None,
        help="Limit to the first N unique instance ids",
    )
    parser.add_argument(
        "--instance-ids",
        nargs="+",
        default=None,
        help="Explicit instance ids (space separated)",
    )
    parser.add_argument(
        "--namespace",
        default=None,
        help='Docker image namespace (use "none" to build locally)',
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Parallel container workers",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Per-instance test timeout in seconds",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate matrix and write a manifest without evaluating",
    )
    args = parser.parse_args(argv)

    from hecate.execution import load_execution_config, run_execution

    config = load_execution_config(
        config_path=args.config,
        input_path=Path(args.input_path) if args.input_path else None,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        run_id=args.run_id,
        model=args.model,
        instance_ids=args.instance_ids,
        tasks=args.tasks,
        dry_run=args.dry_run,
        namespace=args.namespace,
        max_workers=args.max_workers,
        timeout=args.timeout,
    )
    result = run_execution(config)
    print(
        f"run_id={result.run_id} attempted={result.pairs_attempted} "
        f"resume_skip={result.pairs_skipped_resume} "
        f"no_patch={result.pairs_skipped_no_patch} "
        f"evaluated={result.pairs_evaluated} resolved={result.pairs_resolved} "
        f"pending={result.pairs_pending}"
    )
    print(f"records={result.records_path}")
    print(f"manifest={result.manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
