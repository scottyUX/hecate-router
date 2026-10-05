#!/usr/bin/env python3
"""Analyze the three-model SWE-bench Verified experiment.

Reads <run-root>/<model>/{preds.json, <id>/<id>.traj.json, executions.jsonl}
and the pre-registered task file; writes to --out-dir:

    analysis.md      human-readable report
    summary.json     every number in the report
    per_task.csv     one row per (model, task): status, resolved, cost, features

Runs before grading too (resolved columns are then empty and rates read "–"),
which is useful for checking coverage and cost mid-run.

Usage:
    python scripts/analyze_three_model.py
    python scripts/analyze_three_model.py --run-root /path --out-dir /tmp/a
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MODELS = ("opus", "gemini", "minimax")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-root", type=Path, default=Path("data/outputs/runs/three-model-verified"))
    parser.add_argument("--tasks-file", type=Path, default=Path("configs/three_model_tasks.json"))
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--out-dir", type=Path, default=None, help="default: <run-root>/analysis")
    args = parser.parse_args(argv)

    from hecate.agent.experiment_analysis import (
        cross_model,
        feature_separation,
        load_runs,
        per_model,
        per_task_rows,
        render_markdown,
    )

    tasks = json.loads(args.tasks_file.read_text())["tasks"]
    models = [m for m in args.models if (args.run_root / m).is_dir()]
    if not models:
        print(f"error: no model directories under {args.run_root}", file=sys.stderr)
        return 1
    runs = load_runs(args.run_root, tasks, models)

    summary = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "run_root": str(args.run_root),
        "tasks_file": str(args.tasks_file),
        "n_tasks": len(tasks),
        "models": models,
        "per_model": per_model(runs, models),
        "cross_model": cross_model(runs, models),
        "features": feature_separation(runs, models),
    }

    out = args.out_dir or args.run_root / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=list) + "\n")
    (out / "analysis.md").write_text(render_markdown(summary, models))
    rows = per_task_rows(runs)
    with (out / "per_task.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    for m in models:
        p = summary["per_model"][m]
        print(f"{m:8s} attempted={p['attempted']} infra={p['infra_failures']} "
              f"graded={p['graded']} resolved={p['resolved']} cost=${p['total_cost_usd']}")
    print(f"wrote {out}/analysis.md, summary.json, per_task.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
