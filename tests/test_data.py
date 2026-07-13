"""Tests for SWE-bench Lite loading and GenerationRecord round-trips."""

from __future__ import annotations

from pathlib import Path

from hecate.data import (
    GenerationRecord,
    append_jsonl,
    load_swebench_lite,
    read_jsonl,
)


def _sample_record(**overrides) -> GenerationRecord:
    base = dict(
        instance_id="django__django-12345",
        repo="django/django",
        base_commit="abc123def456",
        model_slug="qwen/qwen-2.5-7b-instruct",
        tier="small",
        prompt="Fix the bug in foo.py",
        prompt_hash="deadbeef",
        prompt_ref="prompts/deadbeef.txt",
        context_files=["foo.py", "tests/test_foo.py"],
        raw_response="```diff\n--- a/foo.py\n+++ b/foo.py\n```",
        extracted_patch="--- a/foo.py\n+++ b/foo.py\n",
        patch_parse_ok=True,
        prompt_tokens=128,
        completion_tokens=64,
        cost_usd=0.00123,
        decoding_params={"temperature": 0.0, "max_tokens": 4096},
        timestamp="2026-07-13T20:00:00Z",
        run_id="pilot-001",
        patch_applied=None,
        fail_to_pass=None,
        pass_to_pass=None,
    )
    base.update(overrides)
    return GenerationRecord(**base)


def test_generation_record_json_roundtrip():
    record = _sample_record()
    restored = GenerationRecord.from_json(record.to_json())
    assert restored == record


def test_generation_record_to_dict_includes_stage2_nulls():
    data = _sample_record().to_dict()
    assert "patch_applied" in data
    assert "fail_to_pass" in data
    assert "pass_to_pass" in data
    assert data["patch_applied"] is None
    assert data["fail_to_pass"] is None
    assert data["pass_to_pass"] is None


def test_generation_record_jsonl_roundtrip(tmp_path: Path):
    path = tmp_path / "outputs" / "records.jsonl"
    first = _sample_record(run_id="r1")
    second = _sample_record(
        run_id="r2",
        model_slug="meta-llama/llama-3-8b-instruct",
        tier="small",
        patch_applied=True,
        fail_to_pass=["tests/test_foo.py::test_a"],
        pass_to_pass=["tests/test_foo.py::test_b"],
    )

    append_jsonl(path, first)
    append_jsonl(path, second)
    restored = read_jsonl(path)

    assert restored == [first, second]


def test_load_swebench_lite_has_300_instances():
    tasks = load_swebench_lite()
    assert len(tasks) == 300

    first = tasks[0]
    assert first.instance_id
    assert first.repo
    assert first.base_commit
    assert first.problem_statement
    assert first.patch
