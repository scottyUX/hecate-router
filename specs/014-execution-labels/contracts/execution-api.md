# Contract: `hecate.execution` API

Public surface consumed by `scripts/run_execution.py`, `scripts/run_labels.py`, and tests.

## Predictions

```python
def has_executable_patch(record: GenerationRecord) -> bool: ...

def to_prediction(record: GenerationRecord) -> dict[str, str]:
    """Return instance_id, model_name_or_path, model_patch."""

def write_predictions(records: list[GenerationRecord], path: Path | str) -> Path:
    """Write JSONL predictions for records that have an executable patch."""
```

## Harness protocol

```python
@dataclass(frozen=True)
class HarnessRequest:
    predictions_path: Path
    run_id: str
    instance_ids: tuple[str, ...]
    dataset_name: str
    split: str
    max_workers: int
    timeout: int
    namespace: str | None
    report_dir: Path
    cache_level: str = "env"
    force_rebuild: bool = False
    modal: bool = False

@dataclass(frozen=True)
class HarnessResult:
    log_dir: Path  # report_dir / "logs" / "run_evaluation" / run_id

class Harness(Protocol):
    def run(self, request: HarnessRequest) -> HarnessResult: ...
```

`SwebenchHarness.run` MUST chdir to `request.report_dir` (or equivalent) so SWE-bench relative `logs/run_evaluation/` lands under the execution run directory.

`ScriptedHarness` writes synthetic `report.json` files for tests and MUST NOT start Docker.

## Merge

```python
def load_instance_report(log_dir: Path, model_slug: str, instance_id: str) -> dict | None:
    """Return the inner report object, or None if report.json is missing."""

def apply_report(record: GenerationRecord, report: dict) -> GenerationRecord:
    """Copy patch_applied, resolved, fail_to_pass, pass_to_pass from a report body."""
```

Report body keys (SWE-bench `include_tests_status=True`): `patch_successfully_applied`, `resolved`, optional `tests_status`.

## Runner

```python
@dataclass(frozen=True)
class ExecutionConfig:
    ...  # see data-model.md

@dataclass(frozen=True)
class ExecutionResult:
    run_id: str
    manifest_path: Path
    records_path: Path
    pairs_attempted: int
    pairs_skipped_resume: int
    pairs_skipped_no_patch: int
    pairs_evaluated: int
    pairs_resolved: int
    pairs_pending: int

def load_execution_config(...) -> ExecutionConfig: ...

def run_execution(
    config: ExecutionConfig,
    *,
    harness: Harness | None = None,
) -> ExecutionResult: ...
```

When `harness` is omitted and `dry_run` is false, use `SwebenchHarness`. Dry-run MUST NOT construct `SwebenchHarness`.

## Semantics

| ID | Rule |
|----|------|
| E-1 | Stage-1 input JSONL is never opened for write |
| E-2 | Missing requested (task, model) pairs → `ValueError` before harness calls |
| E-3 | Resume: `patch_applied is not None` in output JSONL → skip |
| E-4 | No executable patch → record applied/resolved false; no harness call |
| E-5 | Missing `report.json` after harness → do not append; counts as pending |
| E-5b | Missing `report.json` but instance is in SWE-bench `error_ids` → write applied/resolved false (apply/eval error, not retry) |
| E-6 | Manifest always written |
| E-7 | Default pytest path uses an injected harness; no Docker |

## Labels

```python
def build_labels(
    records: list[GenerationRecord],
    *,
    m1_slug: str,
    m2_slug: str,
    positive_rate_threshold: float = 0.15,
) -> tuple[list[RoutingLabel], dict]:
    """Return label rows and pre-flight dict."""
```

| ID | Rule |
|----|------|
| L-1 | `m1_resolves` is True iff the small-model record has `resolved is True` |
| L-2 | Complementarity is exactly one of both / only_m1 / only_m2 / neither |
| L-3 | `routing_headroom = oracle_routing_resolve_rate - always_m2_resolve_rate` |
| L-4 | Tasks missing m1 or m2 are incomplete, not labeled |

## Out of scope

- ModernBERT training
- Mutating Stage-1 generation runs
- Implementing a custom Docker eval loop
