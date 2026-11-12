# E11 runbook: router PPO vs GRPO on the DGX Spark

For the lab member running E11 over SSH. The spec (`spec.md`, rev 4) is the
source of truth; this file only says how to carry it out. If the two
disagree, stop and ask Scott.

Total machine time is about 7–13 hours of runs plus setup. No API keys, no
cloud machines and no containers for agents are involved.

## 0. Before you start

- [ ] The spec has an "Authorized" amendment from Scott. Without it, do not
      run anything, including step 2.
- [ ] The code changes in spec §5 (`--objective`, the GRPO/PPO losses, the
      critic head, `scripts/fetch_miniswe_costs.py`, the tests) are merged
      on `main`. You run them; you do not change them.
- [ ] You can `ssh` to the Spark with **your own** key or account (Tailscale
      `100.100.25.117`). Never use someone else's key.

## Rules on the Spark (from `CLAUDE.md`)

- No `sudo`, no firmware updates (`fwupdmgr`), nothing that reboots or
  sleeps the machine.
- Long jobs run in `tmux` and log to a file. Never in a bare SSH session.
- Check free disk with `df -h /` before any download.
- The GPU reports memory as "Not Supported" in `nvidia-smi`; use `free -h`.
- It is aarch64 (ARM): use NVIDIA's NGC containers rather than random pip
  wheels.
- Don't change hyperparameters, seeds, the split or the reward. If
  something looks wrong, stop and ask.
- Don't compare arms while runs are going. Comparisons are computed once,
  after all nine runs (spec §8).

## 1. Get the code and data onto the Spark

The labels CSV is in git; the trajectories under `data/raw/` are not, but
the runner checks them, so they must be copied too. From a machine that has
the full repo (Scott's Mac), run:

```bash
rsync -az --exclude .git --exclude .venv --exclude web/node_modules --exclude web/.next --exclude .DS_Store ./ <you>@spark:~/work/hecate/
```

Then on the Spark, record what you got:

```bash
cd ~/work/hecate && git -C . log -1 --format=%h 2>/dev/null; ls data/external data/raw/trajs | head
```

(If the copy has no `.git`, write down the commit hash Scott synced from.)

## 2. Environment (gate G0)

```bash
df -h /
docker images | head
```

Start the newest NGC PyTorch container that has an arm64 build, mounting
the repo, a results folder and the Hugging Face cache. Write the exact tag
you used in your notes.

```bash
mkdir -p ~/hecate-artifacts ~/e11-logs
tmux new -s e11
docker run --gpus all -it --rm --ipc=host -v ~/work/hecate:/workspace/hecate -v ~/hecate-artifacts:/artifacts -v ~/e11-logs:/logs -v ~/.cache/huggingface:/root/.cache/huggingface nvcr.io/nvidia/pytorch:<YY.MM>-py3
```

Inside the container:

```bash
cd /workspace/hecate
pip install -e ".[train,dev]"
python -c "import torch, transformers, peft; print(torch.__version__, torch.cuda.is_available(), transformers.__version__, peft.__version__)"
python -c "import bitsandbytes as bnb, torch; print(bnb.__version__); torch.nn.Linear(8, 8)" && echo BNB_IMPORTS
```

If pip tries to replace the container's torch, stop it and install the
other packages from `pyproject.toml`'s `train` and `dev` lists without
torch. Do not upgrade torch inside the NGC container.

**QLoRA or bf16 (spec §3):** the smoke in step 5 shows whether 4-bit
loading works. Write the answer down; it applies to every arm.

## 3. Offline tests (gate G1)

```bash
python -m pytest tests/test_router_traj.py tests/test_router_rl.py -q
```

All must pass, including the test that `--objective ce` matches today's
loss. If any fails, stop and ask.

## 4. Per-task costs (spec §2)

```bash
python scripts/fetch_miniswe_costs.py
```

It downloads two public SWE-bench files and writes
`data/external/qwen3coder_vs_claude4opus_costs.csv`. It must report 0
missing django costs.

## 5. Smoke: one epoch per arm (gate G2)

No holdout scoring, nothing copied. Uses the smoke config (`epochs: 1`):

```bash
export E11_COMMON="--backend lora --arm k0 --split specialist --hold-repo django/django --seeds 0 --config configs/router_traj_e11_smoke.yaml --allow-unsynced"
python scripts/run_train_traj.py $E11_COMMON --objective ce   --output-dir /logs/smoke-ce   > /logs/smoke-ce.log 2>&1
python scripts/run_train_traj.py $E11_COMMON --objective grpo --output-dir /logs/smoke-grpo > /logs/smoke-grpo.log 2>&1
python scripts/run_train_traj.py $E11_COMMON --objective ppo  --output-dir /logs/smoke-ppo  > /logs/smoke-ppo.log 2>&1
```

From each `training_summary.json`, note the epoch wall time and peak GPU
memory, and from the host `free -h` during a run. Send Scott:

- time per epoch per arm, peak memory, QLoRA or bf16, the container tag;
- projected total = 9 runs × 5 epochs × time per epoch.

If the projection exceeds 72 hours, stop: the spec drops to 2 seeds by
amendment.

## 6. Full runs

Durable copy (gate G3): the runner copies each finished run to
`$HECATE_ARTIFACTS_URI/runs/<run_id>/` and fails if the copy is incomplete.

```bash
export HECATE_ARTIFACTS_URI=/artifacts
export E11_BASE="--backend lora --arm k0 --split specialist --hold-repo django/django"
```

Run ids come from the helper, so nothing is typed by hand:

```bash
python -c "from hecate.utils.run_ids import make_run_id; print(make_run_id(exp=10, arm='grpo', split='specialist', seed=0))"
```

Order: seed 0 for `ce`, `grpo`, `ppo`; then seed 1; then seed 2. Each run
in its own tmux window, for example:

```bash
RID=$(python -c "from hecate.utils.run_ids import make_run_id; print(make_run_id(exp=10, arm='grpo', split='specialist', seed=0))")
python scripts/run_train_traj.py $E11_BASE --objective grpo --seeds 0 --run-id $RID > /logs/$RID.log 2>&1
```

Two runs at once only if the smoke showed enough memory for both.

**While a run is going** (`tail -n 50 /logs/<run_id>.log`):

- loss and validation numbers are printed each epoch; NaN or inf → stop;
- an out-of-memory error → stop;
- early stopping may end a run before epoch 5. That is expected.

**After each run**, check `/artifacts/runs/<run_id>/` has the adapter,
`training_summary.json` and a 46-line `holdout_scores.jsonl`:

```bash
ls /artifacts/runs/$RID && wc -l /artifacts/runs/$RID/holdout_scores.jsonl
```

## 7. Send results back

When all nine runs are done, pack them on the Spark (outside the container):

```bash
cd ~/hecate-artifacts && tar czf ~/e11-runs.tgz runs/exp-11_* && ls -la ~/e11-runs.tgz
```

Tell Scott where the file is, with your notes (container tag, QLoRA or
bf16, any warnings, wall time per run). Scott copies the runs to
`gs://hecate-506120-artifacts/runs/`; the comparison (spec §6–7) is
computed after that.

## Stop and ask Scott when

- the spec has no "Authorized" amendment;
- a test fails, an install fails, or 4-bit and bf16 both fail to load;
- the smoke projects more than 72 hours;
- any run shows NaN/inf, runs out of memory, or crashes twice;
- disk is under 100 GB free;
- anything would need `sudo`, a reboot, or a change to the spec's settings.
