"""Cross-validate the K-turn LoRA trajectory router (v3)."""

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
    JoinError,
    complementarity,
    read_joined_csv,
    read_joined_text_csv,
)
from hecate.router.backends import ScriptedBackend
from hecate.router.dataset import WhitespaceTokenizer
from hecate.router.metrics import text_route_metrics
from hecate.router.splits import (
    FoldAssignment,
    assign_grouped_repo_folds,
    assign_leave_repo_out,
    repo_histogram,
)
from hecate.router.traj import (
    K_EVAL,
    K_MAX,
    TrajError,
    TrajExample,
    build_traj_examples,
    eval_examples,
    parse_traj_dir,
    second_holdout_repo,
    truncation_report,
)
from hecate.utils.manifest import git_commit_sha, write_run_manifest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


_SPLIT_GROUPED = "grouped"
_SPLIT_LEAVE_REPO = "leave-repo"
_DJANGO_REPO = "django/django"
_DJANGO_HOLD_N = 231
_DJANGO_REST_N = 269
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
ARMS = ("k0", "k3")
PAPER_DEVIATION = (
    "No 3-way LLM paraphrases of q (SWE-Router §A.2); skipped for cost."
)


@dataclass(frozen=True)
class TrajTrainConfig:
    config_path: Path
    csv_path: Path
    traj_dir: Path
    output_dir: Path
    run_id: str
    backbone: str
    max_tokens: int
    n_folds: int
    seeds: tuple[int, ...]
    epochs: int
    batch_size: int
    grad_accum: int
    learning_rate: float
    lora_r: int
    lora_alpha: int
    lora_dropout: float
    qlora: bool
    arm: str
    k_eval: int
    k_max: int
    split_strategy: str
    hold_repo: str
    provenance: str
    hold_only: bool
    cli_overrides: dict[str, Any]


@dataclass(frozen=True)
class TrajTrainResult:
    run_id: str
    output_dir: Path
    results_path: Path
    manifest_path: Path
    readme_path: Path
    mean_route_auc: float
    split_strategy: str
    truncation_rate: float
    arm: str


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return data


def load_traj_train_config(
    *,
    config_path: Path | str | None = None,
    csv_path: Path | str | None = None,
    traj_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    run_id: str | None = None,
    split: str = _SPLIT_GROUPED,
    hold_repo: str = _DJANGO_REPO,
    arm: str = "k3",
    provenance: str = "unknown",
    seeds: tuple[int, ...] | None = None,
    hold_only: bool = False,
) -> TrajTrainConfig:
    root = _repo_root()
    resolved = (
        Path(config_path) if config_path is not None else root / "configs" / "router_traj.yaml"
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
    default_traj = root / "data" / "raw" / "trajs"
    traj = Path(traj_dir) if traj_dir is not None else Path(
        data.get("traj_dir") or default_traj
    )
    if not traj.is_absolute():
        traj = root / traj
    seeds_raw = list(seeds) if seeds is not None else (data.get("seeds") or [0, 1, 2])
    split_strategy = (split or _SPLIT_GROUPED).strip()
    if split_strategy not in {_SPLIT_GROUPED, _SPLIT_LEAVE_REPO}:
        raise ValueError(
            f"unknown split {split_strategy!r}; expected {_SPLIT_GROUPED} or {_SPLIT_LEAVE_REPO}"
        )
    held = (hold_repo or _DJANGO_REPO).strip()
    kind = (arm or "k3").strip().lower()
    if kind not in ARMS:
        raise ValueError(f"unknown arm {kind!r}; expected {ARMS}")
    return TrajTrainConfig(
        config_path=resolved,
        csv_path=csv,
        traj_dir=traj,
        output_dir=out,
        run_id=rid,
        backbone=str(data.get("backbone") or "Qwen/Qwen2.5-Coder-7B-Instruct"),
        max_tokens=int(data.get("max_tokens") or 8192),
        n_folds=int(data.get("n_folds") or 5),
        seeds=tuple(int(s) for s in seeds_raw),
        epochs=int(data.get("epochs") or 5),
        batch_size=int(data.get("batch_size") or 1),
        grad_accum=int(data.get("grad_accum") or 16),
        learning_rate=float(data.get("learning_rate") or 5e-5),
        lora_r=int(data.get("lora_r") or 32),
        lora_alpha=int(data.get("lora_alpha") or 64),
        lora_dropout=float(data.get("lora_dropout") or 0.05),
        qlora=bool(data.get("qlora", True)),
        arm=kind,
        k_eval=int(data.get("k_eval") or K_EVAL),
        k_max=int(data.get("k_max") or K_MAX),
        split_strategy=split_strategy,
        hold_repo=held,
        provenance=str(provenance or data.get("provenance") or "unknown"),
        hold_only=bool(hold_only),
        cli_overrides={
            "csv_path": str(csv),
            "traj_dir": str(traj),
            "output_dir": str(out),
            "run_id": rid,
            "split": split_strategy,
            "hold_repo": held,
            "arm": kind,
            "provenance": str(provenance or "unknown"),
            "seeds": [int(s) for s in seeds_raw],
            "hold_only": bool(hold_only),
        },
    )


def _fold_traj(
    examples: list[TrajExample], assignment: FoldAssignment, fold: int
) -> tuple[list[TrajExample], list[TrajExample]]:
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


def _leave_direction(hold_repos: list[str], hold_repo: str) -> str:
    if set(hold_repos) == {hold_repo}:
        return "hold_django" if hold_repo == _DJANGO_REPO else "hold_repo"
    return "hold_rest"


def _summarize_directions(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_dir: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_dir.setdefault(str(row["direction"]), []).append(row)
    out: dict[str, dict[str, Any]] = {}
    for direction, group in by_dir.items():
        summary = _summarize(group)
        summary["n_hold"] = group[0]["n_hold"] if group else 0
        summary["n_train"] = group[0]["n_train"] if group else 0
        summary["always_small_hold"] = group[0].get("always_small") if group else None
        out[direction] = summary
    return out


def _fmt_mean_std(stat: dict[str, Any] | None) -> str:
    if not stat or stat.get("mean") is None:
        return "n/a"
    std = stat.get("std")
    std_s = "n/a" if std is None else f"{float(std):.3f}"
    return f"{float(stat['mean']):.3f} ± {std_s}"


def _eval_k(config: TrajTrainConfig) -> int:
    return 0 if config.arm == "k0" else config.k_eval


def _score_hold(
    train: list[TrajExample],
    hold: list[TrajExample],
    *,
    config: TrajTrainConfig,
    seed: int,
    scripted: ScriptedBackend | None,
) -> dict[str, Any]:
    k = _eval_k(config)
    hold_router = eval_examples(hold, k=k)
    if scripted is not None:
        scores = scripted.predict_proba(
            [ex.text for ex in hold_router],
            instance_ids=[ex.instance_id for ex in hold_router],
        )
        return dict(text_route_metrics(hold_router, scores))
    from hecate.router.traj_lora import TrajLoraBackend

    backend = TrajLoraBackend(
        config.backbone,
        max_tokens=config.max_tokens,
        epochs=config.epochs,
        batch_size=config.batch_size,
        grad_accum=config.grad_accum,
        learning_rate=config.learning_rate,
        lora_r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        qlora=config.qlora,
        log_dir=config.output_dir,
    )
    backend.fit(train, arm=config.arm, seed=seed, k_max=config.k_max)
    scores = backend.predict_proba([ex.text for ex in hold_router])
    return dict(text_route_metrics(hold_router, scores))


def _cv_rows(
    examples: list[TrajExample],
    assignment: FoldAssignment,
    *,
    config: TrajTrainConfig,
    seed: int,
    scripted: ScriptedBackend | None,
    hold_repo: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    k = _eval_k(config)
    for fold in range(assignment.n_folds):
        if config.hold_only and fold != 0:
            continue
        train, hold = _fold_traj(examples, assignment, fold)
        if not train or not hold:
            continue
        hold_router = eval_examples(hold, k=k)
        hold_repos = sorted({ex.repo for ex in hold_router})
        train_repos = sorted({ex.repo for ex in train})
        leak = sorted(set(hold_repos) & set(train_repos))
        metrics = _score_hold(
            train, hold, config=config, seed=seed, scripted=scripted
        )
        rows.append(
            {
                "seed": seed,
                "fold": fold,
                "arm": config.arm,
                "k_eval": k,
                "split": assignment.strategy,
                "direction": (
                    _leave_direction(hold_repos, hold_repo) if hold_repo else None
                ),
                "n_train": len(train),
                "n_hold": len(hold),
                "hold_repos": hold_repos,
                "repo_leak": leak,
                **metrics,
            }
        )
    return rows


def _write_readme(path: Path, payload: dict[str, Any]) -> Path:
    trunc = float(payload.get("truncation_rate") or 0.0)
    arm = payload.get("arm")
    split_primary = payload.get("split_primary")
    lines = [
        f"# Trajectory router v3 — arm `{arm}`",
        "",
        "Dataset: SWE-bench **Verified** (500), mini-SWE-agent v1.0.0, "
        "Qwen3-Coder-480B-A35B-Instruct vs Claude 4 Opus.",
        "",
        "K=0 is a separately trained LoRA on issue text (never sees trajectory "
        "tokens). K=3 packs K∈{0..4} only inside that arm. Route-AUC is primary; "
        "AUROC is diagnostic.",
        "",
        f"Paper deviation: {PAPER_DEVIATION}",
        "",
        f"Trace provenance: `{payload.get('trace_provenance')}`.",
        "",
        f"K=3 truncation rate at {payload.get('max_tokens')} tokens: {trunc:.3f}.",
        "",
    ]
    if split_primary == "leave_repo":
        directions = payload.get("directions") or {}
        block = directions.get("lora") or directions.get("scripted") or {}
        lines.append("## Directions")
        lines.append("")
        for key in ("hold_django", "hold_repo", "hold_rest"):
            item = block.get(key)
            if not item:
                continue
            lines.append(
                f"- `{key}` (n_hold={item.get('n_hold')}): Route-AUC "
                f"{_fmt_mean_std(item.get('route_auc'))}; AUROC "
                f"{_fmt_mean_std(item.get('auroc'))}"
            )
        lines.append("")
    else:
        primary = payload.get("primary") or {}
        block = primary.get("lora") or primary.get("scripted") or {}
        lines.extend(
            [
                "## Grouped 5-fold (do not headline)",
                "",
                f"- Route-AUC {_fmt_mean_std(block.get('route_auc'))}",
                f"- AUROC {_fmt_mean_std(block.get('auroc'))}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _load_labels(csv_path: Path) -> list[JoinedLabel]:
    try:
        rows = read_joined_text_csv(csv_path)
        return [
            JoinedLabel(
                instance_id=row.instance_id,
                repo=row.repo,
                small_model_resolved=row.small_model_resolved,
                large_model_resolved=row.large_model_resolved,
            )
            for row in rows
        ]
    except JoinError:
        return read_joined_csv(csv_path)


def load_traj_examples(
    config: TrajTrainConfig,
    *,
    examples: list[TrajExample] | None = None,
    tokenizer: Any | None = None,
) -> tuple[list[TrajExample], dict[str, Any], dict[str, int]]:
    if examples is not None:
        counts = {
            "n_examples": len(examples),
            "truncated_k3": sum(1 for ex in examples if ex.truncated_at_k(config.k_eval)),
            "early_submit": sum(1 for ex in examples if ex.submitted_early),
        }
        report = {
            "n_labels": len(examples),
            "n_trajs": len(examples),
            "n_matched": len(examples),
            "provenance": config.provenance,
            "n_with_traj_resolved": sum(
                1 for ex in examples if ex.traj_resolved is not None
            ),
        }
        return examples, report, counts
    if not config.traj_dir.exists():
        raise TrajError(
            f"traj dir missing: {config.traj_dir}. Run scripts/fetch_qwen_trajs.py first."
        )
    parsed = parse_traj_dir(config.traj_dir)
    labels = _load_labels(config.csv_path)
    tok = tokenizer or WhitespaceTokenizer()
    examples, match, counts = build_traj_examples(
        parsed,
        labels,
        k_max=config.k_max,
        tokenizer=tok,
        max_tokens=config.max_tokens,
        provenance=config.provenance,
    )
    return examples, match.__dict__, counts


def run_traj_train(
    config: TrajTrainConfig,
    *,
    backend: str = "scripted",
    scripted_scores: dict[str, float] | None = None,
    examples: list[TrajExample] | None = None,
) -> TrajTrainResult:
    examples, match_payload, counts = load_traj_examples(config, examples=examples)
    if not examples:
        raise ValueError("No trajectory examples after label match")
    router_for_hist = eval_examples(examples, k=_eval_k(config))
    histogram = repo_histogram(router_for_hist)
    second_repo = second_holdout_repo(router_for_hist, config.hold_repo)
    trunc = truncation_report(
        examples,
        k=config.k_eval,
        max_tokens=config.max_tokens,
        tokenizer=WhitespaceTokenizer(),
    )
    truncation_rate = float(trunc["truncation_rate"])
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
    scripted: ScriptedBackend | None = None
    head_name = "lora"
    if backend == "scripted":
        scripted = ScriptedBackend(scripted_scores or {})
        head_name = "scripted"
    elif backend != "lora":
        raise ValueError(f"unknown backend {backend!r}; expected scripted or lora")

    config.output_dir.mkdir(parents=True, exist_ok=True)

    leave_repo = config.split_strategy == _SPLIT_LEAVE_REPO
    if leave_repo and config.hold_repo == _DJANGO_REPO and len(examples) == 500:
        n_hold = sum(1 for ex in examples if ex.repo == _DJANGO_REPO)
        n_rest = len(examples) - n_hold
        if n_hold != _DJANGO_HOLD_N or n_rest != _DJANGO_REST_N:
            raise ValueError(
                f"leave-django-out expected n={_DJANGO_HOLD_N}/{_DJANGO_REST_N}, "
                f"got {n_hold}/{n_rest}"
            )

    primary_rows: list[dict[str, Any]] = []
    for seed in config.seeds:
        if leave_repo:
            assignment = assign_leave_repo_out(
                router_for_hist, config.hold_repo, seed=seed
            )
            primary_rows.extend(
                _cv_rows(
                    examples,
                    assignment,
                    config=config,
                    seed=seed,
                    scripted=scripted,
                    hold_repo=config.hold_repo,
                )
            )
            continue
        grouped = assign_grouped_repo_folds(
            router_for_hist, n_folds=config.n_folds, seed=seed
        )
        primary_rows.extend(
            _cv_rows(
                examples,
                grouped,
                config=config,
                seed=seed,
                scripted=scripted,
            )
        )

    config.output_dir.mkdir(parents=True, exist_ok=True)
    if leave_repo:
        directions = {head_name: _summarize_directions(primary_rows)}
        primary_summary: dict[str, Any] = {}
        headline_dirs = directions.get(head_name) or {}
        claim = headline_dirs.get("hold_django") or headline_dirs.get("hold_repo") or {}
        mean_auc = (claim.get("route_auc") or {}).get("mean")
        split_primary = "leave_repo"
        n_folds_out = 1 if config.hold_only else 2
        arm_label = (
            f"trajectory v3 {config.arm} leave-django-out"
            if config.hold_repo == _DJANGO_REPO
            else f"trajectory v3 {config.arm} leave-repo"
        )
    else:
        directions = {}
        primary_summary = {head_name: _summarize(primary_rows)}
        mean_auc = (primary_summary[head_name].get("route_auc") or {}).get("mean")
        split_primary = "grouped_repo"
        n_folds_out = config.n_folds
        arm_label = f"trajectory v3 {config.arm}"
    if mean_auc is None:
        mean_auc = 0.0

    gpu = "cpu"
    try:
        import torch

        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
    except ImportError:
        gpu = "none"

    results = {
        "dataset": "qwen3coder_vs_claude4opus_traj_v3",
        "split": "verified",
        "scaffold": "mini-SWE-agent v1.0.0",
        "small_model": "Qwen3-Coder-480B-A35B-Instruct",
        "large_model": "Claude 4 Opus",
        "arm": arm_label,
        "arm_key": config.arm,
        "k_eval": _eval_k(config),
        "k_max": config.k_max,
        "encoder": config.backbone,
        "n_examples": counts["n_examples"],
        "truncation_rate": truncation_rate,
        "truncation": trunc,
        "max_tokens": config.max_tokens,
        "headroom_pp": HEADROOM_PP,
        "complementarity": comp,
        "repo_histogram": histogram,
        "second_holdout_repo": second_repo,
        "split_primary": split_primary,
        "hold_repo": config.hold_repo if leave_repo else None,
        "seeds": list(config.seeds),
        "n_folds": n_folds_out,
        "primary": primary_summary,
        "primary_folds": {head_name: primary_rows},
        "directions": directions,
        "trace_provenance": config.provenance,
        "label_match": match_payload,
        "paper_deviation": PAPER_DEVIATION,
        "gpu": gpu,
    }
    results_path = config.output_dir / "results.json"
    results_path.write_text(
        json.dumps(results, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (config.output_dir / "truncation.json").write_text(
        json.dumps(trunc, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    snapshot = _load_yaml(config.config_path) if config.config_path.is_file() else {}
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
            "n_folds": n_folds_out,
            "seeds": list(config.seeds),
            "split_strategy": split_primary,
            "hold_repo": config.hold_repo if leave_repo else None,
            "truncation_rate": truncation_rate,
            "k3_truncation_rate": truncation_rate,
            "mean_route_auc": mean_auc,
            "headroom_pp": HEADROOM_PP,
            "n_examples": counts["n_examples"],
            "arm": config.arm,
            "k_eval": _eval_k(config),
            "k_max": config.k_max,
            "trace_provenance": config.provenance,
            "label_match": match_payload,
            "gpu": gpu,
            "paper_deviation": PAPER_DEVIATION,
        },
    )
    readme_path = _write_readme(config.output_dir / "README.md", results)
    return TrajTrainResult(
        run_id=config.run_id,
        output_dir=config.output_dir,
        results_path=results_path,
        manifest_path=manifest,
        readme_path=readme_path,
        mean_route_auc=float(mean_auc),
        split_strategy=split_primary,
        truncation_rate=truncation_rate,
        arm=config.arm,
    )
