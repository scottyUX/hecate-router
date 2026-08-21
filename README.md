# Hecate

**Hecate** is a lightweight routing framework for LLM-assisted software engineering. A small encoder-based router (DistilBERT-class) predicts whether a coding or debugging task can be handled by a *small* model or must be *escalated* to a *large* model — preserving task success while cutting expensive large-model calls.

Hecate's distinguishing idea: routing labels are **execution-grounded**. For each task, several models generate code patches; the patches are applied and run against the project's tests. The cheapest model tier that actually resolves the task defines the label.

## Pipeline stages

| Stage | Description |
|-------|-------------|
| **1 — Patch generation** | Collect one attempted fix per (task, model) pair |
| **2 — Execution** | Apply patches and run tests (Docker harness) |
| **3 — Label construction** | Derive routing labels from execution outcomes |
| **4 — Router training** | Fine-tune the encoder router on labeled data |
| **5 — Evaluation** | Compare router vs. baselines |

Later, the router is fine-tuned on AI-usage data from an undergraduate SDLC course (staged domain adaptation).

**This repository currently covers Stages 1–4** — patch generation, execution
harness, routing-label construction, and the v1 semantic router trainer.
Stage 2 Docker evaluation is operator-run (local or GCP). Router fine-tune is
opt-in (`pip install -e ".[train]"`). CI stays offline with fake harness/encoder.

## Stage 1 objective

For each of the 300 SWE-bench Lite tasks, collect one attempted fix ("patch") from each of two models (small + large Qwen), using an identical generation setup.

**Output:** 600 patches (2 models × 300 tasks) plus full metadata, stored in a schema that downstream stages can read.

## Non-negotiable invariants

These protect the validity of the eventual routing labels:

1. **Shared scaffold.** Every model receives the *identical* issue text, file context, and prompt. The **only** variable is the model slug.
2. **Single-shot generation (v1).** One prompt → one patch. No multi-turn agent loop.
3. **Oracle / retrieval context.** Target file(s) derived from the gold patch (oracle) or BM25 retrieval — same method for all models.
4. **Full counterfactual matrix.** Persist raw outcomes for *every* (task, model) pair. Do not discard per-pair detail.
5. **Store outputs richly; defer label scheme.** Stage 1 records raw patch + metadata so Stage 3 can derive binary or multiclass labels.
6. **Reproducibility.** Every run writes a manifest: config snapshot, model slugs, timestamp, git commit, total cost.

## Target configuration (Option A)

| Tier | Model | Role |
|------|-------|------|
| Strong (large) | Qwen 2.5 72B | escalation target |
| Weak (small) | Qwen 2.5 7B | cheap default |

Provider: OpenRouter. Budget target ≈ $38; hard ceiling $100. See [`configs/option_a.yaml`](configs/option_a.yaml) — slugs, prices, and a 600-sample dry-run cost estimate are recorded (narrowed for S14 after the small-model selection pilot).

## Project board

Track progress on the [Hecate — Stage 1 GitHub Project](https://github.com/users/scottyUX/projects) (link updated after board setup).

## Lab webpage

Project overview and pipeline status: [`web/`](web/) (static site). Preview locally:

```bash
python -m http.server 8080 --directory web
```

Deploy via GitHub Pages — see [`web/README.md`](web/README.md).

## Quick start

```bash
git clone git@github.com:scottyUX/hecate.git
cd hecate
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Add your OpenRouter API key to .env
pytest   # verify install and .env loading
```

### Run the pilot (once implemented)

```bash
python scripts/run_pilot.py --help
python scripts/run_pilot.py --config configs/option_a.yaml --tasks 20 --model qwen2.5-7b
```

### Run the full sweep (once implemented)

```bash
python scripts/run_sweep.py --help
python scripts/run_sweep.py --config configs/option_a.yaml
```

### Run execution and labels (Stage 2–3)

Offline dry-run (no Docker):

```bash
python scripts/run_execution.py --dry-run --tasks 2
```

Live eval needs Docker (on ARM Mac pass `--namespace none`; x86 GCP can pull prebuilt `swebench` images). Then:

```bash
python scripts/run_labels.py --input data/outputs/runs/<exec-run-id>/executions.jsonl
```

See [`specs/014-execution-labels/quickstart.md`](specs/014-execution-labels/quickstart.md)
and the GCP runbook [`docs/EXECUTION_GCP.md`](docs/EXECUTION_GCP.md).

### Train the v1 router (Stage 4)

Offline tests (no weight download):

```bash
python -m pytest tests/test_router.py -q
```

Live fine-tune after labels exist (`pip install -e ".[train]"`):

```bash
python scripts/run_train.py \
  --labels data/outputs/runs/exec-pilot-20/labels.jsonl \
  --generations data/outputs/runs/sweep-2x300-qwen/generations.jsonl \
  --output-dir data/outputs/runs/router-v1 \
  --run-id router-v1 \
  --backend modernbert
```

See [`specs/015-router-training/quickstart.md`](specs/015-router-training/quickstart.md).

## Repository layout

```
hecate/
├── configs/option_a.yaml     # models, tiers, budget
├── configs/execution.yaml    # Stage-2 harness settings
├── src/hecate/
│   ├── data/                 # SWE-bench Lite loading, record schema
│   ├── scaffold/             # context builder, prompt template
│   ├── generation/           # OpenRouter client, patch extraction
│   ├── caching/              # content-hash keyed cache
│   ├── cost/                 # token accounting + budget guard
│   ├── execution/            # SWE-bench eval adapter, labels, pre-flight
│   ├── router/               # Stage-4 encoder (ModernBERT v1)
│   └── utils/                # logging, manifests, hashing
├── scripts/
│   ├── run_pilot.py          # 20 tasks × 1 model
│   ├── run_sweep.py          # 2 models × 300 tasks
│   ├── run_execution.py      # Stage-2 apply + test
│   ├── run_labels.py         # Stage-3 labels + pre-flight
│   └── run_train.py          # Stage-4 router CV
├── data/                     # gitignored: raw/, cache/, outputs/
└── tests/
```

## Open question (deferred to advisors)

v1 routing labels are binary **m1-resolves** (small-model patch applies and tests
pass), as specified for E-M4. Multiclass **cheapest-resolver** remains deferred.

## License

MIT — see [LICENSE](LICENSE).
