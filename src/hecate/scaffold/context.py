"""Stage-1 context builder: oracle file selection from the gold patch.

Oracle context uses the gold patch only to decide *which* files belong in
the prompt (localization), not to give the model the fix itself. File
contents are always read at ``base_commit`` — the pre-fix tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import unidiff
import yaml
from git import GitCommandError
from git import Repo as GitRepo

from hecate.data.tasks import SwebenchTask, get_task

ContextMethod = Literal["oracle", "bm25"]

DEFAULT_CONTEXT_METHOD: ContextMethod = "oracle"

# Caps keep oracle prompts inside small-model context windows (~32k tokens).
DEFAULT_MAX_FILE_CHARS = 24_000
DEFAULT_MAX_TOTAL_FILE_CHARS = 48_000

# SWE-bench's own GitHub mirror of task repos, pinned so base_commit history
# is always available even if the upstream repo rewrites it.
SWEBENCH_MIRROR_ORG = "swe-bench-repos"


def _repo_root() -> Path:
    # src/hecate/scaffold/context.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3]


def _default_config_path() -> Path:
    return _repo_root() / "configs" / "option_a.yaml"


def _default_cache_dir() -> Path:
    """Repo-local cache of bare clones under data/cache (gitignored)."""
    return _repo_root() / "data" / "cache" / "repos"


@dataclass(frozen=True)
class ContextFile:
    """One file's contents as loaded at a task's base_commit."""

    path: str
    content: str


@dataclass(frozen=True)
class ContextBundle:
    """Deterministic file context for one SWE-bench Lite task.

    Identical for every model in a run — only ``model_slug`` may vary in
    generation (see GenerationRecord).
    """

    instance_id: str
    repo: str
    base_commit: str
    method: str
    files: tuple[ContextFile, ...]

    @property
    def paths(self) -> list[str]:
        """Ordered file paths, suitable for ``GenerationRecord.context_files``."""
        return [file.path for file in self.files]


def load_context_method(config_path: Path | str | None = None) -> str:
    """Read ``context.method`` from the option config (default: oracle)."""
    path = Path(config_path) if config_path is not None else _default_config_path()
    if not path.is_file():
        return DEFAULT_CONTEXT_METHOD
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data.get("context", {}).get("method", DEFAULT_CONTEXT_METHOD)


def load_context_limits(
    config_path: Path | str | None = None,
) -> tuple[int, int]:
    """Return ``(max_file_chars, max_total_file_chars)`` from Option A config."""
    path = Path(config_path) if config_path is not None else _default_config_path()
    max_file = DEFAULT_MAX_FILE_CHARS
    max_total = DEFAULT_MAX_TOTAL_FILE_CHARS
    if path.is_file():
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        ctx = data.get("context", {}) or {}
        max_file = int(ctx.get("max_file_chars", max_file))
        max_total = int(ctx.get("max_total_file_chars", max_total))
    if max_file < 1 or max_total < 1:
        raise ValueError("context max_*_chars must be >= 1")
    return max_file, max_total


def _truncate_text(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    omitted = len(content) - limit
    # Keep a stable head prefix so truncation is deterministic.
    return content[:limit] + f"\n\n... [truncated {omitted} chars] ...\n"


def _apply_context_caps(
    files: tuple[ContextFile, ...],
    *,
    max_file_chars: int,
    max_total_file_chars: int,
) -> tuple[ContextFile, ...]:
    """Deterministically truncate file contents to per-file and total budgets."""
    capped: list[ContextFile] = []
    used = 0
    for context_file in files:
        remaining_total = max_total_file_chars - used
        if remaining_total <= 0:
            omitted = len(context_file.content)
            placeholder = (
                f"... [omitted: over total context budget; {omitted} chars] ...\n"
                if omitted
                else ""
            )
            capped.append(ContextFile(path=context_file.path, content=placeholder))
            continue
        per_file_limit = min(max_file_chars, remaining_total)
        content = _truncate_text(context_file.content, per_file_limit)
        capped.append(ContextFile(path=context_file.path, content=content))
        used += len(content)
    return tuple(capped)


def _oracle_file_specs(patch_text: str) -> list[tuple[str, bool]]:
    """Ordered, deduped (path, is_added) pairs for files touched by a gold patch."""
    seen: dict[str, bool] = {}
    for patch_file in unidiff.PatchSet(patch_text):
        if patch_file.path not in seen:
            seen[patch_file.path] = patch_file.is_added_file
    return list(seen.items())


def _clone_url(repo: str) -> str:
    return f"https://github.com/{SWEBENCH_MIRROR_ORG}/{repo.replace('/', '__')}.git"


def _bare_repo_dir(repo: str, cache_dir: Path) -> Path:
    return cache_dir / f"{repo.replace('/', '__')}.git"


def _ensure_repo_clone(repo: str, cache_dir: Path) -> Path:
    """Return a local bare clone of ``repo``, cloning it on first use."""
    repo_dir = _bare_repo_dir(repo, cache_dir)
    if not repo_dir.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        GitRepo.clone_from(_clone_url(repo), str(repo_dir), bare=True)
    return repo_dir


def _read_file_at_commit(repo_dir: Path, commit: str, path: str) -> str:
    git_repo = GitRepo(str(repo_dir))
    try:
        # strip_newline_in_stdout=False: preserve the file's exact trailing
        # newline (GitPython strips it by default).
        return git_repo.git.show(f"{commit}:{path}", strip_newline_in_stdout=False)
    except GitCommandError as exc:
        raise FileNotFoundError(f"{path!r} not found at {commit} in {repo_dir}") from exc


def _build_oracle_context(
    task: SwebenchTask,
    cache_dir: Path,
    *,
    config_path: Path | str | None = None,
) -> ContextBundle:
    repo_dir = _ensure_repo_clone(task.repo, cache_dir)
    files = tuple(
        ContextFile(
            path=path,
            content="" if is_added else _read_file_at_commit(repo_dir, task.base_commit, path),
        )
        for path, is_added in _oracle_file_specs(task.patch)
    )
    max_file, max_total = load_context_limits(config_path)
    files = _apply_context_caps(
        files, max_file_chars=max_file, max_total_file_chars=max_total
    )
    return ContextBundle(
        instance_id=task.instance_id,
        repo=task.repo,
        base_commit=task.base_commit,
        method="oracle",
        files=files,
    )


def build_context(
    instance_id: str,
    *,
    method: ContextMethod | None = None,
    task: SwebenchTask | None = None,
    tasks: list[SwebenchTask] | None = None,
    config_path: Path | str | None = None,
    cache_dir: Path | str | None = None,
) -> ContextBundle:
    """Deterministic file context for one task.

    Method comes from ``method`` if given, else ``context.method`` in
    ``configs/option_a.yaml``. Stage 1 implements ``oracle`` only; ``bm25``
    is accepted for forward compatibility and raises ``NotImplementedError``.

    Same instance_id + same method + same code/config always yields the
    same paths and contents.
    """
    resolved_method = method if method is not None else load_context_method(config_path)

    if resolved_method == "bm25":
        raise NotImplementedError(
            "BM25 context retrieval is not implemented yet — Stage 1 ships "
            "oracle only. Track the BM25 follow-up issue before using this method."
        )
    if resolved_method != "oracle":
        raise ValueError(f"Unknown context method: {resolved_method!r}")

    resolved_task = task if task is not None else get_task(instance_id, tasks=tasks)
    if resolved_task.instance_id != instance_id:
        raise ValueError(
            f"task.instance_id {resolved_task.instance_id!r} does not match "
            f"requested instance_id {instance_id!r}"
        )

    resolved_cache_dir = Path(cache_dir) if cache_dir is not None else _default_cache_dir()
    return _build_oracle_context(
        resolved_task, resolved_cache_dir, config_path=config_path
    )
