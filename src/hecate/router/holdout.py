"""Per-task holdout scores so a λ-curve can be rebuilt without the model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def holdout_scores_path(output_dir: Path) -> Path:
    return Path(output_dir) / "holdout_scores.jsonl"


def write_holdout_scores(
    path: Path,
    *,
    examples: list[Any],
    scores: list[float],
    seed: int,
    fold: int,
    arm: str,
    k_eval: int,
) -> Path:
    """Append per-task holdout scores so a λ-curve can be rebuilt without the model."""
    if len(examples) != len(scores):
        raise ValueError("examples and scores must be the same length")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        for example, score in zip(examples, scores, strict=True):
            handle.write(
                json.dumps(
                    {
                        "instance_id": example.instance_id,
                        "seed": seed,
                        "fold": fold,
                        "arm": arm,
                        "k_eval": k_eval,
                        "score": float(score),
                        "m1_resolves": bool(example.m1_resolves),
                        "m2_resolves": bool(example.m2_resolves),
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    return target
