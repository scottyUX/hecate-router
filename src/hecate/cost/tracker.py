"""Token accounting and hard budget guard (S10).

Prices and budget bounds come from ``configs/option_a.yaml``. The tracker
maintains a running USD total on disk, authorizes proposed paid calls against
the hard ceiling using an upper-bound estimate, and records actual spend after
each call. Soft target is status-only.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

LEDGER_SCHEMA_VERSION = 1


class CostError(Exception):
    """Base error for cost accounting and budget guard failures."""


class BudgetExceededError(CostError):
    """Raised when a proposed estimate would breach the hard ceiling."""

    def __init__(
        self,
        *,
        total_usd: float,
        ceiling_usd: float,
        estimate_usd: float,
    ) -> None:
        self.total_usd = total_usd
        self.ceiling_usd = ceiling_usd
        self.estimate_usd = estimate_usd
        remaining = max(0.0, ceiling_usd - total_usd)
        super().__init__(
            "budget exceeded: refusing call — "
            f"total_usd={total_usd:.6f} ceiling_usd={ceiling_usd:.6f} "
            f"estimate_usd={estimate_usd:.6f} remaining_usd={remaining:.6f}"
        )


class CostConfigError(CostError):
    """Invalid or missing budget/pricing configuration."""


class CostLedgerError(CostError):
    """Corrupt, unreadable, or schema-invalid cost ledger."""


class CostAccountingError(CostError):
    """Invalid tokens, unknown model slug, or non-finite cost values."""


@dataclass(frozen=True)
class BudgetConfig:
    target_usd: float
    ceiling_usd: float


@dataclass(frozen=True)
class ModelPricing:
    slug: str
    input_cost_per_1m: float
    output_cost_per_1m: float


@dataclass(frozen=True)
class BudgetStatus:
    total_usd: float
    target_usd: float
    ceiling_usd: float
    remaining_usd: float
    target_exceeded: bool


def _repo_root() -> Path:
    # src/hecate/cost/tracker.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3]


def _default_config_path() -> Path:
    return _repo_root() / "configs" / "option_a.yaml"


def default_ledger_path() -> Path:
    return _repo_root() / "data" / "outputs" / "cost" / "ledger.json"


def _require_finite_non_negative(name: str, value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise CostAccountingError(f"{name} must be a finite number, got {type(value)!r}")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise CostAccountingError(f"{name} must be finite and >= 0, got {value!r}")
    return number


def _require_token_count(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CostAccountingError(f"{name} must be a non-negative int, got {type(value)!r}")
    if value < 0:
        raise CostAccountingError(f"{name} must be a non-negative int, got {value!r}")
    return value


def _validate_budget(target_usd: float, ceiling_usd: float) -> BudgetConfig:
    if not math.isfinite(target_usd) or target_usd < 0:
        raise CostConfigError(f"budget.target_usd must be finite and >= 0, got {target_usd!r}")
    if not math.isfinite(ceiling_usd) or ceiling_usd <= 0:
        raise CostConfigError(f"budget.ceiling_usd must be finite and > 0, got {ceiling_usd!r}")
    return BudgetConfig(target_usd=float(target_usd), ceiling_usd=float(ceiling_usd))


def load_budget_config(config_path: Path | str | None = None) -> BudgetConfig:
    path = Path(config_path) if config_path is not None else _default_config_path()
    try:
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except OSError as exc:
        raise CostConfigError(f"cannot read config: {path}") from exc
    if not isinstance(data, dict):
        raise CostConfigError(f"config root must be a mapping: {path}")
    budget = data.get("budget")
    if not isinstance(budget, dict):
        raise CostConfigError(f"'budget' missing or invalid in config: {path}")
    if "target_usd" not in budget or "ceiling_usd" not in budget:
        raise CostConfigError(f"'budget.target_usd' and 'budget.ceiling_usd' required: {path}")
    return _validate_budget(budget["target_usd"], budget["ceiling_usd"])


def load_model_pricing(config_path: Path | str | None = None) -> dict[str, ModelPricing]:
    path = Path(config_path) if config_path is not None else _default_config_path()
    try:
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except OSError as exc:
        raise CostConfigError(f"cannot read config: {path}") from exc
    if not isinstance(data, dict):
        raise CostConfigError(f"config root must be a mapping: {path}")
    models = data.get("models")
    if not isinstance(models, list) or not models:
        raise CostConfigError(f"'models' missing or empty in config: {path}")
    pricing: dict[str, ModelPricing] = {}
    for index, model in enumerate(models):
        if not isinstance(model, dict):
            raise CostConfigError(f"models[{index}] must be a mapping in {path}")
        slug = model.get("slug")
        if not slug or not isinstance(slug, str):
            raise CostConfigError(f"models[{index}].slug missing in {path}")
        try:
            inp = float(model["input_cost_per_1m"])
            out = float(model["output_cost_per_1m"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CostConfigError(
                f"models[{index}] missing valid input/output_cost_per_1m in {path}"
            ) from exc
        if not math.isfinite(inp) or inp < 0 or not math.isfinite(out) or out < 0:
            raise CostConfigError(
                f"models[{index}] costs must be finite and >= 0 in {path}"
            )
        pricing[slug] = ModelPricing(
            slug=slug,
            input_cost_per_1m=inp,
            output_cost_per_1m=out,
        )
    return pricing


def estimate_cost(
    model_slug: str,
    prompt_tokens: int,
    completion_tokens: int,
    pricing: dict[str, ModelPricing] | None = None,
) -> float:
    """Return USD cost for token usage against the pricing table."""
    table = pricing if pricing is not None else load_model_pricing()
    if model_slug not in table:
        raise CostAccountingError(f"unknown model slug (no pricing): {model_slug!r}")
    prompt = _require_token_count("prompt_tokens", prompt_tokens)
    completion = _require_token_count("completion_tokens", completion_tokens)
    rates = table[model_slug]
    cost = (prompt / 1_000_000.0) * rates.input_cost_per_1m + (
        completion / 1_000_000.0
    ) * rates.output_cost_per_1m
    if not math.isfinite(cost) or cost < 0:
        raise CostAccountingError(f"computed non-finite cost for {model_slug!r}: {cost!r}")
    return cost


class CostTracker:
    """Running USD total with hard-ceiling authorization and disk persistence."""

    def __init__(
        self,
        *,
        ledger_path: Path | str | None = None,
        budget: BudgetConfig | None = None,
        pricing: dict[str, ModelPricing] | None = None,
        config_path: Path | str | None = None,
    ) -> None:
        self._ledger_path = (
            Path(ledger_path) if ledger_path is not None else default_ledger_path()
        )
        self._budget = budget if budget is not None else load_budget_config(config_path)
        self._pricing = (
            pricing if pricing is not None else load_model_pricing(config_path)
        )
        self._total_usd = self._load_total()

    @property
    def total_usd(self) -> float:
        return self._total_usd

    def status(self) -> BudgetStatus:
        ceiling = self._budget.ceiling_usd
        target = self._budget.target_usd
        total = self._total_usd
        return BudgetStatus(
            total_usd=total,
            target_usd=target,
            ceiling_usd=ceiling,
            remaining_usd=max(0.0, ceiling - total),
            target_exceeded=total > target,
        )

    def authorize(self, estimate_usd: float) -> None:
        estimate = _require_finite_non_negative("estimate_usd", estimate_usd)
        if self._total_usd + estimate > self._budget.ceiling_usd:
            raise BudgetExceededError(
                total_usd=self._total_usd,
                ceiling_usd=self._budget.ceiling_usd,
                estimate_usd=estimate,
            )

    def record(self, actual_usd: float) -> None:
        actual = _require_finite_non_negative("actual_usd", actual_usd)
        self._total_usd += actual
        self._save_ledger()

    def record_usage(
        self,
        model_slug: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        actual = estimate_cost(
            model_slug,
            prompt_tokens,
            completion_tokens,
            pricing=self._pricing,
        )
        self.record(actual)
        return actual

    def _load_total(self) -> float:
        path = self._ledger_path
        if not path.exists():
            return 0.0
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CostLedgerError(f"unreadable cost ledger: {path}") from exc
        if not isinstance(data, dict):
            raise CostLedgerError(f"ledger root must be an object: {path}")
        version = data.get("schema_version")
        if version != LEDGER_SCHEMA_VERSION:
            raise CostLedgerError(
                f"unsupported ledger schema_version={version!r} "
                f"(expected {LEDGER_SCHEMA_VERSION}): {path}"
            )
        if "total_usd" not in data:
            raise CostLedgerError(f"ledger missing total_usd: {path}")
        try:
            total = float(data["total_usd"])
        except (TypeError, ValueError) as exc:
            raise CostLedgerError(f"ledger total_usd invalid: {path}") from exc
        if not math.isfinite(total) or total < 0:
            raise CostLedgerError(f"ledger total_usd must be finite and >= 0: {path}")
        return total

    def _save_ledger(self) -> None:
        path = self._ledger_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "total_usd": self._total_usd,
            "target_usd": self._budget.target_usd,
            "ceiling_usd": self._budget.ceiling_usd,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        fd, tmp_name = tempfile.mkstemp(
            prefix=f"{path.name}.tmp-",
            dir=str(path.parent),
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        except Exception:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
