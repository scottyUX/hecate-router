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
