"""Batch delegation to ``mini-extra swebench`` (parallel agent sweep).

Upstream owns the worker pool, the resume logic, and the per-instance output
layout. This module only builds the argv and shells out, mirroring
:mod:`hecate.agent.miniswe` for the single-instance path.

Upstream writes, under ``--output``:

    <output>/preds.json                       # {instance_id: {model_patch, ...}}
    <output>/<instance_id>/<instance_id>.traj.json

``preds.json`` is keyed by ``instance_id`` alone, with no model dimension, so a
sweep over several models must give each model its own output directory.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from hecate.agent.miniswe import _resolve_mini_extra, require_miniswe


PREDS_FILENAME = "preds.json"


@dataclass(frozen=True)
class MinisweBatchResult:
    """Outcome of a dry-run or live delegation to ``mini-extra swebench``."""

    argv: tuple[str, ...]
    output_dir: Path
    dry_run: bool
    returncode: int

    @property
    def preds_path(self) -> Path:
        return self.output_dir / PREDS_FILENAME


def build_swebench_batch_argv(
    *,
    model: str,
    output_dir: str | Path,
    subset: str = "lite",
    split: str = "test",
    workers: int = 1,
    slice_spec: str | None = None,
    filter_spec: str | None = None,
    redo_existing: bool = False,
    environment_class: str | None = None,
    config_overrides: tuple[str, ...] | list[str] = (),
    mini_extra: str = "mini-extra",
) -> list[str]:
    """Build the ``mini-extra swebench`` argv (no subprocess).

    ``config_overrides`` are passed through as repeated ``-c`` values. Upstream
    drops its default config file as soon as any ``-c`` is given, so the caller
    must include the benchmark config itself (e.g. ``swebench.yaml``) whenever
    it overrides a key such as ``agent.cost_limit``.
    """
    argv: list[str] = [
        mini_extra,
        "swebench",
        "--subset",
        subset,
        "--split",
        split,
        "--model",
        model,
        "--output",
        str(output_dir),
        "--workers",
        str(workers),
    ]
    if slice_spec is not None:
        argv.extend(["--slice", slice_spec])
    if filter_spec is not None:
        argv.extend(["--filter", filter_spec])
    if redo_existing:
        argv.append("--redo-existing")
    if environment_class is not None:
        argv.extend(["--environment-class", environment_class])
    for override in config_overrides:
        argv.extend(["-c", override])
    return argv


def run_swebench_batch(
    *,
    model: str,
    output_dir: str | Path,
    subset: str = "lite",
    split: str = "test",
    workers: int = 1,
    slice_spec: str | None = None,
    filter_spec: str | None = None,
    redo_existing: bool = False,
    environment_class: str | None = None,
    config_overrides: tuple[str, ...] | list[str] = (),
    dry_run: bool = False,
    mini_extra: str | None = None,
) -> MinisweBatchResult:
    """Delegate a batch of SWE-bench instances to mini-SWE-agent.

    Always calls :func:`require_miniswe` so a missing install fails closed with
    an actionable message. When ``dry_run`` is true, builds argv only.
    """
    require_miniswe()
    target = Path(output_dir)
    exe = _resolve_mini_extra(mini_extra)
    argv = build_swebench_batch_argv(
        model=model,
        output_dir=target,
        subset=subset,
        split=split,
        workers=workers,
        slice_spec=slice_spec,
        filter_spec=filter_spec,
        redo_existing=redo_existing,
        environment_class=environment_class,
        config_overrides=config_overrides,
        mini_extra=exe,
    )
    if dry_run:
        return MinisweBatchResult(
            argv=tuple(argv), output_dir=target, dry_run=True, returncode=0
        )

    target.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(argv, check=False)
    return MinisweBatchResult(
        argv=tuple(argv),
        output_dir=target,
        dry_run=False,
        returncode=int(completed.returncode),
    )


__all__ = [
    "PREDS_FILENAME",
    "MinisweBatchResult",
    "build_swebench_batch_argv",
    "run_swebench_batch",
]
