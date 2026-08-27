"""Offline tests for the v3 trajectory router (no torch / no 7B)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from hecate.data.external_miniswe import JoinedLabel
from hecate.router.dataset import WhitespaceTokenizer
from hecate.router.splits import LEAVE_REPO
from hecate.router.traj import (
    TrajError,
    TrajExample,
    build_traj_examples,
    eval_examples,
    format_prefix,
    match_traj_labels,
    packed_prefixes,
    parse_trajectory,
    second_holdout_repo,
    train_rows_for_arm,
    truncation_report,
)
from hecate.router.traj_runner import load_traj_train_config, run_traj_train


def _label(instance_id: str, *, small: bool, large: bool = True, repo: str | None = None) -> JoinedLabel:
    from hecate.data.external_miniswe import parse_repo

    return JoinedLabel(
        instance_id=instance_id,
        repo=repo if repo is not None else parse_repo(instance_id),
        small_model_resolved=small,
        large_model_resolved=large,
    )


def _messages_traj(
    instance_id: str,
    *,
    query: str,
    turns: list[tuple[str, str]],
    resolved: bool | None = None,
) -> dict:
    messages = [
        {"role": "system", "content": "you are an agent"},
        {"role": "user", "content": query},
    ]
    for assistant, obs in turns:
        messages.append({"role": "assistant", "content": assistant})
        if obs is not None:
            messages.append({"role": "user", "content": obs})
    payload: dict = {
        "instance_id": instance_id,
        "messages": messages,
    }
    if resolved is not None:
        payload["info"] = {"resolved": resolved}
    return payload


def _example(
    instance_id: str,
    *,
    repo: str,
    m1: bool,
    prefixes: tuple[str, ...],
    n_turns: int = 3,
    truncated: tuple[bool, ...] | None = None,
) -> TrajExample:
    flags = truncated if truncated is not None else tuple(False for _ in prefixes)
    return TrajExample(
        instance_id=instance_id,
        repo=repo,
        query=prefixes[0],
        prefixes=prefixes,
        truncated_at=flags,
        n_turns=n_turns,
        submitted_early=n_turns < 3,
        m1_resolves=m1,
        m2_resolves=True,
    )


def test_parse_user_observation_boundaries_and_early_submit() -> None:
    full = parse_trajectory(
        _messages_traj(
            "django__django-1",
            query="fix the form",
            turns=[
                ("ls", "file.py"),
                ("cat file.py", "def f():\n    pass"),
                ("edit", "ok"),
                ("tests", "fail"),
            ],
        )
    )
    assert full.n_turns == 4
    assert full.query == "fix the form"
    assert full.turns[0].observation == "file.py"
    assert full.submitted_early is False
    texts, flags = packed_prefixes(full, k_max=4)
    assert len(texts) == 5
    assert texts[0] == "fix the form"
    assert "Turn 3" in texts[3]
    assert flags == (False, False, False, False, False)
    assert "Turn 4" in format_prefix(full, 4)

    early = parse_trajectory(
        {
            "instance_id": "django__django-2",
            "messages": [
                {"role": "user", "content": "tiny bug"},
                {"role": "assistant", "content": "patch then submit"},
            ],
        }
    )
    assert early.n_turns == 1
    assert early.submitted_early is True
    prefixes, _ = packed_prefixes(early, k_max=4)
    assert len(prefixes) == 2
    assert prefixes[0] == "tiny bug"


def test_hf_nested_trajectory_and_truncation_flag() -> None:
    payload = {
        "instance_id": "sympy__sympy-9",
        "trajectory": json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "issue text here"},
                    {"role": "assistant", "content": "search"},
                    {"role": "user", "content": "hits"},
                    {"role": "assistant", "content": "edit"},
                    {"role": "user", "content": "ok"},
                    {"role": "assistant", "content": "submit"},
                ]
            }
        ),
    }
    parsed = parse_trajectory(payload)
    assert parsed.instance_id == "sympy__sympy-9"
    assert parsed.n_turns == 3
    tok = WhitespaceTokenizer()
    texts, flags = packed_prefixes(parsed, k_max=3, tokenizer=tok, max_tokens=2)
    assert texts[0] == "issue text"
    assert flags[0] is True
    assert flags[-1] is True


def test_label_match_fail_closed_on_id_and_resolve_bit() -> None:
    parsed = {
        "django__django-1": parse_trajectory(
            _messages_traj(
                "django__django-1",
                query="q",
                turns=[("a", "o")],
                resolved=True,
            )
        )
    }
    ok = match_traj_labels(
        parsed,
        [_label("django__django-1", small=True)],
        provenance="hf",
    )
    assert ok.n_matched == 1
    ok.raise_if_failed()

    missing = match_traj_labels(
        parsed,
        [_label("django__django-1", small=True), _label("django__django-2", small=False)],
        provenance="hf",
    )
    with pytest.raises(TrajError, match="instance_id sets"):
        missing.raise_if_failed()

    mismatch = match_traj_labels(
        parsed,
        [_label("django__django-1", small=False)],
        provenance="hf",
    )
    with pytest.raises(TrajError, match="resolved bits disagree"):
        mismatch.raise_if_failed()


def test_build_examples_and_k0_vs_packed_k3_rows() -> None:
    labels = [_label("django__django-1", small=True)]
    parsed = {
        "django__django-1": parse_trajectory(
            _messages_traj(
                "django__django-1",
                query="issue",
                turns=[("t1", "o1"), ("t2", "o2"), ("t3", "o3")],
            )
        )
    }
    examples, report, counts = build_traj_examples(
        parsed, labels, provenance="s3"
    )
    assert report.n_matched == 1
    assert counts["n_examples"] == 1
    k0 = train_rows_for_arm(examples, arm="k0")
    k3 = train_rows_for_arm(examples, arm="k3")
    assert len(k0) == 1
    assert k0[0][0] == "issue"
    assert len(k3) == 4
    assert eval_examples(examples, k=0)[0].text == "issue"
    assert "Turn 3" in eval_examples(examples, k=3)[0].text


def test_truncation_report_and_second_holdout_from_histogram() -> None:
    examples = [
        _example(
            f"django/django-{i}",
            repo="django/django",
            m1=True,
            prefixes=("short",),
        )
        for i in range(3)
    ] + [
        _example(
            f"sympy/sympy-{i}",
            repo="sympy/sympy",
            m1=False,
            prefixes=("one two three four five six",),
        )
        for i in range(5)
    ]
    report = truncation_report(examples, k=3, max_tokens=4)
    assert report["n"] == 8
    assert report["n_truncated"] == 5
    assert report["truncation_rate"] == pytest.approx(0.625)
    assert second_holdout_repo(examples, "django/django") == "sympy/sympy"
    with pytest.raises(TrajError, match="no remaining"):
        second_holdout_repo(examples[:3], "django/django")


def test_run_traj_train_leave_repo_scripted(tmp_path: Path) -> None:
    examples: list[TrajExample] = []
    scores: dict[str, float] = {}
    for i in range(4):
        iid = f"django/django-{i}"
        examples.append(
            _example(iid, repo="django/django", m1=True, prefixes=(f"q {iid}", f"t {iid}"))
        )
        scores[iid] = 0.9
    for i in range(4):
        iid = f"sympy/sympy-{i}"
        examples.append(
            _example(iid, repo="sympy/sympy", m1=False, prefixes=(f"q {iid}", f"t {iid}"))
        )
        scores[iid] = 0.1
    yaml_path = tmp_path / "router_traj.yaml"
    yaml_path.write_text(
        yaml.safe_dump({"backbone": "Qwen/Qwen2.5-Coder-7B-Instruct", "seeds": [0]}),
        encoding="utf-8",
    )
    config = load_traj_train_config(
        config_path=yaml_path,
        csv_path=tmp_path / "unused.csv",
        traj_dir=tmp_path / "trajs",
        output_dir=tmp_path / "ldo",
        run_id="traj-ldo",
        split="leave-repo",
        hold_repo="django/django",
        arm="k3",
        provenance="hf",
    )
    config = config.__class__(**{**config.__dict__, "seeds": (0,)})
    result = run_traj_train(
        config, backend="scripted", scripted_scores=scores, examples=examples
    )
    payload = json.loads(result.results_path.read_text(encoding="utf-8"))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert payload["split_primary"] == "leave_repo"
    assert payload["arm_key"] == "k3"
    assert payload["k_eval"] == 3
    assert payload["trace_provenance"] == "hf"
    assert payload["second_holdout_repo"] == "sympy/sympy"
    dirs = payload["directions"]["scripted"]
    assert set(dirs) == {"hold_django", "hold_rest"}
    assert dirs["hold_django"]["n_hold"] == 4
    assert manifest["paper_deviation"].startswith("No 3-way")
    assert "K=0 is a separately trained" in result.readme_path.read_text(encoding="utf-8")
    assert result.split_strategy == "leave_repo"
    for row in payload["primary_folds"]["scripted"]:
        if row["direction"] == "hold_django":
            assert row["hold_repos"] == ["django/django"]
            assert row["split"] == LEAVE_REPO


def test_run_traj_train_k0_grouped_scripted(tmp_path: Path) -> None:
    examples: list[TrajExample] = []
    scores: dict[str, float] = {}
    for repo, n, m1 in (("aa/aa", 4, True), ("bb/bb", 4, False), ("cc/cc", 4, True)):
        for i in range(n):
            iid = f"{repo}-{i}"
            examples.append(
                _example(iid, repo=repo, m1=m1, prefixes=(f"q {iid}", f"t {iid}"))
            )
            scores[iid] = 0.9 if m1 else 0.1
    yaml_path = tmp_path / "router_traj.yaml"
    yaml_path.write_text("backbone: x\n", encoding="utf-8")
    config = load_traj_train_config(
        config_path=yaml_path,
        csv_path=tmp_path / "unused.csv",
        traj_dir=tmp_path / "trajs",
        output_dir=tmp_path / "grp",
        run_id="traj-grp",
        arm="k0",
        provenance="s3",
    )
    config = config.__class__(**{**config.__dict__, "n_folds": 2, "seeds": (0,)})
    result = run_traj_train(
        config, backend="scripted", scripted_scores=scores, examples=examples
    )
    payload = json.loads(result.results_path.read_text(encoding="utf-8"))
    assert payload["split_primary"] == "grouped_repo"
    assert payload["k_eval"] == 0
    assert payload["arm_key"] == "k0"
    assert "scripted" in payload["primary"]
    assert (tmp_path / "grp" / "truncation.json").is_file()


def test_parse_traj_dir_jsonl_and_duplicate_ids(tmp_path: Path) -> None:
    from hecate.router.traj import parse_traj_dir

    path = tmp_path / "full.jsonl"
    rows = [
        _messages_traj("django__django-1", query="a", turns=[("x", "y")]),
        _messages_traj("django__django-1", query="b", turns=[("x", "y")]),
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    with pytest.raises(TrajError, match="duplicate"):
        parse_traj_dir(path)
    unique = tmp_path / "one.jsonl"
    unique.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    stub = tmp_path / "dir"
    stub.mkdir()
    (stub / "full.jsonl").write_text(unique.read_text(encoding="utf-8"), encoding="utf-8")
    (stub / "provenance.json").write_text('{"provenance": "hf"}\n', encoding="utf-8")
    assert set(parse_traj_dir(stub)) == {"django__django-1"}
