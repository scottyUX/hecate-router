# E10 runbook: working on the DGX Spark

For a lab member running E10 on the Spark over SSH. The spec (`spec.md`,
rev 5 with amendments A1 and A2) is the source of truth; this file only says
how to carry it out. If the two disagree, stop and ask Scott.

## 0. Rules before anything else

- **Run only what an amendment authorizes.** Today (13 Nov) that is setup
  (A1) and the upstream SkyRL toolchain check (A2). Nothing for the PPO arms
  (P, P6), no gate G1–G4, and no E10 training or eval pass, until Scott adds
  an amendment to `spec.md` that says so. This is what keeps the
  pre-registration honest: no one sees an E10 number before the rules are
  fixed.
- **Use your own account** (`krishna`) and your own SSH key. Never use
  someone else's key or account.
- **No `sudo`, no reboots, no sleep, no firmware updates** (`fwupdmgr`), no
  driver changes. If something seems to need them, ask Scott.
- **Shared machine.** Before starting anything on the GPU, check `free -h`
  and `docker ps`; another project's `diflh-ollama` container runs there.
  Stop your servers when you are done. Do not touch containers, images or
  files you did not create, except the E10 ones listed in §2.
- **Long jobs in tmux, output to a log file**, e.g.
  `tmux new -d -s job 'cmd > ~/e10-logs/job.log 2>&1'`, then
  `tail -n 50 ~/e10-logs/job.log`.
- **Check disk before downloads**: `df -h /`.
- **No secrets in git or logs.** E10 uses no API keys.

## 1. Access

1. Join the lab's Tailscale network (Scott sends the invite).
2. `ssh krishna@100.100.25.117`
3. Check: `id` lists `docker`; `docker run --rm --gpus all
   nvcr.io/nvidia/cuda:13.0.0-base-ubuntu24.04 nvidia-smi` shows `NVIDIA GB10`.

Get the code (both repos are public):

```bash
mkdir -p ~/work ~/e10-logs && cd ~/work
git clone https://github.com/scottyUX/hecate-router.git hecate
git clone -b scott/train-2xa100 https://github.com/scottyUX/advisor-models.git
git clone https://github.com/NovaSky-AI/SkyRL.git && git -C SkyRL checkout 3e8700f
```

## 2. What is already on the Spark

Built and checked on 13 Nov (`spark/README.md` has the evidence). Docker
images and volumes are visible to every member of the `docker` group.

| Item | Name | What it is |
|---|---|---|
| Student server | `vllm/vllm-openai:v0.20.0` | Serves Qwen3-Coder-30B-A3B FP8 |
| Trainer | `hecate/skyrl-upstream-e10:3e8700f` | Upstream SkyRL, torch 2.14, vLLM 0.33, CUDA 13 |
| Test container | `hecate/swesmith.arm64.jd_1776_tenacity.0d40e76f:e10` | ARM rebuild of the Tenacity SWE-smith image |
| Model weights | Docker volume `e10-hf` | Qwen3-Coder-30B-A3B-Instruct-FP8, Qwen2.5-7B-Instruct |
| Old trainer (do not use) | `hecate/skyrl-e10:arm64` | E7's SkyRL fork; does not run on the GB10 |

Mount the weights with `-v e10-hf:/root/.cache/huggingface`. Do not
download them again.

Two settings every SkyRL run on the Spark needs (flash-attn kernels are not
built for the GB10; see `spark/README.md`):
`trainer.flash_attn=false trainer.remove_microbatch_padding=false`.

## 3. Reproduce the setup checks (authorized, about 30 min)

Do these first, to confirm your access works. Files are in
`~/work/hecate/experiments/e10-ppo-vs-grpo-advisor/spark/`.

**Student server (G0c).** Starts in ~5 min, holds ~40% of GPU memory.

```bash
cd ~/work/hecate/experiments/e10-ppo-vs-grpo-advisor/spark
tmux new -d -s e10-student './serve_student.sh > ~/e10-logs/student.log 2>&1'
curl -s localhost:8100/v1/models          # repeat until it answers
docker stop e10-student                    # when done
```

**Test container (G0b).** All 105 issues should print `OK`.

```bash
python3 make_instances.py ~/work/advisor-models ~/e10-logs/tenacity_instances.jsonl
tmux new -d -s e10-g0b "python3 g0b_check.py hecate/swesmith.arm64.jd_1776_tenacity.0d40e76f:e10 \
  ~/e10-logs/tenacity_instances.jsonl ~/e10-logs/g0b.jsonl > ~/e10-logs/g0b.log 2>&1"
grep -c '^OK' ~/e10-logs/g0b.log    # expect 105 when finished (a few minutes)
```

**Trainer toolchain check (A2).** 3 GRPO+LoRA steps on GSM8K with a 0.5B
model, about 5 min. Not an E10 result.

```bash
mkdir -p ~/e10-work/toolchain
cp toolchain_gsm8k_grpo_lora.sh ~/e10-work/toolchain/run.sh
tmux new -d -s e10-tc "docker run --rm --gpus all --ipc=host --shm-size=16g \
  -v $HOME/e10-work:/w -v e10-hf:/root/.cache/huggingface \
  hecate/skyrl-upstream-e10:3e8700f bash /w/toolchain/run.sh > ~/e10-logs/toolchain.log 2>&1"
grep -a "trainer/global_step" ~/e10-logs/toolchain.log   # expect 1, 2, 3
```

## 4. Next task: port E7's environment to upstream SkyRL (A2)

Code work, done on a branch and reviewed by Scott before anything runs with
it.

- Source: `advisor-models/advisor_models/swe_smith/` (`env.py`,
  `main_swe_smith.py`, `config.py`, `agent_server.py`, `eval_server.py`).
- Target: upstream SkyRL `3e8700f`. `SWESmithEnv` subclasses skyrl-gym's
  `BaseTextEnv`, whose `init`/`step` contract upstream kept, so `env.py`
  should carry over with small changes. The entrypoint moves to
  `skyrl.train.entrypoints.main_base`, and config names follow upstream.
- The agent and eval servers run on the Spark against the ARM test image
  and the local student (`http://localhost:8100/v1`, model `student`).
- Unit test: the ported reward gives the same scores as E7's on fixture
  rollouts (spec G4). Tests must not need a GPU, network or model.
- Do not add anything for the PPO arms.

Open a pull request on `scottyUX/advisor-models` and tell Scott. Do not
start a training run with it.

## 5. Reporting

- Keep logs in `~/e10-logs/` and note in the PR what you ran, when, and
  what happened, including failures.
- Anything unexpected (a test container mismatch, out of memory, a crash):
  stop, save the log, and tell Scott. Do not work around it by changing a
  setting the spec fixes.
