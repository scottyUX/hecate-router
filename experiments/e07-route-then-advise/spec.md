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

Final eval wave 1; 21-epoch resume deviation; pass-3 replacement; exploratory wave 2 (recorded 2026-10-26 ~09:15 PDT)
------------------------------------------------------------------------------------------------------------------------

Wave 1 (12:07–15:06 UTC 26 Oct) evaluated `global_step_295` and the
epoch-10 export as planned. `exp-07_arm-trained_split-tenacityval_seed-0`
and `_run-2` completed with 0 errors. `_run-3` failed: its vLLM server on
GPU 2 crashed at startup ("EngineCore failed to start"), so all 49 issues
errored with a connection error. It is an infrastructure failure and does
not count. The epoch-10 pass completed with 0 errors.

Deviation, 21 epochs instead of 18. SkyRL's `train()` restores
`global_step` and the dataloader on resume but restarts
`for epoch in range(cfg.trainer.epochs)` at 0 with no stop at
`total_training_steps`. After the step-58 crash the run resumed at 56 and
trained 239 more steps, ending at step 295 (~21.1 epochs). Learning rate,
batch, KL and reward are unchanged. The 18-epoch point, `global_step_252`,
is kept in the artifacts bucket.

Gate (unchanged in substance): checks 2 and 3 are decided on the final
checkpoint of the run, `global_step_295`, three passes. The two wave-1
passes have been seen (2-pass point estimates: check 3 pass, check 2 fail);
the gate is not moved to another checkpoint because of them.

Replacement, named here before it starts:
`exp-07_arm-trained_split-tenacityval_seed-0_run-4` replaces `_run-3`,
same checkpoint and flags. The gate join is `_run`, `_run-2`, `_run-4`.

Exploratory wave 2, same eval flags, run alongside the replacement and
never used as the gate or to pick a checkpoint:
  - `exp-07_arm-trainedep10_split-tenacityval_seed-0_run-2` and `_run-3`:
    two more passes of `global_step_140`, so epoch 10 has three passes.
  - `exp-07_arm-trainedep18_split-tenacityval_seed-0`: one pass of
    `global_step_252`, the as-designed 18-epoch checkpoint.
Joins: `final.json` (gate, 3 passes), `ep10.json` (3 passes),
`ep18.json` (1 pass), each with the six check-1 files. vLLM servers start
one at a time with a health check and up to three retries. After the
joins are copied to the bucket, both VMs shut down.

Exploratory Flash transfer test (recorded 2026-10-26 ~12:05 PDT, before any Flash pass of this test)
--------------------------------------------------------------------------------------------------

Known when this was written: the gate result (`final.json` numbers from
`_run`, `_run-2`, `_run-4`: check 3 pass, check 2 fail, trained minus
student-alone +0.6 steps), the step-252 pass, and the first epoch-10 pass.
The other two epoch-10 passes were still running. Nothing below changes
checks 1–3 or their verdicts.

Question (exploratory, not a gate). Advisor Models reports the trained SWE
advisor carrying over to a stronger student of the same family (Gemini
2.5 Flash → Gemini 3 Pro: same resolve rate, 31.7 → 26.3 steps). Here the
advisor was trained with Flash-Lite. Does the step-295 advisor, unchanged,
keep Gemini 2.5 Flash's resolve rate and cut its steps on the 49 test
issues? This also tests one explanation for the check-2 failure: that
Flash-Lite's unresolved runs, which mostly hit the 40-step cap, hide a step
saving (exploratory: resolved runs are 16.7 steps with advice against 19.9
alone).

Arms, same 49 issues and eval flags as the final passes:
  - `exp-07_arm-flashtrained_split-tenacityval_seed-0`, `_run-2`, `_run-3`:
    Flash (`openrouter/google/gemini-2.5-flash`) with the
    `global_step_295` advisor, short-context eval, temperature 0.7, top_p
    0.8, top_k 20, min_p 0, `--max_workers 1`, on gpu-advisor-4 against
    the GPU-0 server already serving step 295.
  - `exp-07_arm-flash_split-tenacityval_seed-0_run-3`, `_run-4`, `_run-5`:
    Flash alone via `eval_swe_smith`, on hecate-worker at fork `93678ef`
    (the commit of student-alone `_run-6`/`_run-7`). The earlier Flash
    passes (`exp-07_arm-flash_split-tenacityval_seed-0`, `_run-2`) are on
    older commits and are kept as a check only.
Join: `flash.json` with `compare_swe_arms.py`, flash ×3 against
flashtrained ×3, plus the six check-1 files for reference.

Reading rule, fixed now: "keeps resolve and cuts steps" needs flashtrained
minus flash steps < 0 with the 95% upper bound < 0, and resolve difference
with a 95% lower bound above −10 points (the check-3 margin). Anything else
is reported as not reproduced on Flash. One seed, 49 issues; exploratory
either way.

Epoch 10 on Flash: decided after the three-pass epoch-10 result is in. If
added, it is one exploratory arm `exp-07_arm-flashtrainedep10_...`, read
only next to the step-295 Flash arm, never in its place.

Budget: about $25 OpenRouter (Flash ~$0.077 per issue × 294) and about 2
extra A100-hours on gpu-advisor-4. Both VMs still shut down when done.

Exploratory open-model student pilot (recorded 2026-10-26 ~14:15 PDT, before any pass of it)
---------------------------------------------------------------------------------------------

Known when this was written: all gate, epoch-10, epoch-18 and Flash transfer
results (Flash: advisor +5.7 points resolve [−1.4, +13.5], −0.4 steps
[−3.0, +1.9]; not reproduced under the Flash reading rule).

Question (exploratory, preliminary). Does the step-295 advisor, unchanged,
carry over to a cheaper open-weight student, and does that student resolve
enough (≥ ~50%) to be a candidate training student for a follow-up that tests
the "Flash-Lite fails too often to teach speed" hypothesis?

Student: `openrouter/qwen/qwen3-coder-30b-a3b-instruct`, priced in the
worker's LiteLLM registry at $0.07/M input, $0.28/M output (OpenRouter list,
26 Oct). Arms, 49 test issues:
  - `exp-07_arm-qwencoder_split-tenacityval_seed-0`, `_run-2`: alone,
    `eval_swe_smith`, on hecate-worker.
  - `exp-07_arm-qwencodertrained_split-tenacityval_seed-0`, `_run-2`: with
    the `global_step_295` advisor, same advisor flags as the final passes,
    on gpu-advisor-4.
Deviations, for time (a preliminary read before the 26 Oct 3 pm meeting):
two passes per arm, not three, and `--max_workers 4`, not 1. The registry
edit leaves the worker checkout dirty at `93678ef`.

Reading: reported as preliminary, with the same paired table and bootstrap
CIs as `flash.json`, into `qwencoder.json`. No gate, no claim. A follow-up
that trains with an open-weight student needs its own spec.

Q7.1 confirmatory: Flash student, LoRA, on the DGX Spark (recorded 2026-10-26 ~evening PDT, DRAFT, not authorized)
-----------------------------------------------------------------------------------------------------------------

Status: DRAFT for review. Nothing below is authorized to run, and no code
changes until this amendment is reviewed. Known when this was written: every
result above (checks 1–3, epoch 10 and 18, the Flash transfer test, the
Qwen3-Coder pilot). No Flash-student training number exists.

Why. §2 0d says Q7.1 is judged only with the paper's student (Gemini 2.5
Flash). The Flash-Lite run cannot headline. Leading explanation for check 2
failing: Flash-Lite resolves ~34%, so few GRPO groups hold resolved runs with
different step counts, and the reward rarely teaches speed. Flash resolves
~60% here (60.3%, three passes; paper 61.2%), so it gives that signal.

Question. With Flash as the training and test student, does a GRPO-trained
Qwen2.5-7B advisor keep Flash's resolve rate and cut its steps on the 49 test
issues?

Hardware. The lab's own NVIDIA DGX Spark (GB10, 128 GB unified memory, ARM
CPU) runs the trainer and the vLLM advisor. hecate-worker (x86) keeps the
SWE-smith containers and the agent/eval servers (ports 8081/8082); the Spark
reaches them through an SSH tunnel, with no new public firewall rule.
`OPENROUTER_API_KEY` lives in a `.env` on the Spark, never in git or logs.
To fill in before authorization: number of Sparks, OS and CUDA version, SSH
host, and a one-week exclusive-use window.

Method change: LoRA, not a full fine-tune. Full fine-tuning (~112 GB of
weights, gradients and Adam state, plus the reference model and vLLM) does
not fit in one Spark's 128 GB. This is a deviation from the Flash-Lite run
and from the paper, recorded now:

  Trainer     same SkyRL fork and launcher as the Flash-Lite run, plus a
              LoRA patch: rank and alpha from config into the policy;
              reference = base model with the adapter disabled (no
              separate reference copy); adapter merged into the weights
              before each sync to vLLM and before each HF export
  LoRA        rank 32, alpha 32, dropout 0, all linear layers (attention
              and MLP). Fixed, not tuned
  LR          1e-5 (10x the full fine-tune's 1e-6, the usual LoRA/full
              ratio for RL; Schulman et al., "LoRA Without Regret", 2025).
              Fixed, not tuned
  Unchanged   GRPO, batch 4 x group 8, KL on, reward, MAX_TURNS=9,
              28,672 prompt / 4,096 generation, zero_reward_on_non_stop,
              training temperature 1.0, the 56 training issues, and 295
              steps (21 epochs, matching the Flash-Lite run's final
              step-295 checkpoint, not the paper's 30)
  Student     openrouter/google/gemini-2.5-flash (training and test)

If SkyRL or vLLM will not build on the Spark, the fallback (OpenPipe ART) is
not covered here; it needs its own amendment before use.

Step time. On 2 x A100 the update, not the rollouts, dominated a step
(smoke 4: rollouts 3.7 min, update 10.8 min with CPU offload). The Spark's
step time is unknown. The smoke measures it; if the mean over the first 5
full-run steps is above 30 min (about 6 days for 295 steps), stop and report
before continuing.

Order of work, each gated on the one before:

  1. Spark setup: SkyRL and vLLM build; vLLM serves the base Qwen2.5-7B;
     the Spark reaches the worker's 8081/8082 through the tunnel.
  2. LoRA patch on a fork branch, unit-tested offline (merge round-trips
     to the same logits as base + adapter).
  3. Untrained control on Flash, three passes (the check-1 analogue):
     `exp-07_arm-flashuntrained_split-tenacityval_seed-0`, `_run-2`,
     `_run-3`, base Qwen2.5-7B advisor served on the Spark, same eval flags
     as the final passes. Reported against the existing Flash-alone passes
     (`exp-07_arm-flash_split-tenacityval_seed-0_run-3/4/5`). If untrained
     steps are not at least 2 below Flash alone, training still runs, but
     the result is labelled "no trade-off to recover", as in check 1.
  4. Smoke: run `exp-07_arm-flashlorasmoke_split-tenacitytrain_seed-0`,
     the same 4 issues and pass rules as the Flash-Lite smoke, plus peak
     memory and step time recorded.
  5. Full run: `exp-07_arm-flashlora_split-tenacitytrain_seed-0`, checkpoint
     every epoch, merged HF export of each, copied to
     `gs://whatsapp-sales-agent-hecate-artifacts/exports/<run>/`.
  6. Eval: the step-295 merged export only, three passes,
     `exp-07_arm-flashloratrained_split-tenacityval_seed-0`, `_run-2`,
     `_run-3`. No checkpoint sweep on the 49.

Abort rules (stop the trainer): the Flash-Lite run's rules (OpenRouter 402,
404s surviving retries, >25% of a step's rollouts errored, two all-zero-reward
steps, out of memory, no checkpoint by step 14), plus the step-time rule
above, plus OpenRouter spend on the run above $800.

Decision rules (Q7.1), fixed now, joined with `compare_swe_arms.py` into
`flashlora.json`, flash ×3 vs flashuntrained ×3 vs flashloratrained ×3:

  Reproduced   trained minus Flash alone: steps upper 95% bound < 0, and
               resolve lower 95% bound > −10 points (the Flash reading
               rule above)
  Partial      steps point estimate < 0 and resolve held, but the steps
               bound includes 0: "direction matches, not significant"
  Not          anything else: "not reproduced with a Flash student
  reproduced   (LoRA)"
  Also         trained vs untrained on resolve and steps (check-3
  reported     analogue), and the share of training groups with resolved
               runs of different step counts, Flash vs Flash-Lite (the
               speed-signal check)

Bridge run, conditional and fixed now. If the result is "Reproduced" or
"Partial", retrain the Flash-Lite advisor with the same LoRA settings
(`exp-07_arm-litelora_split-tenacitytrain_seed-0`, then three test passes
`exp-07_arm-liteloratrained_split-tenacityval_seed-0`, `_run-2`, `_run-3`)
and compare it with the full fine-tune's final passes. It must land within
±10 points of 31.9% resolved and show no step cut, or the student-strength
reading is reported as confounded with LoRA. If the result is "Not
reproduced", the bridge is skipped and the write-up states that LoRA is
untested against a full fine-tune here, so a LoRA-specific failure is not
ruled out.

Budget (OpenRouter list prices, 26 Oct; GPU $0 on the Spark):

  Untrained control, Flash, 3 x 49          ~$10
  Smoke                                     ~$5
  Training, 295 steps x 32 rollouts, Flash  ~$570–660 (cap $800)
  Eval, 3 x 49, Flash + advisor             ~$15
  hecate-worker (n2-standard-32), 3–7 days  ~$75–180
  Total, Flash run                          ~$675–870
  Bridge, if triggered                      +~$580 API, +2–6 days

Time: setup and LoRA patch 1–3 days, control and smoke ~0.5 day, training
2–6 days (step time unknown), eval ~0.5 day.

Not authorized by this amendment: any Spark setup, code change, pass,
training step or spend. Authorization comes after review, recorded below.

Exploratory: a released SFT critic as the advisor (recorded 2026-10-26 ~evening PDT, DRAFT, not authorized)
-----------------------------------------------------------------------------------------------------------

Status: DRAFT for review. Nothing below is authorized. Known when this was
written: every result above. No pass with this critic exists.

Why. Advisor Models' trained advisor weights are not public (checked again
26 Oct: none on Hugging Face under the authors or NovaSky-AI). The closest
released model is the critic from Gandhi et al., "Steer, Don't Solve:
Training Small Critic Models for Large Code Agents" (arXiv:2606.21811):
`code-critic-model/Qwen3-8B-Critic-SFT`, Apache-2.0, not gated. It is
Qwen3-8B fine-tuned (SFT, not RL) on Claude Opus 4.6 critiques of agent
trajectories on 500 R2E-Gym tasks (matplotlib, moto, sympy), and it raised
resolve rates for six agents on SWE-bench Verified (e.g. GPT-OSS-120B
20.4 → 31.4). Our transfer results so far use an advisor that did not beat
its own student (check 3: −2.1 points), so they cannot separate "advice
does not transfer" from "this advice is weak". This critic works on the
agents it was built for, so it is a cleaner transfer test, with no
training.

Question (exploratory, no gate). On the 49 Tenacity test issues, in our
harness, does the released 8B critic change resolve rate and steps for
Flash-Lite, Flash and Qwen3-Coder-30B, against each student alone and
against our step-295 advisor with the same student?

Fit with our harness. Their agent loop is a fork of mini-swe-agent, the
scaffold family we use, and their critic fires every k = 5 agent steps,
the same interval as our advisor (`max_steps_per_advisor_call = 5`). A
`--advisor_mode critic` option in `eval_advisor.py` changes only what the
advisor reads and when it first speaks:

  Input       their multiturn format (`_build_prm_messages_multiturn` in
              their `default_prm.py`): their system prompt, copied
              verbatim from a training record of
              `code-critic-model/critic-sft-cwm-qwen`; the task; the
              agent's full message history; up to 5 previous critiques;
              then the closing request line. Needs a read-only agent
              server endpoint that returns the session's messages (our
              observation is a rolling summary, not the trajectory)
  First call  after the first 5 agent steps, not before step 1 (theirs)
  Step-aware  their nudge at 27 of our 40 steps (their 100 of 150,
  nudge       scaled), with step_limit 40
  Sampling    temperature 0, top_p 1, thinking off
              (`chat_template_kwargs: {enable_thinking: false}`),
              max_tokens 1024
  Serving     vLLM bf16, `--max-model-len 65536`, served name `critic`
  Unchanged   how advice enters the agent's context (our agent server's
              injection, the same for every advisor arm), the 40-step
              cap, the student flags, the eval server, the join

Recorded differences from their setup: our 40-step cap (theirs 150), our
advice injection (theirs: a supervisor message carrying a condensed history
of past critiques), no dedup or best-of-N (both off in their main config),
and SWE-smith Tenacity rather than SWE-bench Verified.

Arms, 49 test issues, `--max_workers 1`, three passes each:

  Student      Alone (existing passes)               + critic (new)
  Flash-Lite   weakalone run-5/6/7                   exp-07_arm-litecritic_split-tenacityval_seed-0{,_run-2,_run-3}
  Flash        flash run-3/4/5                       exp-07_arm-flashcritic_split-tenacityval_seed-0{,_run-2,_run-3}
  Qwen3-Coder  qwencoder, _run-2, + _run-3 (new)     exp-07_arm-qwencodercritic_split-tenacityval_seed-0{,_run-2,_run-3}

Control on Flash only: the untrained base `Qwen/Qwen3-8B` in the same critic
mode, three passes, `exp-07_arm-flashbasecritic_split-tenacityval_seed-0`
`{,_run-2,_run-3}`, to separate "any critique" from the trained critic.

Before any 49-issue pass: offline unit tests on fixture message histories
(message builder output matches their builder; no provider call), then a
1-issue smoke per student that must show at least one critique delivered,
no context-length error, and a scored result.

Reading. Joined per student with `compare_swe_arms.py` into
`critic_<student>.json`. For each student, critic minus alone, with the
Flash reading rule: "keeps resolve and cuts steps" needs the steps 95%
upper bound < 0 and the resolve 95% lower bound > −10 points; "raises
resolve" needs the resolve 95% lower bound > 0. Also reported: critic minus
our step-295 advisor with the same student, critic minus base critic on
Flash, cost per fix with the critic priced at a hosted Qwen3-8B rate, and
critique count and length per issue. One repo, 49 issues: exploratory
either way, and never a Q7.1 result.

Hardware. The critic runs on the lab's DGX Spark (vLLM, bf16,
`--max-model-len 65536`); no GPU is rented. When the Phase C trainer runs on
the same Spark, the critic server is capped at about 35 GB
(`--gpu-memory-utilization`), measured in the Phase C smoke. hecate-worker
runs the containers, as before.

Budget (OpenRouter list prices, 26 Oct):

  Flash-Lite + critic, 3 x 49     ~$10
  Flash + critic, 3 x 49          ~$10
  Qwen3-Coder + critic, 3 x 49    ~$2, plus one alone pass ~$0.60
  Flash + base Qwen3-8B, 3 x 49   ~$10
  Smokes                          ~$2
  hecate-worker, ~2 days          ~$50
  GPU                             $0 (the lab's Spark)
  Total                           ~$85 (cap $150)

Time: code and tests ~1 day; passes ~2–3 h each, run one student at a time
(13 passes, about 1.5–2 days on one critic server).

Not authorized by this amendment: the code change, the agent server
endpoint, any pass or spend. Authorization comes after review.

Exploratory Codex harness pilot: GPT-5.4-nano alone, then with the step-295 advisor (recorded 2026-10-27, before any pass of it)
------------------------------------------------------------------------------------------------------------------------------

Known when this was written: every result above. No Codex pass exists. The
two DRAFT amendments above stay unauthorized; this one is authorized by
Scott (27 Oct), the second stage only under the rule below.

Question (exploratory, no gate). Our advisor was trained with Flash-Lite in
mini-swe-agent. Codex (OpenAI's open-source agent CLI) is a different
harness: function-call tools, its own `apply_patch` edit format, its own
plan tool and context compaction, and a system prompt written for GPT
models. In Codex with a cheap GPT student, (a) does the pipeline work and
does the student leave room for advice, and (b) if so, does the step-295
advisor, unchanged, change resolve rate and steps? This moves the student
and the harness together; it cannot say which one caused a difference
(the 2x2 that separates them needs its own amendment).

Student: `openai/gpt-5.4-nano` via OpenRouter, $0.20/M input, $0.02/M
cached input, $1.25/M output (OpenRouter list, 27 Oct). Reasoning effort
pinned to `medium` in the Codex config; no temperature control (reasoning
model).

Harness:
  Codex       latest release on the day of setup, pinned by version and
              SHA-256 of the static x86_64 Linux binary, both recorded in
              each run dir. Run as `codex exec` inside each Tenacity
              container with the approvals and sandbox bypass (the
              container is the sandbox), repo at its usual path.
  Task text   the problem statement plus a fixed one-line instruction
              (fix the issue; do not edit tests), recorded verbatim.
              Codex's own system prompt, unmodified.
  Endpoint    Codex -> a local proxy -> OpenRouter Responses API, in
              both arms. Alone, the proxy passes requests through
              unchanged and only counts and logs; with the advisor, it
              also inserts advice. So the only difference between arms is
              the advice.
  Step        one model request = one step. Cap: the proxy refuses
              request 41 (HTTP 400, never sent to OpenRouter) and the
              runner stops Codex; the diff at that point is graded, as at
              mini-swe-agent's 40-step cap. Tool calls are also counted,
              since one request can carry several. Timeout 45 min.
  Patch       `git diff` of the container repo when Codex exits, graded
              with the same SWE-smith grading as `eval_swe_smith`.

Advisor arm, the same as our harness where it can be:
  Calls       initial advice before the first request, then every 5
              requests (`max_steps_per_advisor_call = 5`)
  Input       `ADVISOR_TEMPLATE` task prompt, the previous advice, and
              `build_advisor_observation` applied to the Codex history
              mapped to `[role]: content` messages (assistant text and
              tool calls with arguments as assistant, tool outputs as
              user; reasoning items left out, as they are encrypted):
              the last 10 messages in `ADVISOR_FOLLOWUP_TEMPLATE`, tail
              60,000 chars, as in our harness
  Delivery    mini-swe-agent's `add_advice` wrapper (`<advice>` block)
              appended to the last input item's text, usually the last
              tool output, as `add_advice` appends to the last message.
              Codex resends its own history, so the proxy re-applies each
              past advice to the same item on every later request, as it
              stays in mini-swe-agent's history. Every delivery logged
  Advisor     `global_step_295`, the same vLLM flags and sampling as the
              final passes; served on the lab's Spark if it is reachable
              from hecate-worker, else one GCP L4 (g2-standard-8).
              Location does not change the weights or sampling.

Before any pass: offline tests of the proxy (pass-through is byte-identical;
cap; history rendering; advice insertion) on fixture requests, then a
1-issue smoke that must end with a graded patch. Smokes use Tenacity train
issues, never the 49 test issues. Codex runs the model under its own name
(`gpt-5.4-nano`, so it uses its built-in model metadata) and the proxy
rewrites the request model to OpenRouter's `openai/gpt-5.4-nano`; the first
smoke ran without this (Codex warned it had no metadata) and is discarded.

Students changed (recorded 2026-10-27, after the two train-issue smokes and
before any pass on the 49 test issues). Codex 0.164.0 ships model metadata
only for the GPT-5.5/5.6/6 families, so `gpt-5.4-nano` ran on Codex's
fallback metadata in both smokes. GPT-5.4-nano is dropped. Two students
instead, run in parallel on hecate-worker, `--max_workers 4` each:
  - `google/gemini-2.5-flash-lite`: the advisor's training student, so
    against E7's mini-swe-agent arms only the harness changes. Codex has no
    metadata for it (fallback); `model_context_window = 1048576`; the
    proxy strips `reasoning` and reasoning `include` entries so it runs
    without thinking, as in E7. Run ids `exp-07_arm-codexlite_...` and,
    with the advisor, `exp-07_arm-codexlitetrained_...`.
  - `openai/gpt-6-luna` ($0.10/M input, $0.01/M cached, $0.50/M output,
    OpenRouter list 27 Oct): a GPT student with Codex's own metadata, run
    under Codex's defaults for it (no effort override). Run ids
    `exp-07_arm-codexluna_...` and `exp-07_arm-codexlunatrained_...`.
Everything else above holds per student: one train-issue smoke each, then
stage 1 (one alone pass of the 49), and the stage-2 rule applied to each
student separately (Scott chose conditional, 27 Oct). Codex's first request
per run (model, reasoning, tools) is logged as the record of its settings.
Proxy cost is computed from list prices because OpenRouter's Responses
usage carries no cost; the pass total is checked against the key's
OpenRouter usage before and after.

Code: `advisor_models/swe_smith/codex_proxy.py`, `eval_codex.py` and
`tests/test_codex_proxy.py` in the advisor-models fork, a separate path
next to `eval_swe_smith`/`eval_advisor` (unchanged). Codex 0.164.0
(`rust-v0.164.0`), binary SHA-256
`b93f6811d3f653f0fb83be4050d857fb9abbb111dfa2ce160563327daff7f306`.

Stage 1, alone: `exp-07_arm-codexnano_split-tenacityval_seed-0`, one pass
over the 49 test issues.

Rule for stage 2, fixed now. Run the advisor arm only if both hold:
  - pipeline: at most 4 of 49 runs end in an infrastructure error
    (provider error, container failure, no gradeable outcome), and
  - headroom: GPT-5.4-nano alone resolves 10–39 of 49 (about 20–80%).
Also reported, not part of the rule: failure types from a read of the
unresolved runs (wrong localization, wrong fix, malformed or no patch, cap
hit), edits made by `apply_patch` vs shell, compactions per run.

Stage 2, if the rule holds:
  - `exp-07_arm-codexnanotrained_split-tenacityval_seed-0`, `_run-2`,
    `_run-3`: with the step-295 advisor.
  - `exp-07_arm-codexnano_split-tenacityval_seed-0_run-2`, `_run-3`:
    two more alone passes, for three per arm.
Join: `codexnano.json` with `compare_swe_arms.py`. Reading rule, the Flash
one: "keeps resolve and cuts steps" needs the steps 95% upper bound < 0
and the resolve 95% lower bound > −10 points; "raises resolve" needs the
resolve 95% lower bound > 0. Also reported: rescues vs harms per issue,
advice deliveries per run, tool calls, tokens, cost. One repo, 49 issues,
one advisor seed: exploratory either way, never a Q7.1 result. The 44
unused Tenacity issues with problem statements are not touched here.

If the rule fails: stop and report stage 1. A switch to another student or
benchmark needs its own amendment.

Budget (OpenRouter list, 27 Oct; ~$0.15–0.30 per run):
  Stage 1, 49 runs                ~$7–15
  Stage 2, 245 runs               ~$37–75
  Smokes                          ~$2
  hecate-worker, ~2–3 days        ~$75–110
  Advisor GPU, stage 2 only       $0 on the Spark, ~$20 on an L4
  Total                           ~$120–220 (cap $250; stage 1 alone
                                  cap $40)

Stage 1 result (27 Oct; runs copied to `gs://hecate-506120-artifacts/runs/`):

  Student      Resolved       Infra errors  Mean steps  Empty diff  API cost
  Flash-Lite   5 of 42 graded 7             9.4         29 of 42    $0.13
  gpt-6-luna   42 of 49       0             6.2         0           $0.15
  OpenRouter key usage over both passes: $146.95 -> $147.23 ($0.28).

Rule applied as written: neither student goes to stage 2.
  - gpt-6-luna fails headroom (42 > 39 of 49): too strong on Tenacity.
  - Flash-Lite fails the pipeline condition (7 > 4 errors). All 7 are
    OpenRouter routing requests to a Google endpoint that returns 404 for
    `gemini-2.5-flash-lite` ("no longer available to new users"), the
    transient 404 E7 handled with retries; the proxy does not retry.
    Separately from the errors, Flash-Lite in Codex mostly stops early: a
    reply without a tool call ends a Codex run (10 of 42 runs used 3 steps
    or fewer, 29 left no diff), where mini-swe-agent keeps it going to its
    submit command or the 40-step cap.
Any rerun (a proxy retry for provider 404s and a rerun of the 7 errored
issues, or another student) is a new decision, recorded before it runs.

Flash-Lite rerun with harness fixes (recorded 2026-10-28, before the pass):

Log review of `codexlite` found three problems, two of them in our setup:
  - Provider 404s hit 90 of 424 requests (21%) in 17 issues, not only the
    7 counted as errors. Two more runs (`func_basic__q99obeha`,
    `func_pm_ctrl_shuffle__6vzkm0lh`) were cut off by a 404 and a third
    (`func_basic__9b67b0zh`) by a dropped stream; all three were graded
    as unresolved. Codex retries 5 times with almost no wait, then ends
    the run.
  - Codex has no metadata for `google/gemini-2.5-flash-lite`, so Flash-Lite
    got Codex's fallback setup: no `apply_patch` tool, an `exec_command`
    with a `sandbox_permissions` escalation option that approval "never"
    refuses, and `request_user_input`. Many early stops are the model
    asking for escalation or saying it cannot apply a patch.
  - Flash-Lite sometimes writes a tool call as text (`<ctrl42>call
    print(default_api.exec_command(...`) or prints a patch as markdown.
    Codex treats any reply without a tool call as the end; mini-swe-agent
    answers it with a format error and goes on. This is the harness and
    is not changed.

Fixes (advisor-models `codex_proxy.py`, `eval_codex.py`):
  - The proxy retries 404/408/409/429/5xx and connection errors, up to 8
    attempts with 2 s doubling backoff (cap 30 s). One Codex request is
    still one step.
  - A run is an infrastructure error if any request still failed after
    the retries, or Codex reports `turn.failed` for any reason but the
    step cap.
  - Flash-Lite gets a one-model `model_catalog_json`: Codex's built-in
    `gpt-5.5` entry (plain Responses, no Code Mode) with slug, context
    window (1,048,576) and reasoning/search/image/speed-tier fields
    changed (`CATALOG_OVERRIDES`). It now has `apply_patch` (freeform, the
    only type Codex 0.164 accepts) and gpt-5.5's instructions.
    `exec_command` keeps its escalation option and `request_user_input`
    stays; Codex ignores `unified_exec = false`.
  Smoke (3 train issues, `runs/smoke-codexlitefix`): 0 of 3 resolved,
  0 errors, 2–13 steps; 404s retried and absorbed; no `apply_patch` use
  (edits by `sed` and heredocs).

Run: `exp-07_arm-codexlitefix_split-tenacityval_seed-0`, the same 49
Tenacity test issues, one pass, Flash-Lite alone. Stage-2 rule unchanged
(at most 4 of 49 errors, 10–39 resolved); if it holds, stage 2 is
`codexlitefixtrained` plus two more alone passes, as written above.
`codexlite` stays as recorded. Budget: ~$0.25 API, worker a few hours.

GPT-5-nano added as a second Codex student (recorded 2026-10-28, before its
pass; the `codexlitefix` pass was already running):
  - Why: gpt-6-luna (42/49) is too strong for the advisor to matter. GPT-5-nano
    is the cheapest GPT-5 model ($0.05 in / $0.005 cached / $0.40 out per
    1M on OpenRouter) and the most likely to land in the 10–39 band. Picked
    over gpt-4.1-nano (no reasoning, closer to Flash-Lite, but likely under
    10 and without custom-tool support for `apply_patch`).
  - Settings: reasoning effort medium; context window 400,000; a catalog
    entry copied from gpt-5.5 like Flash-Lite's, but it keeps gpt-5.5's
    reasoning fields (efforts limited to low/medium/high, default medium).
    Same proxy retries and error rule.
  - Smoke (3 train issues, `runs/smoke-codex5nano`): 1 of 3 resolved,
    0 errors, 11–20 steps, $0.01; it calls `apply_patch` (2 of 3 runs).
  - Run: `exp-07_arm-codex5nano_split-tenacityval_seed-0`, the 49 Tenacity
    test issues, one pass, alone. Same stage-2 rule (at most 4 errors,
    10–39 resolved); stage 2 would be `codex5nanotrained` plus two more
    alone passes, recorded and costed before it runs. Budget: under $1 API.
    The step-295 advisor was trained on Flash-Lite without thinking; a
    reasoning GPT student is a transfer case, so stage 2 would be read as
    exploratory transfer, not as Q7.1.

GPT-5-nano stage 1 result and stage 2 setup (recorded 2026-10-28, before any advised pass):

Stage 1, `exp-07_arm-codex5nano_split-tenacityval_seed-0`: 32 of 49
resolved, 0 errors, 11.2 mean steps (median 10, none ≤ 3 steps, no cap
hit), 7 empty diffs, `apply_patch` used in 42 runs, $0.54. The rule holds
(0 ≤ 4 errors; 10 ≤ 32 ≤ 39), so stage 2 runs. Same harness as
`codexlitefix` (7/49, 0 errors, 18 runs ≤ 3 steps, no `apply_patch`).

Flash-Lite rerun, causes (exploratory, from the logs): Codex's
`apply_patch` is an OpenAI custom tool. Through OpenRouter Gemini receives
it only as text and writes `print(apply_patch(...))` instead of a call (a
direct test outside Codex reproduces this). The gpt-5.5 instructions tell
it to use `apply_patch`, so it prints patches for the user or says it
cannot. 5 runs hit refused `sandbox_permissions` escalations, and 4 ended
on a text-form tool call at step 1.

Stage 2 advisor host: `global_step_295` was only on `gpu-advisor-4`'s disk
(exports up to step 280 were in GCS). A clone of that disk
(`advisor-ckpt-clone`, us-central1-c, pd-ssd) is attached read-only to a
new `advisor-l4` (g2-standard-8, 1× L4, on-demand). `gpu-advisor-4` is
untouched. The export is now also in
`gs://whatsapp-sales-agent-hecate-artifacts/exports/exp-07_arm-trained_split-tenacitytrain_seed-0_run-2/global_step_295/global_step_295/`.
Serving matches the E7 final passes: vLLM 0.9.2, dtype auto (bf16 in the
log), `--max-model-len 32768`, seed 0, served name `advisor`. Recorded
difference: L4 instead of A100 (same weights and sampling), and
`transformers` pinned to 4.53.2 because vLLM 0.9.2 fails with the current
release. KV cache: 77,312 tokens.

Stage 2 runs (49 test issues each, `--max_workers 4`, all in parallel on
hecate-worker):
  - `exp-07_arm-codex5nanotrained_split-tenacityval_seed-0`, `_run-2`,
    `_run-3`: `--advisor_model hosted_vllm/advisor --advisor_api_base
    http://10.128.0.15:8000/v1`, temperature 0.7, top_p 0.8, top_k 20,
    min_p 0 (the E7 final-pass sampling).
  - `exp-07_arm-codex5nano_split-tenacityval_seed-0_run-2`, `_run-3`:
    alone.
Before them: a 2-issue train smoke with the advisor, which must end with
graded patches and advice deliveries logged. Join: three alone vs three
advised with `compare_swe_arms.py`. Reading rule as above (Flash rule:
"keeps resolve and cuts steps" needs steps 95% upper bound < 0 and
resolve 95% lower bound > −10 points; "raises resolve" needs resolve 95%
lower bound > 0). Also reported: advice deliveries, advice lost to
compaction, rescues vs harms. Exploratory transfer (a reasoning GPT
student; the advisor was trained on Flash-Lite), never Q7.1. Budget:
~$3 API, ~$3 L4, ~$5 worker. The L4 and worker stop when done; the clone
disk and L4 VM are deleted only on Scott's yes.
