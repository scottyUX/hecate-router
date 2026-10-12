#!/usr/bin/env python3
"""Pre-spend check: does r2's resolved config match the leaderboard's? (spec 018)

For each model, resolves the config mini-extra would run with (config file
plus the runner's -c overrides, --model and --model-class, merged the way
upstream merges them), serializes it the way a trajectory records
``info.config``, and diffs it field by field against
configs/leaderboard_reference/<entry>.json.

Only differences listed in ALLOWED (each with its reason) pass; anything else
fails. Offline: no model call, no Docker.

Usage:
    python scripts/check_leaderboard_config.py                 # r2
    python scripts/check_leaderboard_config.py --experiment r1 # expected to fail
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Dotted-path prefix -> why r2 may differ from the leaderboard there.
ALLOWED: dict[str, str] = {
    "model_type": "OpenRouter model class instead of a direct-API LitellmModel",
    "model.model_name": "OpenRouter slug instead of the provider's direct model id",
    "model.litellm_model_registry": "field exists only on LitellmModel's config",
    "model.model_kwargs.reasoning_effort": "litellm's param; r2 sends OpenRouter's equivalent",
    "model.model_kwargs.reasoning": "OpenRouter's reasoning param, effort=high as on the leaderboard",
    "model.model_kwargs.provider": "pins OpenRouter to the provider(s) the leaderboard used",
}


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_three_model", ROOT / "scripts" / "run_three_model.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["run_three_model"] = module
    spec.loader.exec_module(module)
    return module


def flatten(d: object, prefix: str = "") -> dict[str, object]:
    if isinstance(d, dict) and d:
        out: dict[str, object] = {}
        for k, v in d.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
        return out
    return {prefix: d}


def resolved_trajectory_config(overrides: list[str], agent_model: str, model_class: str | None, image: str) -> dict:
    """What a trajectory's info.config would hold for this run."""
    from minisweagent.agents.default import AgentConfig
    from minisweagent.config import get_config_from_spec
    from minisweagent.environments import get_environment_class
    from minisweagent.environments.docker import DockerEnvironmentConfig
    from minisweagent.models import get_model
    from minisweagent.utils.serialize import UNSET, recursive_merge

    # Same merge as minisweagent.run.benchmarks.swebench.main.
    configs = [get_config_from_spec(s) for s in overrides]
    configs.append({
        "environment": {"environment_class": "docker"},
        "model": {"model_name": agent_model, "model_class": model_class or UNSET},
    })
    config = recursive_merge(*configs)
    model = get_model(config=config["model"])
    env = {k: v for k, v in config["environment"].items() if k != "environment_class"}
    env_class = get_environment_class(config["environment"]["environment_class"])
    return {
        "agent": AgentConfig(**config["agent"]).model_dump(mode="json"),
        # The swebench batch runner always uses this agent class.
        "agent_type": "minisweagent.run.benchmarks.swebench.ProgressTrackingAgent",
        **model.serialize()["info"]["config"],
        "environment": DockerEnvironmentConfig(**env, image=image).model_dump(mode="json"),
        "environment_type": f"{env_class.__module__}.{env_class.__name__}",
    }


def diff(ours: dict, reference: dict) -> list[tuple[str, object, object]]:
    a, b = flatten(ours), flatten(reference)
    return [
        (k, a.get(k, "<absent>"), b.get(k, "<absent>"))
        for k in sorted(set(a) | set(b))
        if a.get(k, "<absent>") != b.get(k, "<absent>")
    ]


def allowed_reason(path: str) -> str | None:
    for prefix, reason in ALLOWED.items():
        if path == prefix or path.startswith(prefix + "."):
            return reason
    return None


def check(experiment_key: str) -> int:
    run = _load_runner()
    experiment = run.EXPERIMENTS[experiment_key]
    failed = False
    for key in ("opus", "gemini", "minimax"):
        spec = experiment.models[key]
        reference_spec = spec if spec.leaderboard_entry else run.R2_MODELS[key]
        ref_path = ROOT / run.reference_config_path(reference_spec)
        reference = json.loads(ref_path.read_text())["config"]
        ours = resolved_trajectory_config(
            run.config_overrides_for(spec, ROOT / experiment.config),
            spec.agent_model,
            spec.model_class,
            reference["environment"]["image"],
        )
        print(f"== {key} vs {reference_spec.leaderboard_entry}")
        for path, mine, theirs in diff(ours, reference):
            reason = allowed_reason(path)
            failed |= reason is None
            tag = "ok  " if reason else "FAIL"
            print(f"  {tag} {path}: ours={mine!r:.70} leaderboard={theirs!r:.70}")
            if reason:
                print(f"       ({reason})")
    print("RESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--experiment", default="r2", choices=("r1", "r2"))
    args = parser.parse_args(argv)
    return check(args.experiment)


if __name__ == "__main__":
    sys.exit(main())
