"""Offline tests for S10 cost tracker and hard budget guard."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from hecate.cost import (
    LEDGER_SCHEMA_VERSION,
    BudgetConfig,
    BudgetExceededError,
    CostAccountingError,
    CostLedgerError,
    CostTracker,
    ModelPricing,
    estimate_cost,
    load_budget_config,
    load_model_pricing,
)

QWEN_72B = "qwen/qwen-2.5-72b-instruct"


@pytest.fixture
def pricing() -> dict[str, ModelPricing]:
    return load_model_pricing()


@pytest.fixture
def budget() -> BudgetConfig:
    return load_budget_config()


def test_option_a_budget_defaults(budget: BudgetConfig) -> None:
    assert budget.target_usd == 38.0
    assert budget.ceiling_usd == 100.0


def test_estimate_cost_matches_hand_computed(pricing: dict[str, ModelPricing]) -> None:
    # qwen-2.5-72b: in 0.36 / out 0.40 per 1M
    prompt_tokens = 4_000
    completion_tokens = 1_500
    expected = (4_000 / 1e6) * 0.36 + (1_500 / 1e6) * 0.40
    actual = estimate_cost(
        QWEN_72B,
        prompt_tokens,
        completion_tokens,
        pricing=pricing,
    )
    assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)


def test_unknown_slug_raises(pricing: dict[str, ModelPricing]) -> None:
    with pytest.raises(CostAccountingError, match="unknown model slug"):
        estimate_cost("not/a-real-model", 10, 10, pricing=pricing)


def test_negative_tokens_rejected(pricing: dict[str, ModelPricing]) -> None:
    with pytest.raises(CostAccountingError):
        estimate_cost(QWEN_72B, -1, 10, pricing=pricing)
    with pytest.raises(CostAccountingError):
        estimate_cost(QWEN_72B, 10, -1, pricing=pricing)


def test_bool_tokens_rejected(pricing: dict[str, ModelPricing]) -> None:
    with pytest.raises(CostAccountingError):
        estimate_cost(QWEN_72B, True, 10, pricing=pricing)  # type: ignore[arg-type]


def test_record_sums_totals(
    tmp_path: Path,
    budget: BudgetConfig,
    pricing: dict[str, ModelPricing],
) -> None:
    tracker = CostTracker(
        ledger_path=tmp_path / "ledger.json",
        budget=budget,
        pricing=pricing,
    )
    a = tracker.record_usage(QWEN_72B, 1000, 500)
    b = tracker.record_usage(QWEN_72B, 2000, 100)
    assert math.isclose(tracker.total_usd, a + b, rel_tol=0.0, abs_tol=1e-12)


def test_authorize_refuses_over_ceiling(tmp_path: Path, pricing: dict[str, ModelPricing]) -> None:
    tracker = CostTracker(
        ledger_path=tmp_path / "ledger.json",
        budget=BudgetConfig(target_usd=38.0, ceiling_usd=1.0),
        pricing=pricing,
    )
    tracker.record(0.9)
    with pytest.raises(BudgetExceededError) as exc_info:
        tracker.authorize(0.2)
    err = exc_info.value
    assert err.total_usd == 0.9
    assert err.ceiling_usd == 1.0
    assert err.estimate_usd == 0.2
    message = str(err)
    assert "0.900000" in message or "total_usd=0.9" in message
    assert "ceiling_usd=1" in message
    assert "estimate_usd=0.2" in message


def test_authorize_allows_exact_ceiling(
    tmp_path: Path, pricing: dict[str, ModelPricing]
) -> None:
    tracker = CostTracker(
        ledger_path=tmp_path / "ledger.json",
        budget=BudgetConfig(target_usd=38.0, ceiling_usd=1.0),
        pricing=pricing,
    )
    tracker.record(0.6)
    tracker.authorize(0.4)  # 0.6 + 0.4 == 1.0 → allowed


def test_authorize_allows_under_headroom(
    tmp_path: Path, pricing: dict[str, ModelPricing]
) -> None:
    tracker = CostTracker(
        ledger_path=tmp_path / "ledger.json",
        budget=BudgetConfig(target_usd=38.0, ceiling_usd=100.0),
        pricing=pricing,
    )
    tracker.authorize(1.0)


def test_simulated_over_budget_run_halts(
    tmp_path: Path, pricing: dict[str, ModelPricing]
) -> None:
    """SC-001: multi-step simulated run stops before exceeding ceiling."""
    ceiling = 1.0
    tracker = CostTracker(
        ledger_path=tmp_path / "ledger.json",
        budget=BudgetConfig(target_usd=0.5, ceiling_usd=ceiling),
        pricing=pricing,
    )
    calls_authorized = 0
    halted_reason: str | None = None
    # Each step uses a fixed upper-bound estimate of $0.4
    for _ in range(10):
        estimate = 0.4
        try:
            tracker.authorize(estimate)
        except BudgetExceededError as exc:
            halted_reason = str(exc)
            break
        calls_authorized += 1
        tracker.record(0.4)

    assert calls_authorized == 2  # 0.4 + 0.4 = 0.8; third would be 1.2 > 1.0
    assert tracker.total_usd <= ceiling
    assert halted_reason is not None
    assert "budget exceeded" in halted_reason


def test_restart_loads_persisted_total(
    tmp_path: Path,
    budget: BudgetConfig,
    pricing: dict[str, ModelPricing],
) -> None:
    ledger = tmp_path / "ledger.json"
    first = CostTracker(ledger_path=ledger, budget=budget, pricing=pricing)
    first.record(1.25)
    second = CostTracker(ledger_path=ledger, budget=budget, pricing=pricing)
    assert second.total_usd == 1.25


def test_missing_ledger_starts_at_zero(
    tmp_path: Path,
    budget: BudgetConfig,
    pricing: dict[str, ModelPricing],
) -> None:
    tracker = CostTracker(
        ledger_path=tmp_path / "missing.json",
        budget=budget,
        pricing=pricing,
    )
    assert tracker.total_usd == 0.0


def test_corrupt_ledger_fails_closed(
    tmp_path: Path,
    budget: BudgetConfig,
    pricing: dict[str, ModelPricing],
) -> None:
    ledger = tmp_path / "ledger.json"
    ledger.write_text("{not json", encoding="utf-8")
    with pytest.raises(CostLedgerError):
        CostTracker(ledger_path=ledger, budget=budget, pricing=pricing)


def test_schema_invalid_ledger_fails_closed(
    tmp_path: Path,
    budget: BudgetConfig,
    pricing: dict[str, ModelPricing],
) -> None:
    ledger = tmp_path / "ledger.json"
    ledger.write_text(
        json.dumps({"schema_version": LEDGER_SCHEMA_VERSION, "not_total": 1.0}),
        encoding="utf-8",
    )
    with pytest.raises(CostLedgerError, match="total_usd"):
        CostTracker(ledger_path=ledger, budget=budget, pricing=pricing)


def test_soft_target_does_not_block_authorize(
    tmp_path: Path, pricing: dict[str, ModelPricing]
) -> None:
    tracker = CostTracker(
        ledger_path=tmp_path / "ledger.json",
        budget=BudgetConfig(target_usd=1.0, ceiling_usd=100.0),
        pricing=pricing,
    )
    tracker.record(1.5)
    status = tracker.status()
    assert status.target_exceeded is True
    assert status.remaining_usd == pytest.approx(98.5)
    tracker.authorize(0.5)  # still under ceiling
