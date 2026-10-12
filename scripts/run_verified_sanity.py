#!/usr/bin/env python3
"""SWE-bench Verified sanity-check run (spec 017).

Single model (gpt-5-mini via OpenRouter), exactly 14 named SWE-bench Verified
instances, $1.00 total spend cap. Reproduces one published leaderboard entry
(20260217_mini-v2.0.0_gpt-5-mini) closely enough to check this repo's harness
gives the same resolved/unresolved verdicts as the official one.

Not a variant of scripts/run_miniswe_sweep.py: that script's tier-cost-limit
split and multi-model manifest loop are load-bearing for the real two-model
Lite sweep and shouldn't be bent to fit a one-off single-model check. This
script is deliberately smaller and does not take a --model or --tasks flag —
the model and instance set are both pinned by design, not configurable here.

Usage:
    python scripts/run_verified_sanity.py --dry-run
    python scripts/run_verified_sanity.py
    python scripts/run_verified_sanity.py --convert-only   # re-merge existing output
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path


MODEL_SLUG = "openai/gpt-5-mini"
AGENT_MODEL = "openrouter/openai/gpt-5-mini"
LEADERBOARD_REFERENCE = "20260217_mini-v2.0.0_gpt-5-mini"

# Fixed 14-instance set (spec 017 "Fixed Instance Set"). Not a CLI flag: this
# run is pinned to exactly this set by design.
VERIFIED_INSTANCE_IDS: tuple[str, ...] = (
    "matplotlib__matplotlib-26113",
    "django__django-12741",
    "sympy__sympy-11618",
    "scikit-learn__scikit-learn-25931",
    "sphinx-doc__sphinx-8120",
    "pytest-dev__pytest-7324",
    "pydata__xarray-2905",
    "psf__requests-1921",
    "psf__requests-1766",
    "astropy__astropy-14182",
    "django__django-16642",
    "django__django-12308",
    "mwaskom__seaborn-3187",
    "pylint-dev__pylint-4661",
)

DEFAULT_GLOBAL_COST_LIMIT_USD = 1.00


def _filter_spec_for(instance_ids: tuple[str, ...]) -> str:
    """Exact-set regex for mini-extra's --filter (no id-list flag upstream)."""
    return "^(" + "|".join(instance_ids) + ")$"


def _miniswe_version() -> str | None:
    try:
        import minisweagent

        return getattr(minisweagent, "__version__", None)
    except ImportError:
        return None


def validate_instance_ids(instance_ids: tuple[str, ...], dataset_ids: set[str]) -> None:
    """Fail loudly (spec FR-002) before any model call if an id is unknown."""
    missing = [iid for iid in instance_ids if iid not in dataset_ids]
    if missing:
        raise ValueError(
            f"{len(missing)} instance id(s) not found in SWE-bench Verified "
            f"(test split): {missing}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SWE-bench Verified sanity check: gpt-5-mini vs the "
        f"{LEADERBOARD_REFERENCE} leaderboard entry"
    )
    parser.add_argument(
        "--miniswe-config",
        default="configs/miniswe_verified_single.yaml",
        help="Benchmark config (full replacement of upstream's default)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/outputs/runs/verified-sanity-gpt5mini",
        help="Run directory: agent output plus merged generations.jsonl",
    )
    parser.add_argument("--run-id", default="verified-sanity-gpt5mini")
    parser.add_argument(
        "--global-cost-limit",
        type=float,
        default=DEFAULT_GLOBAL_COST_LIMIT_USD,
        help="Hard ceiling on TOTAL spend for this run (spec FR-007/FR-008)",
    )
    parser.add_argument(
        "--redo-existing",
        action="store_true",
        help="Re-run instances already present in preds.json",
    )
    parser.add_argument(
        "--convert-only",
        action="store_true",
        help="Skip the agent run; just merge existing output into generations.jsonl",
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Convert even when some instances are missing from mini-SWE output",
    )
    parser.add_argument(
        "--platform",
        default=None,
        help="Docker --platform for the agent container, e.g. linux/amd64 on arm64 hosts",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print argv only")
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

    tasks = load_swebench_verified()
    dataset_ids = {task.instance_id for task in tasks}
    try:
        validate_instance_ids(VERIFIED_INSTANCE_IDS, dataset_ids)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    run_dir = Path(args.output_dir)
    filter_spec = _filter_spec_for(VERIFIED_INSTANCE_IDS)

    config_overrides: list[str] = [str(args.miniswe_config)]
    if args.platform:
        import json

        extra_run_args = ["--rm", "--platform", args.platform]
        config_overrides.append(f"environment.run_args={json.dumps(extra_run_args)}")

    if not args.convert_only:
        try:
            result = run_swebench_batch(
                model=AGENT_MODEL,
                output_dir=run_dir,
                subset="verified",
                split="test",
                # Sequential: required for the global cap to bind before
                # starting each new task (spec FR-008; see plan.md) --
                # swebench.py submits every instance up front and --workers
                # only bounds concurrency.
                workers=1,
                filter_spec=filter_spec,
                redo_existing=args.redo_existing,
                environment_class="docker",
                config_overrides=tuple(config_overrides),
                global_cost_limit=args.global_cost_limit,
                dry_run=args.dry_run,
            )
        except MinisweNotInstalledError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"argv={' '.join(result.argv)}")
        if result.returncode != 0 and not args.dry_run:
            print(
                f"warning: run exited {result.returncode}; "
                "converting whatever completed",
                file=sys.stderr,
            )

    if args.dry_run:
        print(f"dataset=SWE-bench_Verified matched_ids={len(VERIFIED_INSTANCE_IDS)}")
        return 0

    try:
        outcomes = read_outcomes(run_dir)
    except MinisweConvertError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    submitted = sum(1 for o in outcomes.values() if o.submitted)
    print(f"instances={len(outcomes)} submitted={submitted} empty={len(outcomes) - submitted}")

    relevant_tasks = [task for task in tasks if task.instance_id in VERIFIED_INSTANCE_IDS]
    try:
        records = build_records(
            {MODEL_SLUG: outcomes},
            relevant_tasks,
            tiers={MODEL_SLUG: "small"},
            run_id=args.run_id,
            scaffold_version=">=2,<3",
            require_complete=not args.allow_incomplete,
        )
    except MinisweConvertError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    records_path = write_generations(records, run_dir / "generations.jsonl")

    by_exit: dict[str, int] = {}
    for outcome in outcomes.values():
        key = outcome.exit_status or "unknown"
        by_exit[key] = by_exit.get(key, 0) + 1
    costs = [o.cost_usd for o in outcomes.values() if o.cost_usd is not None]

    manifest_path = write_run_manifest(
        run_dir / "manifest-verified-sanity.json",
        {
            "run_id": args.run_id,
            "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "git_commit": git_commit_sha(cwd=Path(__file__).resolve().parents[1]),
            "scaffold": "mini-swe-agent",
            "scaffold_version": _miniswe_version(),
            "leaderboard_reference": LEADERBOARD_REFERENCE,
            "miniswe_config_path": str(args.miniswe_config),
            "model_slug": MODEL_SLUG,
            "agent_model": AGENT_MODEL,
            "subset": "verified",
            "split": "test",
            "instance_ids": list(VERIFIED_INSTANCE_IDS),
            "global_cost_limit_usd": args.global_cost_limit,
            "workers": 1,
            "filter": filter_spec,
            "redo_existing": args.redo_existing,
            "convert_only": args.convert_only,
            "instances": len(outcomes),
            "instances_submitted": submitted,
            "instances_empty": len(outcomes) - submitted,
            "exit_status_counts": by_exit,
            "total_cost_usd": round(sum(costs), 6) if costs else None,
            "records_path": str(records_path),
            "instance_outcomes": [
                {
                    "instance_id": o.instance_id,
                    "exit_status": o.exit_status,
                    "cost_usd": o.cost_usd,
                    "api_calls": o.api_calls,
                    "patch_chars": len(o.model_patch or ""),
                }
                for o in sorted(outcomes.values(), key=lambda x: x.instance_id)
            ],
        },
    )
    print(f"manifest={manifest_path}")
    print(f"run_id={args.run_id} records={len(records)} path={records_path}")
    print(
        "next: python scripts/run_execution.py --config configs/execution_verified.yaml "
        f"--input {records_path} --output-dir {run_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
