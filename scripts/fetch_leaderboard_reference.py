#!/usr/bin/env python3
"""Snapshot the leaderboard entries' run configs for the r2 rerun (spec 018).

For each of the three bash-only leaderboard entries r2 matches, fetches one
published trajectory and writes its ``info.config`` and ``info.mini_version``
to configs/leaderboard_reference/<entry>.json. Also fetches MiniMax
trajectories for a sample of tasks and writes per-call provider counts to
configs/leaderboard_reference/minimax_provider_mix.json.

Run once and commit the output: scripts/check_leaderboard_config.py diffs r2's
resolved config against these files offline.

Usage:
    python scripts/fetch_leaderboard_reference.py
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ENTRIES = {
    "opus": "20260217_mini-v2.0.0_claude-4-5-opus-high",
    "gemini": "20260217_mini-v2.0.0_gemini-3-flash-high",
    "minimax": "20260217_mini-v2.0.0_minimax-2-5-high",
}
TRAJS = "https://swe-bench-submissions.s3.amazonaws.com/bash-only"
TASKS_FILE = Path("configs/three_model_tasks.json")
OUT_DIR = Path("configs/leaderboard_reference")
# Config is identical across an entry's trajectories (checked on 3 tasks per
# entry); one is enough for the snapshot.
CONFIG_TASK = "astropy__astropy-13033"
PROVIDER_SAMPLE_EVERY = 5  # every 5th of the 100 tasks -> 20 trajectories


def fetch_traj(entry: str, instance_id: str) -> dict:
    url = f"{TRAJS}/{entry}/trajs/{instance_id}/{instance_id}.traj.json"
    with urllib.request.urlopen(url, timeout=120) as resp:
        return json.load(resp)


def reference_from_traj(entry: str, instance_id: str, traj: dict) -> dict:
    info = traj["info"]
    return {
        "entry": entry,
        "source": f"{TRAJS}/{entry}/trajs/{instance_id}/{instance_id}.traj.json",
        "mini_version": info.get("mini_version"),
        "config": info["config"],
    }


def provider_counts(trajs: list[dict]) -> dict:
    calls: Counter[str] = Counter()
    tasks: Counter[str] = Counter()
    mixed = 0
    for traj in trajs:
        providers = [
            str(m.get("extra", {}).get("response", {}).get("provider"))
            for m in traj["messages"]
            if m.get("role") == "assistant"
        ]
        calls.update(providers)
        tasks.update(set(providers))
        mixed += len(set(providers)) > 1
    total = sum(calls.values())
    return {
        "calls": dict(calls.most_common()),
        "call_share": {p: round(n / total, 4) for p, n in calls.most_common()},
        "tasks_touching": dict(tasks.most_common()),
        "tasks_with_multiple_providers": mixed,
        "n_tasks": len(trajs),
        "n_calls": total,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for entry in ENTRIES.values():
        ref = reference_from_traj(entry, CONFIG_TASK, fetch_traj(entry, CONFIG_TASK))
        (args.out_dir / f"{entry}.json").write_text(json.dumps(ref, indent=2) + "\n")
        print(f"wrote {entry}.json (mini_version={ref['mini_version']})")

    ids = [t["instance_id"] for t in json.loads(TASKS_FILE.read_text())["tasks"]]
    sample = ids[::PROVIDER_SAMPLE_EVERY]
    with cf.ThreadPoolExecutor(8) as pool:
        trajs = list(pool.map(lambda i: fetch_traj(ENTRIES["minimax"], i), sample))
    mix = {"entry": ENTRIES["minimax"], "instance_ids": sample, **provider_counts(trajs)}
    (args.out_dir / "minimax_provider_mix.json").write_text(json.dumps(mix, indent=2) + "\n")
    print(f"wrote minimax_provider_mix.json: {mix['call_share']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
