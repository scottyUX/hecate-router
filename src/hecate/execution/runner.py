"""Stage-2 execution orchestrator.

Reads Stage-1 generation JSONL, evaluates executable patches via an injectable
harness, and writes a new run directory. Stage-1 artifacts are never mutated.
"""

from __future__ import annotations

import importlib.metadata
import uuid
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from hecate.data import GenerationRecord, append_jsonl, read_jsonl
from hecate.execution.harness import (
    Harness,
    HarnessRequest,
    ScriptedHarness,
    SwebenchHarness,
    sanitize_model_slug,
)
from hecate.execution.merge import apply_report, load_error_ids, load_instance_report
from hecate.execution.predictions import has_executable_patch, write_predictions
from hecate.utils.manifest import git_commit_sha, write_run_manifest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_execution_config_path() -> Path:
    return _repo_root() / "configs" / "execution.yaml"


def _load_yaml(config_path: Path) -> dict[str, Any]:
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {config_path}")
    return data


def _resolve_path(path: Path | str, *, base: Path) -> Path:
    target = Path(path)
    if target.is_absolute():
        return target
    return base / target


def _namespace(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if text.lower() in {"", "none", "null"}:
        return None
    return text


def _model_entries(option_a: dict[str, Any]) -> list[dict[str, Any]]:
    models = option_a.get("models") or []
    return [m for m in models if isinstance(m, dict) and m.get("slug")]


def _ordered_slugs(option_a: dict[str, Any]) -> tuple[str, ...]:
    small: list[str] = []
    large: list[str] = []
    other: list[str] = []
    for model in _model_entries(option_a):
        slug = str(model["slug"])
        tier = str(model.get("tier", ""))
        if tier == "small":
            small.append(slug)
        elif tier == "large":
            large.append(slug)
        else:
            other.append(slug)
    ordered = tuple(small + large + other)
    if not ordered:
        raise ValueError("No model slugs found in Option A config")
    return ordered


def _slug_for_tier(option_a: dict[str, Any], tier: str) -> str:
    for model in _model_entries(option_a):
        if str(model.get("tier", "")) == tier and model.get("slug"):
            return str(model["slug"])
    raise ValueError(f"No {tier}-tier model slug found in Option A config")


def _swebench_version() -> str | None:
    try:
        return importlib.metadata.version("swebench")
    except importlib.metadata.PackageNotFoundError:
        return None


@dataclass(frozen=True)
class ExecutionConfig:
    config_path: Path
    option_a_path: Path
    input_path: Path
    output_dir: Path
    run_id: str
    model_slugs: tuple[str, ...]
    instance_ids: tuple[str, ...] | None
    task_limit: int | None
    dry_run: bool
    dataset_name: str
    split: str
    max_workers: int
    timeout: int
    namespace: str | None
    cache_level: str
    force_rebuild: bool
    modal: bool
    m1_slug: str
    m2_slug: str
    positive_rate_threshold: float
    cli_overrides: dict[str, Any]


@dataclass(frozen=True)
class ExecutionResult:
    run_id: str
    manifest_path: Path
    records_path: Path
    pairs_attempted: int
    pairs_skipped_resume: int
    pairs_skipped_no_patch: int
    pairs_evaluated: int
    pairs_resolved: int
    pairs_pending: int


def load_execution_config(
    *,
    config_path: Path | str | None = None,
    input_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    run_id: str | None = None,
    model: str | None = None,
    models: list[str] | tuple[str, ...] | None = None,
    instance_ids: list[str] | tuple[str, ...] | None = None,
    tasks: int | None = None,
    dry_run: bool = False,
    namespace: str | None = None,
    max_workers: int | None = None,
    timeout: int | None = None,
) -> ExecutionConfig:
    """Build an :class:`ExecutionConfig` from YAML plus CLI-style overrides."""
    resolved_config = (
        Path(config_path)
        if config_path is not None
        else _default_execution_config_path()
    )
    if not resolved_config.is_absolute():
        resolved_config = _resolve_path(resolved_config, base=_repo_root())
    data = _load_yaml(resolved_config)

    option_a_path = _resolve_path(
        data.get("option_a_config") or "configs/option_a.yaml",
        base=_repo_root(),
    )
    option_a = _load_yaml(option_a_path)
    known = set(_ordered_slugs(option_a))

    if models is not None:
        slugs = tuple(models)
    elif model is not None:
        slugs = (model,)
    else:
        slugs = _ordered_slugs(option_a)
    unknown = [slug for slug in slugs if slug not in known]
    if unknown:
        raise ValueError(
            f"Unknown model slug(s): {unknown!r}. Configured slugs: {sorted(known)}"
        )

    if tasks is not None and tasks < 1:
        raise ValueError("tasks must be >= 1")

    rid = run_id or uuid.uuid4().hex[:12]
    out = (
        Path(output_dir)
        if output_dir is not None
        else _repo_root() / "data" / "outputs" / "runs" / rid
    )
    generations = (
        Path(input_path)
        if input_path is not None
        else _resolve_path(
            data.get("input_generations")
            or "data/outputs/runs/sweep-2x300-qwen/generations.jsonl",
            base=_repo_root(),
        )
    )
    if not generations.is_absolute():
        generations = _resolve_path(generations, base=_repo_root())

    ns = _namespace(namespace) if namespace is not None else _namespace(data.get("namespace"))
    overrides: dict[str, Any] = {}
    if input_path is not None:
        overrides["input_path"] = str(input_path)
    if output_dir is not None:
        overrides["output_dir"] = str(output_dir)
    if run_id is not None:
        overrides["run_id"] = run_id
    if model is not None:
        overrides["model"] = model
    if models is not None:
        overrides["models"] = list(models)
    if instance_ids is not None:
        overrides["instance_ids"] = list(instance_ids)
    if tasks is not None:
        overrides["tasks"] = tasks
    if dry_run:
        overrides["dry_run"] = True
    if namespace is not None:
        overrides["namespace"] = namespace
    if max_workers is not None:
        overrides["max_workers"] = max_workers
    if timeout is not None:
        overrides["timeout"] = timeout

    return ExecutionConfig(
        config_path=resolved_config,
        option_a_path=option_a_path,
        input_path=generations,
        output_dir=out,
        run_id=rid,
        model_slugs=slugs,
        instance_ids=tuple(instance_ids) if instance_ids is not None else None,
        task_limit=tasks,
        dry_run=dry_run,
        dataset_name=str(data.get("dataset_name") or "SWE-bench/SWE-bench_Lite"),
        split=str(data.get("split") or "test"),
        max_workers=int(max_workers if max_workers is not None else data.get("max_workers") or 4),
        timeout=int(timeout if timeout is not None else data.get("timeout") or 1800),
        namespace=ns,
        cache_level=str(data.get("cache_level") or "env"),
        force_rebuild=bool(data.get("force_rebuild") or False),
        modal=bool(data.get("modal") or False),
        m1_slug=_slug_for_tier(option_a, "small"),
        m2_slug=_slug_for_tier(option_a, "large"),
        positive_rate_threshold=float(
            data.get("m1_positive_rate_flag_threshold") or 0.15
        ),
        cli_overrides=overrides,
    )


def _select_instance_ids(
    records: list[GenerationRecord], config: ExecutionConfig
) -> tuple[str, ...]:
    if config.instance_ids is not None:
        selected = tuple(config.instance_ids)
    else:
        seen: list[str] = []
        for record in records:
            if record.instance_id not in seen:
                seen.append(record.instance_id)
        selected = tuple(seen)
    if config.task_limit is not None:
        selected = selected[: config.task_limit]
    if not selected:
        raise ValueError("No instance ids selected for execution")
    return selected


def _assert_matrix_complete(
    records: list[GenerationRecord],
    instance_ids: tuple[str, ...],
    model_slugs: tuple[str, ...],
) -> None:
    have = {(record.instance_id, record.model_slug) for record in records}
    missing = [
        f"{instance_id} × {slug}"
        for instance_id in instance_ids
        for slug in model_slugs
        if (instance_id, slug) not in have
    ]
    if missing:
        preview = ", ".join(missing[:8])
        extra = f" (+{len(missing) - 8} more)" if len(missing) > 8 else ""
        raise ValueError(
            f"Incomplete generation matrix; missing {len(missing)} pair(s): "
            f"{preview}{extra}"
        )


def _finished_pairs(records_path: Path) -> set[tuple[str, str]]:
    if not records_path.is_file():
        return set()
    return {
        (record.instance_id, record.model_slug)
        for record in read_jsonl(records_path)
        if record.patch_applied is not None
    }


def _no_patch_record(record: GenerationRecord) -> GenerationRecord:
    return replace(
        record,
        patch_applied=False,
        resolved=False,
        fail_to_pass=[],
        pass_to_pass=[],
    )


def _stage1_run_ids(records: list[GenerationRecord]) -> list[str]:
    seen: list[str] = []
    for record in records:
        if record.run_id and record.run_id not in seen:
            seen.append(record.run_id)
    return seen


def _write_execution_manifest(
    config: ExecutionConfig,
    *,
    records_path: Path,
    counts: dict[str, int],
    input_records: list[GenerationRecord],
) -> Path:
    snapshot = _load_yaml(config.config_path)
    payload: dict[str, Any] = {
        "run_id": config.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_sha(),
        "config_path": str(config.config_path),
        "config_snapshot": snapshot,
        "cli_overrides": config.cli_overrides,
        "dry_run": config.dry_run,
        "input_path": str(config.input_path),
        "records_path": str(records_path),
        "model_slugs": list(config.model_slugs),
        "dataset_name": config.dataset_name,
        "split": config.split,
        "namespace": config.namespace,
        "swebench_version": _swebench_version(),
        "stage1_run_ids": _stage1_run_ids(input_records),
        **counts,
    }
    return write_run_manifest(config.output_dir / "manifest.json", payload)


def run_execution(
    config: ExecutionConfig,
    *,
    harness: Harness | None = None,
) -> ExecutionResult:
    """Evaluate requested pairs and write ``executions.jsonl`` + manifest."""
    records = read_jsonl(config.input_path)
    instance_ids = _select_instance_ids(records, config)
    _assert_matrix_complete(records, instance_ids, config.model_slugs)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    records_path = config.output_dir / "executions.jsonl"
    matrix_size = len(instance_ids) * len(config.model_slugs)

    if config.dry_run:
        manifest = _write_execution_manifest(
            config,
            records_path=records_path,
            counts={
                "pairs_attempted": matrix_size,
                "pairs_skipped_resume": 0,
                "pairs_skipped_no_patch": 0,
                "pairs_evaluated": 0,
                "pairs_resolved": 0,
                "pairs_pending": 0,
            },
            input_records=records,
        )
        return ExecutionResult(
            run_id=config.run_id,
            manifest_path=manifest,
            records_path=records_path,
            pairs_attempted=matrix_size,
            pairs_skipped_resume=0,
            pairs_skipped_no_patch=0,
            pairs_evaluated=0,
            pairs_resolved=0,
            pairs_pending=0,
        )

    active_harness = harness if harness is not None else SwebenchHarness()
    done = _finished_pairs(records_path)
    by_key = {(record.instance_id, record.model_slug): record for record in records}

    skipped_resume = 0
    skipped_no_patch = 0
    evaluated = 0
    resolved = 0
    pending = 0
    executable_by_model: dict[str, list[GenerationRecord]] = defaultdict(list)

    for instance_id in instance_ids:
        for slug in config.model_slugs:
            if (instance_id, slug) in done:
                skipped_resume += 1
                continue
            record = by_key[(instance_id, slug)]
            if not has_executable_patch(record):
                append_jsonl(records_path, _no_patch_record(record))
                skipped_no_patch += 1
            else:
                executable_by_model[slug].append(record)

    for slug, group in executable_by_model.items():
        if not group:
            continue
        pred_path = (
            config.output_dir / f"predictions-{sanitize_model_slug(slug)}.jsonl"
        )
        write_predictions(group, pred_path)
        request = HarnessRequest(
            predictions_path=pred_path,
            run_id=config.run_id,
            instance_ids=tuple(record.instance_id for record in group),
            dataset_name=config.dataset_name,
            split=config.split,
            max_workers=config.max_workers,
            timeout=config.timeout,
            namespace=config.namespace,
            report_dir=config.output_dir,
            cache_level=config.cache_level,
            force_rebuild=config.force_rebuild,
            modal=config.modal,
        )
        result = active_harness.run(request)
        error_ids = load_error_ids(
            config.output_dir, slug, config.run_id
        )
        for record in group:
            report = load_instance_report(
                result.log_dir, record.model_slug, record.instance_id
            )
            if report is None:
                if record.instance_id in error_ids:
                    filled = _no_patch_record(record)
                    append_jsonl(records_path, filled)
                    evaluated += 1
                    continue
                pending += 1
                continue
            filled = apply_report(record, report)
            append_jsonl(records_path, filled)
            evaluated += 1
            if filled.resolved:
                resolved += 1

    manifest = _write_execution_manifest(
        config,
        records_path=records_path,
        counts={
            "pairs_attempted": matrix_size,
            "pairs_skipped_resume": skipped_resume,
            "pairs_skipped_no_patch": skipped_no_patch,
            "pairs_evaluated": evaluated,
            "pairs_resolved": resolved,
            "pairs_pending": pending,
        },
        input_records=records,
    )
    return ExecutionResult(
        run_id=config.run_id,
        manifest_path=manifest,
        records_path=records_path,
        pairs_attempted=matrix_size,
        pairs_skipped_resume=skipped_resume,
        pairs_skipped_no_patch=skipped_no_patch,
        pairs_evaluated=evaluated,
        pairs_resolved=resolved,
        pairs_pending=pending,
    )


# Re-export test double so callers can `from hecate.execution.runner import ScriptedHarness`
__all__ = [
    "ExecutionConfig",
    "ExecutionResult",
    "ScriptedHarness",
    "load_execution_config",
    "run_execution",
]
