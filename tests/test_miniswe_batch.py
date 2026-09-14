"""Offline tests for the mini-SWE batch sweep and record conversion."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from hecate.agent.batch import build_swebench_batch_argv, run_swebench_batch
from hecate.agent.convert import (
    AgentOutcome,
    MinisweConvertError,
    build_records,
    read_outcomes,
    read_preds,
    write_generations,
)
from hecate.data.records import read_jsonl
from hecate.data.tasks import SwebenchTask
from hecate.execution.predictions import has_executable_patch


PATCH = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x\n+y\n"


def _arg(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def _task(instance_id: str, repo: str = "django/django") -> SwebenchTask:
    return SwebenchTask(
        instance_id=instance_id,
        repo=repo,
        base_commit="deadbeef",
        problem_statement="boom",
        patch="",
    )


def _write_output_dir(
    root: Path, rows: dict[str, str], *, info: dict | None = None
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    preds = {
        instance_id: {
            "model_name_or_path": "openrouter/qwen/qwen-2.5-7b-instruct",
            "instance_id": instance_id,
            "model_patch": patch_text,
        }
        for instance_id, patch_text in rows.items()
    }
    (root / "preds.json").write_text(json.dumps(preds), encoding="utf-8")
    for instance_id in rows:
        instance_dir = root / instance_id
        instance_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "info": info
            if info is not None
            else {
                "exit_status": "Submitted",
                "model_stats": {"instance_cost": 0.012, "api_calls": 7},
            },
            "messages": [{"role": "user", "content": "boom"}],
        }
        (instance_dir / f"{instance_id}.traj.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
    return root


def test_batch_argv_uses_swebench_subcommand_not_single() -> None:
    argv = build_swebench_batch_argv(
        model="openrouter/qwen/qwen-2.5-7b-instruct",
        output_dir="/tmp/out",
        workers=8,
    )
    assert argv[:2] == ["mini-extra", "swebench"]
    assert _arg(argv, "--workers") == "8"
    assert _arg(argv, "--output") == "/tmp/out"
    assert _arg(argv, "--subset") == "lite"
    # Upstream's default split is dev; Hecate always grades the test split.
    assert _arg(argv, "--split") == "test"


def test_batch_argv_optional_flags_are_omitted_by_default() -> None:
    argv = build_swebench_batch_argv(model="m", output_dir="/tmp/out")
    assert "--slice" not in argv
    assert "--filter" not in argv
    assert "--redo-existing" not in argv


def test_batch_argv_slice_and_overrides() -> None:
    argv = build_swebench_batch_argv(
        model="m",
        output_dir="/tmp/out",
        slice_spec="0:5",
        redo_existing=True,
        environment_class="docker",
        config_overrides=("swebench.yaml", "agent.cost_limit=0.25"),
    )
    assert _arg(argv, "--slice") == "0:5"
    assert "--redo-existing" in argv
    assert _arg(argv, "--environment-class") == "docker"
    assert argv.count("-c") == 2
    assert "agent.cost_limit=0.25" in argv


def test_run_batch_dry_run_does_not_shell_out(tmp_path: Path) -> None:
    with patch("hecate.agent.batch.require_miniswe"), patch(
        "hecate.agent.batch.subprocess.run"
    ) as run:
        result = run_swebench_batch(
            model="m", output_dir=tmp_path / "out", dry_run=True
        )
    run.assert_not_called()
    assert result.dry_run is True
    assert result.returncode == 0
    assert result.preds_path == tmp_path / "out" / "preds.json"


def test_read_preds_missing_file_is_actionable(tmp_path: Path) -> None:
    with pytest.raises(MinisweConvertError, match="missing"):
        read_preds(tmp_path)


def test_read_outcomes_pulls_traj_metadata(tmp_path: Path) -> None:
    _write_output_dir(tmp_path / "m", {"django__django-10914": PATCH})
    outcomes = read_outcomes(tmp_path / "m")
    outcome = outcomes["django__django-10914"]
    assert outcome.submitted is True
    assert outcome.exit_status == "Submitted"
    assert outcome.cost_usd == pytest.approx(0.012)
    assert outcome.api_calls == 7
    assert outcome.traj_path is not None


def test_empty_submission_is_not_executable(tmp_path: Path) -> None:
    """A step-limited agent submits ""; that must not read as a usable patch."""
    _write_output_dir(
        tmp_path / "m",
        {"django__django-10914": ""},
        info={"exit_status": "LimitsExceeded", "model_stats": {}},
    )
    outcomes = read_outcomes(tmp_path / "m")
    records = build_records(
        {"qwen/qwen-2.5-7b-instruct": outcomes},
        [_task("django__django-10914")],
        tiers={"qwen/qwen-2.5-7b-instruct": "small"},
    )
    assert records[0].patch_parse_ok is False
    assert has_executable_patch(records[0]) is False
    assert records[0].decoding_params["exit_status"] == "LimitsExceeded"


def test_build_records_emits_full_matrix(tmp_path: Path) -> None:
    tasks = [_task("django__django-10914"), _task("astropy__astropy-12907")]
    small = read_outcomes(
        _write_output_dir(
            tmp_path / "small",
            {"django__django-10914": PATCH, "astropy__astropy-12907": ""},
        )
    )
    large = read_outcomes(
        _write_output_dir(
            tmp_path / "large",
            {"django__django-10914": PATCH, "astropy__astropy-12907": PATCH},
        )
    )
    records = build_records(
        {"qwen/qwen-2.5-7b-instruct": small, "qwen/qwen-2.5-72b-instruct": large},
        tasks,
        tiers={
            "qwen/qwen-2.5-7b-instruct": "small",
            "qwen/qwen-2.5-72b-instruct": "large",
        },
        run_id="miniswe-smoke",
    )
    pairs = {(r.instance_id, r.model_slug) for r in records}
    assert len(pairs) == 4, "run_execution asserts a complete instance x model matrix"
    assert all(r.repo == "django/django" for r in records)
    assert all(r.base_commit == "deadbeef" for r in records)
    assert all(r.run_id == "miniswe-smoke" for r in records)


def test_build_records_rejects_missing_pair(tmp_path: Path) -> None:
    outcomes = read_outcomes(
        _write_output_dir(tmp_path / "m", {"django__django-10914": PATCH})
    )
    with pytest.raises(MinisweConvertError, match="absent from mini-SWE output"):
        build_records(
            {"qwen/qwen-2.5-7b-instruct": outcomes},
            [_task("django__django-10914"), _task("astropy__astropy-12907")],
            tiers={"qwen/qwen-2.5-7b-instruct": "small"},
        )


def test_build_records_allows_incomplete_when_asked(tmp_path: Path) -> None:
    outcomes = read_outcomes(
        _write_output_dir(tmp_path / "m", {"django__django-10914": PATCH})
    )
    records = build_records(
        {"qwen/qwen-2.5-7b-instruct": outcomes},
        [_task("django__django-10914"), _task("astropy__astropy-12907")],
        tiers={"qwen/qwen-2.5-7b-instruct": "small"},
        require_complete=False,
    )
    assert len(records) == 1


def test_build_records_requires_a_tier(tmp_path: Path) -> None:
    outcomes = read_outcomes(
        _write_output_dir(tmp_path / "m", {"django__django-10914": PATCH})
    )
    with pytest.raises(MinisweConvertError, match="no tier configured"):
        build_records(
            {"qwen/qwen-2.5-7b-instruct": outcomes},
            [_task("django__django-10914")],
            tiers={},
        )


def test_written_generations_round_trip(tmp_path: Path) -> None:
    outcomes = read_outcomes(
        _write_output_dir(tmp_path / "m", {"django__django-10914": PATCH})
    )
    records = build_records(
        {"qwen/qwen-2.5-7b-instruct": outcomes},
        [_task("django__django-10914")],
        tiers={"qwen/qwen-2.5-7b-instruct": "small"},
    )
    path = write_generations(records, tmp_path / "generations.jsonl")
    reloaded = read_jsonl(path)
    assert len(reloaded) == 1
    assert reloaded[0].extracted_patch == PATCH
    assert has_executable_patch(reloaded[0]) is True


def test_agent_records_carry_no_prompt_or_raw_response(tmp_path: Path) -> None:
    """The agent read the repo itself; there is no Stage-1 prompt to record."""
    outcomes = read_outcomes(
        _write_output_dir(tmp_path / "m", {"django__django-10914": PATCH})
    )
    record = build_records(
        {"qwen/qwen-2.5-7b-instruct": outcomes},
        [_task("django__django-10914")],
        tiers={"qwen/qwen-2.5-7b-instruct": "small"},
    )[0]
    assert record.prompt is None
    assert record.raw_response is None
    assert record.context_files == []
    assert record.decoding_params["scaffold"] == "mini-swe-agent"


def test_outcome_submitted_ignores_whitespace_only_patch() -> None:
    assert AgentOutcome(instance_id="i", model_patch="   \n").submitted is False
