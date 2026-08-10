# Data Model: Cost Tracker & Hard Budget Guard (S10)

## Entity: `BudgetConfig`

```python
@dataclass(frozen=True)
class BudgetConfig:
    target_usd: float      # soft planning target (≈ 38.0)
    ceiling_usd: float     # hard fail-closed ceiling (100.0)
```

Loaded from `configs/option_a.yaml` → `budget.*`. Both must be finite and
`ceiling_usd > 0`; `target_usd` must be finite and `>= 0`.

## Entity: `ModelPricing`

```python
@dataclass(frozen=True)
class ModelPricing:
    slug: str
    input_cost_per_1m: float
    output_cost_per_1m: float
```

Loaded from `models[]` in Option A. Lookup by exact slug string.

## Entity: `CostLedger` (on-disk)

JSON object:

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | int | bump invalidates old files (fail closed) |
| `total_usd` | float | running sum of recorded actuals |
| `target_usd` | float | copied from config at write time (informational) |
| `ceiling_usd` | float | copied from config at write time (informational) |
| `updated_at` | str | ISO-8601 UTC timestamp |

Default path: `data/outputs/cost/ledger.json` (overridable for tests).

## Entity: `BudgetStatus`

```python
@dataclass(frozen=True)
class BudgetStatus:
    total_usd: float
    target_usd: float
    ceiling_usd: float
    remaining_usd: float          # max(0, ceiling - total)
    target_exceeded: bool         # total > target
```

## Computation

```text
cost_usd(prompt_tokens, completion_tokens, pricing) =
    (prompt_tokens / 1e6) * pricing.input_cost_per_1m
  + (completion_tokens / 1e6) * pricing.output_cost_per_1m
```

Maps to `GenerationRecord.cost_usd` when the runner builds records (S11).

## Errors

| Type | When |
|------|------|
| `BudgetExceededError` | `authorize` when `total + estimate > ceiling` |
| `CostConfigError` | missing/invalid budget or pricing config |
| `CostLedgerError` | corrupt/unreadable/schema-invalid ledger on load |
| `CostAccountingError` | missing prices for slug, invalid/missing tokens, non-finite costs |

## Mapping to existing records

No schema change to `GenerationRecord`. S11 sets `cost_usd` from
`estimate_cost(...)` / tracker helpers when writing JSONL.
