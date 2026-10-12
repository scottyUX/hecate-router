#!/usr/bin/env python3
"""Three-model SWE-bench Verified experiment: one model per invocation.

Runs mini-SWE-agent on a pre-registered task set for ONE of Claude Opus 4.5,
Gemini 3 Flash or MiniMax M2.5. The three models are meant to run
concurrently as three separate processes (see scripts/launch_three_model.sh);
each gets its own output directory and preds.json, since upstream keys
preds.json by instance_id alone.

Two experiments, selected with --experiment:

  r1  100 tasks, configs/miniswe_three_model.yaml (the gpt-5-mini sanity
      check's agent setup), mini-swe-agent 2.4.6, provider-default reasoning,
      no per-task cost cap, per-process caps summing to $250.
  r2  50 of r1's tasks, configs/miniswe_leaderboard.yaml, mini-swe-agent
      2.0.0, every setting matched to the SWE-bench bash-only leaderboard
      entries (specs/018-three-model-r2): high reasoning, $3 per task,
      leaderboard providers via OpenRouter, per-process caps summing to $130.

Usage:
    python scripts/run_three_model.py --model opus --dry-run
    python scripts/run_three_model.py --experiment r2 --model opus --workers 4
    python scripts/run_three_model.py --model opus --tasks 2      # smoke
    python scripts/run_three_model.py --model opus --convert-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ModelSpec:
    key: str
    slug: str  # OpenRouter slug, also the model_slug on generation records
    providers: tuple[str, ...]  # OpenRouter providers this model may be served by
    global_cost_limit_usd: float
    # Extra -c overrides for this model only. Kept to operational settings;
    # anything that changes what the model sees must stay shared.
    extra_overrides: tuple[str, ...] = ()
    # Recorded in the manifest; must match the reasoning actually sent.
    reasoning: str = "provider default (not pinned)"
    # r2 only. The complete model_kwargs sent to OpenRouter, replacing r1's
    # extra_body.provider.order override, plus the model block fields the
    # leaderboard set per model. None on r1 specs.
    model_kwargs: dict | None = field(default=None, hash=False)
    set_cache_control: str | None = None
    model_class: str | None = None
    leaderboard_entry: str | None = None

    @property
    def agent_model(self) -> str:
        """--model for mini-extra: litellm needs the openrouter/ prefix (r1);
        the OpenRouter model classes take the bare slug (r2)."""
        return self.slug if self.model_class else f"openrouter/{self.slug}"


# Per-process caps sum to the $250 experiment budget. Split by expected cost
# (Opus list price is ~10-20x the other two). With --workers > 1 a cap can be
# overshot by the tasks already in flight when it trips.
MODELS: dict[str, ModelSpec] = {
    spec.key: spec
    for spec in (
        ModelSpec(
            "opus",
            "anthropic/claude-opus-4.5",
            ("anthropic", "amazon-bedrock", "google-vertex"),
            185.0,
        ),
        ModelSpec(
            "gemini",
            "google/gemini-3-flash-preview",
            ("google-ai-studio", "google-vertex"),
            40.0,
            # litellm's price table returns $0 for some Gemini 3 Flash calls
            # and mini-SWE then kills the instance (3/12 in the first minutes
            # of the run). Ignoring keeps the instance alive; that call is
            # counted as $0 toward the cap, but OpenRouter's billed usage.cost
            # is still in every saved response for the real total.
            ("model.cost_tracking=ignore_errors",),
        ),
        ModelSpec("minimax", "minimax/minimax-m2.5", ("minimax",), 25.0),
    )
}

# r2: every value below is copied from the leaderboard entries' trajectories
# (configs/leaderboard_reference/), translated to OpenRouter where the entry
# called a provider directly. scripts/check_leaderboard_config.py verifies the
# resolved config against those files before any spend.
_R2_COMMON_KWARGS = {
    "drop_params": True,
    "temperature": None,
    "parallel_tool_calls": True,
    # OpenRouter's unified reasoning param. The Opus and Gemini entries sent
    # litellm's reasoning_effort="high" to the provider APIs directly; the
    # MiniMax entry sent exactly this over OpenRouter.
    "reasoning": {"effort": "high"},
}
_OPENROUTER_HEADERS = "hecate.agent.openrouter_headers.OpenRouterHeadersModel"

# Caps: leaderboard $/task x 50 is ~$38 / $18 / $4; caps are ~2x that.
R2_MODELS: dict[str, ModelSpec] = {
    spec.key: spec
    for spec in (
        ModelSpec(
            "opus",
            "anthropic/claude-opus-4.5",
            ("anthropic",),
            75.0,
            reasoning="effort=high",
            model_kwargs={
                **_R2_COMMON_KWARGS,
                # The entry called Anthropic directly.
                "provider": {"order": ["anthropic"], "allow_fallbacks": False},
                "extra_headers": {"anthropic-beta": "interleaved-thinking-2025-05-14"},
            },
            set_cache_control="default_end",
            # Upstream OpenRouterModel would put extra_headers in the body.
            model_class=_OPENROUTER_HEADERS,
            leaderboard_entry="20260217_mini-v2.0.0_claude-4-5-opus-high",
        ),
        ModelSpec(
            "gemini",
            "google/gemini-3-flash-preview",
            ("google-ai-studio",),
            40.0,
            reasoning="effort=high",
            model_kwargs={
                **_R2_COMMON_KWARGS,
                # The entry called Google AI Studio directly.
                "provider": {"order": ["google-ai-studio"], "allow_fallbacks": False},
            },
            set_cache_control=None,
            model_class="openrouter",
            leaderboard_entry="20260217_mini-v2.0.0_gemini-3-flash-high",
        ),
        ModelSpec(
            "minimax",
            "minimax/minimax-m2.5",
            ("novita", "minimax/fp8", "atlas-cloud"),
            15.0,
            reasoning="effort=high",
            model_kwargs={
                **_R2_COMMON_KWARGS,
                # The entry was unpinned and OpenRouter load-balanced it across
                # Novita, Minimax, Fireworks, SiliconFlow and AtlasCloud
                # (configs/leaderboard_reference/minimax_provider_mix.json).
                # Fireworks and SiliconFlow no longer serve M2.5; `only`
                # without `order` keeps the load balancing among the rest.
                # minimax/fp8 excludes the newer minimax/highspeed endpoint.
                "provider": {"only": ["novita", "minimax/fp8", "atlas-cloud"]},
            },
            set_cache_control=None,
            model_class="openrouter",
            leaderboard_entry="20260217_mini-v2.0.0_minimax-2-5-high",
        ),
    )
}


@dataclass(frozen=True)
class Experiment:
    key: str
    run_id: str
    config: Path
    tasks_file: Path
    run_root: Path
    models: dict[str, ModelSpec] = field(hash=False)
    # The mini-swe-agent version this experiment ran on. Checked against the
    # installed version before any model call and written to every record,
    # so finishing r1's queued tasks needs 2.4.6, not the current pin.
    scaffold_version: str = ""


EXPERIMENTS: dict[str, Experiment] = {
    "r1": Experiment(
        "r1",
        "three-model-verified",
        Path("configs/miniswe_three_model.yaml"),
        Path("configs/three_model_tasks.json"),
        Path("data/outputs/runs/three-model-verified"),
        MODELS,
        scaffold_version="2.4.6",
    ),
    "r2": Experiment(
        "r2",
        "three-model-verified-r2",
        Path("configs/miniswe_leaderboard.yaml"),
        Path("configs/three_model_tasks_r2.json"),
        Path("data/outputs/runs/three-model-verified-r2"),
        R2_MODELS,
        scaffold_version="2.0.0",
    ),
}

TASKS_FILE = EXPERIMENTS["r1"].tasks_file
DEFAULT_CONFIG = EXPERIMENTS["r1"].config
RUN_ROOT = EXPERIMENTS["r1"].run_root
RUN_ID = EXPERIMENTS["r1"].run_id
EXECUTION_DATASET = "SWE-bench/SWE-bench_Verified"
LEADERBOARD_REFERENCE_DIR = Path("configs/leaderboard_reference")
# The leaderboard entries are labeled mini-swe-agent 2.0.0, but their
# trajectories record 2.1.0. The two releases differ only in the interactive
# agent, which the swebench batch runner does not use.
LEADERBOARD_MINI_VERSION_NOTE = (
    "leaderboard metadata says 2.0.0; its trajectories record 2.1.0, which "
    "differs from 2.0.0 only in agents/interactive.py (unused in batch runs)"
)


def load_task_ids(path: Path = TASKS_FILE) -> tuple[str, ...]:
    return tuple(t["instance_id"] for t in json.loads(path.read_text())["tasks"])


def filter_spec_for(instance_ids: tuple[str, ...]) -> str:
    """Exact-set regex for mini-extra's --filter (no id-list flag upstream)."""
    return "^(" + "|".join(instance_ids) + ")$"


def config_overrides_for(
    spec: ModelSpec, config_path: Path, platform: str | None = None
) -> list[str]:
    overrides = [str(config_path)]
    if spec.model_kwargs is None:
        overrides.append(
            f"model.model_kwargs.extra_body.provider.order={json.dumps(list(spec.providers))}"
        )
    else:
        overrides += [
            f"model.model_kwargs={json.dumps(spec.model_kwargs)}",
            # Explicit null matters: upstream turns cache control on for any
            # model name containing "anthropic"/"claude" unless the key is set.
            f"model.set_cache_control={json.dumps(spec.set_cache_control)}",
        ]
    overrides += spec.extra_overrides
    if platform:
        overrides.append(
            f"environment.run_args={json.dumps(['--rm', '--platform', platform])}"
        )
    return overrides


# Tracebacks that mean the harness, not the model, ended the instance.
INFRA_TRACEBACK_MARKERS = (
    "Error calculating cost",
    # OpenRouter 402s: the account ran out of credits mid-run (Opus,
    # 2026-10-05). Billing, not the model.
    "in_flight_budget_exhausted",
    "requires more credits",
    "exceed your available credits",
    # r2's OpenRouterModel surfaces the same 402 as a bare HTTP error.
    "HTTP 402",
    # r2: OpenRouterModel refuses a response with no billed cost. Retried
    # rather than counted; investigate if it recurs (spec 018 edge cases).
    "No valid cost information available from OpenRouter",
)


def _is_infra_failure(model_dir: Path, iid: str) -> bool:
    traj = model_dir / iid / f"{iid}.traj.json"
    if not traj.exists():
        return True
    try:
        info = json.loads(traj.read_text()).get("info", {})
    except (OSError, json.JSONDecodeError):
        return True
    trace = str(info.get("traceback") or "")
    return any(marker in trace for marker in INFRA_TRACEBACK_MARKERS)


def prune_infra_failures(model_dir: Path) -> list[str]:
    """Re-queue instances the harness, not the model, ended.

    Two cases: no trajectory at all (container start / image pull failed
    before the agent existed; the gap that cost the sanity check
    matplotlib-26113), or a trajectory ended by a known harness error (see
    INFRA_TRACEBACK_MARKERS). Upstream's resume skips anything already in
    preds.json, so the entry is removed; any trajectory dir is moved under
    _infra_failed/ rather than deleted, so the failed attempt stays on record.
    """
    preds_path = model_dir / "preds.json"
    if not preds_path.exists():
        return []
    preds = json.loads(preds_path.read_text())
    pruned = sorted(iid for iid in preds if _is_infra_failure(model_dir, iid))
    if pruned:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        preds_path.with_suffix(f".json.bak-{stamp}").write_text(preds_path.read_text())
        for iid in pruned:
            del preds[iid]
            if (model_dir / iid).exists():
                dest = model_dir / "_infra_failed" / f"{iid}-{stamp}"
                dest.parent.mkdir(exist_ok=True)
                (model_dir / iid).rename(dest)
        preds_path.write_text(json.dumps(preds, indent=2))
    return pruned


def write_grading_configs(spec: ModelSpec, model_dir: Path) -> Path:
    """Single-model option_a + execution config for run_execution.py.

    Generated next to the run output (not under configs/) because they only
    point run_execution.py at this model's generations.jsonl.
    """
    option_a = model_dir / "option_a.yaml"
    option_a.write_text(
        yaml.safe_dump(
            {
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "models": [{"slug": spec.slug, "tier": "small"}],
            },
            sort_keys=False,
        )
    )
    execution = model_dir / "execution.yaml"
    execution.write_text(
        yaml.safe_dump(
            {
                "input_generations": str(model_dir / "generations.jsonl"),
                "option_a_config": str(option_a),
                "dataset_name": EXECUTION_DATASET,
                "split": "test",
                "max_workers": 4,
                "timeout": 1800,
                "namespace": "swebench",
                "cache_level": "env",
                "force_rebuild": False,
                "modal": False,
                "m1_positive_rate_flag_threshold": 0.15,
            },
            sort_keys=False,
        )
    )
    return execution


def reference_config_path(spec: ModelSpec) -> Path | None:
    if spec.leaderboard_entry is None:
        return None
    return LEADERBOARD_REFERENCE_DIR / f"{spec.leaderboard_entry}.json"


def docker_image_digests(instance_ids: tuple[str, ...]) -> dict[str, str | None]:
    """Repo digest of each instance's local image (None if absent or no docker).

    The leaderboard and these runs both use :latest tags, which can move.
    """
    digests: dict[str, str | None] = {}
    for iid in instance_ids:
        name = iid.replace("__", "_1776_")
        image = f"docker.io/swebench/sweb.eval.x86_64.{name}:latest".lower()
        try:
            out = subprocess.run(
                ["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", image],
                capture_output=True, text=True, check=False, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            out = None
        repo_digests = json.loads(out.stdout) if out and out.returncode == 0 else []
        digests[iid] = repo_digests[0] if repo_digests else None
    return digests


def _miniswe_version() -> str | None:
    try:
        import minisweagent

        return getattr(minisweagent, "__version__", None)
    except ImportError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Three-model Verified experiment runner")
    parser.add_argument("--experiment", choices=sorted(EXPERIMENTS), default="r1")
    parser.add_argument("--model", required=True, choices=sorted(MODELS))
    parser.add_argument(
        "--miniswe-config", type=Path, default=None, help="default: the experiment's"
    )
    parser.add_argument(
        "--run-root", type=Path, default=None, help="default: the experiment's"
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--global-cost-limit",
        type=float,
        default=None,
        help="Override this model's process-wide spend cap (USD)",
    )
    parser.add_argument(
        "--tasks", type=int, default=None, help="Only the first N task ids (smoke)"
    )
    parser.add_argument("--redo-existing", action="store_true")
    parser.add_argument(
        "--prune-infra-failures",
        action="store_true",
        help="Drop preds.json entries with no trajectory (never reached the "
        "model) so the next run retries them, then exit",
    )
    parser.add_argument("--convert-only", action="store_true")
    parser.add_argument("--platform", default=None, help="e.g. linux/amd64 on arm64 hosts")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    from hecate.agent.batch import run_swebench_batch
    from hecate.agent.convert import (
        MinisweConvertError,
        build_records,
        read_outcomes,
        write_generations,
    )
    from hecate.agent.miniswe import MinisweNotInstalledError
    from hecate.data.tasks import load_swebench_verified
    from hecate.utils.env import load_env
    from hecate.utils.manifest import git_commit_sha, write_run_manifest

    load_env()
    experiment = EXPERIMENTS[args.experiment]
    spec = experiment.models[args.model]
    miniswe_config = args.miniswe_config or experiment.config
    run_root = args.run_root or experiment.run_root
    cost_limit = (
        args.global_cost_limit
        if args.global_cost_limit is not None
        else spec.global_cost_limit_usd
    )

    will_call_model = not (args.dry_run or args.convert_only or args.prune_infra_failures)
    installed = _miniswe_version()
    if will_call_model and installed != experiment.scaffold_version:
        print(
            f"error: {args.experiment} runs on mini-swe-agent "
            f"{experiment.scaffold_version}, installed is {installed}",
            file=sys.stderr,
        )
        return 1

    instance_ids = load_task_ids(experiment.tasks_file)
    if args.tasks is not None:
        instance_ids = instance_ids[: args.tasks]

    tasks = load_swebench_verified()
    dataset_ids = {t.instance_id for t in tasks}
    missing = [i for i in instance_ids if i not in dataset_ids]
    if missing:
        print(f"error: ids not in SWE-bench Verified: {missing}", file=sys.stderr)
        return 2

    model_dir = run_root / spec.key
    if args.prune_infra_failures:
        pruned = prune_infra_failures(model_dir)
        print(f"pruned={len(pruned)} {pruned}")
        return 0
    filter_spec = filter_spec_for(instance_ids)
    overrides = config_overrides_for(spec, miniswe_config, args.platform)
    agent_model = spec.agent_model
    started = datetime.now(timezone.utc)

    if not args.convert_only:
        try:
            result = run_swebench_batch(
                model=agent_model,
                output_dir=model_dir,
                subset="verified",
                split="test",
                workers=args.workers,
                filter_spec=filter_spec,
                redo_existing=args.redo_existing,
                environment_class="docker",
                model_class=spec.model_class,
                config_overrides=tuple(overrides),
                global_cost_limit=cost_limit,
                dry_run=args.dry_run,
            )
        except MinisweNotInstalledError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"argv={' '.join(result.argv)}")
        if result.returncode != 0 and not args.dry_run:
            print(
                f"warning: run exited {result.returncode}; converting whatever completed",
                file=sys.stderr,
            )

    if args.dry_run:
        print(
            f"experiment={args.experiment} model={spec.slug} tasks={len(instance_ids)} "
            f"cap=${cost_limit} run_root={run_root}"
        )
        return 0

    try:
        outcomes = read_outcomes(model_dir)
    except MinisweConvertError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Instances listed in preds.json with no trajectory never reached the
    # model (container start / image pull failed): infra failures, not model
    # failures. Upstream resume skips anything in preds.json, so these must be
    # pruned from preds.json before a re-run will retry them.
    # Same test as --prune-infra-failures, so an instance killed by e.g. an
    # OpenRouter 402 is never graded as a model failure, pruned or not.
    infra_failed = sorted(
        i
        for i, o in outcomes.items()
        if o.exit_status is None or _is_infra_failure(model_dir, i)
    )
    submitted = sum(1 for o in outcomes.values() if o.submitted)
    print(
        f"instances={len(outcomes)} submitted={submitted} "
        f"infra_failed={len(infra_failed)}"
    )

    # Infra failures never reached the model; grading their empty patch would
    # record them as unresolved, i.e. as model failures. Leave them out of
    # generations.jsonl entirely (they stay listed in the manifest).
    wanted = set(instance_ids) - set(infra_failed)
    records = build_records(
        {spec.slug: {i: o for i, o in outcomes.items() if i in wanted}},
        [t for t in tasks if t.instance_id in wanted],
        tiers={spec.slug: "small"},
        run_id=f"{experiment.run_id}-{spec.key}",
        scaffold_version=experiment.scaffold_version,
        require_complete=False,
    )
    records_path = write_generations(records, model_dir / "generations.jsonl")
    execution_cfg = write_grading_configs(spec, model_dir)

    by_exit: dict[str, int] = {}
    for o in outcomes.values():
        by_exit[o.exit_status or "no_trajectory"] = by_exit.get(o.exit_status or "no_trajectory", 0) + 1
    costs = [o.cost_usd for o in outcomes.values() if o.cost_usd is not None]

    # One manifest per invocation (timestamped) so a --convert-only pass never
    # overwrites the record of the run that produced the trajectories.
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    kind = "convert" if args.convert_only else "run"
    agent_config = yaml.safe_load(miniswe_config.read_text())
    reference = reference_config_path(spec)
    r2_fields = (
        {
            "leaderboard_entry": spec.leaderboard_entry,
            "leaderboard_mini_version_note": LEADERBOARD_MINI_VERSION_NOTE,
            "reference_config_path": str(reference),
            "reference_config_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
            "model_class": spec.model_class,
            "model_kwargs": spec.model_kwargs,
            "set_cache_control": spec.set_cache_control,
            "docker_image_digests": docker_image_digests(instance_ids),
        }
        if reference is not None
        else {}
    )
    manifest_path = write_run_manifest(
        model_dir / f"manifest-{kind}-{stamp}.json",
        {
            "run_id": f"{experiment.run_id}-{spec.key}",
            "experiment": experiment.run_id,
            "invocation": kind,
            "started": started.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "argv": sys.argv,
            "git_commit": git_commit_sha(cwd=Path(__file__).resolve().parents[1]),
            "scaffold": "mini-swe-agent",
            "scaffold_version": _miniswe_version(),
            "expected_scaffold_version": experiment.scaffold_version,
            "miniswe_config_path": str(miniswe_config),
            "miniswe_config": agent_config,
            "config_overrides": overrides,
            "model_key": spec.key,
            "model_slug": spec.slug,
            "agent_model": agent_model,
            "providers": list(spec.providers),
            "reasoning": spec.reasoning,
            "subset": "verified",
            "split": "test",
            "tasks_file": str(experiment.tasks_file),
            "instance_ids": list(instance_ids),
            "global_cost_limit_usd": cost_limit,
            "per_task_cost_limit_usd": agent_config["agent"].get("cost_limit") or None,
            "workers": args.workers,
            "redo_existing": args.redo_existing,
            "instances": len(outcomes),
            "instances_submitted": submitted,
            "infra_failed": infra_failed,
            "exit_status_counts": by_exit,
            "total_cost_usd": round(sum(costs), 6) if costs else None,
            "records_path": str(records_path),
            "execution_config": str(execution_cfg),
            **r2_fields,
        },
    )
    print(f"manifest={manifest_path}")
    print(
        f"next: python scripts/run_execution.py --config {execution_cfg} "
        f"--output-dir {model_dir} --run-id {experiment.run_id}-{spec.key}-exec"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
