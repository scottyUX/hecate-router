"""Cross-validate the text-only frozen-encoder router."""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from hecate.data.external_miniswe import (
    HEADROOM_PP,
    TEXT_CSV_NAME,
    JoinedLabel,
    complementarity,
    read_joined_text_csv,
)
from hecate.router.backends import FrozenHead, FrozenModernBertEmbedder, ScriptedBackend
from hecate.router.dataset import (
    RouterExample,
    WhitespaceTokenizer,
    build_examples_from_text,
)
from hecate.router.metrics import text_route_metrics
from hecate.router.splits import (
    FoldAssignment,
    assign_grouped_repo_folds,
    assign_label_stratified_folds,
    repo_histogram,
)
from hecate.utils.manifest import git_commit_sha, write_run_manifest

_BALANCE_LOW = 0.40
_BALANCE_HIGH = 0.60
_METRIC_KEYS = (
    "route_auc",
    "lift_vs_large_auc",
    "auroc",
    "f1",
    "accuracy",
    "brier",
    "always_small",
    "always_large",
    "oracle",
    "headroom",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class TextTrainConfig:
    config_path: Path
    csv_path: Path
    output_dir: Path
    run_id: str
    backbone: str
    max_tokens: int
    n_folds: int
    seeds: tuple[int, ...]
    epochs: int
    batch_size: int
    learning_rate: float
    freeze_encoder: bool
    heads: tuple[str, ...]
    hidden_size: int
    dropout: float
    cli_overrides: dict[str, Any]


@dataclass(frozen=True)
class TextTrainResult:
    run_id: str
    output_dir: Path
    results_path: Path
    manifest_path: Path
    readme_path: Path
    mean_route_auc: float
    split_strategy: str
    truncation_rate: float


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return data


def load_text_train_config(
    *,
    config_path: Path | str | None = None,
    csv_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    run_id: str | None = None,
) -> TextTrainConfig:
    root = _repo_root()
    resolved = (
        Path(config_path) if config_path is not None else root / "configs" / "router_text.yaml"
    )
    if not resolved.is_absolute():
        resolved = root / resolved
    data = _load_yaml(resolved)
    rid = run_id or uuid.uuid4().hex[:12]
    out = (
        Path(output_dir)
        if output_dir is not None
        else root / "data" / "outputs" / "runs" / rid
    )
    default_csv = root / "data" / "external" / TEXT_CSV_NAME
    csv = Path(csv_path) if csv_path is not None else Path(
        data.get("csv_path") or default_csv
    )
    if not csv.is_absolute():
        csv = root / csv
    seeds_raw = data.get("seeds") or [0, 1, 2]
    heads_raw = data.get("heads") or ["logreg", "mlp"]
    return TextTrainConfig(
        config_path=resolved,
        csv_path=csv,
        output_dir=out,
        run_id=rid,
        backbone=str(data.get("backbone") or "answerdotai/ModernBERT-base"),
        max_tokens=int(data.get("max_tokens") or 2048),
        n_folds=int(data.get("n_folds") or 5),
        seeds=tuple(int(s) for s in seeds_raw),
        epochs=int(data.get("epochs") or 4),
        batch_size=int(data.get("batch_size") or 8),
        learning_rate=float(data.get("learning_rate") or 2e-5),
        freeze_encoder=bool(data.get("freeze_encoder", True)),
        heads=tuple(str(h) for h in heads_raw),
        hidden_size=int(data.get("hidden_size") or 128),
        dropout=float(data.get("dropout") or 0.2),
        cli_overrides={
            "csv_path": str(csv),
            "output_dir": str(out),
            "run_id": rid,
        },
    )


def _pos_rate(examples: list[RouterExample]) -> float:
    if not examples:
        return 0.0
    return sum(1 for ex in examples if ex.m1_resolves) / len(examples)


def _pos_weight(examples: list[RouterExample]) -> float | None:
    rate = _pos_rate(examples)
    n_pos = sum(1 for ex in examples if ex.m1_resolves)
    n_neg = len(examples) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    if rate < _BALANCE_LOW or rate > _BALANCE_HIGH:
        return n_neg / n_pos
    return None


def _fold_examples(
    examples: list[RouterExample], assignment: FoldAssignment, fold: int
) -> tuple[list[RouterExample], list[RouterExample]]:
    by_id = {ex.instance_id: ex for ex in examples}
    train = [
        by_id[iid] for iid, assigned in assignment.fold_of.items() if assigned != fold
    ]
    hold = [
        by_id[iid] for iid, assigned in assignment.fold_of.items() if assigned == fold
    ]
    return train, hold


def _mean_std(values: list[float | None]) -> dict[str, float | None]:
    nums = [float(v) for v in values if v is not None and not (
        isinstance(v, float) and math.isnan(v)
    )]
    if not nums:
        return {"mean": None, "std": None, "n": 0}
    mean = sum(nums) / len(nums)
    if len(nums) == 1:
        return {"mean": mean, "std": 0.0, "n": len(nums)}
    var = sum((x - mean) ** 2 for x in nums) / (len(nums) - 1)
    return {"mean": mean, "std": var ** 0.5, "n": len(nums)}


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in _METRIC_KEYS:
        out[key] = _mean_std([row.get(key) for row in rows])
    return out


def _scripted_fold_metrics(
    hold: list[RouterExample],
    backend: ScriptedBackend,
) -> dict[str, Any]:
    scores = backend.predict_proba(
        [ex.text for ex in hold],
        instance_ids=[ex.instance_id for ex in hold],
    )
    return dict(text_route_metrics(hold, scores))


def _head_fold_metrics(
    train: list[RouterExample],
    hold: list[RouterExample],
    embeddings: dict[str, list[float]],
    *,
    kind: str,
    config: TextTrainConfig,
    seed: int,
) -> dict[str, Any]:
    weight = _pos_weight(train)
    head = FrozenHead(
        kind,
        in_dim=len(next(iter(embeddings.values()))),
        hidden_size=config.hidden_size,
        dropout=config.dropout,
        epochs=config.epochs,
        batch_size=config.batch_size,
        learning_rate=config.learning_rate,
    )
    head.fit(
        [embeddings[ex.instance_id] for ex in train],
        [ex.m1_resolves for ex in train],
        seed=seed,
        pos_weight=weight,
    )
    scores = head.predict_proba([embeddings[ex.instance_id] for ex in hold])
    payload = dict(text_route_metrics(hold, scores))
    payload["weighted_bce"] = weight is not None
    payload["pos_weight"] = weight
    payload["train_pos_rate"] = _pos_rate(train)
    payload["hold_pos_rate"] = _pos_rate(hold)
    return payload


def _cv_rows(
    examples: list[RouterExample],
    assignment: FoldAssignment,
    *,
    config: TextTrainConfig,
    seed: int,
    head: str,
    embeddings: dict[str, list[float]] | None,
    scripted: ScriptedBackend | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fold in range(assignment.n_folds):
        train, hold = _fold_examples(examples, assignment, fold)
        if not train or not hold:
            continue
        hold_repos = sorted({ex.repo for ex in hold})
        train_repos = sorted({ex.repo for ex in train})
        leak = sorted(set(hold_repos) & set(train_repos))
        if scripted is not None:
            metrics = _scripted_fold_metrics(hold, scripted)
            metrics["weighted_bce"] = False
            metrics["pos_weight"] = None
            metrics["train_pos_rate"] = _pos_rate(train)
            metrics["hold_pos_rate"] = _pos_rate(hold)
        else:
            assert embeddings is not None
            metrics = _head_fold_metrics(
                train, hold, embeddings, kind=head, config=config, seed=seed
            )
        rows.append(
            {
                "seed": seed,
                "fold": fold,
                "head": head,
                "split": assignment.strategy,
                "n_train": len(train),
                "n_hold": len(hold),
                "hold_repos": hold_repos,
                "repo_leak": leak,
                **metrics,
            }
        )
    return rows


def _fmt_mean_std(stat: dict[str, Any] | None) -> str:
    if not stat or stat.get("mean") is None:
        return "n/a"
    std = stat.get("std")
    std_s = "n/a" if std is None else f"{float(std):.3f}"
    return f"{float(stat['mean']):.3f} ± {std_s}"


def _write_readme(path: Path, payload: dict[str, Any]) -> Path:
    grouped = payload.get("primary", {})
    logreg = grouped.get("logreg") or grouped.get("scripted") or {}
    mlp = grouped.get("mlp") or {}
    trunc = float(payload.get("truncation_rate") or 0.0)
    lines = [
        "# Text-only router v1",
        "",
        "Dataset: SWE-bench **Verified** (500), mini-SWE-agent v1.0.0, "
        "Qwen3-Coder-480B-A35B-Instruct vs Claude 4 Opus.",
        "",
        "This is the **text-only v1** arm. Encoder is **frozen** ModernBERT-base. "
        "Headline split is **grouped by repo** (each repo in one fold).",
        "",
        f"Headroom vs always-Opus: **{HEADROOM_PP} pp** "
        "(oracle 71.4% − always-large 67.6%). Routing value is cost "
        "(send both-win tasks to Qwen), not accuracy lift.",
        "",
        f"Truncation rate at 2048 tokens: {trunc:.3f}.",
        "",
        "## Route-AUC (normalized cost vs resolved-rate)",
        "",
        f"- logreg (frozen CLS): mean {_fmt_mean_std(logreg.get('route_auc'))}",
        f"- mlp (frozen CLS): mean {_fmt_mean_std(mlp.get('route_auc'))}",
        "",
        "Label-stratified (repo-leaky) numbers are in `results.json` under "
        "`split_sensitivity`.",
        "",
        "Do not merge with Qwen 2.5 Lite labels. Spec 015 `run_train.py` is unchanged.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_text_train(
    config: TextTrainConfig,
    *,
    backend: str = "scripted",
    scripted_scores: dict[str, float] | None = None,
    examples: list[RouterExample] | None = None,
) -> TextTrainResult:
    if examples is None:
        rows = read_joined_text_csv(config.csv_path)
        examples, counts = build_examples_from_text(rows)
    else:
        counts = {
            "n_examples": len(examples),
            "skipped_incomplete": 0,
            "skipped_no_text": 0,
            "truncated": sum(1 for ex in examples if ex.truncated),
        }
    if not examples:
        raise ValueError("No router examples after loading the text join")

    histogram = repo_histogram(examples)
    comp = complementarity(
        [
            JoinedLabel(
                instance_id=ex.instance_id,
                repo=ex.repo,
                small_model_resolved=ex.m1_resolves,
                large_model_resolved=ex.m2_resolves,
            )
            for ex in examples
        ]
    )

    embeddings: dict[str, list[float]] | None = None
    truncation_rate = (
        counts["truncated"] / counts["n_examples"] if counts["n_examples"] else 0.0
    )
    scripted: ScriptedBackend | None = None
    heads = config.heads
    if backend == "scripted":
        scripted = ScriptedBackend(scripted_scores or {})
        heads = ("scripted",)
    elif backend == "frozen":
        embedder = FrozenModernBertEmbedder(
            config.backbone,
            max_tokens=config.max_tokens,
            batch_size=config.batch_size,
        )
        vectors = embedder.embed([ex.text for ex in examples])
        embeddings = {
            ex.instance_id: vec for ex, vec in zip(examples, vectors, strict=True)
        }
        truncation_rate = (
            embedder.n_truncated / len(examples) if examples else 0.0
        )
    else:
        raise ValueError(f"unknown backend: {backend}")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    primary_rows: dict[str, list[dict[str, Any]]] = {head: [] for head in heads}
    sensitivity_rows: dict[str, list[dict[str, Any]]] = {head: [] for head in heads}

    for seed in config.seeds:
        grouped = assign_grouped_repo_folds(
            examples, n_folds=config.n_folds, seed=seed
        )
        leaky = assign_label_stratified_folds(
            examples, n_folds=config.n_folds, seed=seed
        )
        for head in heads:
            primary_rows[head].extend(
                _cv_rows(
                    examples,
                    grouped,
                    config=config,
                    seed=seed,
                    head=head,
                    embeddings=embeddings,
                    scripted=scripted,
                )
            )
            sensitivity_rows[head].extend(
                _cv_rows(
                    examples,
                    leaky,
                    config=config,
                    seed=seed,
                    head=head,
                    embeddings=embeddings,
                    scripted=scripted,
                )
            )

    checkpoints: dict[str, str] = {}
    if embeddings is not None:
        import torch

        for kind in config.heads:
            head = FrozenHead(
                kind,
                in_dim=len(next(iter(embeddings.values()))),
                hidden_size=config.hidden_size,
                dropout=config.dropout,
                epochs=config.epochs,
                batch_size=config.batch_size,
                learning_rate=config.learning_rate,
            )
            head.fit(
                [embeddings[ex.instance_id] for ex in examples],
                [ex.m1_resolves for ex in examples],
                seed=config.seeds[0],
                pos_weight=_pos_weight(examples),
            )
            ckpt = config.output_dir / f"head_{kind}.pt"
            torch.save(head.state_dict(), ckpt)
            checkpoints[kind] = str(ckpt)

    primary_summary = {head: _summarize(rows) for head, rows in primary_rows.items()}
    sensitivity_summary = {
        head: _summarize(rows) for head, rows in sensitivity_rows.items()
    }
    headline = primary_summary.get("logreg") or primary_summary.get("scripted") or {}
    mean_auc = headline.get("route_auc", {}).get("mean")
    if mean_auc is None:
        mean_auc = 0.0

    results = {
        "dataset": "qwen3coder_vs_claude4opus_with_text",
        "split": "verified",
        "scaffold": "mini-SWE-agent v1.0.0",
        "small_model": "Qwen3-Coder-480B-A35B-Instruct",
        "large_model": "Claude 4 Opus",
        "arm": "text-only v1",
        "encoder": "frozen ModernBERT-base",
        "n_examples": counts["n_examples"],
        "truncation_rate": truncation_rate,
        "max_tokens": config.max_tokens,
        "headroom_pp": HEADROOM_PP,
        "complementarity": comp,
        "repo_histogram": histogram,
        "split_primary": "grouped_repo",
        "split_sensitivity": "label_stratified",
        "seeds": list(config.seeds),
        "n_folds": config.n_folds,
        "primary": primary_summary,
        "primary_folds": primary_rows,
        "sensitivity": sensitivity_summary,
        "sensitivity_folds": sensitivity_rows,
        "checkpoints": checkpoints,
        "backbone": config.backbone,
        "freeze_encoder": config.freeze_encoder,
    }
    results_path = config.output_dir / "results.json"
    results_path.write_text(
        json.dumps(results, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    snapshot = _load_yaml(config.config_path)
    manifest = write_run_manifest(
        config.output_dir / "manifest.json",
        {
            "run_id": config.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": git_commit_sha(),
            "config_path": str(config.config_path),
            "config_snapshot": snapshot,
            "cli_overrides": config.cli_overrides,
            "backbone": config.backbone,
            "freeze_encoder": config.freeze_encoder,
            "n_folds": config.n_folds,
            "seeds": list(config.seeds),
            "split_strategy": "grouped_repo",
            "truncation_rate": truncation_rate,
            "mean_route_auc": mean_auc,
            "headroom_pp": HEADROOM_PP,
            "n_examples": counts["n_examples"],
            "checkpoints": checkpoints,
        },
    )
    readme_path = _write_readme(config.output_dir / "README.md", results)
    return TextTrainResult(
        run_id=config.run_id,
        output_dir=config.output_dir,
        results_path=results_path,
        manifest_path=manifest,
        readme_path=readme_path,
        mean_route_auc=float(mean_auc),
        split_strategy="grouped_repo",
        truncation_rate=truncation_rate,
    )
