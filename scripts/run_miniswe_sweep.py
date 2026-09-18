#!/usr/bin/env python3
"""Run the agent-scaffold sweep: N models x 300 SWE-bench Lite tasks.

Mirrors scripts/run_sweep.py, but the patch comes from mini-SWE-agent running
bash in a container instead of Stage-1 prose extraction. Output is the same
generations.jsonl, so scripts/run_execution.py grades both paths identically.

Usage:
    python scripts/run_miniswe_sweep.py --dry-run
    python scripts/run_miniswe_sweep.py --tasks 1            # smoke
    python scripts/run_miniswe_sweep.py --workers 8          # full 2 x 300
    python scripts/run_miniswe_sweep.py --convert-only       # re-merge existing output

Each model gets its own mini-SWE output directory because upstream's preds.json
is keyed by instance_id alone and would otherwise collide across models.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# Measured reference (data/output/runs/sweep-2x300-qwen, parser path, 600
# samples): $0.567 total -- $0.00162/instance for 72b, $0.00027/instance for 7b.
# The agent path resends its history every step so it costs strictly more, but
# the multiplier is unmeasured on this scaffold. This cap is a bound, not an
# estimate: 600 x $0.10 = $60 worst case, inside option_a.yaml's $100 ceiling.
DEFAULT_COST_LIMIT_USD = 0.10
DEFAULT_COST_LIMIT_LARGE_USD = 0.50

# mini-SWE passes no timeout to litellm, so a provider request that never
# responds blocks its worker indefinitely (observed: one 72B request open 11+
# minutes with zero retry warnings, because tenacity only fires on an
# exception). The longest legitimate response measured here was 229s, so the
# timeout must sit well above that to avoid killing slow-but-live calls.
DEFAULT_REQUEST_TIMEOUT_S = 300.0
DEFAULT_WALL_TIME_LIMIT_S = 2700.0


def _slug_to_dirname(slug: str) -> str:
    return slug.replace("/", "__")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hecate mini-SWE-agent sweep runner")
    parser.add_argument(
        "--config",
        default="configs/option_a.yaml",
        help="Model/tier config (shared with the Stage-1 sweep)",
    )
    parser.add_argument(
        "--miniswe-config",
        default="configs/miniswe.yaml",
        help="Agent scaffold config",
    )
    parser.add_argument(
        "--output-dir",
        default="data/outputs/runs/miniswe-2x300-qwen",
        help="Run directory: per-model agent output plus merged generations.jsonl",
    )
    parser.add_argument("--run-id", default="miniswe-2x300-qwen")
    parser.add_argument(
        "--tasks",
        type=int,
        default=None,
        help="Limit to the first N instances (smoke); default: all 300",
    )
    parser.add_argument(
        "--workers", type=int, default=1, help="Parallel agent workers per model"
    )
    parser.add_argument(
        "--model",
        action="append",
        default=None,
        help="Model slug to run (repeatable); default: every model in --config",
    )
    parser.add_argument(
        "--cost-limit",
        type=float,
        default=DEFAULT_COST_LIMIT_USD,
        help=(
            "Per-instance USD cap. Default is deliberately far below "
            "miniswe.yaml's inherited 3.00: the whole 600-sample single-shot "
            "sweep cost $0.57 total, so a $3 per-instance cap bounds nothing."
        ),
    )
    parser.add_argument(
        "--cost-limit-large",
        type=float,
        default=DEFAULT_COST_LIMIT_LARGE_USD,
        help=(
            "Per-instance USD cap for tier=large models. The large tier costs "
            "~15x the small tier per instance, so one shared cap either "
            "truncates the large arm or lets the small arm loop unchecked."
        ),
    )
    parser.add_argument(
        "--global-cost-limit",
        type=float,
        default=None,
        help=(
            "Hard ceiling on TOTAL spend per model, via MSWEA_GLOBAL_COST_LIMIT. "
            "Per-instance caps do not bound a sweep: 300 tasks x $1 is $300. "
            "Upstream raises once cumulative spend crosses this. Applied per "
            "model process, so the sweep's ceiling is this x number of models."
        ),
    )
    parser.add_argument(
        "--step-limit",
        type=int,
        default=None,
        help="Per-instance agent step cap (default: upstream swebench.yaml)",
    )
    parser.add_argument(
        "--redo-existing",
        action="store_true",
        help="Re-run instances already present in preds.json",
    )
    parser.add_argument(
        "--convert-only",
        action="store_true",
        help="Skip the agent runs; just merge existing output into generations.jsonl",
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Convert even when some (instance, model) pairs are missing",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=DEFAULT_REQUEST_TIMEOUT_S,
        help=(
            "Per-request timeout in seconds, passed to litellm. mini-SWE sets "
            "none, so a stalled provider request blocks its worker forever; a "
            "timeout turns that into a retry (upstream retries 10x with "
            "exponential backoff). 0 disables."
        ),
    )
    parser.add_argument(
        "--wall-time-limit",
        type=float,
        default=DEFAULT_WALL_TIME_LIMIT_S,
        help=(
            "Per-instance wall-clock cap in seconds (agent.wall_time_limit_seconds). "
            "Backstop so one pathological instance cannot stall a sweep. 0 disables."
        ),
    )
    parser.add_argument(
        "--filter",
        dest="filter_spec",
        default=None,
        help=(
            "Regex over instance ids, passed to mini-extra --filter. Use it to "
            "sample across repos; --tasks alone slices 0:N, and SWE-bench Lite "
            "is ordered by repo, so a small --tasks draws from one repo only."
        ),
    )
    parser.add_argument(
        "--platform",
        default=None,
        help=(
            "Docker --platform for the agent container, e.g. linux/amd64 to "
            "emulate the x86-only SWE-bench images on an arm64 Mac. Leave "
            "unset on the x86 exec VM."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Print argv only")
    args = parser.parse_args(argv)

    import yaml

    from hecate.agent.batch import run_swebench_batch
    from hecate.agent.convert import (
        MinisweConvertError,
        build_records,
        read_outcomes,
        write_generations,
    )
    from hecate.agent.miniswe import MinisweNotInstalledError, load_miniswe_config
    from hecate.data.tasks import load_swebench_lite
    from hecate.utils.env import load_env

    load_env()

    option_a = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    configured = {
        str(entry["slug"]): str(entry.get("tier") or "small")
        for entry in (option_a.get("models") or [])
    }
    slugs = args.model or list(configured)
    unknown = [slug for slug in slugs if slug not in configured]
    if unknown:
        print(f"error: models absent from {args.config}: {unknown}", file=sys.stderr)
        return 2

    miniswe = load_miniswe_config(args.miniswe_config)
    scaffold = miniswe.get("scaffold") or {}
    defaults = miniswe.get("defaults") or {}
    subset = str(scaffold.get("subset") or "lite")
    split = str(scaffold.get("split") or "test")
    environment_class = defaults.get("environment_class") or "docker"
    cost_limit = (
        args.cost_limit
        if args.cost_limit is not None
        else defaults.get("cost_limit")
    )

    # Upstream drops its default config as soon as any -c is passed, so the
    # benchmark config has to be named explicitly alongside any override.
    # The benchmark config is swebench.yaml for every SWE-bench subset; the
    # subset is selected with --subset, not by a per-subset config file.
    overrides: list[str] = []
    extra_run_args = ["--rm"] + (["--platform", args.platform] if args.platform else [])
    if (
        cost_limit is not None
        or args.step_limit is not None
        or args.platform
        or args.request_timeout
        or args.wall_time_limit
    ):
        overrides.append("swebench.yaml")
        if cost_limit is not None:
            overrides.append(f"agent.cost_limit={cost_limit}")
        if args.step_limit is not None:
            overrides.append(f"agent.step_limit={args.step_limit}")
        if args.wall_time_limit:
            overrides.append(
                f"agent.wall_time_limit_seconds={int(args.wall_time_limit)}"
            )
        if args.request_timeout:
            overrides.append(f"model.model_kwargs.timeout={args.request_timeout}")
        if args.platform:
            # SWE-bench images are linux/x86_64 only; on an arm64 host docker
            # needs the platform stated explicitly to emulate them.
            overrides.append(f"environment.run_args={json.dumps(extra_run_args)}")

    slice_spec = f"0:{args.tasks}" if args.tasks else None
    run_dir = Path(args.output_dir)

    # mini-SWE reports litellm-style slugs; option_a.yaml holds the bare slug.
    def _agent_model(slug: str) -> str:
        prefix = str(defaults.get("model") or "")
        provider = prefix.split("/", 1)[0] if "/" in prefix else "openrouter"
        return f"{provider}/{slug}"

    outcomes_by_model = {}
    for slug in slugs:
        model_dir = run_dir / _slug_to_dirname(slug)
        tier_cost_limit = (
            args.cost_limit_large
            if configured.get(slug) == "large"
            else cost_limit
        )
        model_overrides = [
            f"agent.cost_limit={tier_cost_limit}"
            if o.startswith("agent.cost_limit=")
            else o
            for o in overrides
        ]
        if not args.convert_only:
            try:
                result = run_swebench_batch(
                    model=_agent_model(slug),
                    output_dir=model_dir,
                    subset=subset,
                    split=split,
                    workers=args.workers,
                    slice_spec=slice_spec,
                    filter_spec=args.filter_spec,
                    redo_existing=args.redo_existing,
                    environment_class=environment_class,
                    config_overrides=tuple(model_overrides),
                    global_cost_limit=args.global_cost_limit,
                    dry_run=args.dry_run,
                )
            except MinisweNotInstalledError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            print(f"[{slug}] argv={' '.join(result.argv)}")
            if args.dry_run:
                continue
            if result.returncode != 0:
                print(
                    f"warning: {slug} exited {result.returncode}; "
                    "converting whatever completed",
                    file=sys.stderr,
                )
        try:
            outcomes_by_model[slug] = read_outcomes(model_dir)
        except MinisweConvertError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        submitted = sum(1 for o in outcomes_by_model[slug].values() if o.submitted)
        print(
            f"[{slug}] instances={len(outcomes_by_model[slug])} "
            f"submitted={submitted} empty={len(outcomes_by_model[slug]) - submitted}"
        )

    if args.dry_run:
        return 0

    tasks = load_swebench_lite()
    if args.tasks:
        tasks = tasks[: args.tasks]

    try:
        records = build_records(
            outcomes_by_model,
            tasks,
            tiers=configured,
            run_id=args.run_id,
            scaffold_version=str(scaffold.get("version_range") or ""),
            require_complete=not args.allow_incomplete,
        )
    except MinisweConvertError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    records_path = write_generations(records, run_dir / "generations.jsonl")
    print(f"run_id={args.run_id} records={len(records)} path={records_path}")
    print(
        "next: python scripts/run_execution.py "
        f"--input {records_path} --output-dir {run_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
