"""Injectable encoder backends. Scripted path must not import torch."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class EncoderBackend(Protocol):
    def fit(
        self,
        texts: list[str],
        labels: list[bool],
        *,
        seed: int,
        instance_ids: list[str] | None = None,
    ) -> None: ...

    def predict_proba(
        self,
        texts: list[str],
        *,
        instance_ids: list[str] | None = None,
    ) -> list[float]: ...


class ScriptedBackend:
    """Deterministic scores from instance id (tests / dry-run)."""

    def __init__(self, scores: dict[str, float] | None = None) -> None:
        self.scores = dict(scores or {})

    def fit(
        self,
        texts: list[str],
        labels: list[bool],
        *,
        seed: int,
        instance_ids: list[str] | None = None,
    ) -> None:
        del texts, labels, seed, instance_ids

    def predict_proba(
        self,
        texts: list[str],
        *,
        instance_ids: list[str] | None = None,
    ) -> list[float]:
        if instance_ids is not None:
            return [float(self.scores.get(iid, 0.0)) for iid in instance_ids]
        return [0.0] * len(texts)


class ModernBertBackend:
    """Fine-tune answerdotai/ModernBERT-base. Imports torch only when used."""

    def __init__(
        self,
        model_name: str = "answerdotai/ModernBERT-base",
        *,
        max_tokens: int = 2048,
        epochs: int = 2,
        batch_size: int = 8,
        learning_rate: float = 2e-5,
    ) -> None:
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self._model = None
        self._tokenizer = None
        self._device = None

    def fit(
        self,
        texts: list[str],
        labels: list[bool],
        *,
        seed: int,
        instance_ids: list[str] | None = None,
    ) -> None:
        del instance_ids
        torch = _torch()
        AutoTokenizer, AutoModel = _transformers()
        torch.manual_seed(seed)
        device = _device(torch)
        self._device = device
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModel.from_pretrained(self.model_name, num_labels=2)
        model.to(device)
        model.train()
        optimizer = torch.optim.AdamW(model.parameters(), lr=self.learning_rate)
        for _ in range(self.epochs):
            for start in range(0, len(texts), self.batch_size):
                batch_text = texts[start : start + self.batch_size]
                batch_y = labels[start : start + self.batch_size]
                encoded = tokenizer(
                    batch_text,
                    padding=True,
                    truncation=True,
                    max_length=self.max_tokens,
                    return_tensors="pt",
                )
                encoded = {key: val.to(device) for key, val in encoded.items()}
                y = torch.tensor(
                    [1 if flag else 0 for flag in batch_y],
                    dtype=torch.long,
                    device=device,
                )
                out = model(**encoded, labels=y)
                optimizer.zero_grad()
                out.loss.backward()
                optimizer.step()
        self._model = model
        self._tokenizer = tokenizer

    def predict_proba(
        self,
        texts: list[str],
        *,
        instance_ids: list[str] | None = None,
    ) -> list[float]:
        del instance_ids
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("ModernBertBackend.fit must be called first")
        torch = _torch()
        model = self._model
        tokenizer = self._tokenizer
        device = self._device
        model.eval()
        scores: list[float] = []
        with torch.no_grad():
            for start in range(0, len(texts), self.batch_size):
                batch_text = texts[start : start + self.batch_size]
                encoded = tokenizer(
                    batch_text,
                    padding=True,
                    truncation=True,
                    max_length=self.max_tokens,
                    return_tensors="pt",
                )
                encoded = {key: val.to(device) for key, val in encoded.items()}
                logits = model(**encoded).logits
                prob = torch.softmax(logits, dim=-1)[:, 1]
                scores.extend(float(x) for x in prob.cpu())
        return scores


class FrozenModernBertEmbedder:
    """Frozen ModernBERT-base CLS embeddings. Imports torch only when used."""

    def __init__(
        self,
        model_name: str = "answerdotai/ModernBERT-base",
        *,
        max_tokens: int = 2048,
        batch_size: int = 8,
    ) -> None:
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.batch_size = batch_size
        self._model = None
        self._tokenizer = None
        self._device = None
        self.n_truncated = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        torch = _torch()
        AutoTokenizer, AutoModel = _encoder_transformers()
        device = _device(torch)
        self._device = device
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModel.from_pretrained(self.model_name)
        model.to(device)
        model.eval()
        for param in model.parameters():
            param.requires_grad = False
        self._tokenizer = tokenizer
        self._model = model
        truncated = 0
        vectors: list[list[float]] = []
        with torch.no_grad():
            for start in range(0, len(texts), self.batch_size):
                batch = texts[start : start + self.batch_size]
                for text in batch:
                    token_ids = tokenizer.encode(
                        text,
                        add_special_tokens=True,
                        truncation=True,
                        max_length=self.max_tokens + 1,
                    )
                    if len(token_ids) > self.max_tokens:
                        truncated += 1
                encoded = tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=self.max_tokens,
                    return_tensors="pt",
                )
                encoded = {key: val.to(device) for key, val in encoded.items()}
                hidden = model(**encoded).last_hidden_state[:, 0, :]
                vectors.extend(row.tolist() for row in hidden.cpu())
        self.n_truncated = truncated
        return vectors


class FrozenHead:
    """Logistic or MLP head on frozen CLS vectors."""

    def __init__(
        self,
        kind: str,
        *,
        in_dim: int = 768,
        hidden_size: int = 128,
        dropout: float = 0.2,
        epochs: int = 4,
        batch_size: int = 8,
        learning_rate: float = 2e-5,
    ) -> None:
        if kind not in {"logreg", "mlp"}:
            raise ValueError(f"unknown head kind: {kind}")
        self.kind = kind
        self.in_dim = in_dim
        self.hidden_size = hidden_size
        self.dropout = dropout
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self._module = None
        self._device = None

    def _build(self, torch):  # type: ignore[no-untyped-def]
        if self.kind == "logreg":
            return torch.nn.Linear(self.in_dim, 1)
        return torch.nn.Sequential(
            torch.nn.Linear(self.in_dim, self.hidden_size),
            torch.nn.GELU(),
            torch.nn.Dropout(self.dropout),
            torch.nn.Linear(self.hidden_size, 1),
        )

    def fit(
        self,
        features: list[list[float]],
        labels: list[bool],
        *,
        seed: int,
        pos_weight: float | None = None,
    ) -> None:
        torch = _torch()
        torch.manual_seed(seed)
        device = _device(torch)
        self._device = device
        if features:
            self.in_dim = len(features[0])
        module = self._build(torch)
        module.to(device)
        module.train()
        optimizer = torch.optim.AdamW(module.parameters(), lr=self.learning_rate)
        weight = None
        if pos_weight is not None:
            weight = torch.tensor([pos_weight], dtype=torch.float32, device=device)
        loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=weight)
        x_all = torch.tensor(features, dtype=torch.float32, device=device)
        y_all = torch.tensor(
            [1.0 if flag else 0.0 for flag in labels],
            dtype=torch.float32,
            device=device,
        ).unsqueeze(1)
        for _ in range(self.epochs):
            for start in range(0, len(features), self.batch_size):
                batch_x = x_all[start : start + self.batch_size]
                batch_y = y_all[start : start + self.batch_size]
                logits = module(batch_x)
                loss = loss_fn(logits, batch_y)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        self._module = module

    def predict_proba(self, features: list[list[float]]) -> list[float]:
        if self._module is None:
            raise RuntimeError("FrozenHead.fit must be called first")
        torch = _torch()
        module = self._module
        device = self._device
        module.eval()
        scores: list[float] = []
        with torch.no_grad():
            for start in range(0, len(features), self.batch_size):
                batch = torch.tensor(
                    features[start : start + self.batch_size],
                    dtype=torch.float32,
                    device=device,
                )
                logits = module(batch).squeeze(-1)
                prob = torch.sigmoid(logits)
                scores.extend(float(x) for x in prob.cpu().reshape(-1))
        return scores

    def state_dict(self) -> dict:
        if self._module is None:
            raise RuntimeError("FrozenHead.fit must be called first")
        return {
            "kind": self.kind,
            "in_dim": self.in_dim,
            "hidden_size": self.hidden_size,
            "dropout": self.dropout,
            "state_dict": {key: val.detach().cpu() for key, val in self._module.state_dict().items()},
        }

    @classmethod
    def from_checkpoint(cls, path: str | Path, *, device=None) -> FrozenHead:
        """Load a head saved by ``state_dict`` / ``torch.save``. Defaults to CPU."""
        torch = _torch()
        target = Path(path)
        try:
            payload = torch.load(target, map_location="cpu", weights_only=True)
        except TypeError:
            payload = torch.load(target, map_location="cpu")
        if not isinstance(payload, dict) or "kind" not in payload or "state_dict" not in payload:
            raise ValueError(f"unrecognized head checkpoint: {target}")
        head = cls(
            str(payload["kind"]),
            in_dim=int(payload.get("in_dim") or 768),
            hidden_size=int(payload.get("hidden_size") or 128),
            dropout=float(payload.get("dropout") or 0.2),
        )
        module = head._build(torch)
        module.load_state_dict(payload["state_dict"])
        if device is None:
            device = torch.device("cpu")
        module.to(device)
        module.eval()
        head._module = module
        head._device = device
        return head


def _torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "ModernBertBackend requires the train extra: pip install -e '.[train]'"
        ) from exc
    return torch


def _transformers():
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "ModernBertBackend requires the train extra: pip install -e '.[train]'"
        ) from exc
    return AutoTokenizer, AutoModelForSequenceClassification


def _encoder_transformers():
    try:
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "FrozenModernBertEmbedder requires the train extra: pip install -e '.[train]'"
        ) from exc
    return AutoTokenizer, AutoModel


def _device(torch):  # type: ignore[no-untyped-def]
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
