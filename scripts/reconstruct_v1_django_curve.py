#!/usr/bin/env python3
"""Reconstruct the v1 leave-django-out λ-sweep. Does not overwrite v1 artifacts.

Fits a fresh FrozenHead(logreg) on the 269 non-django cached CLS vectors using
the same recipe as text_runner._head_fold_metrics. Never loads head_logreg.pt
(that checkpoint was fit on all 500).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from hecate.router.backends import FrozenHead
from hecate.router.dataset import build_examples_from_text
from hecate.router.metrics import DEFAULT_LAMBDAS, sweep_lambda_curve, text_route_metrics
from hecate.router.splits import assign_leave_repo_out
from hecate.router.struct_metrics import assemble_features
from hecate.router.text_runner import (
    _DJANGO_HOLD_N,
    _DJANGO_REPO,
    _DJANGO_REST_N,
    _cls_cache_path,
    _fold_examples,
    _load_cls_cache,
    _pos_weight,
    load_text_train_config,
)
from hecate.data.external_miniswe import read_joined_text_csv
from hecate.utils.manifest import git_commit_sha, write_run_manifest

# Published django-holdout logistic (3-seed mean ± sample std) from
# data/outputs/runs/router-v1-text-ldo/results.json — do not overwrite that file.
_RECORDED_MEAN = 0.4772354082698911
_RECORDED_STD = 0.029759605869338474
_RECORDED_SEEDS = {
    0: 0.4446185997910138,
    1: 0.4841767427974325,
    2: 0.502910882221227,
}
_EXPECTED_ALWAYS_OPUS = 0.7056277056277057
_EXPECTED_ALWAYS_QWEN = 0.5800865800865801
_EXPECTED_ORACLE = 0.7445887445887446
_ENDPOINT_TOL = 1e-9
# Single-seed Route-AUC vs the recorded 3-seed mean: flag if outside mean ± 2 std.
_MEAN_BAND_K = 2.0


def _mismatch(observed: float, expected: float, tol: float) -> bool:
    return abs(observed - expected) > tol


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _fit_ldo_logreg(examples, embeddings, config, seed: int):
    assignment = assign_leave_repo_out(examples, _DJANGO_REPO, seed=seed)
    train, hold = _fold_examples(examples, assignment, fold=0)
    if len(train) != _DJANGO_REST_N or len(hold) != _DJANGO_HOLD_N:
        raise SystemExit(
            f"fold examples mismatch seed={seed}: train={len(train)} hold={len(hold)}"
        )
    leak = sorted({ex.repo for ex in hold} & {ex.repo for ex in train})
    if leak:
        raise SystemExit(f"repo leak into train: {leak}")
    x_train = assemble_features(
        [ex.instance_id for ex in train],
        features="text",
        cls=embeddings,
        metrics=None,
        scaler=None,
    )
    x_hold = assemble_features(
        [ex.instance_id for ex in hold],
        features="text",
        cls=embeddings,
        metrics=None,
        scaler=None,
    )
    head = FrozenHead(
        "logreg",
        in_dim=len(x_train[0]),
        hidden_size=config.hidden_size,
        dropout=config.dropout,
        epochs=config.epochs,
        batch_size=config.batch_size,
        learning_rate=config.learning_rate,
    )
    head.fit(
        x_train,
        [ex.m1_resolves for ex in train],
        seed=seed,
        pos_weight=_pos_weight(train),
    )
    scores = head.predict_proba(x_hold)
    metrics = dict(text_route_metrics(hold, scores))
    metrics["weighted_bce"] = _pos_weight(train) is not None
    return train, hold, scores, metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/router_text.yaml")
    parser.add_argument(
        "--output-dir",
        default="data/outputs/runs/v1-django-holdout-curve",
        help="New run dir. Will not write into router-v1-text or router-v1-text-ldo.",
    )
    parser.add_argument(
        "--curve-seed",
        type=int,
        default=0,
        help="Seed whose scores are written to the curve and per-task CSV.",
    )
    parser.add_argument(
        "--seeds",
        default="0,1,2",
        help="Seeds to refit for the Route-AUC sanity gate (v1 used 0,1,2).",
    )
    args = parser.parse_args(argv)

    root = _repo_root()
    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    forbidden = {
        (root / "data/outputs/runs/router-v1-text").resolve(),
        (root / "data/outputs/runs/router-v1-text-ldo").resolve(),
    }
    if out_dir.resolve() in forbidden:
        raise SystemExit(f"refusing to write into v1 artifact dir {out_dir}")
    leaked_head = root / "data/outputs/runs/router-v1-text/head_logreg.pt"
    if leaked_head.is_file():
        print(
            f"note: ignoring leaked grouped checkpoint {leaked_head} "
            "(fit on all 500; not used)",
            flush=True,
        )

    config = load_text_train_config(config_path=args.config)
    rows = read_joined_text_csv(config.csv_path)
    examples, counts = build_examples_from_text(rows)
    n_django = sum(1 for ex in examples if ex.repo == _DJANGO_REPO)
    n_rest = len(examples) - n_django
    print(
        f"loaded n={len(examples)} django={n_django} rest={n_rest} "
        f"skipped_incomplete={counts.get('skipped_incomplete')} "
        f"skipped_no_text={counts.get('skipped_no_text')}",
        flush=True,
    )
    if n_django != _DJANGO_HOLD_N or n_rest != _DJANGO_REST_N:
        raise SystemExit(
            f"split count mismatch: expected django={_DJANGO_HOLD_N} rest={_DJANGO_REST_N}, "
            f"got {n_django}/{n_rest}"
        )

    cache_path = _cls_cache_path(config.backbone)
    ids = [ex.instance_id for ex in examples]
    embeddings = _load_cls_cache(cache_path, ids)
    if embeddings is None:
        raise SystemExit(
            f"frozen CLS cache missing or incomplete at {cache_path}; "
            "refusing to re-encode with ModernBERT"
        )
    print(f"cls_cache={cache_path} n_vectors={len(embeddings)}", flush=True)

    seed_list = [int(part.strip()) for part in str(args.seeds).split(",") if part.strip()]
    if args.curve_seed not in seed_list:
        seed_list = [args.curve_seed, *seed_list]

    curve_hold: list | None = None
    curve_scores: list[float] | None = None
    seed_aucs: dict[int, float] = {}
    flags: list[str] = []

    for seed in seed_list:
        train, hold, scores, metrics = _fit_ldo_logreg(
            examples, embeddings, config, seed
        )
        auc = float(metrics["route_auc"])
        seed_aucs[seed] = auc
        recorded = _RECORDED_SEEDS.get(seed)
        recorded_note = (
            f" recorded_seed={recorded:.6f} delta={auc - recorded:+.6f}"
            if recorded is not None
            else ""
        )
        print(
            f"seed={seed} n_train={len(train)} n_hold={len(hold)} "
            f"route_auc={auc:.6f} auroc={metrics.get('auroc')}{recorded_note}",
            flush=True,
        )
        if seed == args.curve_seed:
            curve_hold = hold
            curve_scores = scores

    if curve_hold is None or curve_scores is None:
        raise SystemExit("curve seed produced no scores")

    endpoints = text_route_metrics(curve_hold, curve_scores)
    always_opus = float(endpoints["always_large"])
    always_qwen = float(endpoints["always_small"])
    oracle = float(endpoints["oracle"])
    print("\nendpoints (django holdout, labels only):", flush=True)
    for name, observed, expected in (
        ("always-Opus (always_large)", always_opus, _EXPECTED_ALWAYS_OPUS),
        ("always-Qwen (always_small)", always_qwen, _EXPECTED_ALWAYS_QWEN),
        ("oracle", oracle, _EXPECTED_ORACLE),
    ):
        bad = _mismatch(observed, expected, _ENDPOINT_TOL)
        mark = "MISMATCH" if bad else "ok"
        print(
            f"  {name}: observed={observed:.6f} ({100 * observed:.1f}%) "
            f"expected={expected:.6f} ({100 * expected:.1f}%) [{mark}]",
            flush=True,
        )
        if bad:
            flags.append(f"{name}: {observed} vs {expected}")

    mean_auc = sum(seed_aucs.values()) / len(seed_aucs)
    band = _MEAN_BAND_K * _RECORDED_STD
    curve_auc = seed_aucs[args.curve_seed]
    print("\nRoute-AUC sanity:", flush=True)
    print(
        f"  curve seed {args.curve_seed}: {curve_auc:.6f} "
        f"(recorded seed {_RECORDED_SEEDS.get(args.curve_seed, float('nan')):.6f})",
        flush=True,
    )
    print(
        f"  this run mean over {sorted(seed_aucs)}: {mean_auc:.6f} "
        f"(recorded 3-seed mean {_RECORDED_MEAN:.6f} ± {_RECORDED_STD:.6f})",
        flush=True,
    )
    if abs(mean_auc - _RECORDED_MEAN) > band:
        flags.append(
            f"mean Route-AUC {mean_auc:.6f} is outside recorded "
            f"{_RECORDED_MEAN:.6f} ± {_MEAN_BAND_K}*{_RECORDED_STD:.6f}"
        )
        print("  FLAG: mean is outside the recorded ±2 std band", flush=True)
    else:
        print("  mean is inside the recorded ±2 std band", flush=True)
    for seed, auc in seed_aucs.items():
        recorded = _RECORDED_SEEDS.get(seed)
        if recorded is not None and abs(auc - recorded) > 0.02:
            flags.append(f"seed {seed} Route-AUC {auc:.6f} vs recorded {recorded:.6f}")

    curve = sweep_lambda_curve(curve_hold, curve_scores, lambdas=DEFAULT_LAMBDAS)
    out_dir.mkdir(parents=True, exist_ok=True)
    curve_json = out_dir / "v1_django_holdout_curve.json"
    curve_csv = out_dir / "v1_django_holdout_curve.csv"
    per_task = out_dir / "v1_django_holdout_per_task.csv"
    payload = {
        "arm": "text-only v1 leave-django-out curve reconstruction",
        "backbone": config.backbone,
        "n_hold": len(curve_hold),
        "n_train": _DJANGO_REST_N,
        "hold_repo": _DJANGO_REPO,
        "curve_seed": args.curve_seed,
        "lambdas": len(curve),
        "cls_cache": str(cache_path),
        "used_grouped_head_logreg_pt": False,
        "endpoints": {
            "always_opus": always_opus,
            "always_qwen": always_qwen,
            "oracle": oracle,
        },
        "route_auc_by_seed": seed_aucs,
        "route_auc_mean": mean_auc,
        "recorded_route_auc_mean": _RECORDED_MEAN,
        "recorded_route_auc_std": _RECORDED_STD,
        "flags": flags,
        "points": curve,
        "cost_definition": (
            "cost = share routed to the large model (Claude 4 Opus); "
            "frac_cheap = share routed to Qwen; use_small = score >= lambda"
        ),
    }
    curve_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with curve_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["lambda", "frac_cheap", "cost", "resolved_rate"],
        )
        writer.writeheader()
        writer.writerows(curve)
    with per_task.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "instance_id",
                "predicted_score",
                "resolved_by_qwen",
                "resolved_by_opus",
            ],
        )
        writer.writeheader()
        for ex, score in zip(curve_hold, curve_scores, strict=True):
            writer.writerow(
                {
                    "instance_id": ex.instance_id,
                    "predicted_score": score,
                    "resolved_by_qwen": int(ex.m1_resolves),
                    "resolved_by_opus": int(ex.m2_resolves),
                }
            )

    write_run_manifest(
        out_dir / "manifest.json",
        {
            "run_id": "v1-django-holdout-curve",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "git_commit": git_commit_sha(cwd=root),
            "config_path": str(config.config_path),
            "cli_overrides": {
                "curve_seed": args.curve_seed,
                "seeds": seed_list,
                "output_dir": str(out_dir),
            },
            "config_snapshot": {
                "backbone": config.backbone,
                "epochs": config.epochs,
                "batch_size": config.batch_size,
                "learning_rate": config.learning_rate,
                "heads": list(config.heads),
                "csv_path": str(config.csv_path),
            },
            "environment": {
                "python": sys.version.split()[0],
            },
            "status": "flagged" if flags else "ok",
            "n_hold": len(curve_hold),
            "n_train": _DJANGO_REST_N,
            "flags": flags,
            "outputs": {
                "curve_json": str(curve_json),
                "curve_csv": str(curve_csv),
                "per_task_csv": str(per_task),
            },
        },
    )
    print(f"\nwrote {curve_json}", flush=True)
    print(f"wrote {curve_csv}", flush=True)
    print(f"wrote {per_task}", flush=True)
    if flags:
        print("FLAGS:", flush=True)
        for item in flags:
            print(f"  - {item}", flush=True)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
