"""Execution backends, loaded lazily so local Codex needs no benchmark loader.

Existing Stage-2/3 public imports remain available. Importing a Codex module must
not eagerly import datasets/SWE-bench or initialize another execution backend.
"""
from __future__ import annotations
from importlib import import_module

_MODULE_EXPORTS = {
    "harness": (
        "Harness",
        "HarnessRequest",
        "HarnessResult",
        "ScriptedHarness",
        "ScriptedOutcome",
        "SwebenchHarness",
    ),
    "labels": ("RoutingLabel", "build_labels"),
    "merge": ("apply_report", "load_error_ids", "load_instance_report"),
    "predictions": ("has_executable_patch", "to_prediction", "write_predictions"),
    "runner": (
        "ExecutionConfig",
        "ExecutionResult",
        "load_execution_config",
        "run_execution",
    ),
}
_EXPORTS = {name: module for module, names in _MODULE_EXPORTS.items() for name in names}
__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f"{__name__}.{_EXPORTS[name]}"), name)
    globals()[name] = value
    return value
