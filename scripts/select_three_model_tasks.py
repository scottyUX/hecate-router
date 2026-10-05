#!/usr/bin/env python3
"""Pre-register the 100-task set for the three-model Verified experiment.

Draws 100 SWE-bench Verified instances uniformly at random (fixed seed) and
writes them, with repo and the dataset's own difficulty annotation, to
configs/three_model_tasks.json. Run once, commit the output, then never
re-run against a different seed: the task set must be fixed before any model
is called.

Usage:
    python scripts/select_three_model_tasks.py            # writes the file
    python scripts/select_three_model_tasks.py --check    # verify it still matches
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

DATASET = "princeton-nlp/SWE-bench_Verified"
SEED = 20261005
N_TASKS = 100
DEFAULT_OUT = Path("configs/three_model_tasks.json")


def select(rows: list[dict], *, seed: int = SEED, n: int = N_TASKS) -> list[dict]:
    """Uniform sample without replacement, deterministic given the row set.

    Sorts by instance_id first so the draw does not depend on dataset row order.
    """
    pool = sorted(rows, key=lambda r: r["instance_id"])
    picked = random.Random(seed).sample(pool, n)
    return sorted(
        (
            {
                "instance_id": r["instance_id"],
                "repo": r["repo"],
                "difficulty": r["difficulty"],
            }
            for r in picked
        ),
        key=lambda r: r["instance_id"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    from datasets import load_dataset

    ds = load_dataset(DATASET, split="test", cache_dir="data/raw/hf")
    rows = [
        {"instance_id": r["instance_id"], "repo": r["repo"], "difficulty": r["difficulty"]}
        for r in ds
    ]
    tasks = select(rows)
    payload = {
        "dataset": DATASET,
        "split": "test",
        "seed": SEED,
        "method": "uniform random sample without replacement over all 500 "
        "Verified test instances, sorted by instance_id before sampling",
        "n": len(tasks),
        "difficulty_counts": dict(Counter(t["difficulty"] for t in tasks)),
        "repo_counts": dict(Counter(t["repo"] for t in tasks).most_common()),
        "tasks": tasks,
    }

    if args.check:
        existing = json.loads(args.out.read_text())
        if existing["tasks"] != tasks:
            print(f"error: {args.out} does not match seed {SEED}", file=sys.stderr)
            return 1
        print(f"ok: {args.out} matches seed {SEED}")
        return 0

    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {args.out}: {payload['difficulty_counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
