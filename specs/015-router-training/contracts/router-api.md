# Contract: `hecate.router` API

Public surface consumed by `scripts/run_train.py` and tests.

## Dataset

```python
def build_examples(
    labels: list[RoutingLabel],
    generations: list[GenerationRecord],
    *,
    tokenizer: Tokenizer,
    max_tokens: int = 2048,
) -> tuple[list[RouterExample], dict[str, int]]:
    """Join labels to m1 prompts. counts include skipped_incomplete, skipped_no_text, truncated."""
```

`RouterExample.text` MUST NOT contain `extracted_patch`.

## Splits

```python
def assign_folds(
    examples: list[RouterExample],
    *,
    n_folds: int = 5,
    seed: int = 0,
) -> FoldAssignment:
    """Prefer label×repo strata; fall back to repo, then round-robin."""
```

## Metrics

```python
def route_metrics(
    examples: list[RouterExample],
    scores: list[float],
    *,
    lambdas: tuple[float, ...] | None = None,
) -> dict[str, float]:
    """always_m1/m2, random, oracle, route_auc, best_lambda, best_route_rate."""
```

Serve rule: m1 if `score >= λ` else m2. Routed resolve uses that model’s `*_resolves` bit.

## Backends

```python
class EncoderBackend(Protocol):
    def fit(self, texts: list[str], labels: list[bool], *, seed: int) -> None: ...
    def predict_proba(self, texts: list[str]) -> list[float]: ...
```

`ScriptedBackend` MUST NOT import torch. `ModernBertBackend` MAY import torch/transformers inside methods.

## Runner

```python
def run_train(config: TrainConfig, *, backend: EncoderBackend | None = None) -> TrainResult:
    """Write examples.jsonl, metrics.json, manifest.json under output_dir."""
```

| ID | Rule |
|----|------|
| R-1 | Patch text is never concatenated into `text` |
| R-2 | Default pytest path uses ScriptedBackend |
| R-3 | Route-AUC ≤ 0 still writes artifacts (`go_nogo=floor`) |
| R-4 | Manifest includes split_strategy and truncation_rate |
