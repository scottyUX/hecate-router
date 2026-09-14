#!/usr/bin/env python3
"""Train the K-turn trajectory router (v3).

Usage:
    python scripts/run_train_traj.py --backend scripted --arm k3
    python scripts/run_train_traj.py --backend lora --arm k0 --split leave-repo
    python scripts/run_train_traj.py --backend lora --arm k3 --split leave-repo
    python scripts/run_train_traj.py --backend lora --arm k1 --split specialist

LoRA runs require HECATE_ARTIFACTS_URI (gs://... or file://...) so adapters
are copied off the training disk. Pass --allow-unsynced only to debug locally.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Hecate trajectory router v3 (LoRA value head)"
    )
    parser.add_argument("--config", default="configs/router_traj.yaml")
    parser.add_argument("--csv", default=None, help="Joined labels CSV")
    parser.add_argument("--traj-dir", default=None, help="Directory or JSONL of traces")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--split",
        choices=("grouped", "leave-repo", "specialist"),
        default="grouped",
        help="grouped = 5-fold pack-by-repo. leave-repo = hold --hold-repo then reverse. "
        "specialist = train and test on --hold-repo (80/20, fold 0 holdout).",
    )
    parser.add_argument(
        "--hold-repo",
        default="django/django",
        help="leave-repo: repo to hold out. specialist: repo to train AND test on.",
    )
    parser.add_argument(
        "--allow-unsynced",
        action="store_true",
        help="Permit --backend lora without HECATE_ARTIFACTS_URI. Weights may be lost.",
    )
    parser.add_argument("--arm", choices=("k0", "k1", "k3"), default="k3")
    parser.add_argument(
        "--backend",
        choices=("scripted", "lora"),
        default="scripted",
        help="scripted = no torch. lora = Qwen2.5-Coder-7B QLoRA",
    )
    parser.add_argument(
        "--provenance",
        default="unknown",
        help="Trace source recorded on the manifest (s3|docent|hf|re-run)",
    )
    parser.add_argument(
        "--seeds",
        default=None,
        help="Comma-separated seeds. Smoke uses 0; config default is 0,1,2.",
    )
    parser.add_argument(
        "--hold-only",
        action="store_true",
        help="Leave-repo: train/eval the hold-repo fold only (skip the reverse fold).",
    )
    args = parser.parse_args(argv)

    from hecate.router.traj import TRAJ_ARMS
    from hecate.router.traj_runner import load_traj_train_config, run_traj_train
    from hecate.utils.env import load_env

    load_env()
    if args.arm not in TRAJ_ARMS:
        parser.error(f"unknown arm {args.arm!r}; expected {tuple(TRAJ_ARMS)}")

    seeds = None
    if args.seeds:
        seeds = tuple(int(part.strip()) for part in args.seeds.split(",") if part.strip())
    config = load_traj_train_config(
        config_path=args.config,
        csv_path=args.csv,
        traj_dir=args.traj_dir,
        output_dir=args.output_dir,
        run_id=args.run_id,
        split=args.split,
        hold_repo=args.hold_repo,
        arm=args.arm,
        provenance=args.provenance,
        seeds=seeds,
        hold_only=args.hold_only,
        allow_unsynced=args.allow_unsynced,
    )
    result = run_traj_train(config, backend=args.backend)
    print(
        f"run_id={result.run_id} arm={result.arm} "
        f"mean_route_auc={result.mean_route_auc:.4f} "
        f"split={result.split_strategy} trunc={result.truncation_rate:.3f}"
    )
    print(f"results={result.results_path}")
    print(f"manifest={result.manifest_path}")
    print(f"readme={result.readme_path}")
    if result.artifacts_uri:
        print(f"artifacts={result.artifacts_uri}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
