# mini-SWE-agent in Hecate

**Parallel scaffold** — not Stage-1 single-shot. The agent issues bash commands
inside its own environment; Hecate’s unified-diff parser is **not** used.

Do **not** merge resolve labels from this path with Lite `generations.jsonl`
(Qwen 2.5 7B/72B single-shot). Same rule as [`data/external/README.md`](../data/external/README.md)
for published mini-SWE Verified labels.

## Install

```bash
pip install -e ".[agent]"
```

Default `pip install -e ".[dev]"` does **not** pull `mini-swe-agent` (CI stays
offline and zero-spend).

## Config

[`configs/miniswe.yaml`](../configs/miniswe.yaml) pins:

| Field | Default |
|-------|---------|
| subset | `lite` |
| split | `test` |
| model | `openrouter/qwen/qwen-2.5-7b-instruct` |
| environment | `docker` |
| cost_limit | `3.0` |

Set `OPENROUTER_API_KEY` in `.env` (see [`.env.example`](../.env.example)).

## Dry-run (no Docker / no API)

```bash
python scripts/run_miniswe.py --dry-run
python scripts/run_miniswe.py --dry-run --instance django__django-10914
```

Prints the `mini-extra swebench-single ...` argv after confirming the package
imports.

## Live single instance

Needs Docker (x86 images; ARM Mac has the same limits as
[`EXECUTION_GCP.md`](EXECUTION_GCP.md)) and a provider key:

```bash
python scripts/run_miniswe.py \
  --instance django__django-10914 \
  --model openrouter/qwen/qwen-2.5-7b-instruct \
  --output-dir data/outputs/runs/miniswe-smoke
```

Equivalent upstream CLI:

```bash
mini-extra swebench-single \
  --subset lite \
  --split test \
  --model openrouter/qwen/qwen-2.5-7b-instruct \
  -i django__django-10914 \
  --exit-immediately
```

## What this branch does not do

- Amend Stage-1 constitution / multi-turn invariants
- Wire into `run_generation` / `extract_patch` / apply repair
- Batch 300/500 sweeps or router training on new agent labels
