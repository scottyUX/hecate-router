"""Stage-4 encoder router (semantic-only v1)."""

from __future__ import annotations

from hecate.router.backends import (
    EncoderBackend,
    ModernBertBackend,
    ScriptedBackend,
)
from hecate.router.dataset import (
    RouterExample,
    WhitespaceTokenizer,
    build_examples,
    build_examples_from_text,
)
from hecate.router.metrics import route_metrics, text_route_metrics
from hecate.router.struct_metrics import (
    METRIC_NAMES,
    assemble_features,
    fit_metric_scaler,
    metrics_from_python_source,
)
from hecate.router.runner import TrainConfig, TrainResult, load_train_config, run_train
from hecate.router.splits import (
    FoldAssignment,
    assign_folds,
    assign_grouped_repo_folds,
    assign_label_stratified_folds,
    assign_leave_repo_out,
)
from hecate.router.text_runner import (
    TextTrainConfig,
    TextTrainResult,
    load_text_train_config,
    run_text_train,
)

__all__ = [
    "EncoderBackend",
    "FoldAssignment",
    "ModernBertBackend",
    "RouterExample",
    "ScriptedBackend",
    "TextTrainConfig",
    "TextTrainResult",
    "TrainConfig",
    "TrainResult",
    "WhitespaceTokenizer",
    "METRIC_NAMES",
    "assemble_features",
    "assign_folds",
    "fit_metric_scaler",
    "metrics_from_python_source",
    "assign_grouped_repo_folds",
    "assign_label_stratified_folds",
    "assign_leave_repo_out",
    "build_examples",
    "build_examples_from_text",
    "load_text_train_config",
    "load_train_config",
    "route_metrics",
    "run_text_train",
    "run_train",
    "text_route_metrics",
]
