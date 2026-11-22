"""Versioned numeric observations and train-only frozen normalization."""

from __future__ import annotations
import json
import math
from pathlib import Path
from hecate.telemetry.events import digest

FEATURES = (
    "completed_interactions",
    "model_requests",
    "transport_attempts",
    "advisor_calls",
    "request_budget_used",
    "elapsed_s",
    "time_budget_used",
    "command_failure_rate",
    "command_timeouts",
    "repeated_errors",
    "visible_passed",
    "visible_failed",
    "visible_pass_delta",
    "input_tokens",
    "output_tokens",
    "inference_s",
    "context_used",
    "active_model_m2",
    "advisor_progress",
    "advisor_stuckness",
    "advisor_remaining_difficulty",
    "advisor_confidence",
)


class StateBuilder:
    def __init__(self, config, normalizer=None):
        self.config = config
        if (
            config.get("schema_version") != "hecate.observation.v1"
            or tuple(config.get("features", [])) != FEATURES
        ):
            raise ValueError("Unknown observation schema or feature order")
        if (
            config.get("initial_decision") is not False
            or config.get("cadence", 0) < 1
            or config.get("command_window", 0) < 1
        ):
            raise ValueError("Invalid checkpoint/window configuration")
        if (
            config.get("error_signature") != "stderr-whitespace-v1"
            or config["normalization"].get("clipping") != "none"
        ):
            raise ValueError("Unsupported observation transform")
        if config["normalization"].get("epsilon", 0) <= 0:
            raise ValueError("Invalid normalization epsilon")
        self.schema_hash = digest(config)
        self.normalizer = normalizer
        if normalizer:
            artifact = dict(normalizer)
            recorded = artifact.pop("hash", None)
            if (
                digest(artifact) != recorded
                or artifact.get("schema_hash") != self.schema_hash
                or artifact.get("features") != list(FEATURES)
            ):
                raise ValueError("Normalizer hash/schema mismatch")

    def build(self, row, *, router_ready=False):
        values = row["features"]
        if set(values) != set(FEATURES):
            raise ValueError("Feature schema mismatch")
        if router_ready and (
            not self.normalizer
            or row.get("action_mask") is None
            or values["active_model_m2"] is None
        ):
            raise ValueError(
                "Router-ready output needs frozen normalization and explicit controller context"
            )
        vector = []
        mask = []
        for name in FEATURES:
            value = values[name]
            valid = (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
            )
            stat = self.normalizer["stats"][name] if self.normalizer else None
            if stat and not stat["count"]:
                valid = False
            if valid:
                number = float(value)
                if stat and name != "active_model_m2":
                    number = (number - stat["mean"]) / max(
                        stat["std"], self.config["normalization"]["epsilon"]
                    )
                vector.append(number)
                mask.append(True)
            else:
                vector.append(0.0)
                mask.append(False)
        return {
            **row,
            "schema_version": self.config["schema_version"],
            "schema_hash": self.schema_hash,
            "feature_order": list(FEATURES),
            "vector": vector,
            "validity_mask": mask,
            "action_mask": row.get("action_mask"),
            "normalizer_hash": self.normalizer["hash"] if self.normalizer else None,
            "mode": (
                "router_ready"
                if router_ready
                else "normalized_diagnostic" if self.normalizer else "raw_diagnostic"
            ),
        }

    def fit(self, rows, split_manifest):
        training = set(split_manifest["training_ids"])
        reserved = set(split_manifest["reserved_ids"])
        if not training or training & reserved:
            raise ValueError("Training/reserved split is empty or overlaps")
        if not rows:
            raise ValueError("No training observations")
        for row in rows:
            identity = row["identity"]
            task = identity["task_id"]
            if (
                task not in training
                or task in reserved
                or identity.get("split") != "train"
            ):
                raise ValueError(
                    "Normalization may only fit explicitly designated training tasks"
                )
            self.build(row)
        stats = {}
        for name in FEATURES:
            values = [
                float(r["features"][name])
                for r in rows
                if isinstance(r["features"][name], (int, float))
                and not isinstance(r["features"][name], bool)
                and math.isfinite(r["features"][name])
            ]
            mean = sum(values) / len(values) if values else 0.0
            stats[name] = {
                "mean": mean,
                "std": (
                    math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
                    if values
                    else 0.0
                ),
                "count": len(values),
            }
        artifact = {
            "version": "hecate.normalizer.v1",
            "schema_hash": self.schema_hash,
            "features": list(FEATURES),
            "stats": stats,
            "fitting_task_ids": sorted({r["identity"]["task_id"] for r in rows}),
            "fitting_observations_hash": digest(rows),
            "split_manifest_hash": digest(split_manifest),
        }
        artifact["hash"] = digest(artifact)
        return artifact


def save_normalizer(path, artifact):
    with Path(path).open("x") as stream:
        json.dump(artifact, stream, indent=2, allow_nan=False)
