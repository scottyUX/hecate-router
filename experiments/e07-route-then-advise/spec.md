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
