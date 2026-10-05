#!/usr/bin/env python3
"""Three-model SWE-bench Verified experiment: one model per invocation.

Runs mini-SWE-agent on the 100 pre-registered tasks in
configs/three_model_tasks.json for ONE of Claude Opus 4.5, Gemini 3 Flash or
MiniMax M2.5. The three models are meant to run concurrently as three
separate processes (see scripts/launch_three_model.sh); each gets its own
output directory and preds.json, since upstream keys preds.json by
instance_id alone.

Same agent, prompt, step_limit and environment as the gpt-5-mini sanity check
(configs/miniswe_three_model.yaml documents the deltas). No per-task cost cap;
each process has its own MSWEA_GLOBAL_COST_LIMIT, and the defaults sum to the
$250 experiment budget.

Usage:
    python scripts/run_three_model.py --model opus --dry-run
    python scripts/run_three_model.py --model opus --workers 4
    python scripts/run_three_model.py --model opus --tasks 2      # smoke
    python scripts/run_three_model.py --model opus --convert-only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ModelSpec:
    key: str
    slug: str  # OpenRouter slug, also the model_slug on generation records
    providers: tuple[str, ...]  # OpenRouter provider.order, no fallbacks beyond these
    global_cost_limit_usd: float


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
        ),
        ModelSpec("minimax", "minimax/minimax-m2.5", ("minimax",), 25.0),
    )
}

TASKS_FILE = Path("configs/three_model_tasks.json")
DEFAULT_CONFIG = Path("configs/miniswe_three_model.yaml")
RUN_ROOT = Path("data/outputs/runs/three-model-verified")
RUN_ID = "three-model-verified"
EXECUTION_DATASET = "SWE-bench/SWE-bench_Verified"


def load_task_ids(path: Path = TASKS_FILE) -> tuple[str, ...]:
    return tuple(t["instance_id"] for t in json.loads(path.read_text())["tasks"])


def filter_spec_for(instance_ids: tuple[str, ...]) -> str:
    """Exact-set regex for mini-extra's --filter (no id-list flag upstream)."""
    return "^(" + "|".join(instance_ids) + ")$"


def config_overrides_for(
    spec: ModelSpec, config_path: Path, platform: str | None = None
) -> list[str]:
    overrides = [
        str(config_path),
        f"model.model_kwargs.extra_body.provider.order={json.dumps(list(spec.providers))}",
    ]
    if platform:
        overrides.append(
            f"environment.run_args={json.dumps(['--rm', '--platform', platform])}"
        )
    return overrides


def prune_infra_failures(model_dir: Path) -> list[str]:
    """Remove preds.json entries whose instance never produced a trajectory.

    Upstream writes a preds.json entry even when the container fails to start,
    and its resume logic skips anything already in preds.json, so without this
    those instances would never be retried. Checks for the trajectory file
    itself, not its exit status, so failures before agent creation are caught
    too (the gap that cost the sanity check matplotlib-26113).
    """
    preds_path = model_dir / "preds.json"
    if not preds_path.exists():
        return []
    preds = json.loads(preds_path.read_text())
    pruned = sorted(
        iid for iid in preds if not (model_dir / iid / f"{iid}.traj.json").exists()
    )
    if pruned:
        backup = preds_path.with_suffix(
            f".json.bak-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        )
        backup.write_text(preds_path.read_text())
        for iid in pruned:
            del preds[iid]
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


def _miniswe_version() -> str | None:
    try:
        import minisweagent

        return getattr(minisweagent, "__version__", None)
    except ImportError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Three-model Verified experiment runner")
    parser.add_argument("--model", required=True, choices=sorted(MODELS))
    parser.add_argument("--miniswe-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--run-root", type=Path, default=RUN_ROOT)
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
    spec = MODELS[args.model]
    cost_limit = (
        args.global_cost_limit
        if args.global_cost_limit is not None
        else spec.global_cost_limit_usd
    )

    instance_ids = load_task_ids()
    if args.tasks is not None:
        instance_ids = instance_ids[: args.tasks]

    tasks = load_swebench_verified()
    dataset_ids = {t.instance_id for t in tasks}
    missing = [i for i in instance_ids if i not in dataset_ids]
    if missing:
        print(f"error: ids not in SWE-bench Verified: {missing}", file=sys.stderr)
        return 2

    model_dir = args.run_root / spec.key
    if args.prune_infra_failures:
        pruned = prune_infra_failures(model_dir)
        print(f"pruned={len(pruned)} {pruned}")
        return 0
    filter_spec = filter_spec_for(instance_ids)
    overrides = config_overrides_for(spec, args.miniswe_config, args.platform)
    agent_model = f"openrouter/{spec.slug}"
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
        print(f"model={spec.slug} tasks={len(instance_ids)} cap=${cost_limit}")
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
    infra_failed = sorted(
        i for i, o in outcomes.items() if o.traj_path is None or o.exit_status is None
    )
    submitted = sum(1 for o in outcomes.values() if o.submitted)
    print(
        f"instances={len(outcomes)} submitted={submitted} "
        f"infra_failed={len(infra_failed)}"
    )

    wanted = set(instance_ids)
    records = build_records(
        {spec.slug: {i: o for i, o in outcomes.items() if i in wanted}},
        [t for t in tasks if t.instance_id in wanted],
        tiers={spec.slug: "small"},
        run_id=f"{RUN_ID}-{spec.key}",
        scaffold_version=">=2,<3",
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
    manifest_path = write_run_manifest(
        model_dir / f"manifest-{kind}-{stamp}.json",
        {
            "run_id": f"{RUN_ID}-{spec.key}",
            "experiment": RUN_ID,
            "invocation": kind,
            "started": started.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "argv": sys.argv,
            "git_commit": git_commit_sha(cwd=Path(__file__).resolve().parents[1]),
            "scaffold": "mini-swe-agent",
            "scaffold_version": _miniswe_version(),
            "miniswe_config_path": str(args.miniswe_config),
            "miniswe_config": yaml.safe_load(args.miniswe_config.read_text()),
            "config_overrides": overrides,
            "model_key": spec.key,
            "model_slug": spec.slug,
            "agent_model": agent_model,
            "providers": list(spec.providers),
            "reasoning": "provider default (not pinned)",
            "subset": "verified",
            "split": "test",
            "tasks_file": str(TASKS_FILE),
            "instance_ids": list(instance_ids),
            "global_cost_limit_usd": cost_limit,
            "per_task_cost_limit_usd": None,
            "workers": args.workers,
            "redo_existing": args.redo_existing,
            "instances": len(outcomes),
            "instances_submitted": submitted,
            "infra_failed": infra_failed,
            "exit_status_counts": by_exit,
            "total_cost_usd": round(sum(costs), 6) if costs else None,
            "records_path": str(records_path),
            "execution_config": str(execution_cfg),
        },
    )
    print(f"manifest={manifest_path}")
    print(
        f"next: python scripts/run_execution.py --config {execution_cfg} "
        f"--output-dir {model_dir} --run-id {RUN_ID}-{spec.key}-exec"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
