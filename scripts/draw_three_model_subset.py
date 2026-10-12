#!/usr/bin/env python3
"""Pre-register the r2 task subset (spec 018): a seeded draw from r1's tasks.

Draws N tasks uniformly at random without replacement from an existing task
file (r1's configs/three_model_tasks.json) and writes them in the same shape,
plus the source file and its git commit. Run once, commit the output, before
any model is called.

Usage:
    python scripts/draw_three_model_subset.py            # writes the file
    python scripts/draw_three_model_subset.py --check    # verify it still matches
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

SOURCE = Path("configs/three_model_tasks.json")
SEED = 20261012
N_TASKS = 50
DEFAULT_OUT = Path("configs/three_model_tasks_r2.json")


def draw(tasks: list[dict], *, seed: int = SEED, n: int = N_TASKS) -> list[dict]:
    """Uniform sample without replacement, deterministic given the task set.

    Sorts by instance_id first so the draw does not depend on file order.
    """
    pool = sorted(tasks, key=lambda t: t["instance_id"])
    return sorted(random.Random(seed).sample(pool, n), key=lambda t: t["instance_id"])


def build_payload(source: dict, source_path: Path, source_commit: str | None) -> dict:
    tasks = draw(source["tasks"])
    return {
        "dataset": source["dataset"],
        "split": source["split"],
        "seed": SEED,
        "method": f"uniform random sample without replacement of {N_TASKS} of the "
        f"{len(source['tasks'])} tasks in {source_path}, sorted by instance_id "
        "before sampling",
        "source_file": str(source_path),
        "source_commit": source_commit,
        "n": len(tasks),
        "difficulty_counts": dict(Counter(t["difficulty"] for t in tasks)),
        "repo_counts": dict(Counter(t["repo"] for t in tasks).most_common()),
        "tasks": tasks,
    }


def _last_commit(path: Path) -> str | None:
    out = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", str(path)],
        capture_output=True, text=True, check=False,
    )
    return out.stdout.strip() or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    source = json.loads(args.source.read_text())
    tasks = draw(source["tasks"])

    if args.check:
        existing = json.loads(args.out.read_text())
        if existing["tasks"] != tasks:
            print(f"error: {args.out} does not match seed {SEED}", file=sys.stderr)
            return 1
        print(f"ok: {args.out} matches seed {SEED}")
        return 0

    payload = build_payload(source, args.source, _last_commit(args.source))
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {args.out}: {payload['difficulty_counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
