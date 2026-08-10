# Contract: `hecate.generation.runner` API

Public orchestration surface consumed by `scripts/run_pilot.py` and tests.
Signatures are the contract; bodies are defined in implementation.

## Types

```python
@dataclass(frozen=True)
class RunConfig:
    config_path: Path
    task_limit: int
    model_slugs: tuple[str, ...]
    dry_run: bool
    output_dir: Path
    cache_dir: Path | None = None
    ledger_path: Path | None = None
    run_id: str | None = None

@dataclass(frozen=True)
class RunResult:
    run_id: str
    manifest_path: Path
    records_path: Path
    pairs_attempted: int
    pairs_cache_hit: int
    pairs_generated: int
    pairs_refused_budget: int
    total_cost_usd: float
```

## Entry points

```python
def load_run_config(
    *,
    config_path: Path | str | None = None,
    tasks: int = 1,
    model: str | None = None,
    dry_run: bool = False,
    output_dir: Path | str | None = None,
) -> RunConfig: ...

async def run_generation(config: RunConfig) -> RunResult: ...
```

When `model` is None, pilot defaults to the first `tier: small` slug in Option A
(`qwen/qwen-2.5-7b-instruct`). Unknown slug → fail closed before the loop.

## Semantics

| ID | Rule |
|----|------|
| R-1 | Shared scaffold: same context + prompt for all models on a task |
| R-2 | Cache hit ⇒ no provider call, no `authorize`, no `record_usage` |
| R-3 | Paid path: authorize upper-bound estimate then `complete` |
| R-4 | `BudgetExceededError` ⇒ no provider call; increment refused count |
| R-5 | Successful paid generation ⇒ cache `put` + `record_usage` |
| R-6 | Failures / parse failures ⇒ no cache `put`; no spend recorded |
| R-7 | Every processed pair appends one `GenerationRecord` to JSONL |
| R-8 | Manifest always written with constitution-required fields |
| R-9 | `dry_run=True` ⇒ no network, no credential required |
| R-10 | Module tests MUST pass offline with zero spend |

## Manifest helper (`hecate.utils.manifest`)

```python
def write_run_manifest(path: Path | str, payload: dict) -> Path: ...
def git_commit_sha() -> str | None: ...
```

## Out of scope

- Changing S7–S10 internal algorithms
- Stage-2 execution fields beyond null placeholders
