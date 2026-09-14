"""QLoRA value head for trajectory-conditioned routing. Imported only for --backend lora."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hecate.router.traj import (
    EARLY_STOP_METRIC,
    EARLY_STOP_MIN_DELTA,
    EARLY_STOP_PATIENCE,
    FIT_VAL_N,
    GRAD_CLIP_NORM,
    K_EVAL,
    TrajExample,
    binary_brier,
    binary_log_loss,
    carve_fit_val,
    eval_examples,
    parse_arm,
    shuffle_train_rows,
    train_rows_for_arm,
)


def _require_train():
    try:
        import torch
        from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    except ImportError as exc:
        raise RuntimeError(
            "traj LoRA requires the train extra: pip install -e '.[train]'"
        ) from exc
    return torch, LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


def _device(torch):  # type: ignore[no-untyped-def]
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class TrajLoraBackend:
    """Qwen2.5-Coder-7B LoRA classifier. QLoRA + grad checkpoint + microbatch 1."""

    def __init__(
        self,
        model_name: str,
        *,
        max_tokens: int = 8192,
        epochs: int = 5,
        batch_size: int = 1,
        grad_accum: int = 16,
        learning_rate: float = 5e-5,
        lora_r: int = 32,
        lora_alpha: int = 64,
        lora_dropout: float = 0.05,
        qlora: bool = True,
        log_dir: Path | None = None,
        val_size: int = FIT_VAL_N,
        grad_clip_norm: float = GRAD_CLIP_NORM,
        early_stopping: bool = False,
        early_stopping_metric: str = EARLY_STOP_METRIC,
        early_stopping_patience: int = EARLY_STOP_PATIENCE,
        early_stopping_min_delta: float = EARLY_STOP_MIN_DELTA,
    ) -> None:
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.epochs = epochs
        self.batch_size = batch_size
        self.grad_accum = grad_accum
        self.learning_rate = learning_rate
        self.lora_r = lora_r
        self.lora_alpha = lora_alpha
        self.lora_dropout = lora_dropout
        self.qlora = qlora
        self.log_dir = Path(log_dir) if log_dir is not None else None
        self.val_size = int(val_size)
        self.grad_clip_norm = float(grad_clip_norm)
        self.early_stopping = bool(early_stopping)
        self.early_stopping_metric = (early_stopping_metric or EARLY_STOP_METRIC).strip()
        self.early_stopping_patience = int(early_stopping_patience)
        self.early_stopping_min_delta = float(early_stopping_min_delta)
        self._model = None
        self._tokenizer = None
        self._device = None
        self._score = None
        self.n_train = 0
        self.n_val = 0
        self.val_instance_ids: tuple[str, ...] = ()

    def _load(self) -> None:
        torch, LoraConfig, TaskType, get_peft_model, prepare_kbit, AutoModel, AutoTokenizer, BitsAndBytesConfig = _require_train()
        device = _device(torch)
        self._device = device
        tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"
        quant = None
        if self.qlora and device.type == "cuda":
            quant = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
        if device.type == "cuda":
            torch.backends.cuda.enable_flash_sdp(True)
            torch.backends.cuda.enable_mem_efficient_sdp(True)
            torch.backends.cuda.enable_math_sdp(False)
        kwargs: dict[str, Any] = {
            "trust_remote_code": True,
            "torch_dtype": torch.bfloat16 if device.type != "cpu" else torch.float32,
            "attn_implementation": "sdpa",
        }
        if quant is not None:
            kwargs["quantization_config"] = quant
            kwargs["device_map"] = "auto"
        model = AutoModel.from_pretrained(self.model_name, **kwargs)
        if quant is not None:
            model = prepare_kbit(model)
        try:
            model.gradient_checkpointing_enable(
                gradient_checkpointing_kwargs={"use_reentrant": False}
            )
        except TypeError:
            model.gradient_checkpointing_enable()
        lora = LoraConfig(
            r=self.lora_r,
            lora_alpha=self.lora_alpha,
            lora_dropout=self.lora_dropout,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        )
        model = get_peft_model(model, lora)
        hidden = int(model.config.hidden_size)
        score = torch.nn.Linear(hidden, 2)
        torch.nn.init.zeros_(score.weight)
        torch.nn.init.zeros_(score.bias)
        score.to(device)
        self._model = model
        self._tokenizer = tokenizer
        self._score = score
        if hasattr(model, "enable_input_require_grads"):
            model.enable_input_require_grads()
        if hasattr(model, "config"):
            model.config.use_cache = False

    def _log_path(self, name: str) -> Path | None:
        if self.log_dir is None:
            return None
        self.log_dir.mkdir(parents=True, exist_ok=True)
        return self.log_dir / name

    def _append_jsonl(self, name: str, row: dict[str, Any]) -> None:
        path = self._log_path(name)
        if path is None:
            return
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _gpu_mem_gb(self, torch) -> float | None:  # type: ignore[no-untyped-def]
        if not torch.cuda.is_available():
            return None
        return round(torch.cuda.max_memory_allocated() / (1024**3), 3)

    def _last_token_hidden(self, encoded, torch):  # type: ignore[no-untyped-def]
        """Decoder hidden state at the last non-pad token. Skips the LM head.

        CausalLM logits at 8192 tokens are ~2GB and OOM the L4 backward.
        LoRA adapters are in-place on the decoder modules.
        """
        model = self._model
        assert model is not None
        base = model.get_base_model() if hasattr(model, "get_base_model") else model
        decoder = getattr(base, "model", base)
        kwargs: dict[str, Any] = {"input_ids": encoded["input_ids"]}
        attn = encoded.get("attention_mask")
        padded = attn is not None and bool((attn == 0).any())
        # A dense attention_mask forces SDPA's math kernel (~7GB at 8192).
        if padded:
            kwargs["attention_mask"] = attn
        hidden = decoder(**kwargs, use_cache=False).last_hidden_state
        if padded:
            last = attn.sum(dim=1) - 1
        else:
            last = torch.full(
                (hidden.size(0),),
                hidden.size(1) - 1,
                device=hidden.device,
                dtype=torch.long,
            )
        return hidden[torch.arange(hidden.size(0), device=hidden.device), last]

    def _step_optimizer(self, torch, optimizer, params) -> None:  # type: ignore[no-untyped-def]
        if self.grad_clip_norm > 0:
            torch.nn.utils.clip_grad_norm_(params, self.grad_clip_norm)
        optimizer.step()
        optimizer.zero_grad()

    def _val_metrics(
        self, examples: list[TrajExample], *, arm: str
    ) -> tuple[float | None, float | None]:
        if not examples:
            return None, None
        _kind, spec = parse_arm(arm)
        k = K_EVAL if spec.eval_k is None else spec.eval_k
        hold = eval_examples(examples, k=k)
        probs = self.predict_proba([ex.text for ex in hold])
        labels = [ex.m1_resolves for ex in hold]
        return binary_log_loss(probs, labels), binary_brier(probs, labels)

    def fit(
        self,
        examples: list[TrajExample],
        *,
        arm: str,
        seed: int,
        k_max: int = 4,
    ) -> None:
        torch, *_ = _require_train()
        torch.manual_seed(seed)
        if self._model is None:
            self._load()
        model = self._model
        tokenizer = self._tokenizer
        score = self._score
        device = self._device
        assert model is not None and tokenizer is not None and score is not None
        fit_examples, val_examples = carve_fit_val(
            examples, n_val=self.val_size, seed=seed
        )
        self.n_train = len(fit_examples)
        self.n_val = len(val_examples)
        self.val_instance_ids = tuple(ex.instance_id for ex in val_examples)
        model.train()
        score.train()
        rows = train_rows_for_arm(fit_examples, arm=arm, k_max=k_max)
        print(
            f"traj_lora fit arm={arm} seed={seed} n_rows={len(rows)} "
            f"n_train={self.n_train} n_val={self.n_val} "
            f"epochs={self.epochs} max_tokens={self.max_tokens} "
            f"log_dir={self.log_dir}",
            flush=True,
        )
        self._append_jsonl(
            "train_meta.jsonl",
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": "fit_start",
                "arm": arm,
                "seed": seed,
                "n_rows": len(rows),
                "n_train": self.n_train,
                "n_val": self.n_val,
                "n_split_train": len(examples),
                "val_instance_ids": list(self.val_instance_ids),
                "epochs": self.epochs,
                "max_tokens": self.max_tokens,
                "batch_size": self.batch_size,
                "grad_accum": self.grad_accum,
                "learning_rate": self.learning_rate,
                "lora_r": self.lora_r,
                "lora_alpha": self.lora_alpha,
                "qlora": self.qlora,
                "grad_clip_norm": self.grad_clip_norm,
                "early_stopping": self.early_stopping,
                "early_stopping_metric": self.early_stopping_metric,
                "early_stopping_patience": self.early_stopping_patience,
                "early_stopping_min_delta": self.early_stopping_min_delta,
            },
        )
        params = [p for p in model.parameters() if p.requires_grad] + list(score.parameters())
        optimizer = torch.optim.AdamW(params, lr=self.learning_rate)
        loss_fn = torch.nn.CrossEntropyLoss()
        step = 0
        best_state = None
        best_val = None
        bad_epochs = 0
        stopped_epoch = None
        optimizer.zero_grad()
        for _epoch in range(self.epochs):
            epoch_rows = shuffle_train_rows(rows, seed=seed, epoch=_epoch)
            epoch_losses: list[float] = []
            epoch_seq: list[int] = []
            epoch_trunc = 0
            epoch_t0 = time.perf_counter()
            model.train()
            score.train()
            for start in range(0, len(epoch_rows), self.batch_size):
                t0 = time.perf_counter()
                batch = epoch_rows[start : start + self.batch_size]
                texts = [row[0] for row in batch]
                instance_ids = [row[2] for row in batch]
                labels = torch.tensor(
                    [1 if row[1] else 0 for row in batch],
                    dtype=torch.long,
                    device=device,
                )
                encoded = tokenizer(
                    texts,
                    padding=len(texts) > 1,
                    truncation=True,
                    max_length=self.max_tokens,
                    return_tensors="pt",
                )
                seq_len = int(encoded["input_ids"].shape[1])
                truncated = seq_len >= self.max_tokens
                encoded = {key: val.to(device) for key, val in encoded.items()}
                gathered = self._last_token_hidden(encoded, torch)
                logits = score(gathered.to(dtype=score.weight.dtype))
                loss = loss_fn(logits, labels) / self.grad_accum
                loss.backward()
                step += 1
                loss_val = float(loss.item() * self.grad_accum)
                step_ms = (time.perf_counter() - t0) * 1000
                mem = self._gpu_mem_gb(torch)
                epoch_losses.append(loss_val)
                epoch_seq.append(seq_len)
                epoch_trunc += int(truncated)
                self._append_jsonl(
                    "train.jsonl",
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "arm": arm,
                        "seed": seed,
                        "step": step,
                        "epoch": _epoch,
                        "n_rows": len(epoch_rows),
                        "instance_id": instance_ids[0] if instance_ids else None,
                        "seq_len": seq_len,
                        "truncated": truncated,
                        "loss": round(loss_val, 6),
                        "lr": self.learning_rate,
                        "step_ms": round(step_ms, 1),
                        "gpu_mem_gb": mem,
                    },
                )
                if step == 1 or step % 25 == 0:
                    print(
                        f"  step={step}/{len(rows) * self.epochs} epoch={_epoch} "
                        f"loss={loss_val:.4f} seq={seq_len} "
                        f"step_ms={step_ms:.0f} mem_gb={mem}",
                        flush=True,
                    )
                if step % self.grad_accum == 0:
                    self._step_optimizer(torch, optimizer, params)
            if step % self.grad_accum != 0:
                self._step_optimizer(torch, optimizer, params)
            mean_loss = sum(epoch_losses) / len(epoch_losses) if epoch_losses else None
            seq_sorted = sorted(epoch_seq)
            mid = len(seq_sorted) // 2
            val_ce, val_brier = self._val_metrics(val_examples, arm=arm)
            summary = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "arm": arm,
                "seed": seed,
                "epoch": _epoch,
                "mean_loss": None if mean_loss is None else round(mean_loss, 6),
                "val_ce": None if val_ce is None else round(val_ce, 6),
                "val_brier": None if val_brier is None else round(val_brier, 6),
                "n_steps": len(epoch_losses),
                "n_truncated": epoch_trunc,
                "seq_p50": seq_sorted[mid] if seq_sorted else None,
                "seq_max": max(seq_sorted) if seq_sorted else None,
                "elapsed_s": round(time.perf_counter() - epoch_t0, 1),
                "gpu_mem_gb": self._gpu_mem_gb(torch),
            }
            self._append_jsonl("train_epochs.jsonl", summary)
            print(
                f"  epoch={_epoch} mean_loss={summary['mean_loss']} "
                f"val_ce={summary['val_ce']} val_brier={summary['val_brier']} "
                f"seq_p50={summary['seq_p50']} seq_max={summary['seq_max']} "
                f"trunc={epoch_trunc} elapsed_s={summary['elapsed_s']}",
                flush=True,
            )
            if self.early_stopping and val_ce is not None:
                improved = (
                    best_val is None
                    or (best_val - val_ce) >= self.early_stopping_min_delta
                )
                if improved:
                    best_val = val_ce
                    bad_epochs = 0
                    best_state = {
                        "model": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
                        "score": {k: v.detach().cpu().clone() for k, v in score.state_dict().items()},
                    }
                else:
                    bad_epochs += 1
                    if bad_epochs >= self.early_stopping_patience:
                        stopped_epoch = _epoch
                        break
        if self.early_stopping and best_state is not None:
            model.load_state_dict(best_state["model"])
            score.load_state_dict(best_state["score"])
        self._append_jsonl(
            "train_meta.jsonl",
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": "fit_end",
                "arm": arm,
                "seed": seed,
                "steps": step,
                "n_train": self.n_train,
                "n_val": self.n_val,
                "stopped_epoch": stopped_epoch,
                "early_stopping_used": bool(self.early_stopping and stopped_epoch is not None),
            },
        )

    def predict_proba(self, texts: list[str]) -> list[float]:
        if self._model is None or self._tokenizer is None or self._score is None:
            raise RuntimeError("TrajLoraBackend.fit must be called first")
        torch, *_ = _require_train()
        model = self._model
        tokenizer = self._tokenizer
        score = self._score
        device = self._device
        model.eval()
        score.eval()
        probs: list[float] = []
        with torch.no_grad():
            for start in range(0, len(texts), max(self.batch_size, 1)):
                batch = texts[start : start + max(self.batch_size, 1)]
                encoded = tokenizer(
                    batch,
                    padding=len(batch) > 1,
                    truncation=True,
                    max_length=self.max_tokens,
                    return_tensors="pt",
                )
                encoded = {key: val.to(device) for key, val in encoded.items()}
                gathered = self._last_token_hidden(encoded, torch)
                logits = score(gathered.to(dtype=score.weight.dtype))
                soft = torch.softmax(logits, dim=-1)[:, 1]
                probs.extend(float(x) for x in soft.cpu())
        return probs

    def save(self, path: Path) -> None:
        """Write adapter + score head. Call after fit; weights are otherwise process-local."""
        if self._model is None or self._score is None:
            raise RuntimeError("TrajLoraBackend.fit must be called first")
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        self._model.save_pretrained(target / "adapter")
        self._tokenizer.save_pretrained(target / "adapter")
        torch, *_ = _require_train()
        torch.save(self._score.state_dict(), target / "score.pt")
