# Contract: `hecate.cost` cost / budget API

Public surface re-exported from `hecate.cost`, consumed by the S11 runner.
Signatures are the contract; bodies are defined in implementation.

## Types

```python
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
```

## Exceptions

```python
class CostError(Exception): ...
class BudgetExceededError(CostError):
    total_usd: float
    ceiling_usd: float
    estimate_usd: float
class CostConfigError(CostError): ...
class CostLedgerError(CostError): ...
class CostAccountingError(CostError): ...
```

`BudgetExceededError` message MUST include current total, ceiling, and refused
estimate (FR-005).

## Config helpers

```python
def load_budget_config(config_path: Path | str | None = None) -> BudgetConfig: ...
def load_model_pricing(config_path: Path | str | None = None) -> dict[str, ModelPricing]: ...
```

Default `config_path` is repo `configs/option_a.yaml`.

## Cost helpers

```python
def estimate_cost(
    model_slug: str,
    prompt_tokens: int,
    completion_tokens: int,
    pricing: dict[str, ModelPricing] | None = None,
) -> float: ...
```

- Requires non-negative ints for token counts; unknown slug → `CostAccountingError`.
- If `pricing` is `None`, load from default Option A config.

## Tracker

```python
class CostTracker:
    def __init__(
        self,
        *,
        ledger_path: Path | str | None = None,
        budget: BudgetConfig | None = None,
        pricing: dict[str, ModelPricing] | None = None,
    ) -> None: ...

    @property
    def total_usd(self) -> float: ...

    def status(self) -> BudgetStatus: ...

    def authorize(self, estimate_usd: float) -> None:
        """Raise BudgetExceededError if total + estimate > ceiling."""

    def record(self, actual_usd: float) -> None:
        """Add actual spend and persist ledger."""

    def record_usage(
        self,
        model_slug: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """authorize is NOT implied — compute cost, record it, return USD."""
```

### Semantics (normative)

| ID | Rule |
|----|------|
| K-1 | `authorize`: allow iff `total_usd + estimate_usd <= ceiling_usd` |
| K-2 | `estimate_usd` / `actual_usd` must be finite and `>= 0` |
| K-3 | `record` / `record_usage` persist via atomic temp + `os.replace` |
| K-4 | Missing ledger on init → `total_usd = 0` (not an error) |
| K-5 | Corrupt/schema-invalid ledger on init → `CostLedgerError` |
| K-6 | Soft target never causes `authorize` to raise |
| K-7 | Unknown model slug / invalid tokens → `CostAccountingError` |
| K-8 | Default ledger path: `data/outputs/cost/ledger.json` |
| K-9 | Module never opens a network connection or reads API credentials |

## Module constants

```python
LEDGER_SCHEMA_VERSION: int
def default_ledger_path() -> Path: ...
```
