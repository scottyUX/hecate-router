"""Offline tests for Stage-4 router dataset, splits, and Route-AUC."""

from __future__ import annotations

from pathlib import Path

from hecate.data import GenerationRecord, append_jsonl
from hecate.execution.labels import RoutingLabel
from hecate.router import (
    ScriptedBackend,
    WhitespaceTokenizer,
    assign_folds,
    build_examples,
    load_train_config,
    route_metrics,
    run_train,
)
from hecate.router.dataset import RouterExample
from hecate.router.splits import LABEL_REPO, ROUND_ROBIN

QWEN_7B = "qwen/qwen-2.5-7b-instruct"
QWEN_72B = "qwen/qwen-2.5-72b-instruct"
PATCH = "SECRET_PATCH_SHOULD_NOT_LEAK"


def _gen(instance_id: str, prompt: str, **overrides) -> GenerationRecord:
    base = dict(
        instance_id=instance_id,
        repo="django/django",
        base_commit="abc",
        model_slug=QWEN_7B,
        tier="small",
        prompt=prompt,
        prompt_hash="h",
        extracted_patch=PATCH,
        patch_parse_ok=True,
        run_id="sweep",
    )
    base.update(overrides)
    return GenerationRecord(**base)


def _label(
    instance_id: str, *, m1: bool, m2: bool, repo: str = "django/django"
) -> RoutingLabel:
    return RoutingLabel(
        instance_id=instance_id,
        repo=repo,
        m1_slug=QWEN_7B,
        m2_slug=QWEN_72B,
        m1_resolves=m1,
        m2_resolves=m2,
        complementarity="both" if m1 and m2 else "neither",
    )


def _example(
    instance_id: str,
    *,
    m1: bool,
    m2: bool,
    repo: str = "django/django",
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


def test_build_examples_truncates_and_excludes_patch() -> None:
    labels = [_label("t1", m1=True, m2=False)]
    gens = [_gen("t1", "alpha beta gamma delta")]
    rows, counts = build_examples(
        labels, gens, tokenizer=WhitespaceTokenizer(), max_tokens=2
    )
    assert len(rows) == 1
    assert rows[0].truncated is True
    assert rows[0].text == "alpha beta"
    assert PATCH not in rows[0].text
    assert counts["truncated"] == 1
    assert rows[0].m1_resolves is True


def test_build_examples_skips_incomplete() -> None:
    labels = [_label("missing", m1=False, m2=False)]
    rows, counts = build_examples(
        labels, [], tokenizer=WhitespaceTokenizer(), max_tokens=8
    )
    assert rows == []
    assert counts["skipped_incomplete"] == 1


def test_assign_folds_label_repo_when_dense() -> None:
    examples = []
    for repo in ("aa/aa", "bb/bb"):
        for flag in (True, False):
            for i in range(3):
                examples.append(
                    _example(
                        f"{repo}-{flag}-{i}",
                        m1=flag,
                        m2=not flag,
                        repo=repo,
                    )
                )
    assignment = assign_folds(examples, n_folds=3, seed=0)
    assert assignment.strategy == LABEL_REPO
    assert set(assignment.fold_of.values()) == {0, 1, 2}


def test_assign_folds_falls_back_round_robin() -> None:
    examples = [_example(f"x{i}", m1=False, m2=False) for i in range(3)]
    assignment = assign_folds(examples, n_folds=5, seed=1)
    assert assignment.strategy == ROUND_ROBIN
    assert len(assignment.fold_of) == 3


def test_route_auc_positive_when_scores_rank_m1() -> None:
    examples = [
        _example("a", m1=True, m2=False),
        _example("b", m1=False, m2=True),
    ]
    metrics = route_metrics(examples, [0.9, 0.1])
    assert metrics["always_m1"] == 0.5
    assert metrics["always_m2"] == 0.5
    assert metrics["oracle"] == 1.0
    assert metrics["route_auc"] > 0
    assert metrics["best_route_rate"] == 1.0


def test_route_auc_zero_when_constant_m2_policy() -> None:
    examples = [
        _example("a", m1=False, m2=True),
        _example("b", m1=False, m2=True),
    ]
    # scores all 0 → for λ>0 always m2, matching always_m2
    metrics = route_metrics(examples, [0.0, 0.0], lambdas=(0.0, 0.5, 1.0))
    assert metrics["always_m2"] == 1.0
    assert abs(metrics["route_auc"]) < 0.51


def test_run_train_scripted_writes_manifest(tmp_path: Path) -> None:
    labels_path = tmp_path / "labels.jsonl"
    gens_path = tmp_path / "gens.jsonl"
    labels = [
        _label(f"t{i}", m1=(i < 2), m2=True, repo="django/django")
        for i in range(6)
    ]
    with labels_path.open("w", encoding="utf-8") as handle:
        for row in labels:
            handle.write(
                __import__("json").dumps(row.to_dict(), ensure_ascii=False) + "\n"
            )
    for i in range(6):
        append_jsonl(gens_path, _gen(f"t{i}", f"issue text {i}"))
    scores = {f"t{i}": (0.9 if i < 2 else 0.1) for i in range(6)}
    config = load_train_config(
        labels_path=labels_path,
        generations_path=gens_path,
        output_dir=tmp_path / "router",
        run_id="router-test",
    )
    # Shrink folds for the tiny set via object replace — use round_robin n_folds=2
    config = config.__class__(
        **{**config.__dict__, "n_folds": 2, "seeds": (0,)}
    )
    result = run_train(config, backend=ScriptedBackend(scores))
    assert result.examples_path.is_file()
    assert result.metrics_path.is_file()
    assert result.manifest_path.is_file()
    assert result.go_nogo in {"go", "floor"}
    payload = __import__("json").loads(result.manifest_path.read_text())
    assert "split_strategy" in payload
    assert "truncation_rate" in payload
    assert payload["go_nogo"] == result.go_nogo
    texts = result.examples_path.read_text()
    assert PATCH not in texts
