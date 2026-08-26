"""Tests for the Stage-1 oracle context builder and prompt template."""

from __future__ import annotations

from pathlib import Path

import pytest
from git import Repo as GitRepo

from hecate.data import SwebenchTask
from hecate.scaffold import (
    PROMPT_VERSION,
    ContextBundle,
    ContextFile,
    build_context,
    load_context_method,
    load_oracle_files_uncapped,
    prompt_hash,
    render_prompt,
    write_prompt,
)

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


def test_load_oracle_files_uncapped_skips_prompt_caps(tmp_path: Path):
    task, cache_dir = _make_local_task(tmp_path)
    files = load_oracle_files_uncapped(task, cache_dir=cache_dir)
    assert [item.path for item in files] == ["pkg/mod.py", "pkg/new_mod.py"]
    assert files[0].content == "def base():\n    return 1\n"
    assert files[1].content == ""


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


# --- Prompt template (S6) -------------------------------------------------


def _sample_prompt_task(**overrides) -> SwebenchTask:
    base = dict(
        instance_id="django__django-12345",
        repo="django/django",
        base_commit="abc123def456",
        problem_statement="foo() raises KeyError when bar is missing.",
        patch="--- a/foo.py\n+++ b/foo.py\n@@\n-bad\n+good\n",
        test_patch=None,
        fail_to_pass=None,
        pass_to_pass=None,
    )
    base.update(overrides)
    return SwebenchTask(**base)


def _sample_prompt_context() -> ContextBundle:
    return ContextBundle(
        instance_id="django__django-12345",
        repo="django/django",
        base_commit="abc123def456",
        method="oracle",
        files=(
            ContextFile(path="foo.py", content="def foo():\n    return bar['missing']\n"),
            ContextFile(path="tests/test_foo.py", content="def test_foo():\n    assert foo()\n"),
        ),
    )


def test_render_prompt_contains_issue_and_file_context():
    task = _sample_prompt_task()
    context = _sample_prompt_context()

    prompt = render_prompt(task, context)

    assert prompt
    assert task.problem_statement in prompt
    assert task.repo in prompt
    assert task.instance_id in prompt
    assert "foo.py" in prompt
    assert "def foo():" in prompt
    assert "tests/test_foo.py" in prompt
    assert "unified diff" in prompt.lower()


def test_render_prompt_is_deterministic():
    task = _sample_prompt_task()
    context = _sample_prompt_context()

    first = render_prompt(task, context)
    second = render_prompt(task, context)

    assert first == second
    assert prompt_hash(first) == prompt_hash(second)


def test_render_prompt_does_not_leak_gold_patch():
    task = _sample_prompt_task()
    context = _sample_prompt_context()

    prompt = render_prompt(task, context)

    assert task.patch not in prompt


def test_render_prompt_empty_context_is_valid():
    task = _sample_prompt_task()
    context = ContextBundle(
        instance_id=task.instance_id,
        repo=task.repo,
        base_commit=task.base_commit,
        method="oracle",
        files=(),
    )

    prompt = render_prompt(task, context)

    assert task.problem_statement in prompt
    assert "unified diff" in prompt.lower()


def test_render_prompt_empty_problem_statement_is_deterministic():
    task = _sample_prompt_task(problem_statement="")
    context = _sample_prompt_context()

    first = render_prompt(task, context)
    second = render_prompt(task, context)

    assert first == second
    assert "## Issue" in first
    assert "unified diff" in first.lower()


def test_render_prompt_includes_diff_like_content_verbatim():
    task = _sample_prompt_task(patch="SECRET_GOLD_PATCH")
    context = ContextBundle(
        instance_id=task.instance_id,
        repo=task.repo,
        base_commit=task.base_commit,
        method="oracle",
        files=(
            ContextFile(
                path="foo.py",
                content="```\n--- a/foo.py\n+++ b/foo.py\n@@ diff-like @@\n",
            ),
        ),
    )

    prompt = render_prompt(task, context)

    assert "@@ diff-like @@" in prompt
    assert "```" in prompt
    assert task.patch not in prompt


def test_prompt_version_is_stable():
    assert PROMPT_VERSION == "v5"
    task = _sample_prompt_task()
    context = _sample_prompt_context()
    prompt = render_prompt(task, context, version=PROMPT_VERSION)
    assert "unified diff" in prompt.lower()
    assert "---/+++" in prompt or "---" in prompt
    assert "Example of a valid unified diff:" in prompt
    assert "@@ -1,3 +1,3 @@" in prompt
    with pytest.raises(ValueError, match="Unsupported prompt version"):
        render_prompt(task, context, version="v999")


def test_context_caps_truncate_large_files(tmp_path: Path):
    from hecate.scaffold.context import _apply_context_caps, ContextFile

    huge = "x" * 10_000
    files = (
        ContextFile(path="a.py", content=huge),
        ContextFile(path="b.py", content=huge),
    )
    capped = _apply_context_caps(
        files, max_file_chars=1_000, max_total_file_chars=1_500
    )
    assert len(capped[0].content) < len(huge)
    assert "truncated" in capped[0].content
    assert sum(len(f.content) for f in capped) <= 1_500 + 80  # placeholders


def test_prompt_hash_and_write_prompt(tmp_path: Path):
    prompt = "hello prompt"
    digest = prompt_hash(prompt)
    assert digest == prompt_hash(prompt)
    assert len(digest) == 64

    ref = write_prompt(prompt, output_dir=tmp_path)
    path = Path(ref)
    assert path.is_file()
    assert path.name == f"{digest}.txt"
    assert path.read_text(encoding="utf-8") == prompt


def test_real_lite_instance_prompt():
    """One real SWE-bench Lite instance: context + prompt (network required)."""
    from hecate.data.tasks import get_task

    task = get_task("psf__requests-1963")
    bundle = build_context(task.instance_id, method="oracle", task=task)
    prompt = render_prompt(task, bundle)

    assert prompt
    assert task.problem_statement in prompt
    assert "requests/sessions.py" in prompt
    assert task.patch not in prompt
    assert prompt_hash(prompt) == prompt_hash(render_prompt(task, bundle))
