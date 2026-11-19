# E10 G0 setup on the DGX Spark (amendment A1, 2026-11-13)

Setup only. No eval or training pass has run; PPO arms (P, P6) untouched.

Spark: `spark-c606`, Ubuntu 24.04.4 (aarch64), GB10 (compute 12.1), driver
580.126.09, 119 GiB RAM, Docker 29.1.3. Work dir `~/e10-work`, logs
`~/e10-logs`. Shared machine: an unrelated `diflh-ollama` container runs.

| Gate | Status | Evidence |
|---|---|---|
| G0a Docker without sudo | pass | user `sanath` is in group `docker`; `--gpus all` sees the GB10 |
| G0b ARM Tenacity image | pass on the Spark (105/105) | `tenacity-arm64.Dockerfile`, `g0b_check.py`, `g0b_arm64.jsonl` |
| G0b x86 comparison | pass (A3, 16 Nov): 105/105 identical to ARM | `g0b_x86_64.jsonl`; see "G0b x86 comparison" below |
| G0c student serving | pass | `serve_student.sh`; FP8 loads, answers, 444 output tok/s at 32 concurrent |
| W E7's grader on ARM (A4) | pass (16 Nov): 105/105 | `w_swesmith_arm_check.jsonl`; see "W" below |
| S live agent session (A4) | pass (16 Nov): 29 steps, features in every response | `s_live_session.json`; see "S" below |
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
test issues pass.

### G0b x86 comparison (amendment A3, 2026-11-16)

Same `g0b_check.py` (md5 `3ed01e95…`) and the same instance file (md5
`6cd9ed87…`, byte-identical to the Spark's), run on `hecate-worker`
(n2-standard-32, x86_64, project `whatsapp-sales-agent`) against E7's image
`jyangballin/swesmith.x86_64.jd_1776_tenacity.0d40e76f:latest` (image id
`sha256:7ec64b27…`). 105/105 OK in about 2 minutes. Compared per instance with
`g0b_arm64.jsonl`: the same `ok` flag, F2P/P2P counts, and empty lists of
unexpected results on all 105, no instance missing on either side. G0b
passes. The worker was started for this run only and stopped after it
(about 6 minutes up).

## W: E7's grader on the ARM image (amendment A4, 2026-11-16)

advisor-models `3c8d8d1` cloned to `~/work/advisor-models-e10`; grading venv
`~/venvs/e10-eval` from `configs/e10_eval_requirements.txt` (swesmith 0.0.9,
swebench 4.1.0). `scripts/e10_check_swesmith_arm.py` with
`SWESMITH_IMAGE_OVERRIDE=hecate/swesmith.arm64.jd_1776_tenacity.0d40e76f:e10`
(the wrapper reports platform `linux/arm64`), 8 workers, run tag
`e10armcheck-20261116-124628`: swesmith's own `run_evaluation` grades the fix
(gold patch) and the bug (empty patch) of every issue. **105/105 OK** (56
train, 49 test) in about 9 minutes: every fix resolved with all listed tests
passing, every bug unresolved with no FAIL_TO_PASS test passing and every
PASS_TO_PASS test passing, both runs `completed`, and the test counts equal to
`g0b_arm64.jsonl`'s. A 2-issue run first (`--limit 2`) also passed. Results:
`w_swesmith_arm_check.jsonl`; swesmith's per-issue logs in
`~/e10-work/swesmith-arm-check/` (9.7 MB). No container was left running.
So D2 holds: E10 grades with E7's grader through `swesmith_arm.py`.

## S: one live agent session (amendment A4, 2026-11-16)

Student: `serve_student.sh` (FP8, `--gpu-memory-utilization 0.40`), answering
on port 8100 after about 290 s; host memory used rose from 6 to 54 GiB.
Agent server: advisor-models `3c8d8d1`, venv `~/venvs/e10-agent`
(mini-swe-agent's dependencies plus Flask; litellm 1.109.1), on
127.0.0.1:8081 with `HOSTED_VLLM_API_BASE=http://localhost:8100/v1`,
`LITELLM_MODEL_REGISTRY_PATH=configs/litellm_local_student_registry.json`,
`SWESMITH_IMAGE_OVERRIDE=hecate/swesmith.arm64.jd_1776_tenacity.0d40e76f:e10`
and `--log-dir ~/e10-logs/agent-sessions-S`. Mini-swe-agent sends no
sampling settings, so the student samples with vLLM's defaults for the
model; this is the setting G1 and every arm use unless an amendment
changes it.

`s_live_session.py`: one session on the first training issue
(`jd__tenacity.0d40e76f.lm_rewrite__0siuyh3e`), model
`hosted_vllm/student`, empty advice (E7's student-alone path), 5 student
steps per call as the training env does. **Pass**: 6 calls, 29 student
steps, then the student submitted (787-character patch) after 171 s. Each of
the 5 non-final responses carried the seven features, in [0, 1], with the
right advice turn and step count; the exit-code window and progress changed
as the run went (progress after a diff change at step 15; no test command was
run, so `no_tests_yet` stayed 1). The agent server logged no error and no
feature-update failure, and wrote the session log
(`…_75afdda2.jsonl`, 74 KB), named as the trajectory writer expects.
The reward was not computed (A4: S is not a result). Report:
`s_live_session.json`. Both servers were stopped afterwards.

## G1, attempt 1: advisor vLLM 0.20 — out of memory at start-up (2026-11-16)

`gate_run.sh g1 0.20`, advisor-models `d9799e8`. The student, eval server
and agent server came up; the trainer then ran out of memory while building
its workers, before any rollout: Ray killed the workers when node memory
reached 122.6 GB, over its threshold of 122.1 GB (95% of 128.5 GB). Peak
used memory in the 10 s log: 113 GiB (minimum available 5 GiB); the log shows
about 42 GiB with the student alone, rising to 92 GiB as the trainer loaded.
Ray's top memory user was `FSDPRefWorkerBase.offload_to_cpu`, 17.6 GB: with
KL loss on, upstream SkyRL builds a separate frozen reference copy of
Qwen2.5-7B and "offloads it to CPU", which on the GB10's unified memory frees
nothing. Upstream has no option to use the policy with its adapter disabled
as the reference, which is what spec §2 specifies. No training step ran; the
cleanup stopped every container and server. Logs: `~/e10-logs/g1-attempt1/`.

## G1, attempt 2: adapter-off reference, advisor vLLM 0.20 — out of memory later (2026-11-16)

advisor-models `e06e2fd` (branch `scott/e10-adapter-off-ref`): the reference
is the policy with its LoRA adapter disabled (spec §2), so no reference actor
is built. That part worked: no reference worker in Ray's memory report, peak
used memory down from 113 to 102 GiB in the 10 s log, and start-up got past
where attempt 1 died. Ray then killed the workers at 114.1 of 119.7 GB (95.4%)
right after the advisor vLLM was put to sleep for the first time: upstream
forces sleep level 1 whenever FSDP syncs only the LoRA adapter (it always does
with FSDP), and level 1 copies the advisor's ~15 GB of base weights to CPU
memory, which on the GB10 is the same pool. Ray's top users at the kill: the
advisor vLLM worker 31.0 GB, the policy worker 12.1 GB (still loading). No
rollout ran. Logs: `~/e10-logs/g1-attempt2/`.

## G1, attempt 3: advisor vLLM 0.15 — out of memory at the same point (2026-11-16)

Same code (`e06e2fd`), advisor vLLM 0.15. Memory held at about 78 GiB with
the student and the advisor vLLM loaded, then rose over about 90 s, while the
policy model loaded, was offloaded to CPU and the advisor vLLM slept at level
1, to 112 GiB in the 10 s log; Ray killed six workers at 114.6 of 119.7 GB
(95.7%). No rollout ran. The lower vLLM share saved about 6 GB, less than the
copies the offloads make: upstream's colocated mode moves models to CPU
memory to free GPU memory, which on the GB10's unified memory duplicates them
instead (policy at start-up, the advisor vLLM's base weights at every sleep).
The unrelated `diflh-ollama` container held 17 MB. Logs: `~/e10-logs/g1-attempt3/`.

## G1, attempts 4–7: models kept resident (2026-11-16)

advisor-models `ea6575a` (`spark_resident.py`): no CPU offload and no vLLM
sleep, since on unified memory both only duplicate weights.

- Attempt 4 (0.15) and 5 (0.15): peak 77–78 GiB, no out-of-memory; the advisor
  vLLM refused to start. With the Ray logs kept (`gate_run.sh` now mounts
  `/tmp/ray`), its own log shows 1.64 GiB for KV cache at 0.15, less than one
  32,768-token conversation needs (~1.75 GiB for Qwen2.5-7B). 0.15 is too
  small.
- Attempt 6 (0.20): KV cache 5.14 GiB; peak 85 GiB; the policy worker failed
  to create its CUDA context ("CUDA error: out of memory") with 33 GiB
  "available": truly free memory was 1.4–3.8 GiB and 34–48 GiB was file cache
  (the weights just read). CUDA on the GB10 cannot use file cache.
  `trim_weight_cache.py` drops the cache of the e10-hf weight files with
  `posix_fadvise(DONTNEED)` (no sudo); on the idle Spark it moved 30 GB from
  cache to free. `gate_run.sh` runs it every 10 s during a gate.
- Attempt 7 (0.20, with trimming): start-up passed and **all 32 rollouts
  ran**: `E10 rollouts: n=32 length=0 not_stop=0 rewarded=17 zeroed=0`
  (setup run; not a result). Generation took 2,441 s (41 min) for one step;
  memory held at 110 GiB used, 8 GiB free throughout. The trainer's first
  forward pass over the batch (32 sequences, longest 26,798 tokens, one at a
  time, SDPA attention since flash-attn has no GB10 build, log-probs chunked by
  1,024) was killed by Ray at 95% within about 20 s. No training update ran
  and no trajectory file was written. Upstream's fused LM-head log-prob option
  is Megatron-only.

Projection from attempt 7: at about 41 min of generation per step, 295 steps
are about 8.5 days per arm and 150 steps about 4.3 days, before training time
and evaluation. Logs: `~/e10-logs/g1/` (attempts 4–6 in `g1-attempt4`–`6`).

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
