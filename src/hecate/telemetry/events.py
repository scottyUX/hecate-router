"""Versioned canonical events; evaluation data has no observation input type."""

from __future__ import annotations
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any

EVENT_VERSION = "hecate.events.v1"
KINDS = {
    "model_request",
    "model_response",
    "model_failure",
    "tool_start",
    "tool_complete",
    "advisor_call",
    "advisor_assessment",
    "visible_tests",
    "controller",
    "boundary",
    "termination",
    "legacy_step",
}
FORBIDDEN = {
    "resolved",
    "reward",
    "gold_patch",
    "ground_truth",
    "eval_id",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "final_patch",
}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def reject_evaluator(value):
    if isinstance(value, dict):
        if FORBIDDEN.intersection(value):
            raise ValueError("Evaluator-only fields are not observation inputs")
        for item in value.values():
            reject_evaluator(item)
    elif isinstance(value, list):
        for item in value:
            reject_evaluator(item)


@dataclass(frozen=True)
class Event:
    episode_id: str
    event_id: str
    sequence: int
    kind: str
    source: str
    payload: dict = field(default_factory=dict)
    timestamp: float | None = None
    clock: str | None = None
    version: str = EVENT_VERSION
    identity: dict = field(default_factory=dict)
    quality: tuple[str, ...] = ()

    def __post_init__(self):
        if self.version != EVENT_VERSION or self.kind not in KINDS:
            raise ValueError("Unsupported event schema/type")
        if not self.episode_id or not self.event_id or self.sequence < 0:
            raise ValueError("Invalid event identity/order")
        reject_evaluator(self.payload)
        reject_evaluator(self.identity)
        if self.timestamp is not None and not math.isfinite(self.timestamp):
            raise ValueError("Invalid timestamp")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        reject_evaluator(value)
        return cls(**value)
