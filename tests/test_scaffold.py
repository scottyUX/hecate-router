"""Tests for the Stage-1 prompt template."""

from __future__ import annotations

from hecate.data.tasks import SwebenchTask
from hecate.scaffold import (
    PROMPT_VERSION,
    ContextBundle,
    ContextFile,
    prompt_hash,
    render_prompt,
)


def _sample_task(**overrides) -> SwebenchTask:
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


def _sample_context() -> ContextBundle:
    return ContextBundle(
        files=[
            ContextFile(path="foo.py", content="def foo():\n    return bar['missing']\n"),
            ContextFile(path="tests/test_foo.py", content="def test_foo():\n    assert foo()\n"),
        ]
    )


def test_render_prompt_contains_issue_and_file_context():
    task = _sample_task()
    context = _sample_context()

    prompt = render_prompt(task, context)

    assert prompt
    assert task.problem_statement in prompt
    assert "foo.py" in prompt
    assert "def foo():" in prompt
    assert "tests/test_foo.py" in prompt
    assert "def test_foo():" in prompt
    assert task.repo in prompt


def test_render_prompt_is_deterministic():
    task = _sample_task()
    context = _sample_context()

    first = render_prompt(task, context)
    second = render_prompt(task, context)

    assert first == second
    assert prompt_hash(first) == prompt_hash(second)


def test_render_prompt_does_not_leak_gold_patch():
    task = _sample_task()
    context = _sample_context()

    prompt = render_prompt(task, context)

    assert task.patch not in prompt


def test_prompt_version_is_stable():
    assert PROMPT_VERSION == "v1"