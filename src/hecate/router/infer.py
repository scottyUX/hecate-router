"""Serve-time scoring for the text-only v1 router (frozen CLS + logreg).

Importing this module does not require torch. Encoder/head load is lazy.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXPERIMENTAL_WARNING = "experimental — near-chance AUROC, see lab journal"
DEFAULT_THRESHOLD = 0.5
DEFAULT_ENCODER_ID = "answerdotai/ModernBERT-base"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_HEAD_KIND = "logreg"


def sigmoid_linear(features: list[float], weight: list[float], bias: float) -> float:
    """Numerically stable sigmoid(w·x + b). Stdlib-only for default CI."""
    if len(features) != len(weight):
        raise ValueError(
            f"feature dim {len(features)} != weight dim {len(weight)}"
        )
    logit = float(bias)
    for value, coeff in zip(features, weight, strict=True):
        logit += float(value) * float(coeff)
    if logit >= 0:
        exp_neg = math.exp(-logit)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(logit)
    return exp_pos / (1.0 + exp_pos)


def routing_decision(p_small_resolves: float, threshold: float = DEFAULT_THRESHOLD) -> str:
    if p_small_resolves >= threshold:
        return "small"
    return "large"


def require_problem_statement(text: str) -> str:
    stripped = (text or "").strip()
    if not stripped:
        raise ValueError("problem_statement must be non-empty")
    return stripped


def make_route_response(
    p_small_resolves: float,
    *,
    run_id: str,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    p = float(p_small_resolves)
    return {
        "p_small_resolves": p,
        "routing_decision": routing_decision(p, threshold),
        "model_version": run_id,
        "warning": EXPERIMENTAL_WARNING,
    }


def logreg_params_from_payload(payload: dict[str, Any]) -> tuple[list[float], float]:
    """Extract Linear(in→1) row and bias from a FrozenHead checkpoint dict."""
    kind = payload.get("kind")
    if kind != DEFAULT_HEAD_KIND:
        raise ValueError(f"serving requires kind={DEFAULT_HEAD_KIND!r}, got {kind!r}")
    state = payload.get("state_dict")
    if not isinstance(state, dict) or "weight" not in state or "bias" not in state:
        raise ValueError("checkpoint missing Linear weight/bias")
    weight_raw = _as_nested_floats(state["weight"])
    bias_raw = _as_nested_floats(state["bias"])
    if not weight_raw or not isinstance(weight_raw[0], list):
        raise ValueError("logreg weight must have shape [1, in_dim]")
    if len(weight_raw) != 1:
        raise ValueError(f"logreg weight rows {len(weight_raw)} != 1")
    bias_row = bias_raw if isinstance(bias_raw[0], float) else _flatten_floats(bias_raw)
    if len(bias_row) != 1:
        raise ValueError(f"logreg bias length {len(bias_row)} != 1")
    return [float(x) for x in weight_raw[0]], float(bias_row[0])


def load_head_payload(path: str | Path) -> dict[str, Any]:
    torch = _torch()
    target = Path(path)
    try:
        payload = torch.load(target, map_location="cpu", weights_only=True)
    except TypeError:
        payload = torch.load(target, map_location="cpu")
    if not isinstance(payload, dict):
        raise ValueError(f"unrecognized head checkpoint: {target}")
    return payload


def read_manifest(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return data


def encoder_id_from_manifest(manifest: dict[str, Any]) -> str:
    snapshot = manifest.get("config_snapshot")
    if isinstance(snapshot, dict) and snapshot.get("backbone"):
        return str(snapshot["backbone"])
    if manifest.get("backbone"):
        return str(manifest["backbone"])
    return DEFAULT_ENCODER_ID


def run_id_from_manifest(manifest: dict[str, Any], fallback: str | None = None) -> str:
    if manifest.get("run_id"):
        return str(manifest["run_id"])
    if fallback:
        return fallback
    raise ValueError("manifest missing run_id")


@dataclass
class RouterScorer:
    """Loaded encoder + logreg head kept in memory across requests."""

    encoder_id: str
    run_id: str
    max_tokens: int
    _tokenizer: Any
    _model: Any
    _device: Any
    _weight: list[float]
    _bias: float
    _head: Any | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        torch = _torch()
        model = self._model
        tokenizer = self._tokenizer
        device = self._device
        model.eval()
        vectors: list[list[float]] = []
        with torch.no_grad():
            encoded = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=self.max_tokens,
                return_tensors="pt",
            )
            encoded = {key: val.to(device) for key, val in encoded.items()}
            hidden = model(**encoded).last_hidden_state[:, 0, :]
            vectors.extend(row.tolist() for row in hidden.cpu())
        return vectors

    def score_text(self, text: str) -> float:
        features = self.embed([text])[0]
        if self._head is not None:
            return float(self._head.predict_proba([features])[0])
        return sigmoid_linear(features, self._weight, self._bias)

    def route(self, text: str, *, threshold: float = DEFAULT_THRESHOLD) -> dict[str, Any]:
        statement = require_problem_statement(text)
        p = self.score_text(statement)
        return make_route_response(p, run_id=self.run_id, threshold=threshold)


def load_scorer(
    *,
    head_path: str | Path,
    manifest_path: str | Path | None = None,
    encoder_id: str | None = None,
    run_id: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    device: str = "cpu",
) -> RouterScorer:
    """Load HF encoder once and the logreg head from a local checkpoint."""
    payload = load_head_payload(head_path)
    weight, bias = logreg_params_from_payload(payload)
    manifest: dict[str, Any] = {}
    if manifest_path is not None:
        manifest = read_manifest(manifest_path)
    resolved_encoder = encoder_id or encoder_id_from_manifest(manifest)
    if run_id:
        resolved_run = run_id
    elif manifest:
        resolved_run = run_id_from_manifest(manifest)
    else:
        raise ValueError("run_id is required (manifest or ROUTER_RUN_ID)")
    tokenizer, model, torch_device = _load_encoder(resolved_encoder, device=device)
    from hecate.router.backends import FrozenHead

    head = FrozenHead.from_checkpoint(head_path, device=torch_device)
    return RouterScorer(
        encoder_id=resolved_encoder,
        run_id=resolved_run,
        max_tokens=max_tokens,
        _tokenizer=tokenizer,
        _model=model,
        _device=torch_device,
        _weight=weight,
        _bias=bias,
        _head=head,
    )


def _load_encoder(model_name: str, *, device: str = "cpu"):
    torch = _torch()
    AutoTokenizer, AutoModel = _encoder_transformers()
    torch_device = torch.device(device)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.to(torch_device)
    model.eval()
    for param in model.parameters():
        param.requires_grad = False
    return tokenizer, model, torch_device


def _torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "router serving requires torch: pip install torch (CPU wheel is enough)"
        ) from exc
    return torch


def _encoder_transformers():
    try:
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "router serving requires transformers: pip install transformers"
        ) from exc
    return AutoTokenizer, AutoModel


def _as_nested_floats(value: Any) -> list:
    if hasattr(value, "detach"):
        value = value.detach().cpu().tolist()
    elif hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (int, float)):
        return [float(value)]
    if not isinstance(value, list):
        raise ValueError(f"cannot coerce tensor-like value: {type(value)}")
    return value


def _flatten_floats(value: list) -> list[float]:
    out: list[float] = []
    for item in value:
        if isinstance(item, list):
            out.extend(_flatten_floats(item))
        else:
            out.append(float(item))
    return out
