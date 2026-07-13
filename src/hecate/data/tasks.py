"""SWE-bench Lite task loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datasets import load_dataset

SWEBENCH_LITE_DATASET = "princeton-nlp/SWE-bench_Lite"
SWEBENCH_LITE_SPLIT = "test"
SWEBENCH_LITE_EXPECTED_COUNT = 300


def _default_cache_dir() -> Path:
    """Repo-local Hugging Face cache under data/raw/hf."""
    # src/hecate/data/tasks.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3] / "data" / "raw" / "hf"


@dataclass(frozen=True)
class SwebenchTask:
    """One SWE-bench Lite instance used as a Stage-1 task."""

    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    patch: str
    test_patch: str | None = None
    fail_to_pass: str | None = None
    pass_to_pass: str | None = None


def _row_to_task(row: dict) -> SwebenchTask:
    return SwebenchTask(
        instance_id=row["instance_id"],
        repo=row["repo"],
        base_commit=row["base_commit"],
        problem_statement=row["problem_statement"],
        patch=row["patch"],
        test_patch=row.get("test_patch"),
        fail_to_pass=row.get("FAIL_TO_PASS"),
        pass_to_pass=row.get("PASS_TO_PASS"),
    )


def load_swebench_lite(*, cache_dir: Path | str | None = None) -> list[SwebenchTask]:
    """Load all SWE-bench Lite test instances (expected: 300).

    Caches under ``data/raw/hf`` by default (gitignored via ``data/raw/``).
    """
    resolved_cache = Path(cache_dir) if cache_dir is not None else _default_cache_dir()
    resolved_cache.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(
        SWEBENCH_LITE_DATASET,
        split=SWEBENCH_LITE_SPLIT,
        cache_dir=str(resolved_cache),
    )
    tasks = [_row_to_task(row) for row in dataset]

    if len(tasks) != SWEBENCH_LITE_EXPECTED_COUNT:
        raise ValueError(
            f"Expected {SWEBENCH_LITE_EXPECTED_COUNT} SWE-bench Lite instances, "
            f"got {len(tasks)} from {SWEBENCH_LITE_DATASET} ({SWEBENCH_LITE_SPLIT})"
        )
    return tasks


def get_task(
    instance_id: str,
    *,
    tasks: list[SwebenchTask] | None = None,
    cache_dir: Path | str | None = None,
) -> SwebenchTask:
    """Return the task with ``instance_id``, loading Lite if ``tasks`` is omitted."""
    pool = tasks if tasks is not None else load_swebench_lite(cache_dir=cache_dir)
    for task in pool:
        if task.instance_id == instance_id:
            return task
    raise KeyError(f"No SWE-bench Lite task with instance_id={instance_id!r}")
