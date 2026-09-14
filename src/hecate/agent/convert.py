"""Convert mini-SWE-agent batch output into Hecate generation records.

The agent path produces its patch with ``git diff`` inside the container, so
there is no Stage-1 extraction step here. ``patch_parse_ok`` still carries the
signal :func:`hecate.execution.predictions.has_executable_patch` reads: it is
true when the agent actually submitted a non-empty patch, false when it
submitted nothing (step/cost limit hit, crash, or a missing submit command).

A record is emitted for every requested (instance, model) pair, including the
empty submissions, because ``run_execution`` asserts a complete matrix before
evaluating and counts patch-less pairs as ``no_patch`` rather than dropping
them silently.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from hecate.agent.batch import PREDS_FILENAME
from hecate.data import GenerationRecord
from hecate.data.tasks import SwebenchTask


class MinisweConvertError(RuntimeError):
    """Raised when mini-SWE output cannot be mapped onto the record schema."""


@dataclass(frozen=True)
class AgentOutcome:
    """One instance's result read back off a mini-SWE batch output dir."""

    instance_id: str
    model_patch: str
    exit_status: str | None = None
    cost_usd: float | None = None
    api_calls: int | None = None
    traj_path: Path | None = None

    @property
    def submitted(self) -> bool:
        return bool(self.model_patch and self.model_patch.strip())


def read_preds(output_dir: Path | str) -> dict[str, str]:
    """Read ``preds.json`` into ``{instance_id: model_patch}``."""
    path = Path(output_dir) / PREDS_FILENAME
    if not path.exists():
        raise MinisweConvertError(f"missing {path} (did the batch run produce output?)")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise MinisweConvertError(f"expected a JSON object in {path}")
    return {
        str(instance_id): str((row or {}).get("model_patch") or "")
        for instance_id, row in payload.items()
    }


def _read_traj(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def read_outcomes(output_dir: Path | str) -> dict[str, AgentOutcome]:
    """Read every instance's patch plus its trajectory metadata."""
    root = Path(output_dir)
    outcomes: dict[str, AgentOutcome] = {}
    for instance_id, patch in read_preds(root).items():
        traj_path = root / instance_id / f"{instance_id}.traj.json"
        info = _read_traj(traj_path).get("info", {}) if traj_path.exists() else {}
        stats = info.get("model_stats") or {}
        outcomes[instance_id] = AgentOutcome(
            instance_id=instance_id,
            model_patch=patch,
            exit_status=info.get("exit_status") or None,
            cost_usd=stats.get("instance_cost"),
            api_calls=stats.get("api_calls"),
            traj_path=traj_path if traj_path.exists() else None,
        )
    return outcomes


def outcome_to_record(
    outcome: AgentOutcome,
    task: SwebenchTask,
    *,
    model_slug: str,
    tier: str,
    run_id: str | None = None,
    scaffold: str = "mini-swe-agent",
    scaffold_version: str | None = None,
) -> GenerationRecord:
    """Map one agent outcome onto the canonical generation record schema."""
    return GenerationRecord(
        instance_id=outcome.instance_id,
        repo=task.repo,
        base_commit=task.base_commit,
        model_slug=model_slug,
        tier=tier,  # type: ignore[arg-type]
        # The agent read the repo itself; there is no single prompt string and
        # no oracle context file list to record on this path.
        prompt=None,
        context_files=[],
        raw_response=None,
        extracted_patch=outcome.model_patch or None,
        patch_parse_ok=outcome.submitted,
        cost_usd=outcome.cost_usd,
        completion_tokens=None,
        decoding_params={
            "scaffold": scaffold,
            "scaffold_version": scaffold_version,
            "exit_status": outcome.exit_status,
            "api_calls": outcome.api_calls,
            "traj_path": str(outcome.traj_path) if outcome.traj_path else None,
        },
        run_id=run_id,
    )


def build_records(
    outcomes_by_model: Mapping[str, Mapping[str, AgentOutcome]],
    tasks: Iterable[SwebenchTask],
    *,
    tiers: Mapping[str, str],
    run_id: str | None = None,
    scaffold_version: str | None = None,
    require_complete: bool = True,
) -> list[GenerationRecord]:
    """Build the full (instance x model) record matrix.

    ``outcomes_by_model`` maps a model slug to that model's outcomes, i.e. one
    entry per mini-SWE output directory. With ``require_complete`` set, every
    task must be present for every model, matching what ``run_execution``
    asserts before it evaluates.
    """
    task_by_id = {task.instance_id: task for task in tasks}
    records: list[GenerationRecord] = []
    missing: list[str] = []

    for model_slug, outcomes in outcomes_by_model.items():
        tier = tiers.get(model_slug)
        if tier is None:
            raise MinisweConvertError(f"no tier configured for model {model_slug}")
        unknown = sorted(set(outcomes) - set(task_by_id))
        if unknown:
            raise MinisweConvertError(
                f"{model_slug}: {len(unknown)} instance ids absent from the dataset: "
                f"{unknown[:5]}"
            )
        for instance_id, task in task_by_id.items():
            outcome = outcomes.get(instance_id)
            if outcome is None:
                missing.append(f"{instance_id} x {model_slug}")
                continue
            records.append(
                outcome_to_record(
                    outcome,
                    task,
                    model_slug=model_slug,
                    tier=tier,
                    run_id=run_id,
                    scaffold_version=scaffold_version,
                )
            )

    if missing and require_complete:
        raise MinisweConvertError(
            f"{len(missing)} pair(s) absent from mini-SWE output: {missing[:5]}"
        )
    return records


def write_generations(
    records: Iterable[GenerationRecord], path: Path | str
) -> Path:
    """Write records as ``generations.jsonl`` (overwrites, not appends)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.to_json())
            handle.write("\n")
    return target


__all__ = [
    "AgentOutcome",
    "MinisweConvertError",
    "build_records",
    "outcome_to_record",
    "read_outcomes",
    "read_preds",
    "write_generations",
]
