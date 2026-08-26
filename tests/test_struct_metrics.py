"""Offline tests for oracle-file AST metrics (no torch / no HF / no clones)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hecate.router.struct_metrics import (
    METRIC_NAMES,
    assemble_features,
    build_oracle_metric_vectors,
    fit_metric_scaler,
    metrics_from_files,
    metrics_from_python_source,
    vector_from_metrics,
    write_metric_cache,
)
from hecate.scaffold.context import ContextFile

_IF_SRC = "def foo(x):\n    if x:\n        return 1\n    return 0\n"
_NESTED_SRC = (
    "def bar(x):\n    if x:\n        if x:\n            return 1\n    return 0\n"
)


def test_ast_metrics_known_cyclo_and_nest() -> None:
    stats = metrics_from_python_source(_IF_SRC)
    assert stats["n_functions"] == 1
    assert stats["max_cyclo"] == 2
    assert stats["mean_cyclo"] == 2
    assert stats["max_nest"] == 1
    assert stats["mean_arity"] == 1
    assert stats["parse_errors"] == 0
    assert stats["loc"] == 4

    nested = metrics_from_python_source(_NESTED_SRC)
    assert nested["n_functions"] == 1
    assert nested["max_cyclo"] == 3
    assert nested["max_nest"] == 2
    assert nested["parse_errors"] == 0


def test_empty_and_unparseable_are_zeros_plus_error_count() -> None:
    empty = metrics_from_python_source("")
    assert empty["parse_errors"] == 0
    assert empty["loc"] == 0
    assert empty["n_functions"] == 0
    assert empty["max_cyclo"] == 0

    bad = metrics_from_python_source("def oops(:\n")
    assert bad["parse_errors"] == 1
    assert bad["n_functions"] == 0
    assert bad["max_cyclo"] == 0
    assert bad["loc"] == 1


def test_metrics_from_files_aggregates_and_counts_parse_errors() -> None:
    files = (
        ContextFile(path="ok.py", content=_IF_SRC),
        ContextFile(path="added.py", content=""),
        ContextFile(path="broken.py", content="not python :"),
    )
    agg = metrics_from_files(files)
    assert agg["n_files"] == 3
    assert agg["n_functions"] == 1
    assert agg["parse_errors"] == 1
    assert agg["max_cyclo"] == 2
    vec = vector_from_metrics(agg)
    assert len(vec) == len(METRIC_NAMES)
    assert len(METRIC_NAMES) == 12


def test_scaler_fits_train_only_not_hold() -> None:
    train = [[0.0, 10.0], [2.0, 10.0]]
    hold = [100.0, 10.0]
    scaler = fit_metric_scaler(train)
    assert scaler.mean[0] == pytest.approx(1.0)
    assert scaler.mean[1] == pytest.approx(10.0)
    assert scaler.std[1] == pytest.approx(0.0)
    # Hold 100 is not in the train mean; scaling uses train stats only.
    scaled_hold = scaler.transform(hold)
    assert scaled_hold[0] == pytest.approx((100.0 - 1.0) / scaler.std[0])
    assert scaled_hold[1] == 0.0
    scaled_train = [scaler.transform(row) for row in train]
    assert sum(row[0] for row in scaled_train) == pytest.approx(0.0)


def test_assemble_fusion_dim_is_cls_plus_k() -> None:
    k = len(METRIC_NAMES)
    cls = {"a": [0.0] * 768}
    metrics = {"a": [float(i) for i in range(k)]}
    scaler = fit_metric_scaler([metrics["a"]])
    fused = assemble_features(
        ["a"], features="fusion", cls=cls, metrics=metrics, scaler=scaler
    )
    assert len(fused[0]) == 768 + k
    text = assemble_features(
        ["a"], features="text", cls=cls, metrics=metrics, scaler=None
    )
    assert len(text[0]) == 768
    only = assemble_features(
        ["a"], features="metrics", cls=None, metrics=metrics, scaler=scaler
    )
    assert len(only[0]) == k


def test_metric_cache_fail_closed_join(tmp_path: Path) -> None:
    zeros = [0.0] * len(METRIC_NAMES)
    path = tmp_path / "oracle_file_metrics.json"
    write_metric_cache(path, {"a": zeros, "b": list(range(len(METRIC_NAMES)))})
    out = build_oracle_metric_vectors([], ["a", "b"], cache_path=path)
    assert set(out) == {"a", "b"}
    assert out["a"] == zeros
    assert len(out["b"]) == 12
    with pytest.raises(ValueError, match="missing from Verified"):
        build_oracle_metric_vectors([], ["a", "missing"], cache_path=path)
