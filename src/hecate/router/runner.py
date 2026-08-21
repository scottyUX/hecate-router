"""Cross-validate the binary m1-resolves router."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from hecate.data import GenerationRecord, read_jsonl
from hecate.execution.labels import RoutingLabel
from hecate.router.backends import EncoderBackend, ScriptedBackend
from hecate.router.dataset import (
    RouterExample,
    WhitespaceTokenizer,
    build_examples,
)
from hecate.router.metrics import route_metrics
from hecate.router.splits import assign_folds
from hecate.utils.manifest import git_commit_sha, write_run_manifest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class TrainConfig:
    config_path: Path
    labels_path: Path
    generations_path: Path
    output_dir: Path
    run_id: str
    backbone: str
    max_tokens: int
    n_folds: int
    seeds: tuple[int, ...]
    epochs: int
    batch_size: int
    learning_rate: float
    m1_slug: str
    m2_slug: str
    cli_overrides: dict[str, Any]


@dataclass(frozen=True)
class TrainResult:
    run_id: str
    manifest_path: Path
    metrics_path: Path
    examples_path: Path
    mean_route_auc: float
    go_nogo: str
    split_strategy: str
    truncation_rate: float


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return data


def load_train_config(
    *,
    config_path: Path | str | None = None,
    labels_path: Path | str,
    generations_path: Path | str,
    output_dir: Path | str | None = None,
    run_id: str | None = None,
) -> TrainConfig:
    resolved = (
        Path(config_path)
        if config_path is not None
        else _repo_root() / "configs" / "router.yaml"
    )
    if not resolved.is_absolute():
        resolved = _repo_root() / resolved
    data = _load_yaml(resolved)
    rid = run_id or uuid.uuid4().hex[:12]
    out = (
        Path(output_dir)
        if output_dir is not None
        else _repo_root() / "data" / "outputs" / "runs" / rid
    )
    seeds_raw = data.get("seeds") or [0, 1, 2]
    return TrainConfig(
        config_path=resolved,
        labels_path=Path(labels_path),
        generations_path=Path(generations_path),
        output_dir=out,
        run_id=rid,
        backbone=str(data.get("backbone") or "answerdotai/ModernBERT-base"),
        max_tokens=int(data.get("max_tokens") or 2048),
        n_folds=int(data.get("n_folds") or 5),
        seeds=tuple(int(s) for s in seeds_raw),
        epochs=int(data.get("epochs") or 2),
        batch_size=int(data.get("batch_size") or 8),
        learning_rate=float(data.get("learning_rate") or 2e-5),
        m1_slug=str(data.get("m1_slug") or "qwen/qwen-2.5-7b-instruct"),
        m2_slug=str(data.get("m2_slug") or "qwen/qwen-2.5-72b-instruct"),
        cli_overrides={
            "labels_path": str(labels_path),
            "generations_path": str(generations_path),
            "output_dir": str(out),
            "run_id": rid,
        },
    )


def load_labels(path: Path | str) -> list[RoutingLabel]:
    rows: list[RoutingLabel] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            rows.append(
                RoutingLabel(
                    instance_id=str(payload["instance_id"]),
                    repo=str(payload.get("repo") or ""),
                    m1_slug=str(payload["m1_slug"]),
                    m2_slug=str(payload["m2_slug"]),
                    m1_resolves=bool(payload["m1_resolves"]),
                    m2_resolves=bool(payload["m2_resolves"]),
                    complementarity=str(payload.get("complementarity") or ""),
                )
            )
    return rows


def run_train(
    config: TrainConfig,
    *,
    backend: EncoderBackend | None = None,
    tokenizer: Any | None = None,
) -> TrainResult:
    labels = load_labels(config.labels_path)
    generations: list[GenerationRecord] = read_jsonl(config.generations_path)
    tok = tokenizer if tokenizer is not None else WhitespaceTokenizer()
    examples, counts = build_examples(
        labels,
        generations,
        tokenizer=tok,
        max_tokens=config.max_tokens,
        m1_slug=config.m1_slug,
    )
    if not examples:
        raise ValueError("No router examples after joining labels and generations")

    active = backend if backend is not None else ScriptedBackend()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    examples_path = config.output_dir / "examples.jsonl"
    with examples_path.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example.to_dict(), ensure_ascii=False))
            handle.write("\n")

    by_id = {ex.instance_id: ex for ex in examples}
    fold_reports: list[dict[str, Any]] = []
    strategies: list[str] = []
    for seed in config.seeds:
        assignment = assign_folds(
            examples, n_folds=config.n_folds, seed=seed
        )
        strategies.append(assignment.strategy)
        for fold in range(config.n_folds):
            hold_ids = [
                iid for iid, f in assignment.fold_of.items() if f == fold
            ]
            train_ids = [
                iid for iid, f in assignment.fold_of.items() if f != fold
            ]
            if not hold_ids or not train_ids:
                continue
            train_ex = [by_id[i] for i in train_ids]
            hold_ex = [by_id[i] for i in hold_ids]
            active.fit(
                [ex.text for ex in train_ex],
                [ex.m1_resolves for ex in train_ex],
                seed=seed,
                instance_ids=[ex.instance_id for ex in train_ex],
            )
            scores = active.predict_proba(
                [ex.text for ex in hold_ex],
                instance_ids=[ex.instance_id for ex in hold_ex],
            )
            metrics = route_metrics(hold_ex, scores)
            fold_reports.append(
                {
                    "seed": seed,
                    "fold": fold,
                    "n_train": len(train_ex),
                    "n_hold": len(hold_ex),
                    **metrics,
                }
            )

    mean_auc = (
        sum(row["route_auc"] for row in fold_reports) / len(fold_reports)
        if fold_reports
        else 0.0
    )
    go_nogo = "go" if mean_auc > 0 else "floor"
    split_strategy = strategies[0] if len(set(strategies)) == 1 else ",".join(strategies)
    truncation_rate = (
        counts["truncated"] / counts["n_examples"] if counts["n_examples"] else 0.0
    )
    metrics_payload = {
        "mean_route_auc": mean_auc,
        "go_nogo": go_nogo,
        "split_strategy": split_strategy,
        "truncation_rate": truncation_rate,
        "counts": counts,
        "folds": fold_reports,
        "always_m2_mean": (
            sum(row["always_m2"] for row in fold_reports) / len(fold_reports)
            if fold_reports
            else 0.0
        ),
        "oracle_mean": (
            sum(row["oracle"] for row in fold_reports) / len(fold_reports)
            if fold_reports
            else 0.0
        ),
    }
    metrics_path = config.output_dir / "metrics.json"
    metrics_path.write_text(
        json.dumps(metrics_payload, indent=2, sort_keys=True) + "\n",
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
            "n_folds": config.n_folds,
            "seeds": list(config.seeds),
            "split_strategy": split_strategy,
            "truncation_rate": truncation_rate,
            "mean_route_auc": mean_auc,
            "go_nogo": go_nogo,
            "n_examples": counts["n_examples"],
        },
    )
    return TrainResult(
        run_id=config.run_id,
        manifest_path=manifest,
        metrics_path=metrics_path,
        examples_path=examples_path,
        mean_route_auc=mean_auc,
        go_nogo=go_nogo,
        split_strategy=split_strategy,
        truncation_rate=truncation_rate,
    )


# Re-export for tests that only need the type
RouterExample = RouterExample
