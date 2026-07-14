"""Tests for the Stage-1 oracle context builder."""

from __future__ import annotations

from pathlib import Path

import pytest
from git import Repo as GitRepo

from hecate.data import SwebenchTask
from hecate.scaffold import ContextBundle, build_context, load_context_method

_SYNTHETIC_PATCH = """--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -1,2 +1,2 @@
 def base():
-    return 1
+    return 2
--- /dev/null
+++ b/pkg/new_mod.py
@@ -0,0 +1,2 @@
+def added():
+    return 3
"""


def _make_local_task(tmp_path: Path) -> tuple[SwebenchTask, Path]:
    """Build a throwaway git repo pre-seeded at the cache location build_context expects."""
    work_dir = tmp_path / "work"
    work_repo = GitRepo.init(work_dir)
    (work_dir / "pkg").mkdir()
    (work_dir / "pkg" / "mod.py").write_text("def base():\n    return 1\n")
    work_repo.index.add(["pkg/mod.py"])
    base_commit = work_repo.index.commit("base").hexsha

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    GitRepo.clone_from(str(work_dir), str(cache_dir / "acme__widget.git"), bare=True)

    task = SwebenchTask(
        instance_id="acme__widget-1",
        repo="acme/widget",
        base_commit=base_commit,
        problem_statement="widget is broken",
        patch=_SYNTHETIC_PATCH,
    )
    return task, cache_dir


def test_oracle_context_reads_base_commit_and_handles_added_files(tmp_path: Path):
    task, cache_dir = _make_local_task(tmp_path)

    bundle = build_context(
        task.instance_id, method="oracle", task=task, cache_dir=cache_dir
    )

    assert isinstance(bundle, ContextBundle)
    assert bundle.instance_id == task.instance_id
    assert bundle.repo == task.repo
    assert bundle.base_commit == task.base_commit
    assert bundle.method == "oracle"
    assert bundle.paths == ["pkg/mod.py", "pkg/new_mod.py"]

    modified, added = bundle.files
    # Pre-fix content at base_commit, not the gold fix ("return 2").
    assert modified.content == "def base():\n    return 1\n"
    # Added file doesn't exist at base_commit: empty content, not an error.
    assert added.content == ""


def test_oracle_context_is_deterministic(tmp_path: Path):
    task, cache_dir = _make_local_task(tmp_path)

    first = build_context(task.instance_id, method="oracle", task=task, cache_dir=cache_dir)
    second = build_context(task.instance_id, method="oracle", task=task, cache_dir=cache_dir)

    assert first == second


def test_bm25_is_explicitly_unimplemented():
    with pytest.raises(NotImplementedError):
        build_context("whatever-1", method="bm25")


def test_unknown_method_raises_value_error(tmp_path: Path):
    task, cache_dir = _make_local_task(tmp_path)
    with pytest.raises(ValueError):
        build_context(task.instance_id, method="not-a-method", task=task, cache_dir=cache_dir)  # type: ignore[arg-type]


def test_task_instance_id_mismatch_raises(tmp_path: Path):
    task, cache_dir = _make_local_task(tmp_path)
    with pytest.raises(ValueError):
        build_context("some-other-id", method="oracle", task=task, cache_dir=cache_dir)


def test_default_config_method_is_oracle():
    assert load_context_method() == "oracle"


def test_real_lite_instance_oracle_context():
    """One real SWE-bench Lite instance, end to end (network required)."""
    bundle = build_context("psf__requests-1963", method="oracle")

    assert bundle.instance_id == "psf__requests-1963"
    assert bundle.repo == "psf/requests"
    assert bundle.paths == ["requests/sessions.py"]
    assert "class Session" in bundle.files[0].content
