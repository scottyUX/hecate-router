"""Thin wrapper around mini-SWE-agent's SWE-bench single-instance runner.

This path does not use Hecate Stage-1 patch extraction. The agent issues bash
commands inside its own environment; do not mix resolve labels with Lite
single-shot generations.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


INSTALL_HINT = 'Install with: pip install -e ".[agent]"'


class MinisweNotInstalledError(ImportError):
    """Raised when the optional mini-swe-agent extra is missing."""


@dataclass(frozen=True)
class MinisweRunResult:
    """Outcome of a dry-run or live delegation to mini-extra."""

    argv: tuple[str, ...]
    dry_run: bool
    returncode: int


def require_miniswe() -> ModuleType:
    """Import ``minisweagent`` or raise an actionable install error."""
    try:
        import minisweagent
    except ImportError as exc:
        raise MinisweNotInstalledError(
            f"mini-swe-agent is not installed. {INSTALL_HINT}"
        ) from exc
    return minisweagent


def build_swebench_single_argv(
    *,
    instance: str,
    model: str,
    subset: str = "lite",
    split: str = "test",
    output: str | None = None,
    cost_limit: float | None = None,
    environment_class: str | None = None,
    exit_immediately: bool = True,
    mini_extra: str = "mini-extra",
) -> list[str]:
    """Build the ``mini-extra swebench-single`` argv (no subprocess)."""
    argv: list[str] = [
        mini_extra,
        "swebench-single",
        "--subset",
        subset,
        "--split",
        split,
        "--model",
        model,
        "--instance",
        instance,
    ]
    if output is not None:
        argv.extend(["--output", output])
    if cost_limit is not None:
        argv.extend(["--cost-limit", str(cost_limit)])
    if environment_class is not None:
        argv.extend(["--environment-class", environment_class])
    if exit_immediately:
        argv.append("--exit-immediately")
    return argv


def _resolve_mini_extra(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    # Prefer the console script installed alongside the running interpreter.
    # PATH may well lead to a mini-extra from a different virtualenv, which
    # would run the agent under a different Python than the caller's.
    sibling = Path(sys.executable).parent / "mini-extra"
    if sibling.is_file():
        return str(sibling)
    found = shutil.which("mini-extra")
    if found:
        return found
    # Fallback: run the console script via the active interpreter's scripts.
    return "mini-extra"


def run_swebench_single(
    *,
    instance: str,
    model: str,
    subset: str = "lite",
    split: str = "test",
    output: str | None = None,
    cost_limit: float | None = None,
    environment_class: str | None = None,
    exit_immediately: bool = True,
    dry_run: bool = False,
    mini_extra: str | None = None,
) -> MinisweRunResult:
    """Delegate one SWE-bench instance to mini-SWE-agent.

    Always calls :func:`require_miniswe` so missing installs fail closed with
    an actionable message. When ``dry_run`` is true, builds argv only.
    """
    require_miniswe()
    exe = _resolve_mini_extra(mini_extra)
    argv = build_swebench_single_argv(
        instance=instance,
        model=model,
        subset=subset,
        split=split,
        output=output,
        cost_limit=cost_limit,
        environment_class=environment_class,
        exit_immediately=exit_immediately,
        mini_extra=exe,
    )
    if dry_run:
        return MinisweRunResult(argv=tuple(argv), dry_run=True, returncode=0)

    completed = subprocess.run(argv, check=False)
    return MinisweRunResult(
        argv=tuple(argv),
        dry_run=False,
        returncode=int(completed.returncode),
    )


def load_miniswe_config(path: str) -> dict:
    """Load ``configs/miniswe.yaml`` (or override path)."""
    from pathlib import Path

    import yaml

    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}, got {type(data).__name__}")
    return data


def argv_from_config(
    config: dict,
    *,
    instance: str | None = None,
    model: str | None = None,
    subset: str | None = None,
    split: str | None = None,
    output: str | None = None,
    cost_limit: float | None = None,
    environment_class: str | None = None,
    exit_immediately: bool | None = None,
) -> list[str]:
    """Merge CLI overrides onto a loaded miniswe config and build argv."""
    scaffold = config.get("scaffold") or {}
    defaults = config.get("defaults") or {}

    resolved_instance = instance or defaults.get("instance") or "0"
    resolved_model = model or defaults.get("model")
    if not resolved_model:
        raise ValueError("model is required (pass --model or set defaults.model)")

    resolved_subset = subset or scaffold.get("subset") or "lite"
    resolved_split = split or scaffold.get("split") or "test"
    resolved_output = output if output is not None else defaults.get("output")
    resolved_cost = (
        cost_limit if cost_limit is not None else defaults.get("cost_limit")
    )
    resolved_env = (
        environment_class
        if environment_class is not None
        else defaults.get("environment_class")
    )
    resolved_exit = (
        exit_immediately
        if exit_immediately is not None
        else bool(defaults.get("exit_immediately", True))
    )

    return build_swebench_single_argv(
        instance=str(resolved_instance),
        model=str(resolved_model),
        subset=str(resolved_subset),
        split=str(resolved_split),
        output=str(resolved_output) if resolved_output else None,
        cost_limit=float(resolved_cost) if resolved_cost is not None else None,
        environment_class=str(resolved_env) if resolved_env else None,
        exit_immediately=resolved_exit,
    )


__all__ = [
    "INSTALL_HINT",
    "MinisweNotInstalledError",
    "MinisweRunResult",
    "argv_from_config",
    "build_swebench_single_argv",
    "load_miniswe_config",
    "require_miniswe",
    "run_swebench_single",
]
