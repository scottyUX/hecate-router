#!/usr/bin/env python3
"""Extract per-run trajectory features for the three-model experiment.

Walks <run-root>/<model>/<instance_id>/<instance_id>.traj.json, computes the
features in hecate.agent.traj_features, joins repo + difficulty from the
pre-registered task file, and writes one row per (model, instance) as CSV and
JSONL. Grading results are deliberately not joined here (that happens in the
analysis step), so nothing in these features can depend on the label.

Usage:
    python scripts/extract_traj_features.py
    python scripts/extract_traj_features.py --run-root /path/to/trajs --out-dir /tmp/feat
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--run-root", type=Path, default=Path("data/outputs/runs/three-model-verified")
    )
    parser.add_argument("--tasks-file", type=Path, default=Path("configs/three_model_tasks.json"))
    parser.add_argument("--out-dir", type=Path, default=None, help="default: --run-root")
    args = parser.parse_args(argv)

    from hecate.agent.traj_features import extract, iter_run_trajectories, load_preds

    tasks = {t["instance_id"]: t for t in json.loads(args.tasks_file.read_text())["tasks"]}
    out_dir = args.out_dir or args.run_root
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    preds_cache: dict[str, dict[str, str]] = {}
    failures: list[str] = []
    for model, traj_path in iter_run_trajectories(args.run_root):
        preds = preds_cache.setdefault(model, load_preds(args.run_root / model))
        try:
            traj = json.loads(traj_path.read_text())
            feats = extract(traj, model=model, patch=preds.get(traj_path.parent.name))
        except Exception as exc:  # one bad file must not sink the table
            failures.append(f"{traj_path}: {exc!r}")
            continue
        task = tasks.get(feats.instance_id, {})
        rows.append(
            {
                **feats.to_dict(),
                "repo": task.get("repo"),
                "difficulty": task.get("difficulty"),
                "in_task_set": feats.instance_id in tasks,
            }
        )

    if not rows:
        print(f"error: no trajectories under {args.run_root}", file=sys.stderr)
        return 1

    jsonl = out_dir / "traj_features.jsonl"
    with jsonl.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    csv_path = out_dir / "traj_features.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"rows={len(rows)} by_model={dict(Counter(r['model'] for r in rows))}")
    print(f"wrote {csv_path} and {jsonl}")
    for f in failures:
        print(f"warning: skipped {f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
