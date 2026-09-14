"""Offline tests for fail-closed run-artifact copies."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from hecate.router.traj import TrajExample, TrajError, parse_arm, train_rows_for_arm
from hecate.router.traj_runner import load_traj_train_config, run_traj_train
from hecate.utils.artifacts import (
    ARTIFACTS_URI_ENV,
    ArtifactError,
    finalize_run_artifacts,
    resolve_artifacts_uri,
    run_dest_uri,
    sync_run_dir,
    verify_run_synced,
)


def _example(instance_id: str, *, repo: str, m1: bool, prefixes: tuple[str, ...]) -> TrajExample:
    return TrajExample(
        instance_id=instance_id,
        repo=repo,
        query=prefixes[0],
        prefixes=prefixes,
        truncated_at=tuple(False for _ in prefixes),
        n_turns=max(len(prefixes) - 1, 0),
        submitted_early=False,
        m1_resolves=m1,
        m2_resolves=True,
        traj_resolved=None,
    )


def test_lora_without_uri_is_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ARTIFACTS_URI_ENV, "")
    with pytest.raises(ArtifactError, match="must be set for --backend lora"):
        resolve_artifacts_uri(backend="lora")
    assert resolve_artifacts_uri(backend="lora", allow_unsynced=True) is None
    assert resolve_artifacts_uri(backend="scripted") is None


def test_sync_and_verify_file_dest(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "results.json").write_text("{}\n", encoding="utf-8")
    (run / "manifest.json").write_text(
        json.dumps({"run_id": "e2-armD-seed0"}) + "\n", encoding="utf-8"
    )
    ckpt = run / "checkpoints" / "k1-seed0-fold0"
    ckpt.mkdir(parents=True)
    (ckpt / "score.pt").write_bytes(b"x")
    (ckpt / "adapter").mkdir()
    (ckpt / "adapter" / "adapter_config.json").write_text("{}\n", encoding="utf-8")
    dest = finalize_run_artifacts(
        run, base_uri=str(tmp_path / "archive"), run_id="e2-armD-seed0"
    )
    assert Path(dest).is_dir()
    assert (Path(dest) / "results.json").is_file()
    assert (Path(dest) / "checkpoints" / "k1-seed0-fold0" / "score.pt").is_file()
    stamped = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert stamped["artifacts_uri"] == dest
    verify_run_synced(run, dest)
    with pytest.raises(ArtifactError, match="overwrite"):
        sync_run_dir(run, dest)


def test_verify_fails_when_remote_missing(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "results.json").write_text("{}\n", encoding="utf-8")
    (run / "manifest.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ArtifactError, match="not complete"):
        verify_run_synced(run, str(tmp_path / "missing"))


def test_run_dest_uri_rejects_nested_run_id() -> None:
    with pytest.raises(ArtifactError, match="single path segment"):
        run_dest_uri("/tmp/archive", "e2/armD")


def test_scripted_traj_run_copies_when_uri_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    examples = [
        _example(f"django/django-{i}", repo="django/django", m1=True, prefixes=(f"q {i}",))
        for i in range(3)
    ] + [
        _example(f"sympy/sympy-{i}", repo="sympy/sympy", m1=False, prefixes=(f"q {i}",))
        for i in range(3)
    ]
    scores = {ex.instance_id: 0.8 if ex.m1_resolves else 0.2 for ex in examples}
    yaml_path = tmp_path / "router_traj.yaml"
    yaml_path.write_text(yaml.safe_dump({"backbone": "x", "seeds": [0]}), encoding="utf-8")
    archive = tmp_path / "archive"
    monkeypatch.setenv(ARTIFACTS_URI_ENV, str(archive))
    config = load_traj_train_config(
        config_path=yaml_path,
        csv_path=tmp_path / "unused.csv",
        traj_dir=tmp_path / "trajs",
        output_dir=tmp_path / "out",
        run_id="e2-armB-seed0",
        split="leave-repo",
        hold_repo="django/django",
        arm="k0",
        provenance="s3",
        seeds=(0,),
        hold_only=True,
    )
    result = run_traj_train(
        config, backend="scripted", scripted_scores=scores, examples=examples
    )
    assert result.artifacts_uri is not None
    dest = Path(result.artifacts_uri)
    assert (dest / "results.json").is_file()
    assert (dest / "manifest.json").is_file()
    remote_manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    assert remote_manifest["artifacts_uri"] == result.artifacts_uri


def test_k1_packs_two_rows_k0_and_k3_unchanged() -> None:
    examples = [
        _example(
            "django/django-1",
            repo="django/django",
            m1=True,
            prefixes=("issue", "t1", "t2", "t3"),
        )
    ]
    assert len(train_rows_for_arm(examples, arm="k0")) == 1
    assert len(train_rows_for_arm(examples, arm="k1")) == 2
    assert len(train_rows_for_arm(examples, arm="k3")) == 4
    kind, spec = parse_arm("k1")
    assert kind == "k1"
    assert spec.eval_k == 1
    assert spec.pack_last == 1
    with pytest.raises(TrajError, match="unknown arm"):
        parse_arm("k2")
