#!/usr/bin/env python3
"""Run a pilot generation sweep: N tasks × 1 model.

Usage:
    python scripts/run_pilot.py --tasks 1 --dry-run
    python scripts/run_pilot.py --tasks 20 --model qwen/qwen-2.5-7b-instruct
"""

from __future__ import annotations

import argparse
import asyncio
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hecate Stage 1 pilot runner")
    parser.add_argument(
        "--config",
        default="configs/option_a.yaml",
        help="Path to config YAML",
    )
    parser.add_argument(
        "--tasks",
        type=int,
        default=20,
        help="Number of SWE-bench Lite tasks",
    )
    parser.add_argument(
        "--model",
        required=False,
        help="Model slug (defaults to first small-tier Option A slug)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate wiring without API calls",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory for records + manifest",
    )
    args = parser.parse_args(argv)

    from hecate.generation import load_run_config, run_generation

    config = load_run_config(
        config_path=args.config,
        tasks=args.tasks,
        model=args.model,
        dry_run=args.dry_run,
        output_dir=args.output_dir,
    )
    result = asyncio.run(run_generation(config))
    print(
        f"run_id={result.run_id} attempted={result.pairs_attempted} "
        f"cache_hits={result.pairs_cache_hit} generated={result.pairs_generated} "
        f"refused={result.pairs_refused_budget} total_usd={result.total_cost_usd:.6f}"
    )
    print(f"records={result.records_path}")
    print(f"manifest={result.manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
