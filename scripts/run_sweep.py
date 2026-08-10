#!/usr/bin/env python3
"""Run the Stage-1 generation sweep: 2 models × 300 SWE-bench Lite tasks.

Usage:
    python scripts/run_sweep.py --dry-run
    python scripts/run_sweep.py
    python scripts/run_sweep.py --tasks 10  # smoke subset
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hecate Stage 1 full sweep runner")
    parser.add_argument(
        "--config",
        default="configs/option_a.yaml",
        help="Path to config YAML",
    )
    parser.add_argument(
        "--tasks",
        type=int,
        default=300,
        help="Number of SWE-bench Lite tasks (default: 300)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate wiring without API calls",
    )
    parser.add_argument(
        "--output-dir",
        default="data/outputs/runs/sweep-2x300-qwen",
        help="Output directory for records + manifest (stable for resume)",
    )
    parser.add_argument(
        "--run-id",
        default="sweep-2x300-qwen",
        help="Run id written into records/manifest",
    )
    args = parser.parse_args(argv)

    from hecate.generation import load_run_config, run_generation

    config = load_run_config(
        config_path=args.config,
        tasks=args.tasks,
        all_models=True,
        dry_run=args.dry_run,
        output_dir=Path(args.output_dir),
        run_id=args.run_id,
    )
    result = asyncio.run(run_generation(config))
    print(
        f"run_id={result.run_id} attempted={result.pairs_attempted} "
        f"cache_hits={result.pairs_cache_hit} generated={result.pairs_generated} "
        f"refused={result.pairs_refused_budget} total_usd={result.total_cost_usd:.6f}"
    )
    print(f"models={list(config.model_slugs)}")
    print(f"records={result.records_path}")
    print(f"manifest={result.manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
