#!/usr/bin/env python3
"""Build Stage-3 routing labels and the E-M4 pre-flight report.

Usage:
    python scripts/run_labels.py --input data/outputs/runs/exec-smoke/executions.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hecate Stage 3 label builder")
    parser.add_argument(
        "--config",
        default="configs/execution.yaml",
        help="Path to execution config YAML (for m1/m2 slugs and threshold)",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="executions.jsonl from Stage 2",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for labels.jsonl, preflight.json, and manifest (default: input parent)",
    )
    args = parser.parse_args(argv)

    from hecate.data import read_jsonl
    from hecate.execution import build_labels, load_execution_config
    from hecate.utils.manifest import git_commit_sha, write_run_manifest

    exec_config = load_execution_config(config_path=args.config)
    records = read_jsonl(args.input)
    labels, preflight = build_labels(
        records,
        m1_slug=exec_config.m1_slug,
        m2_slug=exec_config.m2_slug,
        positive_rate_threshold=exec_config.positive_rate_threshold,
    )

    output_dir = Path(args.output_dir) if args.output_dir else Path(args.input).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    labels_path = output_dir / "labels.jsonl"
    with labels_path.open("w", encoding="utf-8") as handle:
        for label in labels:
            handle.write(json.dumps(label.to_dict(), ensure_ascii=False))
            handle.write("\n")

    preflight_path = output_dir / "preflight.json"
    preflight_path.write_text(
        json.dumps(preflight, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest_path = write_run_manifest(
        output_dir / "labels-manifest.json",
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": git_commit_sha(),
            "input_path": str(args.input),
            "labels_path": str(labels_path),
            "preflight_path": str(preflight_path),
            "n_labels": len(labels),
            "m1_slug": exec_config.m1_slug,
            "m2_slug": exec_config.m2_slug,
            "config_path": str(exec_config.config_path),
        },
    )
    print(
        f"labels={len(labels)} n_tasks={preflight['n_tasks']} "
        f"m1_rate={preflight['m1_resolve_rate']:.3f} "
        f"m2_rate={preflight['m2_resolve_rate']:.3f} "
        f"headroom={preflight['routing_headroom']:.3f} "
        f"scaffold_ok={preflight['shared_scaffold']['ok']}"
    )
    print(f"labels_path={labels_path}")
    print(f"preflight={preflight_path}")
    print(f"manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
