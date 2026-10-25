Experiment 7 — Route-then-Advise
Hecate Lab
Advisor Models SWE (SWE-smith Tenacity) then Hecate escalation · rev 1 — PLANNED
October 17, 2026

Status: Phase 0a pipe smoke done (`_run-2`, eval not trusted). Saturday
2026-10-17 locked the Figure 3 pattern checks below, before any 49-issue
job. Training code lives in the advisor-models fork
(`/Users/scottdavis/advisor-models`, branch `scott/train-2xa100`,
deploy SHA `3ada694`), not `src/hecate/`. Do not add
`experiments/e07/train.py`.

Position in slate: Experiment 7. Does not start, stop, or overwrite E1–E6.

  E6  Generalist K=1 diagnostic
  E7  Route-then-Advise (this document)
  E8  (next)

Roles
-----
Cursor (this session): GCP / DevOps, secrets, VM lifecycle, artifact
durability, review of Claude Code diffs. Does not implement SkyRL or the
agent/eval servers.
Claude Code: implements and runs in `/Users/scottdavis/advisor-models`.
Does not create GCP VMs, open firewall rules, or spend past the cost cap
below without a review pass.

Abstract
--------
Phase 0 reproduces Advisor Models' SWE advice-only result on Tenacity
(Asawa et al., arXiv:2510.02453). Phase 1 adds an escalate action and a
dollar reward (the E7 claim). Phase 0a, authorized 2026-10-17, is a
one-issue pipe smoke only. It cannot headline and is not Q7.1.

Q7.1  Can we reproduce the paper's SWE result (resolve held, steps down)
      on Tenacity with their code and a recorded recipe?
Q7.2  (later, do not start) Does advise-or-escalate beat a one-shot
      router on dollars at matched quality?

1 What is authorized today (Phase 0a)
-------------------------------------

Goal: one weak-alone student pass on **one** Tenacity train issue, through
Docker → agent server → patch → eval server → one result row.

  Script     `python -m advisor_models.swe_smith.eval_swe_smith`
  Data       `data/swe_smith/train_jd__tenacity.json`
  n          `--num_samples 1` (not 56, not 49)
  Model      `openrouter/google/gemini-2.5-flash-lite`
  Workers    `--max_workers 1`
  GPU        none
  Cost cap   $5 for the whole smoke (agent_server default is $3/session)
  Run ID     `exp-07_arm-weakalone_split-tenacity_seed-0`
  Durable    `gs://hecate-506120-artifacts/runs/exp-07_arm-weakalone_split-tenacity_seed-0/`

Planned deviations, locked before the run:

  - Student via OpenRouter, not native Gemini. Needs `OPENROUTER_API_KEY`
    on the **worker**, not only the laptop.
  - One train issue, not the 49-issue test set. Paper numbers
    (61.2% resolve, 19.1 → 14.4 steps) are on the test set. Do not
    compare this smoke to those numbers.

Forbidden today:

  - 56-issue or 49-issue eval
  - Advisor / GRPO / SkyRL / GPU VMs
  - Claiming a paper reproduction
  - Writing secrets into git, scripts, or logs

Done when: one `instance_id` has `resolved` true or false, a step count,
a dollar cost, and the row is in the run dir (local). GCS copy is
Cursor's job after Claude Code says the row exists.

2 After the smoke (not today unless 0a is green and time remains)
-----------------------------------------------------------------

  0b  Same recipe, `--num_samples 3`, same run-id suffix `_run-2` if 0a
      already wrote that id.
  0c  Weak-alone on the **49** validation issues. Still OpenRouter
      unless a Gemini key exists. Still cannot headline as Q7.1.
  0d  Q7.1 confirmatory: paper student (`gemini/gemini-2.5-flash`),
      paper recipe (8×H100, batch 8, 30–40 epochs) or a pre-registered
      cheaper recipe that is labeled as such. The existing
      `scripts/train_swe_smith_1k.sh` (2×A100, batch 4, 18 epochs) is
      a smoke trainer and cannot headline.

3 Infra (Cursor owns)
---------------------

  GCP project   hecate-506120
  Zone          us-central1-a
  Worker        `hecate-exec` (CPU + Docker). Start or create with
                `scripts/provision_exec_vm.sh`. Do not train on it.
  Do not use    `hecate-traj-l4` (1×L4, 24 GB) for 7B GRPO.
  Artifact URI  `gs://hecate-506120-artifacts`
  Ports         agent 8081, eval 8082 (code, not the stale README
                default of 8080 / `--workers 64`).

`eval_server.py` only accepts `--host` and `--port`. Use the source.

4 Decision rule
---------------

Phase 0a has no scientific gate. It passes if the pipe returns a scored
row without a secret leak. Q7.1 is not judged on this run.

5 Result rules (locked 2026-10-17, before any 49-issue job)
-----------------------------------------------------------

We copy Figure 3's pattern, not 61.2 / 19.1 / 14.4. Recipe: Flash-Lite
student (`openrouter/google/gemini-2.5-flash-lite`), 2×A100, 18 epochs,
batch 4. Efficiency-prompt arm is deferred (the prompt is not in the
repo). Three arms.

Checks, judged on the 49 validation issues, three separate `--num_runs 1`
jobs per arm (not `--num_runs 3`, which keeps only the last run):

  1. Trade-off exists, before GRPO. Across the three repeats, untrained
     mean steps per issue are at least 2 below student alone, and
     untrained resolve is below student alone. Step gap under 2: stop.
     Steps drop by at least 2 and resolve does not: "partial — no
     trade-off to recover". Still train. That is not a full check-1 pass.
  2. Trained keeps the speed-up. Mean steps below student alone, close
     to untrained.
  3. Trained recovers resolve. Above untrained. Primary: point estimate
     is at least student-alone minus 10 points. Secondary: report the
     lower 95% bound. The bound is not the gate.
  4. Efficiency prompt deferred.

Eval protocol: full `validation_jd__tenacity.json`, omit `--num_samples`,
same 49, issue-by-issue. All 49 jobs run on `gpu-advisor`, one after
another, same `--max_workers` (4 unless resized, then one value for every
arm). Join with `scripts/compare_swe_arms.py`. Drop an instance from every
arm if it errored in any file.

Checkpoint: highest `global_step_*` via `sort -V`, path
`…/global_step_<N>/policy`. 252 is expected only if the 56-set is
unchanged. Do not sweep checkpoints on the 49. Advisor sampling pinned
on both advisor arms: temperature 0.7, top_p 0.8, top_k 20, min_p 0.0,
max_model_len 32768, served model name `advisor`,
`--api_base http://127.0.0.1:8000/v1/`. No `--is_local`.

Run IDs (`make_run_id` rejects `_run-1`):

  1-issue   exp-07_arm-weakalone_split-tenacitytrain_seed-0_run-3
  56-probe  exp-07_arm-weakalone_split-tenacitytrain_seed-0_run-4
  49 val    exp-07_arm-{weakalone,untrained,trained}_split-tenacityval_seed-0
            then `_run-2` and `_run-3` for the second and third repeats

Saturday train go/no-go (56-probe only, not Figure 3): errors about 0,
and resolved at least 9/56. Below 9/56: PDF fallback (5 tries, train only
if at least 25 remain). More than a couple of errors is infrastructure,
not a student result.

Monday, before GRPO: 56-probe gate holds; check 1 holds or is partial;
OpenRouter topped up to the $300–500 train envelope; resize `hecate-exec`;
kill `vllm serve` (it holds both A100s). Spot `resume_mode=latest` resumes
only after the VM is started and the script is rerun.

Monday card (do not start until the gates above hold):

  gcloud compute instances start hecate-exec gpu-advisor
  set -a; source ~/advisor-models/.env; set +a
  # 49x3 student-alone, then untrained, one job at a time, in tmux
  # vllm from SkyRL/skyrl-train/.venv/bin/vllm
  #   --served-model-name advisor --max-model-len 32768
  # kill vllm, then:
  AGENT_SERVER_URL=http://<worker-int-ip>:8081 \
  EVAL_SERVER_URL=http://<worker-int-ip>:8082 \
  AGENT_MODEL=openrouter/google/gemini-2.5-flash-lite \
  LOGGER=console \
  bash scripts/train_swe_smith_1k.sh 2>&1 | tee runs/<run>/train.log
  # after train: sort -V the export, three trained evals, join script

Known before this lock, so they are not the 49-issue result:

  _run-3  jd__tenacity.0d40e76f.pr_425 resolved, 15 steps, $0.0147,
          one evaluate_sync. Trusted Docker score.
  _run-4  56-probe at --max_workers 4. Errors 52/56. OpenRouter HTTP 402
          in_flight_budget_exhausted. Infrastructure, not a student 0%.
  _run-5  Same probe at --max_workers 1. Errors 45/56, same 402.
          Remaining credit is too low for even one in-flight call to
          clear reliably. Not the Monday gate. Top up OpenRouter before
          any further probe. _run-3 is the only trusted row.

A100 quota in us-central1, us-east1, us-east4, us-west1, us-west4, and
europe-west4 is 0 for NVIDIA_A100_80GB_GPUS, the preemptible counterpart,
A2_CPUS, and PREEMPTIBLE_CPUS. Global GPUS_ALL_REGIONS is 1. A new
increase request on 2026-10-17 was rejected: the project is already at
its daily Quota Increase Requests cap, and a GPUS-ALL-REGIONS preference
from 2026-08-26 is still the only one on file. No gpu-advisor disk until
a quota increase lands. Zone is chosen then.

6 Check 1, recorded 2026-10-23 after seeing run-3
-------------------------------------------------

This section was written after the numbers below were already known.
It is not a pre-registration. `_run-N` here is an attempt number on a
full run id. It is not the repeat index in §5. The 56-probe rows named
`_run-4` and `_run-5` in §5 are `split-tenacitytrain`. They are not
the 49-test files below.

Run-3 (untrained, short context) finished 7/49 resolved, 21.86 mean
steps, 0 errors in its own file, $3.16. Student-alone
`exp-07_arm-weakalone_split-tenacityval_seed-0_run-5` is 22/49, 23.8
steps. The unpaired step gap is 1.94. Those two files had not been
joined when this section was written.

Check 1 is `scripts/compare_swe_arms.py` on these six files only.
Per-issue means. An issue that errored in any file is dropped from
both arms. A mean step gap still under 2 is a final stop. No fourth
pass. No GRPO. An incomplete series (credit stops the set before all
six exist) is no decision: not a stop and not a pass. Top up, then
finish the remaining named passes on the same commit.

  student-alone
    exp-07_arm-weakalone_split-tenacityval_seed-0_run-5
    exp-07_arm-weakalone_split-tenacityval_seed-0_run-6
    exp-07_arm-weakalone_split-tenacityval_seed-0_run-7
  untrained
    exp-07_arm-untrained_split-tenacityval_seed-0_run-3
    exp-07_arm-untrained_split-tenacityval_seed-0_run-4
    exp-07_arm-untrained_split-tenacityval_seed-0_run-5

Does not count: student-alone `split-tenacityval` `_run-4` (49 errors,
empty balance); the unsuffixed untrained attempt (26 errors); untrained
`_run-2` (price file missing). A failed pass is not replaced unless
this section is edited to name the replacement.

Untrained `_run-5` replacement (recorded 2026-10-24 ~02:00 PDT, before
attempt 3 starts). Attempt 1 stopped at 22/49 when the GPU VM was
stopped by hand (23:00 PDT 23 Oct). Attempt 2 stopped at 43/49 when
the Spot VM was preempted (01:09 PDT 24 Oct); a Spot restart at 01:27
was preempted again within a minute. Both are infrastructure stops,
not results; neither wrote a session map. Their logs are kept as
`eval.attempt1.log` and `eval.attempt2.log` in the run dir. Attempt 3
is a full rerun of all 49 issues under the same run id, commit
`93678ef` and flags, on on-demand provisioning (same a2-ultragpu-1g,
same zone and boot disk). Only attempt 3's session map is the gate
file. If attempt 3 is also interrupted, the completed issues are
recovered from its log, only the remaining issues are run on the same
commit and flags, and the two are merged into one map.

Non-inferiority bar (clarification, recorded before any trained
number exists): "student-alone minus 10 points" means the student-alone
three-pass mean from the six-file join, as `compare_swe_arms.py`
computes it (trained minus student-alone at least -0.10 on the joined
issues). The 18/49 figure further down was derived from run-5 alone
and is superseded by this rule.

Order of the four new passes: alone `_run-6`, untrained `_run-4`,
alone `_run-7`, untrained `_run-5`. All four use one commit. Run-5
(student-alone, 18 October) is the checkout that was on the worker
then, `3ada694`, before the 404 retry. Run-3 was scored from the
uncommitted tree that is now `93678ef` (`scott/train-2xa100`). That
SHA difference inside the three-pass set is known. Do not rerun
run-5 to erase it. Record the SHA of each new pass in its run dir.

Advisor eval context, every advisor arm including a later trained
arm: task, last advice, latest observation, 1,024-token reply reserve,
observation tail capped at 60,000 characters. Training still uses the
whole conversation, up to 28,672 prompt tokens and 4,096 reply tokens.
Do not change the eval between arms. A stop under this section is a
stop for the short context. It does not say what a full-history
untrained advisor would have done. No full-history pass is part of
check 1.

Efficiency prompt already ran: 14/49, 26.6 steps, 0 errors, $3.41.
It is a fourth arm. It is not in the six-file gate and it is not the
step baseline.

If check 1 later passes and training starts, non-inferiority is
18/49 (36.7%). 17/49 is 34.7% and fails. The lower 95% bound is
reported and is not the gate. Training keeps
`max_generate_length=4096` and `zero_reward_on_non_stop=true`. The
one-step smoke records the fraction of rollouts that die at that cap.
If nearly all do, stop and revisit this line before the 18 epochs.
GRPO does not start until the worker OpenRouter key shows about $500
still unused.

Training run (recorded 2026-10-24, after check 1 passed, before the smoke)
--------------------------------------------------------------------------

Check 1 passed on the six-file join (results.md, 24 Oct). Training
settings, fixed before any training step runs:

  Code        fork `scott/train-2xa100` at `fc2c988` on the GPU VM
              (adds a logging-only rollout metric and the launcher);
              worker agent/eval servers at `93678ef` (same server code)
  Launcher    `scripts/e07_smoke_then_train.sh`
  Machine     gpu-advisor as a2-ultragpu-2g, on-demand (not Spot: two
              preemptions on 24 Oct); hecate-worker as n2-standard-32
  Student     openrouter/google/gemini-2.5-flash-lite (same as all arms)
  Recipe      unchanged from §5: 18 epochs, batch 4, group 8, LR 1e-6,
              28,672 prompt / 4,096 generation, max_turns 1,
              zero_reward_on_non_stop=true
  Checkpoint  every epoch (CKPT_INTERVAL=14), not every 2. Does not
              change training; limits loss on interruption
  Run name    exp-07_arm-trained_split-tenacitytrain_seed-0
              (smoke: exp-07_arm-trainsmoke_split-tenacitytrain_seed-0,
              no checkpoint written)

Smoke: 4 training issues (func_basic__fyidz2ap, pr_425,
func_basic__wx2vx0ly, combine_file__4gcf36bk), 8 samples, 1 step.
It passes only if all hold: exit 0; no CUDA out-of-memory; at least
one rollout with raw environment reward > 0 before zeroing; error
lines / rollouts <= 0.25; rollouts ended by the length cap / rollouts
<= 0.9. If the length-cap fraction is above 0.9, stop and decide on
max_turns before the 18 epochs. The full run starts only if the smoke
passes.

Abort the full run (stop the GPU) on: OpenRouter 402; Flash-Lite 404s
that survive the retries; more than about 25% of a step's rollouts
errored; two consecutive all-zero-reward steps; CUDA OOM; no
checkpoint by step 14.

The trained arm is scored with the short eval above, on the highest
`global_step_*` export only (`sort -V`). Check 3's bar is the
student-alone three-pass mean minus 10 points on the joined issues,
per the clarification above (24.0% on the current join).

Smoke 1 failed; max_turns deviation and Monday interim (recorded 2026-10-24 ~12:00 PDT, before smoke 2)
--------------------------------------------------------------------------------------------------------

Smoke 1 (`exp-07_arm-trainsmoke_split-tenacitytrain_seed-0`, released
settings) failed the length rule: 30/32 rollouts stopped at the 4,096
response cap; 10 rollouts had raw reward > 0 and 8 of them were zeroed
by `zero_reward_on_non_stop`. Exit 0, no OOM, 0 errors. Mean reward
0.273 before zeroing, 0.057 after.

Deviation from the released code: training uses `generator.max_turns=9`
(fork commit `8809f18`, `MAX_TURNS=9`). Only the 28,672-token prompt cap
then binds, and a resolved rollout keeps the paper's stated reward,
0.5 + 0.5 x (40 - steps)/40. Everything else in the recipe is unchanged.
Reason: the paper describes that reward and never mentions the response
cap; under the released setting most resolved Flash-Lite rollouts score 0.

Smoke 2: `exp-07_arm-trainsmoke_split-tenacitytrain_seed-0_run-2`, same 4
issues and pass rules, `MAX_TURNS=9`. If it passes, the 18-epoch run
`exp-07_arm-trained_split-tenacitytrain_seed-0` starts from the launcher
with `MAX_TURNS=9` and `CKPT_INTERVAL=14`.

Deferred, diagnostic only (does not change this decision): a Flash-student
smoke under the released setting, to measure how often the cap hits the
paper's student; and a question to the authors about their settings.

Monday interim (fixed now, before any trained number): around 22:00 PDT
Sunday 25 Oct, after the latest per-epoch checkpoint, training is paused.
That checkpoint's HF export is served with vLLM on the same GPUs and
scored with one pass of the short-context advisor eval on the 49 test
issues, run id `exp-07_arm-trainedinterim_split-tenacityval_seed-0`.
It is joined against the three-pass student-alone and untrained files
and reported as interim: one pass, partial training, epoch named. It is
not check 2 or check 3. Training then resumes from that checkpoint. The
checks are decided only on the final checkpoint of the full run, three
passes, as above.

Smoke 2 result and sequence parallelism (recorded 2026-10-24 ~13:00 PDT, before smoke 3)
----------------------------------------------------------------------------------------

Smoke 2 (`..._trainsmoke_..._run-2`, `MAX_TURNS=9`, `8809f18`): 11/32
rollouts rewarded, 0 zeroed by length, mean reward 0.285, 0 errors,
8/32 stopped at the 28,672 input limit (all unresolved). Rollouts took
9.1 min. The policy update ran out of GPU memory (CUDA OOM on GPU 0).

Change for smoke 3 and training: `SEQ_PARALLEL=2` (fork `175853a`),
i.e. `trainer.policy.sequence_parallel_size=2` and
`trainer.ref.sequence_parallel_size=2` (Ulysses). This is a parallelism
change only: the algorithm, batch (4 x 8), learning rate, reward and
max_turns 9 are unchanged. Data parallelism on 2 GPUs becomes 1.

Smoke 3: `exp-07_arm-trainsmoke_split-tenacitytrain_seed-0_run-3`, same
4 issues and pass rules, `MAX_TURNS=9 SEQ_PARALLEL=2`. If it passes, the
18-epoch run `exp-07_arm-trained_split-tenacitytrain_seed-0` starts with
the same settings and `CKPT_INTERVAL=14`. If it still runs out of
memory, stop; the next option (CPU offload of policy weights and
optimizer state) is recorded here before it is tried.

The Monday interim (above) is unchanged.

Smoke 3 result, CPU offload, and a 4-GPU fallback (recorded 2026-10-24 ~13:45 PDT, before smoke 4)
---------------------------------------------------------------------------------------------------

Smoke 3 (`..._trainsmoke_..._run-3`, `MAX_TURNS=9 SEQ_PARALLEL=2`,
`175853a`): 19/32 rollouts rewarded, 0 zeroed by length, mean reward
0.490, 0 errors, 5/32 stopped at the input limit, rollouts 7.2 min. The
policy update ran about 100 s and then ran out of GPU memory. Cause: fp32
weights, gradients and Adam state of the 7B policy take about 50-55 GB per
A100 on 2 GPUs, leaving too little for ~31k-token sequences.

Smoke 4: `exp-07_arm-trainsmoke_split-tenacitytrain_seed-0_run-4`, same 4
issues and pass rules, `MAX_TURNS=9 SEQ_PARALLEL=2 CPU_OFFLOAD=1` (fork
`6ae79d9`; FSDP2 CPUOffloadPolicy for the policy). Memory placement only:
algorithm, batch, learning rate, reward unchanged. If it passes and the
step takes 15 minutes or less, the 18-epoch run starts with these settings
and `CKPT_INTERVAL=14`.

Fallback, if smoke 4 fails or a step takes more than 15 minutes: an
a2-ultragpu-4g (4 x A100-80GB) on the same boot disk, flex-start,
`NUM_GPUS=4 MAX_TURNS=9`, CPU offload off, sequence parallelism chosen in
that smoke's spec entry. Quota for it was approved on 24 Oct (A100-80GB
spot and on-demand 4, A2 and preemptible CPUs 96). Global batch 4 x 8 is
unchanged by the GPU count. LoRA is not used: this SkyRL's FSDP worker does
not pass a LoRA rank, and it would change the recipe.

The Monday interim (above) is unchanged.

Smoke 4 passed; training started; 4-GPU request (recorded 2026-10-24 ~14:30 PDT)
---------------------------------------------------------------------------------

Smoke 4 (`..._trainsmoke_..._run-4`, `MAX_TURNS=9 SEQ_PARALLEL=2
CPU_OFFLOAD=1`, `6ae79d9`) passed: exit 0, no OOM, 17/32 rewarded, 0
zeroed, mean reward 0.45, 0 errors, 10/32 stopped at the input limit. One
step took 16.1 min (rollouts 3.7, forward 1.5, update 10.8), above the 15
min line. The 18-epoch run `exp-07_arm-trained_split-tenacitytrain_seed-0`
started at 14:06 PDT with those settings on 2 x A100 (flex-start). The 16.1
min step is a recorded deviation from the 15 min line; the run continues.

A 4 x A100 machine was requested to shorten training (on-demand was out of
stock in us-central1-a and -c; a flex-start request `gpu-advisor-4` is queued
in us-central1-c on disk `gpu-advisor-4`, made from snapshot
`gpu-advisor-20261022`; spot/flex A100-80GB quota raised to 6). If it starts:
setup to `6ae79d9`, then a smoke-only run
`exp-07_arm-trainsmoke_split-tenacitytrain_seed-0_run-5` with `NUM_GPUS=4
MAX_TURNS=9 SEQ_PARALLEL=2 CPU_OFFLOAD=0`, same 4 issues and pass rules.
Switching the training run to 4 GPUs is the user's decision after that
smoke. If switched, the 4-GPU run is a fresh run named
`exp-07_arm-trained_split-tenacitytrain_seed-0_run-2` from step 0 (it does
not resume the 2-GPU checkpoint), and the 2-GPU run is stopped and recorded
as superseded. Global batch 4 x 8, learning rate and reward are unchanged.

2-GPU run lost to host maintenance; 4-GPU run; Monday report (recorded 2026-10-24 ~15:25 PDT, before any trained number)
--------------------------------------------------------------------------------------------------------------------------

The 4-GPU smoke (`..._trainsmoke_..._run-5`, `16dc841`, `NUM_GPUS=4
MAX_TURNS=9 SEQ_PARALLEL=2 CPU_OFFLOAD=0`) passed: exit 0, no OOM, 13/32
rewarded, 0 zeroed, mean reward 0.345, 0 errors, 7/32 stopped at the input
limit, one step 7.5 min (rollouts 5.4 while sharing the worker with the
2-GPU run, forward 0.7, update 1.2).

At 14:59 PDT Compute Engine terminated `gpu-advisor` for host maintenance
(local SSD not recovered; automatic restart with no trainer). The 2-GPU run
`exp-07_arm-trained_split-tenacitytrain_seed-0` had finished 3 of 252 steps
and had no checkpoint. It is recorded as lost, not resumed; `gpu-advisor`
is stopped.

The 18-epoch run is `exp-07_arm-trained_split-tenacitytrain_seed-0_run-2`
on `gpu-advisor-4` (4 x A100-80GB, flex-start), fork `16dc841`, from step
0, started 15:16 PDT with `NUM_GPUS=4 MAX_TURNS=9 SEQ_PARALLEL=2
CPU_OFFLOAD=0 CKPT_INTERVAL=14`. Global batch 4 x 8, learning rate, KL and
reward are unchanged from the earlier amendments. A `@reboot` hook reruns
the same command, so a maintenance restart resumes from the latest
per-epoch checkpoint (`resume_mode=latest`); steps after that checkpoint
are redone. Every 15 min the VM writes `steps.csv` (one row per step:
rollout counts, rewards, pass@8, lengths, loss, KL, entropy, grad norm,
timings; `scripts/e07_steps_csv.py`, fork `3e47010`) and copies it and
`train.log` to `gs://whatsapp-sales-agent-hecate-artifacts/runs/<run>/`.

Final evaluation (checks 2 and 3), unchanged in substance: the highest
`global_step` export (`sort -V`), three passes, run ids
`exp-07_arm-trained_split-tenacityval_seed-0`, `_run-2`, `_run-3`, the same
short-context eval flags as the untrained arm. The only change is
infrastructure: the three passes run at the same time, each against its own
vLLM on its own GPU (ports 8000–8002). They are then joined with the six
check-1 files (`compare_swe_arms.py`, nine files) into
`runs/exp-07_final_split-tenacityval_seed-0/`.

Monday report: if at Sunday 21:50 PDT training is expected to finish by
Monday 01:00 PDT, the Sunday interim is skipped and the Monday report uses
the final three-pass evaluation. Otherwise the interim runs as written
(pause after the latest checkpoint, one pass, labelled interim, resume),
on one GPU while the other three stay idle, and the report is interim.

Crash and resume; disk; exploratory epoch-10 pass (recorded 2026-10-25 ~13:45 PDT, before any trained test number)
-------------------------------------------------------------------------------------------------------------------

Infrastructure, no recipe change. At 06:15 UTC on 25 Oct a policy worker
died at step 58 (`could not unlink the shared memory file`): an automatic
`systemd-logind` restart plus a closing cron session ran `RemoveIPC` and
deleted the trainer's shared memory. `RemoveIPC=no` and linger were set on
both VMs, and the same run resumed from `global_step_56` at 06:20 UTC;
steps 57–58 were redone. HF exports are 29 GB, not 15; exports older than
the newest two are moved to
`gs://whatsapp-sales-agent-hecate-artifacts/exports/<run>/` (local copy
deleted only after the uploaded byte count matches).

Overfitting check, exploratory. From epoch 8 the training KL to the
reference rose faster (0.044 → 0.127 by epoch 12) while training reward
was flat through epoch 11. Advice did not converge per issue (within-issue
3-gram Jaccard ~0.07 at epochs 1–2 and 10–12) and named fewer files.
Training rollouts cannot separate learning from fitting the 56 training
issues, so one extra held-out pass is added:

  Checkpoint  `global_step_140` export (end of epoch 10)
  Run id      `exp-07_arm-trainedep10_split-tenacityval_seed-0`
  Recipe      identical to the final passes (49 test issues, short-context
              eval, temperature 0.7, top_p 0.8, top_k 20, min_p 0), on GPU 3
              alongside the three final passes
  Join        its own file `ep10.json` next to `final.json`: weakalone ×3,
              untrained ×3, trainedep10 ×1

This pass is exploratory and labelled as such. It is not check 2 or check
3, it does not replace or select the checkpoint for them (the final
checkpoint, three passes, stays the only gate), and it is one pass, so it is
read against the final arm's per-pass spread, not as a significance test.
No other epoch is evaluated before the Monday report.
