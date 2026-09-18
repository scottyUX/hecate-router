# Running the agent sweep on hecate-exec

Runbook for `sweep-2x300-mini-swe`: 300 SWE-bench Lite tasks x
{qwen-2.5-7b, qwen-2.5-72b} through mini-SWE-agent, graded by the existing
Stage-2 harness. Pipeline detail is in [`agent-pipeline.md`](agent-pipeline.md).

Model pair kept deliberately as-is, so results are comparable to the
parser-path 600 (`data/output/runs/sweep-2x300-qwen`).

| | |
|---|---|
| Run id / dir | `sweep-2x300-mini-swe` |
| VM | `hecate-exec`, project `hecate-506120`, zone `us-central1-a` |
| Budget ceiling | $33 (hard, enforced) — expected ~$14 |
| `option_a.yaml` target | $38 |

---

## 1. Auth and VM state

```bash
gcloud auth login
gcloud config set project hecate-506120
gcloud compute instances list --zones us-central1-a
```

`hecate-exec` must show `RUNNING`. Start it if not:

```bash
gcloud compute instances start hecate-exec --zone us-central1-a
```

## 2. Sync the tree

```bash
export HECATE_GCP_PROJECT=hecate-506120
./scripts/sync_exec_vm_miniswe.sh
```

Use this script, **not** `sync_exec_vm.sh` — that one scp's a generations file
to a hardcoded destination name and would overwrite the parser-path
`sweep-2x300-qwen/generations.jsonl`.

What it does: creates `data/outputs/runs/sweep-2x300-mini-swe` on the VM, tars
the working tree (excluding `.env`, `.venv*`, `.git`, `data/output*`, caches),
extracts it over `/opt/hecate`, and verifies the VM has an
`OPENROUTER_API_KEY`. It deletes nothing remote and uploads no `.env`.

If the key check fails, set it on the VM directly:

```bash
gcloud compute ssh hecate-exec --zone us-central1-a
vi /opt/hecate/.env        # OPENROUTER_API_KEY=sk-or-v1-...
```

## 3. VM setup

```bash
gcloud compute ssh hecate-exec --project hecate-506120 --zone us-central1-a

cd /opt/hecate && source .venv/bin/activate
pip install -e ".[agent]"

python -c "from hecate.data.tasks import load_swebench_lite; print(len(load_swebench_lite()))"
df -h /                    # see disk note under step 5
```

Expect `300`. If it raises:

```
TypeError: Pickler._batch_setitems() takes 2 positional arguments but 3 were given
```

the venv is Python 3.14. `dill 0.3.8` is broken there and `datasets` is pinned
`<4`, so **do not bump the dependency** — build a 3.12 venv instead:

```bash
python3.12 -m venv .venv312 && source .venv312/bin/activate
pip install -U pip && pip install -e ".[agent]"
```

## 4. Smoke: 3 instances, 3 repos

```bash
python scripts/run_miniswe_sweep.py \
  --filter "django__django-10914|sympy__sympy-20590|astropy__astropy-12907" \
  --model qwen/qwen-2.5-7b-instruct --workers 3 \
  --global-cost-limit 1 --allow-incomplete \
  --output-dir data/outputs/runs/sweep-2x300-mini-swe --run-id sweep-2x300-mini-swe
```

No `--platform` — the VM is x86. `--filter` matters: `--tasks N` slices `0:N`
and SWE-bench Lite is ordered by repo, so small smokes otherwise draw from one
repo only.

Checks four things never yet exercised: native x86 (no Rosetta), `--workers > 1`,
the global ceiling printing `Global cost/call limit: $1.0000 / 0` at startup, and
disk headroom for several ~4GB images.

Expect per instance: `Submitted` / `LimitsExceeded` / `BadRequestError`, ~$0.003
for 7B, a few minutes wall clock.

## 5. Full run

One model at a time, same output dir; the second pass merges both into one
`generations.jsonl`.

```bash
python scripts/run_miniswe_sweep.py --model qwen/qwen-2.5-7b-instruct \
  --workers 8 --global-cost-limit 5 \
  --output-dir data/outputs/runs/sweep-2x300-mini-swe --run-id sweep-2x300-mini-swe

python scripts/run_miniswe_sweep.py --model qwen/qwen-2.5-72b-instruct \
  --workers 8 --global-cost-limit 28 \
  --output-dir data/outputs/runs/sweep-2x300-mini-swe --run-id sweep-2x300-mini-swe
```

**Check disk first.** Each instance pulls its own `sweb.eval.x86_64.<instance>`
image at ~2-4GB; 300 instances is several hundred GB. This is the one failure
that can halt a long run with no warning. Prune between passes if needed:

```bash
docker image prune -a -f --filter "until=24h"
```

**Budget.** `--global-cost-limit` is per model *process*, so the sweep ceiling is
$5 + $28 = $33. Per-instance caps are tier-aware by default (7B $0.10,
72B $0.50). When the global ceiling trips, upstream raises and the remaining
instances do not run — leaving an incomplete matrix that needs
`--allow-incomplete` to convert. The margin over the ~$14 expectation is there so
that stays a safety net, not the stopping condition.

Watch spend live (trajectory costs only appear when an instance ends):

```bash
curl -s -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  https://openrouter.ai/api/v1/credits | python3 -m json.tool
```

**Resume.** Interrupted runs re-run safely: upstream skips instances already in
`preds.json`. Add `--redo-existing` only to force re-runs. Re-merge without
re-running the agent with `--convert-only`.

## 6. Grade and label

```bash
python scripts/run_execution.py \
  --input data/outputs/runs/sweep-2x300-mini-swe/generations.jsonl \
  --output-dir data/outputs/runs/sweep-2x300-mini-swe \
  --run-id sweep-2x300-mini-swe-exec --max-workers 4

python scripts/run_labels.py \
  --input data/outputs/runs/sweep-2x300-mini-swe/executions.jsonl
```

`run_execution.py` fails closed unless every model in `option_a.yaml` is present
for every instance. For a single-model run add `--model <slug>`.

Grading is the slow half — ~155s/instance observed, and unlike the agent phase
(97% API wait) it is CPU-bound, so `--max-workers` matters.

---

## Expected outcomes, not bugs

Consequences of keeping the Qwen2.5 pair for comparability:

- **7B will produce few or no patches.** In smoke testing it issued **0 edit
  commands across 100 commands** on two instances — it explored, then submitted
  empty. Record it as a finding.
- **`BadRequestError` on long instances.** Both models have 32k context and
  mini-SWE resends full history every step with no trimming, so upstream's
  `step_limit: 250` is unreachable. Observed death at call 85.
- **`RepeatedFormatError`.** Format errors run ~10% baseline; three consecutive
  ends a run mid-work.
- **Some failures will not reproduce.** OpenRouter routes per request and
  providers differ (one miscomputed the completion budget by 162 tokens).

## Known gaps

- `run_miniswe_sweep.py` writes **no manifest** and does not copy the run dir to
  `HECATE_ARTIFACTS_URI`, which `CLAUDE.md` requires of every run. `run_sweep.py`
  does. Worth closing before or just after this run.
- A killed instance loses its cost record — `instance_cost` is written only at
  instance end. Use the OpenRouter credits API as the ledger.
- Interrupted runs leave orphaned containers: `docker rm -f $(docker ps -q --filter name=minisweagent)`.
- This branch is behind `main` on `src/hecate/router/*` and `utils/artifacts.py`.
  Harmless here (router training runs on `hecate-traj-l4`, not the exec VM), but
  rebase before doing anything with training or artifact sync from this tree.
