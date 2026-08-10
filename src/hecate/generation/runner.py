"""Stage-1 generation orchestrator (S11).

Ties scaffold → cache → cost → OpenRouter → patch extraction → JSONL records
and a run manifest. Libraries remain unaware of each other; this module is the
only integrator.
"""

from __future__ import annotations

import time
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
    read_jsonl,
)
from hecate.generation.client import CompletionResult, OpenRouterClient
from hecate.generation.errors import OpenRouterError
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


def _ordered_model_slugs(config: dict[str, Any]) -> tuple[str, ...]:
    """Return configured model slugs in YAML order (small tier before large)."""
    small: list[str] = []
    large: list[str] = []
    other: list[str] = []
    for model in config.get("models", []) or []:
        if not isinstance(model, dict) or not model.get("slug"):
            continue
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
        raise ValueError("No model slugs found in config")
    return ordered


def _recorded_pairs(records_path: Path) -> set[tuple[str, str]]:
    """Return ``(instance_id, model_slug)`` pairs already present in JSONL."""
    if not records_path.is_file():
        return set()
    return {
        (record.instance_id, record.model_slug) for record in read_jsonl(records_path)
    }


def load_run_config(
    *,
    config_path: Path | str | None = None,
    tasks: int = 1,
    model: str | None = None,
    models: list[str] | tuple[str, ...] | None = None,
    all_models: bool = False,
    dry_run: bool = False,
    output_dir: Path | str | None = None,
    cache_dir: Path | str | None = None,
    ledger_path: Path | str | None = None,
    run_id: str | None = None,
    repo_cache_dir: Path | str | None = None,
) -> RunConfig:
    """Build a :class:`RunConfig` from CLI-style arguments.

    Model selection (first match wins):
    - ``models``: explicit slug list
    - ``all_models=True``: every slug in Option A (small before large)
    - ``model``: single slug
    - default: first small-tier slug
    """
    if tasks < 1:
        raise ValueError("tasks must be >= 1")

    resolved_config = (
        Path(config_path) if config_path is not None else _default_config_path()
    )
    data = _load_yaml(resolved_config)
    known = set(_model_tiers(data))

    if models is not None:
        slugs = tuple(models)
    elif all_models:
        slugs = _ordered_model_slugs(data)
    elif model is not None:
        slugs = (model,)
    else:
        slugs = (_default_small_slug(data),)

    if not slugs:
        raise ValueError("At least one model slug is required")
    unknown = [slug for slug in slugs if slug not in known]
    if unknown:
        raise ValueError(
            f"Unknown model slug(s): {unknown!r}. Configured slugs: {sorted(known)}"
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
        model_slugs=slugs,
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


def _context_window_tokens(config: dict[str, Any]) -> int:
    generation = config.get("generation", {}) or {}
    return int(generation.get("context_window_tokens", 32_768))


def _clamp_decoding_for_prompt(
    decoding: dict[str, Any],
    prompt: str,
    *,
    context_window_tokens: int,
) -> dict[str, Any]:
    """Shrink max_tokens so rough prompt+completion stays inside the window."""
    prompt_est = max(1, len(prompt.encode("utf-8")) // 4)
    # Leave a small safety margin for tokenizer mismatch / chat wrapping.
    headroom = context_window_tokens - prompt_est - 256
    max_tokens = int(decoding["max_tokens"])
    if headroom < 256:
        # Still attempt a tiny completion rather than requesting an impossible budget.
        clamped = 256
    else:
        clamped = min(max_tokens, headroom)
    if clamped == max_tokens:
        return dict(decoding)
    out = dict(decoding)
    out["max_tokens"] = int(clamped)
    return out


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _build_repair_prompt(previous_response: str) -> str:
    """One-shot rewrite prompt used when the first response fails S8 extract."""
    prior = previous_response.strip()
    if len(prior) > 4000:
        prior = prior[:4000] + "\n... [truncated] ..."
    return "\n".join(
        [
            "Your previous answer was not a valid unified diff "
            "(missing or malformed ---/+++ headers or @@ hunks).",
            "Rewrite it as exactly one valid unified diff and nothing else.",
            "Requirements: include ---/+++ file headers and complete @@ hunks.",
            "No prose, no multiple candidates.",
            "",
            "Previous answer:",
            prior,
        ]
    )


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
    base_decoding = _decoding_params(yaml_data)
    window_tokens = _context_window_tokens(yaml_data)

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
    pairs_repaired = 0
    pairs_already_recorded = 0
    halt_paid = False
    pair_timings: list[dict[str, Any]] = []
    already_recorded = _recorded_pairs(records_path)
    run_started = time.perf_counter()

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
            pair_decoding = _clamp_decoding_for_prompt(
                base_decoding,
                prompt,
                context_window_tokens=window_tokens,
            )
            dec_fp = decoding_fingerprint(pair_decoding)

            for model_slug in config.model_slugs:
                pair_started = time.perf_counter()
                pairs_attempted += 1
                tier = tiers.get(model_slug)
                if tier not in ("small", "large"):
                    raise ValueError(f"Missing tier for model slug {model_slug!r}")

                if (task.instance_id, model_slug) in already_recorded:
                    pairs_already_recorded += 1
                    outcome = "already_recorded"
                    pair_timings.append(
                        {
                            "instance_id": task.instance_id,
                            "model_slug": model_slug,
                            "outcome": outcome,
                            "wall_clock_s": round(
                                time.perf_counter() - pair_started, 3
                            ),
                            "cost_usd": None,
                        }
                    )
                    continue

                key = cache_key(
                    task.instance_id,
                    model_slug,
                    p_hash,
                    PROMPT_VERSION,
                    dec_fp,
                )
                cached = cache.get(key)
                outcome = "unknown"
                cost_usd: float | None = None

                if cached is not None:
                    pairs_cache_hit += 1
                    pairs_generated += 1
                    outcome = "cache_hit"
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
                        decoding=pair_decoding,
                        run_id=run_id,
                    )
                elif config.dry_run:
                    outcome = "dry_run"
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
                        decoding=pair_decoding,
                        run_id=run_id,
                    )
                elif halt_paid:
                    pairs_refused_budget += 1
                    outcome = "refused_budget"
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
                        decoding=pair_decoding,
                        run_id=run_id,
                    )
                else:
                    assert complete is not None
                    prompt_est = max(1, len(prompt.encode("utf-8")) // 4)
                    completion_est = int(pair_decoding["max_tokens"])
                    estimate = estimate_cost(model_slug, prompt_est, completion_est)
                    try:
                        tracker.authorize(estimate)
                    except BudgetExceededError:
                        pairs_refused_budget += 1
                        halt_paid = True
                        outcome = "refused_budget"
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
                            decoding=pair_decoding,
                            run_id=run_id,
                        )
                    else:
                        try:
                            result = await complete(
                                model_slug=model_slug,
                                prompt=prompt,
                                decoding=dict(pair_decoding),
                            )
                        except OpenRouterError as exc:
                            outcome = "provider_error"
                            pair_timings.append(
                                {
                                    "instance_id": task.instance_id,
                                    "model_slug": model_slug,
                                    "outcome": outcome,
                                    "wall_clock_s": round(
                                        time.perf_counter() - pair_started, 3
                                    ),
                                    "cost_usd": None,
                                    "error": f"{type(exc).__name__}: {exc}",
                                }
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
                                raw_response=None,
                                prompt_tokens=None,
                                completion_tokens=None,
                                cost_usd=None,
                                decoding=pair_decoding,
                                run_id=run_id,
                            )
                            continue

                        raw_response = result.text
                        prompt_tokens = result.prompt_tokens
                        completion_tokens = result.completion_tokens
                        cost_usd = 0.0
                        if prompt_tokens is not None and completion_tokens is not None:
                            cost_usd += tracker.record_usage(
                                model_slug, prompt_tokens, completion_tokens
                            )
                        pairs_generated += 1
                        outcome = "generated"

                        extraction = extract_patch(raw_response)
                        if not (
                            extraction.patch_parse_ok and extraction.extracted_patch
                        ):
                            repair_prompt = _build_repair_prompt(raw_response)
                            repair_decoding = _clamp_decoding_for_prompt(
                                base_decoding,
                                repair_prompt,
                                context_window_tokens=window_tokens,
                            )
                            # Prefer a tighter completion budget for format repairs.
                            repair_decoding["max_tokens"] = min(
                                int(repair_decoding["max_tokens"]), 2048
                            )
                            repair_est = estimate_cost(
                                model_slug,
                                max(1, len(repair_prompt.encode("utf-8")) // 4),
                                int(repair_decoding["max_tokens"]),
                            )
                            try:
                                tracker.authorize(repair_est)
                                repair_result = await complete(
                                    model_slug=model_slug,
                                    prompt=repair_prompt,
                                    decoding=dict(repair_decoding),
                                )
                            except BudgetExceededError:
                                pass
                            except OpenRouterError:
                                pass
                            else:
                                if (
                                    repair_result.prompt_tokens is not None
                                    and repair_result.completion_tokens is not None
                                ):
                                    cost_usd += tracker.record_usage(
                                        model_slug,
                                        repair_result.prompt_tokens,
                                        repair_result.completion_tokens,
                                    )
                                repair_extraction = extract_patch(repair_result.text)
                                raw_response = repair_result.text
                                prompt_tokens = repair_result.prompt_tokens
                                completion_tokens = repair_result.completion_tokens
                                if (
                                    repair_extraction.patch_parse_ok
                                    and repair_extraction.extracted_patch
                                ):
                                    extraction = repair_extraction
                                    pairs_repaired += 1
                                    outcome = "repaired"

                        if extraction.patch_parse_ok and extraction.extracted_patch:
                            cache.put(
                                key,
                                CachedGeneration(
                                    raw_response=raw_response,
                                    prompt_tokens=prompt_tokens,
                                    completion_tokens=completion_tokens,
                                    decoding_params=dict(pair_decoding),
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
                            cost_usd=cost_usd if cost_usd > 0 else None,
                            decoding=pair_decoding,
                            run_id=run_id,
                        )

                pair_timings.append(
                    {
                        "instance_id": task.instance_id,
                        "model_slug": model_slug,
                        "outcome": outcome,
                        "wall_clock_s": round(time.perf_counter() - pair_started, 3),
                        "cost_usd": cost_usd,
                        "repaired": outcome == "repaired",
                    }
                )
    finally:
        if client is not None:
            await client.aclose()

    wall_clock_s = round(time.perf_counter() - run_started, 3)
    paid_costs = [t["cost_usd"] for t in pair_timings if t.get("cost_usd") is not None]
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
            "pairs_repaired": pairs_repaired,
            "pairs_already_recorded": pairs_already_recorded,
            "pairs_refused_budget": pairs_refused_budget,
            "wall_clock_s": wall_clock_s,
            "cost_per_sample_usd": (
                (sum(paid_costs) / len(paid_costs)) if paid_costs else None
            ),
            "pair_timings": pair_timings,
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
