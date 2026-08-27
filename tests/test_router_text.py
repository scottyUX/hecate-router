"""Offline tests for the text-only Verified router (no torch / no HF)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hecate.data.external_miniswe import JoinedLabelWithText
from hecate.router.dataset import RouterExample, WhitespaceTokenizer, build_examples_from_text
from hecate.router.metrics import (
    auroc,
    route_metrics,
    sweep_lambda_curve,
    text_route_metrics,
)
from hecate.router.splits import (
    GROUPED_REPO,
    LABEL_STRATIFIED,
    LEAVE_REPO,
    assign_grouped_repo_folds,
    assign_label_stratified_folds,
    assign_leave_repo_out,
    repo_histogram,
)
from hecate.router.text_runner import load_text_train_config, run_text_train


def _example(
    instance_id: str,
    *,
    m1: bool,
    m2: bool,
    repo: str,
    text: str = "issue",
) -> RouterExample:
    return RouterExample(
        instance_id=instance_id,
        repo=repo,
        text=text,
        truncated=False,
        m1_resolves=m1,
        m2_resolves=m2,
    )


def _row(
    instance_id: str,
    *,
    small: bool,
    large: bool,
    statement: str = "issue body",
    repo: str | None = None,
) -> JoinedLabelWithText:
    from hecate.data.external_miniswe import parse_repo

    return JoinedLabelWithText(
        instance_id=instance_id,
        repo=repo if repo is not None else parse_repo(instance_id),
        small_model_resolved=small,
        large_model_resolved=large,
        problem_statement=statement,
        base_commit="abc",
    )


def test_build_examples_from_text_maps_labels_and_fails_on_empty() -> None:
    rows = [
        _row("django__django-1", small=True, large=False, statement="fix the bug"),
        _row("astropy__astropy-2", small=False, large=True, statement="crash in table"),
    ]
    examples, counts = build_examples_from_text(
        rows, tokenizer=WhitespaceTokenizer(), max_tokens=8
    )
    assert counts["n_examples"] == 2
    assert examples[0].m1_resolves is True
    assert examples[0].m2_resolves is False
    assert examples[0].text == "fix the bug"
    assert "patch" not in examples[0].to_dict()
    with pytest.raises(ValueError, match="empty problem_statement"):
        build_examples_from_text(
            [_row("django__django-3", small=True, large=True, statement="  \n")]
        )


def test_grouped_repo_folds_do_not_leak_repos() -> None:
    examples = []
    for repo in ("aa/aa", "bb/bb", "cc/cc", "dd/dd"):
        for j in range(3):
            examples.append(
                _example(
                    f"{repo}-{j}",
                    m1=bool(j % 2),
                    m2=True,
                    repo=repo,
                )
            )
    assignment = assign_grouped_repo_folds(examples, n_folds=2, seed=0)
    assert assignment.strategy == GROUPED_REPO
    by_id = {ex.instance_id: ex for ex in examples}
    for fold in (0, 1):
        hold_repos = {
            by_id[iid].repo
            for iid, assigned in assignment.fold_of.items()
            if assigned == fold
        }
        train_repos = {
            by_id[iid].repo
            for iid, assigned in assignment.fold_of.items()
            if assigned != fold
        }
        assert hold_repos.isdisjoint(train_repos)


def test_label_stratified_may_leak_and_histogram_flags_django_share() -> None:
    examples = [
        _example(f"django-{i}", m1=bool(i < 6), m2=True, repo="django/django")
        for i in range(10)
    ] + [
        _example(f"sympy-{i}", m1=False, m2=True, repo="sympy/sympy")
        for i in range(2)
    ]
    hist = repo_histogram(examples)
    assert hist["n_repos"] == 2
    assert hist["counts"]["django/django"] == 10
    leaky = assign_label_stratified_folds(examples, n_folds=2, seed=0)
    assert leaky.strategy == LABEL_STRATIFIED


def test_normalized_route_auc_perfect_ranker() -> None:
    examples = [
        _example("a", m1=True, m2=True, repo="aa/aa"),
        _example("b", m1=True, m2=True, repo="aa/aa"),
        _example("c", m1=False, m2=True, repo="bb/bb"),
        _example("d", m1=False, m2=True, repo="bb/bb"),
    ]
    scores = [0.9, 0.8, 0.2, 0.1]
    metrics = text_route_metrics(examples, scores, lambdas=(0.0, 0.5, 1.0))
    assert metrics["always_small"] == 0.5
    assert metrics["always_large"] == 1.0
    assert metrics["headroom"] == 0.0
    assert metrics["route_auc"] == pytest.approx(0.75)
    assert metrics["lift_vs_large_auc"] == route_metrics(
        examples, scores, lambdas=(0.0, 0.5, 1.0)
    )["route_auc"]
    assert auroc([ex.m1_resolves for ex in examples], scores) == pytest.approx(1.0)
    assert metrics["accuracy"] == 1.0
    curve = sweep_lambda_curve(examples, scores, lambdas=(0.0, 0.5, 1.0))
    assert [row["lambda"] for row in curve] == [0.0, 0.5, 1.0]
    assert curve[0]["frac_cheap"] == 1.0
    assert curve[0]["cost"] == 0.0
    assert curve[-1]["frac_cheap"] == 0.0
    assert curve[-1]["cost"] == 1.0


def test_leave_repo_out_is_exact_and_fails_closed() -> None:
    examples = [
        _example(f"django-{i}", m1=bool(i % 2), m2=True, repo="django/django")
        for i in range(4)
    ] + [
        _example(f"sympy-{i}", m1=True, m2=True, repo="sympy/sympy")
        for i in range(3)
    ]
    assignment = assign_leave_repo_out(examples, "django/django", seed=0)
    assert assignment.strategy == LEAVE_REPO
    assert assignment.n_folds == 2
    by_id = {ex.instance_id: ex for ex in examples}
    hold0 = {by_id[iid].repo for iid, fold in assignment.fold_of.items() if fold == 0}
    hold1 = {by_id[iid].repo for iid, fold in assignment.fold_of.items() if fold == 1}
    assert hold0 == {"django/django"}
    assert "django/django" not in hold1
    assert hold1 == {"sympy/sympy"}
    assert assignment.fold_of["django-0"] == 0
    assert assignment.fold_of["sympy-0"] == 1
    with pytest.raises(ValueError, match="missing"):
        assign_leave_repo_out(examples, "missing/repo")
    with pytest.raises(ValueError, match="non-empty"):
        assign_leave_repo_out(examples, "  ")
    only_django = [ex for ex in examples if ex.repo == "django/django"]
    with pytest.raises(ValueError, match="covers every example"):
        assign_leave_repo_out(only_django, "django/django")


def test_run_text_train_leave_repo_writes_two_directions(tmp_path: Path) -> None:
    examples = []
    scores: dict[str, float] = {}
    for i in range(4):
        iid = f"django/django-{i}"
        examples.append(
            _example(iid, m1=True, m2=True, repo="django/django", text=f"text {iid}")
        )
        scores[iid] = 0.9
    for i in range(4):
        iid = f"sympy/sympy-{i}"
        examples.append(
            _example(iid, m1=False, m2=True, repo="sympy/sympy", text=f"text {iid}")
        )
        scores[iid] = 0.1
    config = load_text_train_config(
        csv_path=tmp_path / "unused.csv",
        output_dir=tmp_path / "ldo",
        run_id="ldo-test",
        split="leave-repo",
        hold_repo="django/django",
    )
    config = config.__class__(**{**config.__dict__, "seeds": (0,)})
    result = run_text_train(
        config, backend="scripted", scripted_scores=scores, examples=examples
    )
    payload = json.loads(result.results_path.read_text(encoding="utf-8"))
    assert payload["split_primary"] == "leave_repo"
    assert payload["split_sensitivity"] is None
    assert payload["hold_repo"] == "django/django"
    assert payload["arm"] == "text-only v1 leave-django-out"
    assert payload["features"] == "text"
    assert payload["oracle_leak"] is False
    assert payload["primary"] == {}
    assert "route_auc" not in payload["primary"]
    dirs = payload["directions"]["scripted"]
    assert set(dirs) == {"hold_django", "hold_rest"}
    assert dirs["hold_django"]["n_hold"] == 4
    assert dirs["hold_rest"]["n_hold"] == 4
    for row in payload["primary_folds"]["scripted"]:
        assert row["repo_leak"] == []
        if row["direction"] == "hold_django":
            assert row["hold_repos"] == ["django/django"]
        else:
            assert "django/django" not in row["hold_repos"]
    readme = result.readme_path.read_text(encoding="utf-8")
    assert "leave-repo" in readme.lower()
    assert "hold_django" in readme
    assert result.split_strategy == "leave_repo"


def test_run_text_train_scripted_writes_results(tmp_path: Path) -> None:
    examples = []
    scores: dict[str, float] = {}
    for repo, n, m1 in (("aa/aa", 4, True), ("bb/bb", 4, False), ("cc/cc", 4, True)):
        for i in range(n):
            iid = f"{repo}-{i}"
            examples.append(
                _example(iid, m1=m1, m2=True, repo=repo, text=f"text {iid}")
            )
            scores[iid] = 0.9 if m1 else 0.1
    config = load_text_train_config(
        csv_path=tmp_path / "unused.csv",
        output_dir=tmp_path / "run",
        run_id="text-test",
    )
    config = config.__class__(**{**config.__dict__, "n_folds": 2, "seeds": (0,)})
    result = run_text_train(
        config, backend="scripted", scripted_scores=scores, examples=examples
    )
    assert result.results_path.is_file()
    assert result.manifest_path.is_file()
    assert result.readme_path.is_file()
    payload = json.loads(result.results_path.read_text(encoding="utf-8"))
    assert payload["split_primary"] == "grouped_repo"
    assert payload["split_sensitivity"] == "label_stratified"
    assert payload["arm"] == "text-only v1"
    assert payload["features"] == "text"
    assert payload["oracle_leak"] is False
    assert "scripted" in payload["primary"]
    readme = result.readme_path.read_text(encoding="utf-8")
    assert "3.8" in readme
    assert "text-only" in readme.lower()
    for row in payload["primary_folds"]["scripted"]:
        assert row["repo_leak"] == []


def test_run_text_train_scripted_fusion_flags_oracle_leak(tmp_path: Path) -> None:
    from hecate.router.struct_metrics import METRIC_NAMES

    examples = []
    scores: dict[str, float] = {}
    zeros = [0.0] * len(METRIC_NAMES)
    metric_vectors: dict[str, list[float]] = {}
    for repo, n, m1 in (("aa/aa", 4, True), ("bb/bb", 4, False), ("cc/cc", 4, True)):
        for i in range(n):
            iid = f"{repo}-{i}"
            examples.append(
                _example(iid, m1=m1, m2=True, repo=repo, text=f"text {iid}")
            )
            scores[iid] = 0.9 if m1 else 0.1
            metric_vectors[iid] = list(zeros)
    config = load_text_train_config(
        csv_path=tmp_path / "unused.csv",
        output_dir=tmp_path / "run-fusion",
        run_id="fusion-test",
        features="fusion",
    )
    config = config.__class__(**{**config.__dict__, "n_folds": 2, "seeds": (0,)})
    result = run_text_train(
        config,
        backend="scripted",
        scripted_scores=scores,
        examples=examples,
        metric_vectors=metric_vectors,
    )
    payload = json.loads(result.results_path.read_text(encoding="utf-8"))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert payload["features"] == "fusion"
    assert payload["oracle_leak"] is True
    assert payload["arm"] == "oracle-metrics fusion v2"
    assert manifest["features"] == "fusion"
    assert manifest["oracle_leak"] is True
    readme = result.readme_path.read_text(encoding="utf-8")
    assert "leak gold localization" in readme.lower()
    assert "fusion" in readme.lower()
