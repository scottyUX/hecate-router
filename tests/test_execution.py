"""Offline tests for Stage-2 execution and Stage-3 labels."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hecate.data import GenerationRecord, append_jsonl, read_jsonl
from hecate.execution import (
    ScriptedHarness,
    ScriptedOutcome,
    apply_report,
    build_labels,
    has_executable_patch,
    load_execution_config,
    load_instance_report,
    run_execution,
    to_prediction,
    write_predictions,
)

QWEN_7B = "qwen/qwen-2.5-7b-instruct"
QWEN_72B = "qwen/qwen-2.5-72b-instruct"
VALID_PATCH = """\
--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -1,2 +1,2 @@
 def base():
-    return 1
+    return 2
"""


def _record(**overrides) -> GenerationRecord:
    base = dict(
        instance_id="django__django-12345",
        repo="django/django",
        base_commit="abc123",
        model_slug=QWEN_7B,
        tier="small",
        prompt="fix it",
        prompt_hash="hash-a",
        extracted_patch=VALID_PATCH,
        patch_parse_ok=True,
        run_id="sweep-2x300-qwen",
    )
    base.update(overrides)
    return GenerationRecord(**base)


def _write_generations(path: Path, records: list[GenerationRecord]) -> None:
    for record in records:
        append_jsonl(path, record)


def test_has_executable_patch_rejects_parse_failures() -> None:
    assert has_executable_patch(_record()) is True
    assert has_executable_patch(_record(patch_parse_ok=False, extracted_patch=None)) is False
    assert has_executable_patch(_record(extracted_patch="   ")) is False
    assert has_executable_patch(_record(extracted_patch=None, patch_parse_ok=True)) is False


def test_to_prediction_and_write_predictions(tmp_path: Path) -> None:
    good = _record()
    bad = _record(instance_id="other-1", patch_parse_ok=False, extracted_patch=None)
    pred = to_prediction(good)
    assert pred["instance_id"] == good.instance_id
    assert pred["model_name_or_path"] == QWEN_7B
    assert pred["model_patch"] == VALID_PATCH

    path = tmp_path / "preds.jsonl"
    write_predictions([good, bad], path)
    lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    assert len(lines) == 1
    assert lines[0]["instance_id"] == good.instance_id


def test_apply_report_maps_swebench_fields() -> None:
    record = _record()
    report = {
        "patch_successfully_applied": True,
        "resolved": True,
        "tests_status": {
            "FAIL_TO_PASS": {"success": ["t1"], "failure": ["t2"]},
            "PASS_TO_PASS": {"success": ["t3"], "failure": []},
        },
    }
    filled = apply_report(record, report)
    assert filled.patch_applied is True
    assert filled.resolved is True
    assert filled.fail_to_pass == ["t1"]
    assert filled.pass_to_pass == ["t3"]
    assert record.patch_applied is None


def test_apply_report_unwraps_instance_id_key() -> None:
    record = _record()
    wrapped = {
        record.instance_id: {
            "patch_successfully_applied": False,
            "resolved": False,
        }
    }
    filled = apply_report(record, wrapped)
    assert filled.patch_applied is False
    assert filled.resolved is False
    assert filled.fail_to_pass == []
    assert filled.pass_to_pass == []


def test_load_instance_report_missing(tmp_path: Path) -> None:
    assert load_instance_report(tmp_path, QWEN_7B, "missing") is None


def test_run_execution_scripted_harness_and_immutable_input(tmp_path: Path) -> None:
    generations = tmp_path / "generations.jsonl"
    valid = _record()
    invalid = _record(
        model_slug=QWEN_72B,
        tier="large",
        patch_parse_ok=False,
        extracted_patch=None,
        prompt_hash="hash-a",
    )
    _write_generations(generations, [valid, invalid])
    original = generations.read_bytes()

    harness = ScriptedHarness(
        {
            (valid.instance_id, QWEN_7B): ScriptedOutcome(
                patch_successfully_applied=True,
                resolved=True,
                fail_to_pass=("tests/test_a.py::test_x",),
                pass_to_pass=("tests/test_b.py::test_y",),
            )
        }
    )
    out = tmp_path / "exec"
    config = load_execution_config(
        input_path=generations,
        output_dir=out,
        run_id="exec-test",
        tasks=1,
        dry_run=False,
    )
    result = run_execution(config, harness=harness)

    assert generations.read_bytes() == original
    assert result.pairs_attempted == 2
    assert result.pairs_skipped_no_patch == 1
    assert result.pairs_evaluated == 1
    assert result.pairs_resolved == 1
    assert result.pairs_pending == 0

    written = read_jsonl(result.records_path)
    by_slug = {row.model_slug: row for row in written}
    assert by_slug[QWEN_7B].resolved is True
    assert by_slug[QWEN_7B].fail_to_pass == ["tests/test_a.py::test_x"]
    assert by_slug[QWEN_72B].patch_applied is False
    assert by_slug[QWEN_72B].resolved is False
    assert (out / "manifest.json").is_file()
    assert harness.calls and harness.calls[0].report_dir == out


def test_run_execution_dry_run_skips_harness(tmp_path: Path) -> None:
    generations = tmp_path / "generations.jsonl"
    _write_generations(
        generations,
        [
            _record(),
            _record(model_slug=QWEN_72B, tier="large"),
        ],
    )
    harness = ScriptedHarness()
    config = load_execution_config(
        input_path=generations,
        output_dir=tmp_path / "exec",
        run_id="dry",
        tasks=1,
        dry_run=True,
    )
    result = run_execution(config, harness=harness)
    assert harness.calls == []
    assert not result.records_path.is_file()
    payload = json.loads(result.manifest_path.read_text())
    assert payload["dry_run"] is True


def test_incomplete_matrix_fails_closed(tmp_path: Path) -> None:
    generations = tmp_path / "generations.jsonl"
    _write_generations(generations, [_record()])
    config = load_execution_config(
        input_path=generations,
        output_dir=tmp_path / "exec",
        tasks=1,
    )
    with pytest.raises(ValueError, match="Incomplete generation matrix"):
        run_execution(config, harness=ScriptedHarness())


def test_resume_skips_finished_pairs(tmp_path: Path) -> None:
    generations = tmp_path / "generations.jsonl"
    small = _record()
    large = _record(model_slug=QWEN_72B, tier="large")
    _write_generations(generations, [small, large])
    out = tmp_path / "exec"

    first = ScriptedHarness(
        {
            (small.instance_id, QWEN_7B): ScriptedOutcome(
                patch_successfully_applied=True, resolved=False
            ),
            (large.instance_id, QWEN_72B): ScriptedOutcome(
                patch_successfully_applied=True, resolved=True
            ),
        }
    )
    config = load_execution_config(
        input_path=generations,
        output_dir=out,
        run_id="resume",
        tasks=1,
    )
    run_execution(config, harness=first)
    assert len(first.calls) == 2

    second = ScriptedHarness()
    again = run_execution(config, harness=second)
    assert again.pairs_skipped_resume == 2
    assert second.calls == []


def test_missing_report_stays_pending(tmp_path: Path) -> None:
    generations = tmp_path / "generations.jsonl"
    small = _record()
    large = _record(model_slug=QWEN_72B, tier="large")
    _write_generations(generations, [small, large])
    harness = ScriptedHarness(
        {
            (small.instance_id, QWEN_7B): ScriptedOutcome(omit_report=True),
            (large.instance_id, QWEN_72B): ScriptedOutcome(
                patch_successfully_applied=True, resolved=False
            ),
        }
    )
    config = load_execution_config(
        input_path=generations,
        output_dir=tmp_path / "exec",
        run_id="pending",
        tasks=1,
    )
    result = run_execution(config, harness=harness)
    assert result.pairs_pending == 1
    assert result.pairs_evaluated == 1
    written = read_jsonl(result.records_path)
    assert {row.model_slug for row in written} == {QWEN_72B}


def test_harness_error_ids_recorded_as_not_applied(tmp_path: Path) -> None:
    generations = tmp_path / "generations.jsonl"
    small = _record()
    large = _record(model_slug=QWEN_72B, tier="large")
    _write_generations(generations, [small, large])
    harness = ScriptedHarness(
        {
            (small.instance_id, QWEN_7B): ScriptedOutcome(harness_error=True),
            (large.instance_id, QWEN_72B): ScriptedOutcome(
                patch_successfully_applied=True, resolved=False
            ),
        }
    )
    config = load_execution_config(
        input_path=generations,
        output_dir=tmp_path / "exec",
        run_id="apply-err",
        tasks=1,
    )
    result = run_execution(config, harness=harness)
    assert result.pairs_pending == 0
    assert result.pairs_evaluated == 2
    written = {row.model_slug: row for row in read_jsonl(result.records_path)}
    assert written[QWEN_7B].patch_applied is False
    assert written[QWEN_7B].resolved is False
    assert written[QWEN_72B].patch_applied is True


def test_build_labels_preflight_and_scaffold(tmp_path: Path) -> None:
    records = [
        _record(
            instance_id="t-both",
            resolved=True,
            patch_applied=True,
            prompt_hash="same",
        ),
        _record(
            instance_id="t-both",
            model_slug=QWEN_72B,
            tier="large",
            resolved=True,
            patch_applied=True,
            prompt_hash="same",
        ),
        _record(
            instance_id="t-only-m2",
            resolved=False,
            patch_applied=True,
            prompt_hash="same",
        ),
        _record(
            instance_id="t-only-m2",
            model_slug=QWEN_72B,
            tier="large",
            resolved=True,
            patch_applied=True,
            prompt_hash="same",
        ),
        _record(
            instance_id="t-mismatch",
            resolved=False,
            patch_applied=False,
            prompt_hash="left",
        ),
        _record(
            instance_id="t-mismatch",
            model_slug=QWEN_72B,
            tier="large",
            resolved=False,
            patch_applied=False,
            prompt_hash="right",
        ),
        _record(instance_id="t-incomplete", resolved=False),
    ]
    labels, preflight = build_labels(
        records, m1_slug=QWEN_7B, m2_slug=QWEN_72B, positive_rate_threshold=0.5
    )
    assert len(labels) == 3
    by_id = {row.instance_id: row for row in labels}
    assert by_id["t-both"].complementarity == "both"
    assert by_id["t-only-m2"].complementarity == "only_m2"
    assert by_id["t-only-m2"].m1_resolves is False
    assert preflight["incomplete_instance_ids"] == ["t-incomplete"]
    assert preflight["n_tasks"] == 3
    assert preflight["complementarity"]["both"] == 1
    assert preflight["complementarity"]["only_m2"] == 1
    assert preflight["complementarity"]["neither"] == 1
    assert preflight["m1_resolve_rate"] == pytest.approx(1 / 3)
    assert preflight["m2_resolve_rate"] == pytest.approx(2 / 3)
    assert preflight["oracle_routing_resolve_rate"] == pytest.approx(2 / 3)
    assert preflight["routing_headroom"] == pytest.approx(0.0)
    assert preflight["shared_scaffold"]["ok"] is False
    assert "t-mismatch" in preflight["shared_scaffold"]["mismatched_instance_ids"]
    assert preflight["m1_positive_rate_flag"] is True


def test_parse_fail_is_not_m1_positive() -> None:
    records = [
        _record(resolved=False, patch_applied=False, patch_parse_ok=False),
        _record(
            model_slug=QWEN_72B,
            tier="large",
            resolved=True,
            patch_applied=True,
        ),
    ]
    labels, _preflight = build_labels(records, m1_slug=QWEN_7B, m2_slug=QWEN_72B)
    assert labels[0].m1_resolves is False
    assert labels[0].complementarity == "only_m2"


@pytest.mark.live_eval
def test_live_eval_gated() -> None:
    if os.getenv("RUN_LIVE_EVAL") != "1":
        pytest.skip("live eval requires RUN_LIVE_EVAL=1")
    try:
        import docker
    except ImportError:
        pytest.skip("docker Python package not installed")
    try:
        docker.from_env().ping()
    except Exception:
        pytest.skip("Docker daemon not available")
    # Presence of the gold CLI entry is enough for the gated smoke to be wired.
    from swebench.harness.run_evaluation import main as _main

    assert callable(_main)
