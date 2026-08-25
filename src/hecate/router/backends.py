"""Injectable encoder backends. Scripted path must not import torch."""

from __future__ import annotations

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


def _device(torch):  # type: ignore[no-untyped-def]
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
