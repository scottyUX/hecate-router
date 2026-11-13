# E10 G0 setup on the DGX Spark (amendment A1, 2026-11-13)

Setup only. No eval or training pass has run; PPO arms (P, P6) untouched.

Spark: `spark-c606`, Ubuntu 24.04.4 (aarch64), GB10 (compute 12.1), driver
580.126.09, 119 GiB RAM, Docker 29.1.3. Work dir `~/e10-work`, logs
`~/e10-logs`. Shared machine: an unrelated `diflh-ollama` container runs.

| Gate | Status | Evidence |
|---|---|---|
| G0a Docker without sudo | pass | user `sanath` is in group `docker`; `--gpus all` sees the GB10 |
| G0b ARM Tenacity image | pass on the Spark (105/105) | `tenacity-arm64.Dockerfile`, `g0b_check.py`, `g0b_arm64.jsonl` |
| G0b x86 comparison | not run | needs `hecate-worker` (~$2); not authorized by A1 |
| G0c student serving | pass | `serve_student.sh`; FP8 loads, answers, 444 output tok/s at 32 concurrent |
| G0d SkyRL, GRPO + LoRA | blocked on E7's fork; **pass with upstream SkyRL** (A2) | see "G0d after A2" below |

## G0b

`hecate/swesmith.arm64.jd_1776_tenacity.0d40e76f:e10` rebuilds
`jyangballin/swesmith.x86_64.jd_1776_tenacity.0d40e76f` (the single image for
all 105 Tenacity issues). `/testbed` is copied verbatim from the x86 image,
including `.git` with every instance branch; the conda env `testbed` has
Python 3.10.16 and the x86 image's 36 pip versions (setuptools pinned to
75.1.0). Only difference: the editable tenacity version label is
`0.1.dev1+g88214ad37` instead of `+g88214ad` (git hash length).

Check, per issue, in a fresh container with no network: check out the
instance branch, restore the files removed by its "Remove F2P Tests" commit
from the "Bug Patch" commit, run `pytest --disable-warnings --color=no
--tb=no --verbose`; then reverse the bug patch and run again. Pass = every
FAIL_TO_PASS test fails on the bug, every PASS_TO_PASS test passes on the bug,
and every listed test passes after the reversal. 56/56 training and 49/49
test issues pass. The same check on the x86 image is the remaining G0b step.

## G0c

`Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8` (30 GB) and `Qwen/Qwen2.5-7B-Instruct`
(15 GB) are in `~/.cache/huggingface`. `vllm/vllm-openai:v0.20.0` (torch
2.11 + CUDA 13.0) serves the student: Cutlass FP8 linear, Triton FP8 MoE
(no tuned MoE config for GB10 yet), weights load in ~3 min. At
`--gpu-memory-utilization 0.40` the KV cache is 14.9 GiB = 162,704 tokens
(2.5 full 65,536-token conversations at once): 32 long rollouts will queue.
This is a G1 input, not a decision.

## G0d

`hecate/skyrl-e10:arm64` installs the advisor-models SkyRL fork with
`--no-deps` on top of `vllm/vllm-openai:v0.20.0`. The fork pins torch 2.7.0
(cu128), vLLM 0.9.2 and x86-only flash-attn and flashinfer wheels; none of
these run on the GB10 (compute 12.1 needs CUDA 13). Import test:

- OK: `ppo_utils`, `trainer`, `vllm_engine` (import only), `main_base`, `skyrl_gym`
- FAIL `models`, `fsdp_worker`: `flash_attn` missing (`bert_padding`
  pad/unpad, and the Triton cross-entropy in `torch_utils`)
- FAIL `vllm_server`: written for vLLM 0.9.2 (`vllm.utils.FlexibleArgumentParser`
  moved); weight sync to vLLM will need the same port
- Untested: transformers is 5.6.2 here (the fork was built on 4.5x)
- LoRA: `models.py` already wraps peft; the FSDP worker does not pass the
  rank, so the A1 LoRA patch (rank/alpha, reference = adapter off, merge
  before sync/export) is still to be written

Decision (13 Nov, amendment A2): use upstream SkyRL instead.

## G0d after A2: upstream SkyRL `3e8700f`

Image `hecate/skyrl-upstream-e10:3e8700f` (`skyrl-upstream.Dockerfile`, 48.7
GB): CUDA 13.0.1 devel base, uv 0.9.4, `uv sync --frozen --extra fsdp`
from upstream's lock. torch 2.14.0+cu130, vLLM 0.33.0, Ray 2.57.0, peft
0.21.0, transformers 5.16.1, flashinfer kernels for sm121a. The GB10 is
seen as compute (12, 1); PyTorch SDPA runs on it.

flash-attn has no aarch64 wheel. It is installed without its CUDA kernels
(`FLASH_ATTENTION_SKIP_CUDA_BUILD=TRUE`), plus a placeholder
`flash_attn_2_cuda` module (`flash_attn_2_cuda.py`) that raises if any
kernel is called. SkyRL imports flash-attn only for pure-PyTorch padding
helpers. Every run must set `trainer.flash_attn=false` (SDPA) and
`trainer.remove_microbatch_padding=false` (which asserts flash-attn).
Building flash-attn for sm_120 is the fallback if either costs too much.

Toolchain check (A2; `toolchain_gsm8k_grpo_lora.sh`): upstream's GSM8K
LoRA example, Qwen2.5-0.5B-Instruct, GRPO, LoRA rank 32 / alpha 32, KL loss
on, colocated FSDP + vLLM on one GB10, 48 training questions, batch 16 × 4
samples, 3 steps. All 3 steps ran with no traceback; after each step the
LoRA was merged and synced to vLLM (2.4–2.8 s); checkpoint `global_step_3`
saved (1.4 GB). Mean reward 0.000 → 0.016 → 0.031 (a 0.5B model, 512-token
cap: only shows the loop runs, not learning). No Tenacity data was used.

Port of E7's environment (next, A2): E7's `SWESmithEnv` subclasses
skyrl-gym's `BaseTextEnv`, whose `init`/`step` contract upstream kept
(only type hints changed and optional `get_metrics` hooks were added), so
`env.py` should carry over almost unchanged. Remaining: the entrypoint
(`skyrl.train.entrypoints.main_base`), upstream config names, and running
E7's agent and eval servers on the Spark against the ARM image and the
local student.
