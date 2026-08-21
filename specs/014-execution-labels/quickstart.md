# Quickstart: Execution and Labels

Validate 014 offline, then (optional) run a Docker smoke.

## Prerequisites

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Stage-1 input (default): `data/outputs/runs/sweep-2x300-qwen/generations.jsonl`.

## Offline (CI / no Docker)

```bash
pytest tests/test_data.py tests/test_execution.py
```

Expected: all tests pass with no Docker daemon and no `OPENROUTER_API_KEY`.

Dry-run the execution CLI (matrix check + manifest, no containers):

```bash
python scripts/run_execution.py --dry-run --tasks 2 \
  --output-dir data/outputs/runs/exec-dry
```

## Live smoke (optional, Docker)

Gated tests: `RUN_LIVE_EVAL=1 pytest -m live_eval`.

Gold instance (SWE-bench self-check; on ARM Mac add `--namespace none`):

```bash
python -m swebench.harness.run_evaluation \
  --predictions_path gold \
  --instance_ids astropy__astropy-12907 \
  --max_workers 1 \
  --run_id hecate-smoke-gold
```

Hecate pairs (requires Stage-1 file):

```bash
python scripts/run_execution.py \
  --tasks 1 \
  --instance-ids astropy__astropy-12907 \
  --output-dir data/outputs/runs/exec-smoke \
  --run-id exec-smoke
```

Then labels:

```bash
python scripts/run_labels.py \
  --input data/outputs/runs/exec-smoke/executions.jsonl \
  --output-dir data/outputs/runs/exec-smoke
```

Inspect `executions.jsonl`, `labels.jsonl`, `preflight.json`, and `manifest.json`.

## Full matrix (x86 Docker / GCP)

Use `configs/execution.yaml` (`namespace: swebench` to pull prebuilt images).
Provision and operate the VM with [`docs/EXECUTION_GCP.md`](../../docs/EXECUTION_GCP.md).
Resume by reusing `--output-dir` and `--run-id`. After both models finish:

```bash
python scripts/run_labels.py \
  --input data/outputs/runs/<exec-run-id>/executions.jsonl \
  --output-dir data/outputs/runs/<exec-run-id>
```

Pre-flight `routing_headroom` and `m1_positive_rate_flag` gate E-M4 training (issue #18).
