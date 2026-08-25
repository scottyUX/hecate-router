"""SWE-bench task loading (Lite and Verified)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datasets import load_dataset

SWEBENCH_LITE_DATASET = "princeton-nlp/SWE-bench_Lite"
SWEBENCH_LITE_SPLIT = "test"
SWEBENCH_LITE_EXPECTED_COUNT = 300
SWEBENCH_VERIFIED_DATASET = "princeton-nlp/SWE-bench_Verified"
SWEBENCH_VERIFIED_SPLIT = "test"
SWEBENCH_VERIFIED_EXPECTED_COUNT = 500


def _default_cache_dir() -> Path:
    """Repo-local Hugging Face cache under data/raw/hf."""
    # src/hecate/data/tasks.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3] / "data" / "raw" / "hf"


@dataclass(frozen=True)
class SwebenchTask:
    """One SWE-bench instance (Lite or Verified)."""

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


def _load_swebench_split(
    dataset: str,
    split: str,
    expected_count: int,
    *,
    cache_dir: Path | str | None = None,
) -> list[SwebenchTask]:
    resolved_cache = Path(cache_dir) if cache_dir is not None else _default_cache_dir()
    resolved_cache.mkdir(parents=True, exist_ok=True)
    hf_dataset = load_dataset(dataset, split=split, cache_dir=str(resolved_cache))
    tasks = [_row_to_task(row) for row in hf_dataset]
    if len(tasks) != expected_count:
        raise ValueError(
            f"Expected {expected_count} instances, got {len(tasks)} from {dataset} ({split})"
        )
    return tasks


def load_swebench_lite(*, cache_dir: Path | str | None = None) -> list[SwebenchTask]:
    """Load all SWE-bench Lite test instances (expected: 300).

    Caches under ``data/raw/hf`` by default (gitignored via ``data/raw/``).
    """
    return _load_swebench_split(
        SWEBENCH_LITE_DATASET,
        SWEBENCH_LITE_SPLIT,
        SWEBENCH_LITE_EXPECTED_COUNT,
        cache_dir=cache_dir,
    )


def load_swebench_verified(*, cache_dir: Path | str | None = None) -> list[SwebenchTask]:
    """Load all SWE-bench Verified test instances (expected: 500).

    Caches under ``data/raw/hf`` by default (gitignored via ``data/raw/``).
    """
    return _load_swebench_split(
        SWEBENCH_VERIFIED_DATASET,
        SWEBENCH_VERIFIED_SPLIT,
        SWEBENCH_VERIFIED_EXPECTED_COUNT,
        cache_dir=cache_dir,
    )


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
