# Quickstart: Cost Tracker (S10)

Offline verification — no `OPENROUTER_API_KEY`, no network.

## Install / import

```bash
pip install -e ".[dev]"
python -c "from hecate.cost import CostTracker, estimate_cost, BudgetExceededError"
```

## Typical runner-shaped usage

```python
from hecate.cost import CostTracker, estimate_cost, BudgetExceededError

tracker = CostTracker(ledger_path="data/outputs/cost/ledger.json")

# Upper-bound estimate before a paid call (completion = decoding max_tokens).
estimate = estimate_cost(
    model_slug="qwen/qwen-2.5-72b-instruct",
    prompt_tokens=8000,
    completion_tokens=4096,
)
try:
    tracker.authorize(estimate)
except BudgetExceededError as exc:
    print(f"halt: {exc}")  # includes total, ceiling, estimate
    raise

# ... provider call happens in S11 ...

actual = estimate_cost(
    model_slug="qwen/qwen-2.5-72b-instruct",
    prompt_tokens=7900,
    completion_tokens=1200,
)
tracker.record(actual)
print(tracker.status())
```

## Offline verification matrix

| Check | Command / assertion |
|-------|---------------------|
| SC-001 over-budget halt | `pytest tests/test_cost.py -k over_budget -v` |
| SC-002 restart persistence | fresh `CostTracker` on same `tmp_path` ledger |
| SC-003 pricing math | fixture line items vs hand-computed USD |
| SC-004 soft target | total > target, authorize still ok under ceiling |
| SC-005 zero spend | full suite with env scrubbed of API key |

```bash
pytest tests/test_cost.py -v
pytest tests/ -q
```
