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
)
from hecate.router.metrics import route_metrics
from hecate.router.runner import TrainConfig, TrainResult, load_train_config, run_train
from hecate.router.splits import FoldAssignment, assign_folds

__all__ = [
    "EncoderBackend",
    "FoldAssignment",
    "ModernBertBackend",
    "RouterExample",
    "ScriptedBackend",
    "TrainConfig",
    "TrainResult",
    "WhitespaceTokenizer",
    "assign_folds",
    "build_examples",
    "load_train_config",
    "route_metrics",
    "run_train",
]
