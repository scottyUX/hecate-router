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
| Working dir | `~/hecate-mini` (personal clone — see step 2) |
| Budget ceiling | $35 (hard, enforced) — expected ~$24 |
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

## 2. Get the code onto the VM

**Use a personal clone, not `sync_exec_vm.sh`.** `/opt/hecate` is a shared
checkout: group `hecate` can read the tree and write `data/outputs/` only
(`EXECUTION_GCP.md:29`). Pushing a tree into it fails with a wall of
`Cannot utime` / `File exists` / `Cannot mkdir` errors, because tar cannot
overwrite files it does not own. `~/hecate` is a symlink to the same place, so
it hits the same wall.

You still need the onboarding for Docker access:

```bash
gcloud compute ssh hecate-exec --project hecate-506120 --zone us-central1-a
sudo bash /opt/hecate/scripts/onboard_exec_vm_user.sh $(whoami)
exit                      # group membership applies only to new sessions
```

Then clone into your own home directory:

```bash
gcloud compute ssh hecate-exec --project hecate-506120 --zone us-central1-a
cd ~
git clone https://github.com/scottyUX/hecate-router.git hecate-mini
cd hecate-mini && git checkout feat/mini-swe-agent
```

## 3. VM setup

```bash
cd ~/hecate-mini
python3 --version                    # 3.10.12 on hecate-exec; fine
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install -e ".[agent]"

cp /opt/hecate/.env .env 2>/dev/null || echo "OPENROUTER_API_KEY=sk-or-v1-..." > .env
chmod 600 .env
```

Verify the three things that have caused failures before:

```bash
python -c "from hecate.data.tasks import load_swebench_lite; print(len(load_swebench_lite()))"   # 300
docker ps                                                                                        # no sudo needed
df -h ~                                                                                          # 378G free
```

If the dataset load raises
`TypeError: Pickler._batch_setitems() takes 2 positional arguments but 3 were given`,
the venv is Python 3.14. `dill 0.3.8` is broken there and `datasets` is pinned
`<4`, so **do not bump the dependency** — build the venv with `python3.12`.

## 4. Smoke: 3 instances, 3 repos

Already run on 2026-09-18. Both arms, same three instances.

```bash
python scripts/run_miniswe_sweep.py \
  --filter "django__django-10914|sympy__sympy-20590|astropy__astropy-12907" \
  --model qwen/qwen-2.5-<7b|72b>-instruct --workers 3 \
  --global-cost-limit <1|2> --allow-incomplete \
  --output-dir data/outputs/runs/smoke-<arm> --run-id smoke-<arm>
```

No `--platform` — the VM is x86. `--filter` matters: `--tasks N` slices `0:N`
and SWE-bench Lite is ordered by repo, so small smokes otherwise draw from one
repo only. Use a smoke-only `--output-dir`; see 5.0.

### Results

| instance | 7B | 72B |
|---|---|---|
| astropy-12907 | Submitted, 6 calls | **Submitted**, 15 calls, 3,546-char patch |
| django-10914 | **BadRequestError**, 59 calls | **Submitted**, 6 calls, 1,082-char patch |
| sympy-20590 | **BadRequestError**, 39 calls | **Submitted**, 34 calls, 596-char patch |

72B: `{'Submitted': 3}`, 0 empty, $0.2285 total, 243s wall clock at
`--workers 3`. The large arm works end to end and the providers
(DeepInfra/Novita) behave — the failures recorded in
`fmt-pilot-editblocks/manifest.json` are not recurring.

7B failed on the two instances that ran long. Its context fills with its own
output (84% of tokens, measured on a Mac trajectory), so an instance needing
many turns exhausts the window and dies. It is not a provider outage:
`qwen-2.5-7b-instruct` has exactly one provider (Phala) and short runs succeed
against it.

Direct probes against Phala, bypassing mini-SWE: 50,000 chars (25,030 prompt
tokens) succeeds, 70,000 chars fails. Setting `max_tokens=2048` does **not**
help, because at that size the input alone already exceeds the window. There is
no config fix — mini-SWE has no history trimming (`AgentConfig` exposes only
step/cost/wall-time limits).

One caveat on that explanation: 72B's sympy run reached 83,565 chars without
failing, more than either 7B failure, on the same nominal 32k window. So the
effective ceiling is partly provider-side, not purely model context.

## 5. Full run

**Three passes, in order. Run them sequentially, not concurrently.**

Each agent pass is single-model; the third pass merges both arms into one
`generations.jsonl`. `write_generations` opens with `"w"`, and a run invoked
with `--model X` only reads X's directory — so a two-pass-only sequence would
leave a `generations.jsonl` containing just the second model, silently dropping
the first arm's 300 records.

Run everything under `tmux` so an SSH drop does not kill a multi-hour job:

```bash
tmux new -s sweep        # detach: Ctrl-B then D;  reattach: tmux attach -t sweep
```

### 5.0 Clear any smoke output first

Upstream resume skips instances already in `preds.json`, including failed ones.
A smoke left in the run directory freezes its results into the final 300.

```bash
rm -rf data/outputs/runs/sweep-2x300-mini-swe
```

### 5.1 Small arm (~1-2 h, expected ~$1)

```bash
python scripts/run_miniswe_sweep.py --model qwen/qwen-2.5-7b-instruct \
  --workers 8 --global-cost-limit 3 --allow-incomplete \
  --output-dir data/outputs/runs/sweep-2x300-mini-swe \
  --run-id sweep-2x300-mini-swe 2>&1 | tee ~/sweep-7b.log
```

### 5.2 Large arm (~3-4 h, expected ~$23)

```bash
python scripts/run_miniswe_sweep.py --model qwen/qwen-2.5-72b-instruct \
  --workers 8 --global-cost-limit 32 --allow-incomplete \
  --output-dir data/outputs/runs/sweep-2x300-mini-swe \
  --run-id sweep-2x300-mini-swe 2>&1 | tee ~/sweep-72b.log
```

### 5.3 Merge (no API calls, seconds)

No `--model`, so it reads both directories and writes the full 600-record
matrix. `--allow-incomplete` is deliberately absent: a missing pair should fail
loudly here, because `run_execution.py` asserts a complete matrix anyway.

```bash
python scripts/run_miniswe_sweep.py --convert-only \
  --output-dir data/outputs/runs/sweep-2x300-mini-swe \
  --run-id sweep-2x300-mini-swe 2>&1 | tee ~/merge.log
```

Expect `records=600`.

### Running the arms concurrently

Possible but not advised. The arms cannot corrupt each other's agent output
(separate per-model directories and `preds.json` files), and 5.3 rewrites
`generations.jsonl` regardless. The objections are resources: 16 containers at
once, double the concurrent image pulls against a 378G disk, and both arms
hitting OpenRouter together. Sequential also means a problem found in the cheap
arm surfaces before ~$23 is spent on the expensive one. If wall clock matters
more, use `--workers 4` on each.

**Check disk first.** Each instance pulls its own `sweb.eval.x86_64.<instance>`
image at ~2-4GB; 300 instances is several hundred GB. This is the one failure
that can halt a long run with no warning. Prune between passes if needed:

```bash
docker image prune -a -f --filter "until=24h"
```

**Budget.** `--global-cost-limit` is per model *process*, so the sweep ceiling is
$3 + $32 = **$35 hard**, against **~$24 expected** and a $38 target. Per-instance
caps are tier-aware by default (7B $0.10, 72B $0.50).

Measured on the VM smoke, not estimated: 72B cost **$0.0762/instance**
(x300 = $22.85); 7B ~$0.003 (x300 = $0.90). An earlier $14 projection came from
Mac data and was ~75% low, which is why the large arm's ceiling is 32 rather
than 28 — one expensive tail (sympy-20590 alone hit $0.19) should not trip it.

When the global ceiling trips, upstream raises and the remaining instances do
not run, leaving an incomplete matrix. Raise the ceiling and re-run the same
command to resume.

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

- **7B will produce few or no patches.** Across five trajectories on two
  machines it issued **0 edit commands in 100+ commands** — it explores, then
  submits empty. Record it as a finding.
- **`BadRequestError` on long 7B instances.** Its context fills with its own
  output, so instances needing many turns die. 2 of 3 in the smoke. Report
  `exit_status_counts` beside the resolve rate: "7B resolved 4/300" and "7B
  resolved 4/300, of which N were context crashes" support very different
  conclusions, and the manifest already records it.
- **7B failures correlate with turn count, not only difficulty.** A task it
  finishes in ~6 turns succeeds; one needing 40+ fails regardless of whether it
  could have solved it. That is a property of model x window x no-trimming, not
  of capability alone — and it needs stating in any cross-paper comparison,
  since another paper's 7B number on a long-context model measures something
  else.
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
