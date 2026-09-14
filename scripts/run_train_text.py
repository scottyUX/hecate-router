#!/usr/bin/env python3
"""Train the text-only Verified router (frozen ModernBERT).

Usage:
    python scripts/run_train_text.py --backend scripted
    python scripts/run_train_text.py --backend frozen
    python scripts/run_train_text.py --backend frozen --split specialist --seeds 0
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Hecate text-only v1 router (frozen ModernBERT)"
    )
    parser.add_argument("--config", default="configs/router_text.yaml")
    parser.add_argument(
        "--csv",
        default=None,
        help="Joined text CSV (default: data/external/qwen3coder_vs_claude4opus_with_text.csv)",
    )
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--split",
        choices=("grouped", "leave-repo", "specialist"),
        default="grouped",
        help="grouped = 5-fold pack-by-repo (v1). leave-repo = hold --hold-repo, then reverse. "
        "specialist = train and test on --hold-repo (80/20, fold 0 holdout).",
    )
    parser.add_argument(
        "--hold-repo",
        default="django/django",
        help="leave-repo: repo to hold out (fold 0). specialist: repo to train AND test on.",
    )
    parser.add_argument(
        "--features",
        choices=("text", "metrics", "fusion"),
        default="text",
        help="text = frozen CLS only (v1). metrics = oracle-file AST vector. "
        "fusion = CLS + scaled metrics (localization leak).",
    )
    parser.add_argument(
        "--backend",
        choices=("scripted", "frozen"),
        default="scripted",
        help="scripted = no torch. frozen = ModernBERT embeddings + logreg/mlp heads",
    )
    parser.add_argument(
        "--seeds",
        default=None,
        help="Comma-separated seeds. Smoke uses 0; config default is 0,1,2.",
    )
    args = parser.parse_args(argv)

    from hecate.router.text_runner import load_text_train_config, run_text_train
    from hecate.utils.env import load_env

    load_env()
    seeds = None
    if args.seeds:
        seeds = tuple(int(part.strip()) for part in args.seeds.split(",") if part.strip())
    config = load_text_train_config(
        config_path=args.config,
        csv_path=args.csv,
        output_dir=args.output_dir,
        run_id=args.run_id,
        split=args.split,
        hold_repo=args.hold_repo,
        features=args.features,
        seeds=seeds,
    )
    result = run_text_train(config, backend=args.backend)
    print(
        f"run_id={result.run_id} mean_route_auc={result.mean_route_auc:.4f} "
        f"split={result.split_strategy} trunc={result.truncation_rate:.3f} "
        f"features={args.features}"
    )
    print(f"results={result.results_path}")
    print(f"manifest={result.manifest_path}")
    print(f"readme={result.readme_path}")
    if result.artifacts_uri:
        print(f"artifacts={result.artifacts_uri}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
