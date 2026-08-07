# Hecate Router

> Repository: [`scottyUX/hecate-router`](https://github.com/scottyUX/hecate-router). Product name remains **Hecate**.

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

**This repository currently covers Stage 1 only** — patch generation. Stage 1 does not test whether patches work; that is Stage 2.

## Stage 1 objective

For each of the 300 SWE-bench Lite tasks, collect one attempted fix ("patch") from each of four models, using an identical generation setup.

**Output:** 1,200 patches (4 models × 300 tasks) plus full metadata, stored in a schema that downstream stages can read.

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
| Strong (large) | Llama 3.3 70B | escalation target |
| Weak (small) | Qwen 2.5 7B | cheap default |
| Weak (small) | Llama 3.1 8B | cheap default |

Provider: OpenRouter. Budget target ≈ $38; hard ceiling $100. See [`configs/option_a.yaml`](configs/option_a.yaml) — slugs, prices, and a 1,200-sample dry-run cost estimate are recorded (S4).

## Project boards

- **GCP route API (this board):** [Hecate Router](https://github.com/users/scottyUX/projects/6) — epic [#41](https://github.com/scottyUX/hecate-router/issues/41) (`POST /v1/route` on Cloud Run). Stage 1 / E-M3–E-M6 issues remain open and continue in parallel.
- **Stage 1 / pipeline epics:** existing issues (#1–#20 and related) — not closed by the GCP serve board.

## Lab webpage

Project overview and pipeline status: [`web/`](web/) (static site). Preview locally:

```bash
python -m http.server 8080 --directory web
```

Deploy via GitHub Pages — see [`web/README.md`](web/README.md).

## Quick start

```bash
git clone git@github.com:scottyUX/hecate-router.git
cd hecate-router
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

## Repository layout

```
hecate/
├── configs/option_a.yaml     # models, tiers, budget
├── src/hecate/
│   ├── data/                 # SWE-bench Lite loading, record schema
│   ├── scaffold/             # context builder, prompt template
│   ├── generation/           # OpenRouter client, patch extraction
│   ├── caching/              # content-hash keyed cache
│   ├── cost/                 # token accounting + budget guard
│   └── utils/                # logging, manifests, hashing
├── scripts/
│   ├── run_pilot.py          # 20 tasks × 1 model
│   └── run_sweep.py          # 4 models × 300 tasks
├── data/                     # gitignored: raw/, cache/, outputs/
└── tests/
```

## Open question (deferred to advisors)

Label scheme for Stage 3 — **binary "escalate?"** vs. **multiclass "cheapest-resolver."** Stage 1 stores outputs richly enough to defer this until after the pilot reveals the small/large solve-rate split.

## License

MIT — see [LICENSE](LICENSE).
