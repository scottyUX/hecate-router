#!/usr/bin/env python3
"""Train the Stage-4 semantic router (issue #18).

Usage:
    python scripts/run_train.py --labels .../labels.jsonl --generations .../generations.jsonl
    python scripts/run_train.py ... --backend modernbert
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hecate Stage 4 router trainer")
    parser.add_argument("--config", default="configs/router.yaml")
    parser.add_argument("--labels", required=True, help="Stage-3 labels.jsonl")
    parser.add_argument(
        "--generations",
        required=True,
        help="Stage-1 generations.jsonl (prompts; patches are not used as input)",
    )
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--backend",
        choices=("scripted", "modernbert"),
        default="scripted",
        help="scripted = no torch (tests/dry). modernbert = live fine-tune",
    )
    args = parser.parse_args(argv)

    from hecate.router import (
        ModernBertBackend,
        load_train_config,
        run_train,
    )

    config = load_train_config(
        config_path=args.config,
        labels_path=args.labels,
        generations_path=args.generations,
        output_dir=args.output_dir,
        run_id=args.run_id,
    )
    backend = None
    if args.backend == "modernbert":
        backend = ModernBertBackend(
            config.backbone,
            max_tokens=config.max_tokens,
            epochs=config.epochs,
            batch_size=config.batch_size,
            learning_rate=config.learning_rate,
        )
    result = run_train(config, backend=backend)
    print(
        f"run_id={result.run_id} examples={result.examples_path} "
        f"mean_route_auc={result.mean_route_auc:.4f} go_nogo={result.go_nogo} "
        f"split={result.split_strategy} trunc={result.truncation_rate:.3f}"
    )
    print(f"metrics={result.metrics_path}")
    print(f"manifest={result.manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
