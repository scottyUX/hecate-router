"""Stage-1 generation orchestrator (S11).

Ties scaffold → cache → cost → OpenRouter → patch extraction → JSONL records
and a run manifest. Libraries remain unaware of each other; this module is the
only integrator.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol

import yaml

from hecate.caching import (
    CachedGeneration,
    GenerationCache,
    cache_key,
    decoding_fingerprint,
    default_cache_dir,
)
from hecate.cost import BudgetExceededError, CostTracker, estimate_cost
from hecate.data import (
    GenerationRecord,
    SwebenchTask,
    append_jsonl,
    load_swebench_lite,
)
from hecate.generation.client import CompletionResult, OpenRouterClient
from hecate.generation.patch import extract_patch
from hecate.scaffold import (
    PROMPT_VERSION,
    build_context,
    prompt_hash,
    render_prompt,
    write_prompt,
)
from hecate.utils.manifest import git_commit_sha, write_run_manifest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_config_path() -> Path:
    return _repo_root() / "configs" / "option_a.yaml"


class Completer(Protocol):
    async def complete(
        self,
        *,
        model_slug: str,
        prompt: str,
        decoding: dict[str, Any] | None = None,
    ) -> CompletionResult: ...


CompleteFn = Callable[..., Awaitable[CompletionResult]]


@dataclass(frozen=True)
class RunConfig:
    config_path: Path
    task_limit: int
    model_slugs: tuple[str, ...]
    dry_run: bool
    output_dir: Path
    cache_dir: Path | None = None
    ledger_path: Path | None = None
    run_id: str | None = None
    repo_cache_dir: Path | None = None


@dataclass(frozen=True)
class RunResult:
    run_id: str
    manifest_path: Path
    records_path: Path
    pairs_attempted: int
    pairs_cache_hit: int
    pairs_generated: int
    pairs_refused_budget: int
    total_cost_usd: float


def _load_yaml(config_path: Path) -> dict[str, Any]:
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {config_path}")
    return data


def _model_tiers(config: dict[str, Any]) -> dict[str, str]:
    tiers: dict[str, str] = {}
    for model in config.get("models", []) or []:
        if isinstance(model, dict) and model.get("slug") and model.get("tier"):
            tiers[str(model["slug"])] = str(model["tier"])
    return tiers


def _default_small_slug(config: dict[str, Any]) -> str:
    for model in config.get("models", []) or []:
        if isinstance(model, dict) and model.get("tier") == "small" and model.get("slug"):
            return str(model["slug"])
    raise ValueError("No small-tier model slug found in config")


def load_run_config(
    *,
    config_path: Path | str | None = None,
    tasks: int = 1,
    model: str | None = None,
    dry_run: bool = False,
    output_dir: Path | str | None = None,
    cache_dir: Path | str | None = None,
    ledger_path: Path | str | None = None,
    run_id: str | None = None,
    repo_cache_dir: Path | str | None = None,
) -> RunConfig:
    """Build a :class:`RunConfig` from CLI-style arguments."""
    if tasks < 1:
        raise ValueError("tasks must be >= 1")

    resolved_config = (
        Path(config_path) if config_path is not None else _default_config_path()
    )
    data = _load_yaml(resolved_config)
    known = set(_model_tiers(data))
    slug = model if model is not None else _default_small_slug(data)
    if slug not in known:
        raise ValueError(
            f"Unknown model slug: {slug!r}. Configured slugs: {sorted(known)}"
        )

    rid = run_id or uuid.uuid4().hex[:12]
    out = (
        Path(output_dir)
        if output_dir is not None
        else _repo_root() / "data" / "outputs" / "runs" / rid
    )
    return RunConfig(
        config_path=resolved_config,
        task_limit=tasks,
        model_slugs=(slug,),
        dry_run=dry_run,
        output_dir=out,
        cache_dir=Path(cache_dir) if cache_dir is not None else None,
        ledger_path=Path(ledger_path) if ledger_path is not None else None,
        run_id=rid,
        repo_cache_dir=Path(repo_cache_dir) if repo_cache_dir is not None else None,
    )


def _decoding_params(config: dict[str, Any]) -> dict[str, Any]:
    decoding = config.get("decoding", {}) or {}
    return {
        "temperature": float(decoding.get("temperature", 0.0)),
        "max_tokens": int(decoding.get("max_tokens", 4096)),
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _append_record(
    records_path: Path,
    *,
    task: SwebenchTask,
    model_slug: str,
    tier: str,
    prompt: str,
    p_hash: str,
    prompt_ref: str,
    context_paths: list[str],
    raw_response: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cost_usd: float | None,
    decoding: dict[str, Any],
    run_id: str,
) -> None:
    extracted_patch = None
    patch_parse_ok = None
    if raw_response is not None:
        extraction = extract_patch(raw_response)
        extracted_patch = extraction.extracted_patch
        patch_parse_ok = extraction.patch_parse_ok

    append_jsonl(
        records_path,
        GenerationRecord(
            instance_id=task.instance_id,
            repo=task.repo,
            base_commit=task.base_commit,
            model_slug=model_slug,
            tier=tier,  # type: ignore[arg-type]
            prompt=prompt,
            prompt_hash=p_hash,
            prompt_ref=prompt_ref,
            context_files=context_paths,
            raw_response=raw_response,
            extracted_patch=extracted_patch,
            patch_parse_ok=patch_parse_ok,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            decoding_params=dict(decoding),
            timestamp=_utc_now(),
            run_id=run_id,
        ),
    )


async def run_generation(
    config: RunConfig,
    *,
    tasks: list[SwebenchTask] | None = None,
    completer: Completer | CompleteFn | None = None,
) -> RunResult:
    """Execute the (task × model) loop and persist records + manifest."""
    run_id = config.run_id or uuid.uuid4().hex[:12]
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "generations.jsonl"
    manifest_path = output_dir / "manifest.json"

    yaml_data = _load_yaml(config.config_path)
    tiers = _model_tiers(yaml_data)
    decoding = _decoding_params(yaml_data)
    dec_fp = decoding_fingerprint(decoding)

    selected_tasks = tasks if tasks is not None else load_swebench_lite()
    selected_tasks = selected_tasks[: config.task_limit]
    if not selected_tasks:
        raise ValueError("No tasks available to run")

    cache = GenerationCache(config.cache_dir or default_cache_dir())
    tracker = CostTracker(
        ledger_path=config.ledger_path,
        config_path=config.config_path,
    )

    client: OpenRouterClient | None = None
    complete: CompleteFn | None
    if completer is not None:
        if callable(completer) and not hasattr(completer, "complete"):
            complete = completer  # type: ignore[assignment]
        else:
            complete = completer.complete  # type: ignore[union-attr]
    elif config.dry_run:
        complete = None
    else:
        client = OpenRouterClient(config_path=config.config_path)
        complete = client.complete

    pairs_attempted = 0
    pairs_cache_hit = 0
    pairs_generated = 0
    pairs_refused_budget = 0
    halt_paid = False

    try:
        for task in selected_tasks:
            context = build_context(
                task.instance_id,
                method="oracle",
                task=task,
                cache_dir=config.repo_cache_dir,
                config_path=config.config_path,
            )
            prompt = render_prompt(task, context)
            p_hash = prompt_hash(prompt)
            prompt_ref = write_prompt(prompt, output_dir=output_dir / "prompts")
            context_paths = list(context.paths)

            for model_slug in config.model_slugs:
                pairs_attempted += 1
                tier = tiers.get(model_slug)
                if tier not in ("small", "large"):
                    raise ValueError(f"Missing tier for model slug {model_slug!r}")

                key = cache_key(
                    task.instance_id,
                    model_slug,
                    p_hash,
                    PROMPT_VERSION,
                    dec_fp,
                )
                cached = cache.get(key)

                if cached is not None:
                    pairs_cache_hit += 1
                    pairs_generated += 1
                    _append_record(
                        records_path,
                        task=task,
                        model_slug=model_slug,
                        tier=tier,
                        prompt=prompt,
                        p_hash=p_hash,
                        prompt_ref=prompt_ref,
                        context_paths=context_paths,
                        raw_response=cached.raw_response,
                        prompt_tokens=cached.prompt_tokens,
                        completion_tokens=cached.completion_tokens,
                        cost_usd=None,
                        decoding=decoding,
                        run_id=run_id,
                    )
                    continue

                if config.dry_run:
                    _append_record(
                        records_path,
                        task=task,
                        model_slug=model_slug,
                        tier=tier,
                        prompt=prompt,
                        p_hash=p_hash,
                        prompt_ref=prompt_ref,
                        context_paths=context_paths,
                        raw_response=None,
                        prompt_tokens=None,
                        completion_tokens=None,
                        cost_usd=None,
                        decoding=decoding,
                        run_id=run_id,
                    )
                    continue

                if halt_paid:
                    pairs_refused_budget += 1
                    _append_record(
                        records_path,
                        task=task,
                        model_slug=model_slug,
                        tier=tier,
                        prompt=prompt,
                        p_hash=p_hash,
                        prompt_ref=prompt_ref,
                        context_paths=context_paths,
                        raw_response=None,
                        prompt_tokens=None,
                        completion_tokens=None,
                        cost_usd=None,
                        decoding=decoding,
                        run_id=run_id,
                    )
                    continue

                assert complete is not None
                prompt_est = max(1, len(prompt.encode("utf-8")) // 4)
                completion_est = int(decoding["max_tokens"])
                estimate = estimate_cost(model_slug, prompt_est, completion_est)
                try:
                    tracker.authorize(estimate)
                except BudgetExceededError:
                    pairs_refused_budget += 1
                    halt_paid = True
                    _append_record(
                        records_path,
                        task=task,
                        model_slug=model_slug,
                        tier=tier,
                        prompt=prompt,
                        p_hash=p_hash,
                        prompt_ref=prompt_ref,
                        context_paths=context_paths,
                        raw_response=None,
                        prompt_tokens=None,
                        completion_tokens=None,
                        cost_usd=None,
                        decoding=decoding,
                        run_id=run_id,
                    )
                    continue

                result = await complete(
                    model_slug=model_slug,
                    prompt=prompt,
                    decoding=dict(decoding),
                )
                raw_response = result.text
                prompt_tokens = result.prompt_tokens
                completion_tokens = result.completion_tokens
                cost_usd = None
                if prompt_tokens is not None and completion_tokens is not None:
                    cost_usd = tracker.record_usage(
                        model_slug, prompt_tokens, completion_tokens
                    )
                pairs_generated += 1

                extraction = extract_patch(raw_response)
                if extraction.patch_parse_ok and extraction.extracted_patch:
                    cache.put(
                        key,
                        CachedGeneration(
                            raw_response=raw_response,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            decoding_params=dict(decoding),
                            model_slug=model_slug,
                        ),
                    )

                _append_record(
                    records_path,
                    task=task,
                    model_slug=model_slug,
                    tier=tier,
                    prompt=prompt,
                    p_hash=p_hash,
                    prompt_ref=prompt_ref,
                    context_paths=context_paths,
                    raw_response=raw_response,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost_usd,
                    decoding=decoding,
                    run_id=run_id,
                )
    finally:
        if client is not None:
            await client.aclose()

    write_run_manifest(
        manifest_path,
        {
            "run_id": run_id,
            "timestamp": _utc_now(),
            "git_commit": git_commit_sha(cwd=_repo_root()),
            "config_path": str(config.config_path),
            "config_snapshot": yaml_data,
            "model_slugs": list(config.model_slugs),
            "task_limit": config.task_limit,
            "dry_run": config.dry_run,
            "records_path": str(records_path),
            "total_cost_usd": tracker.total_usd,
            "pairs_attempted": pairs_attempted,
            "pairs_cache_hit": pairs_cache_hit,
            "pairs_generated": pairs_generated,
            "pairs_refused_budget": pairs_refused_budget,
        },
    )

    return RunResult(
        run_id=run_id,
        manifest_path=manifest_path,
        records_path=records_path,
        pairs_attempted=pairs_attempted,
        pairs_cache_hit=pairs_cache_hit,
        pairs_generated=pairs_generated,
        pairs_refused_budget=pairs_refused_budget,
        total_cost_usd=tracker.total_usd,
    )
