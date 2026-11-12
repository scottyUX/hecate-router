Experiment 10 — PPO vs GRPO for the advisor, all on the DGX Spark
Hecate Lab
A Qwen2.5-7B LoRA advisor trained twice, GRPO and PPO, for a local Qwen3-Coder-30B student · rev 4 — PLANNED
November 12, 2026

Status: PLANNED. Nothing in this document is authorized to run.

Revision history (all before any code or run):
  rev 1  `f9d6f42`  router, four objectives (now E11, renumbered)
  rev 2  `12a141e`  advisor PPO vs GRPO with LoRA, E7's recipe: Flash-Lite
                    student on OpenRouter, containers on the x86 worker,
                    ~$1,500–1,750
  rev 3  `2eca0c1`  router again; the advisor plan moved to E11
  rev 4  this       Scott's choice, 12 Nov: the advisor study is E10 again,
                    rebuilt to spend as little as possible. The student is
                    Qwen3-Coder-30B-A3B served on the Spark, the Tenacity
                    containers are rebuilt for ARM and run on the Spark, and
                    every training rollout is saved as state, action and
                    reward (§6). The router plan is E11
                    (`experiments/e11-ppo-vs-grpo-router/`).

Position in slate: Experiment 10. Does not start, stop, or overwrite E1–E9.

  E7  Route-then-Advise: trained a Qwen2.5-7B advisor with GRPO (full
      fine-tune, Flash-Lite student, 4× A100)
  E10 PPO vs GRPO for the advisor, all on the Spark (this document)
  E11 PPO vs GRPO for the M1/M2 router (plan; waits until the Spark is free)

Relation to the E7 follow-up proposal ("Does advice transfer?", 26 Oct):
its Phase C bridge (Flash-Lite, LoRA GRPO) is not this run any more, because
the student changed. That bridge needs its own run if approved.

Abstract
--------
E7 trained a Qwen2.5-7B advisor with GRPO (Advisor Models' recipe) to advise
Gemini 2.5 Flash-Lite in mini-SWE-agent on SWE-smith Tenacity. GRPO drops
PPO's learned critic and scores each run against the average of the 8 runs
on the same issue. E7's advisor did not beat Flash-Lite alone, and E7's
notes name one reason: Flash-Lite resolves about a third of issues, so many
groups of 8 hold no resolved run and give GRPO no signal.

E10 asks whether PPO, with a critic that scores each turn of advice, trains
a better advisor than GRPO under the same budget. To spend almost nothing,
everything runs on the lab's DGX Spark: the advisor's trainer, the advisor's
vLLM, a local student (Qwen3-Coder-30B-A3B-Instruct, FP8, which resolved
58.5% of the test issues alone in E7's pilot), and the test containers. No
API calls and no cloud machines, apart from a one-time check of the ARM
containers against the x86 ones.

Q10.1  Does the PPO advisor beat the GRPO advisor, on resolve or steps, on
       the 49 test issues?
Q10.2  Does each advisor beat the student alone?
Q10.3  Does each trained advisor beat the untrained advisor? (Did training
       teach anything?)
Q10.4  Training: reward, KL, share of zero-signal groups, critic quality,
       peak memory, per arm. Descriptive, read from the saved trajectories
       (§6).

1 What is already known
-----------------------

E7, 49 Tenacity test issues, mini-SWE-agent, 40-step cap (E7 final results,
26 Oct):

  Student                       Arm                       Resolve  Mean steps
  Flash-Lite (3 passes)         alone                     34.0%    25.7
                                + untrained advisor       13.5%    22.0
                                + E7 GRPO advisor         31.9%    26.3
  Qwen3-Coder-30B (2 passes,    alone                     58.5%    22.6
    OpenRouter, pilot)          + E7 GRPO advisor         53.2%    23.2

E7's Flash-Lite advisor did not transfer to Qwen3-Coder-30B (−5.3 points
[−13.8, +3.2]). E10 trains for Qwen3-Coder-30B directly. Its 58.5% means
more groups of 8 hold both resolved and unresolved runs, which gives GRPO
more signal than Flash-Lite did; PPO's critic is the other way to get it.

These numbers are context only. The OpenRouter provider and the local FP8
model can behave differently, so E10 measures its own student-alone and
untrained-advisor rows on the Spark (§3).

2 Setup
-------

  Task       SWE-smith Tenacity: the 56 training issues
             (`train_jd__tenacity.json`) and 49 test issues
             (`validation_jd__tenacity.json`), as in E7. Test issues are
             never used in training.
  Harness    mini-SWE-agent with E7's settings: 40-step cap, advice every 5
             student steps, at most 9 advice turns.
  Student    `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8`, served by vLLM on the
             Spark (aarch64, GB10), one fixed configuration for training
             and test, recorded in the run manifest. The student is not
             trained.
  Advisor    `Qwen/Qwen2.5-7B-Instruct`, bf16, LoRA rank 32, alpha 32,
             dropout 0, all linear layers. Reference model = the base with
             the adapter disabled. Adapter merged before each sync to the
             advisor's vLLM and before each export.
  Tests      the Tenacity SWE-smith environment rebuilt as an ARM (aarch64)
             image and run with Docker on the Spark; the agent and eval
             servers run on the Spark too. G0 checks it gives the same
             pass/fail as E7's x86 image.
  Reward     E7's: 0.5 + 0.5 × (40 − steps)/40 if the patch passes the
             hidden tests, else 0; `zero_reward_on_non_stop`.

3 Arms
------

Shared by both trained arms (fixed, not tuned): SkyRL; batch 4 issues × 8
rollouts per step; KL loss to the reference, coefficient 0.001; training
temperature 1.0; E7's prompt and generation limits (28,672 / 4,096
tokens); policy LR 1e-5 (10× E7's full-fine-tune 1e-6, the usual LoRA/full
ratio for RL); one gradient update per rollout batch; seed 0; the same
number of steps, fixed at G2 (295, E7's count, or 150 if G2 shows 295 does
not fit the Spark's schedule; recorded by amendment before either full
run).

  G  GRPO  `advantage_estimator=grpo`: each rollout's reward minus its
           group's mean, divided by the group's std; the same advantage on
           every advice token of that rollout. E7's algorithm, with LoRA.
  P  PPO   `advantage_estimator=gae`, γ = 1, λ = 1: a critic predicts the
           final reward from the conversation so far, and each advice
           turn's tokens get (final reward − the critic's value at that
           turn). Critic: `Qwen/Qwen2.5-1.5B-Instruct` with its own LoRA
           (same shape) and SkyRL's value head, LR 5e-5, value clip 0.2.
           P draws the same 4 × 8 rollouts per step as G; it does not use
           the group to form its baseline.

The 1.5B critic (SkyRL's PPO example size) is chosen so the policy, critic,
advisor vLLM and student fit in the Spark's ~114 GiB together. If G1 shows
room, it stays 1.5B anyway: the critic is fixed before any run.

Untrained comparisons, on the 49 test issues, three passes each:
  A  the student alone
  U  the student with the untrained Qwen2.5-7B advisor

Evaluation of G and P: the final-step export of each, served by vLLM on the
Spark with E7's eval flags (temperature 0.7, top_p 0.8, top_k 20, min_p 0,
1,024-token replies), three passes on the 49 test issues.

Run ids (`hecate.utils.run_ids`):
  Training  `exp-10_arm-grpolora_split-tenacitytrain_seed-0`,
            `exp-10_arm-ppolora_split-tenacitytrain_seed-0`
  Eval      `exp-10_arm-{alone,untrained,grpolora,ppolora}_split-tenacityval_seed-0`,
            `_run-2`, `_run-3`

4 Metrics
---------

Per issue and arm: resolve rate (mean of three 0/1 passes), mean steps,
steps on resolved issues, advice deliveries.

Paired comparisons with `compare_swe_arms.py` (bootstrap over issues, 95%
intervals). An issue that errors in any pass of any arm in a join is dropped
from that join. Joins: P vs G (Q10.1); G vs A and P vs A (Q10.2); G vs U and
P vs U (Q10.3).

Training (Q10.4), per step, from the saved trajectories (§6) and SkyRL's
logs: mean reward, share of rollouts resolved, share of groups with zero
reward std (no GRPO signal), KL, policy entropy; for P the critic's value
loss and explained variance; peak Spark memory per arm.

5 Decision rules (fixed before any E10 run)
-------------------------------------------

Reading rule (E7's Flash rule) for a difference X − Y:
  "X raises resolve": resolve 95% lower bound > 0.
  "X keeps resolve and cuts steps": steps 95% upper bound < 0 and resolve
  95% lower bound > −10 points.
  Anything else: no detectable difference at n = 49.

  1. Q10.1 (P − G). "PPO trains a better advisor" if either reading holds
     for P − G; "GRPO trains a better advisor" if either holds for G − P.
     Otherwise "no detectable difference at n = 49, one training seed".
  2. Q10.2 and Q10.3: each trained arm against A and against U, same
     reading rule, reported for both arms whatever rule 1 says.
  3. Q10.4 is descriptive.
  4. Predictions, recorded now and not rules: no detectable P − G
     difference; neither arm beats A; both beat U on resolve; P has a
     higher share of non-zero advantages than G (by construction).
  5. A second training seed, or a full-fine-tune PPO run, needs its own
     amendment or spec. It is not a reinterpretation of this one.

One training seed per arm, as in E7: a difference can come from the seed,
and the write-up says so next to every rule-1 result.

6 Saved trajectories (state, action, reward)
--------------------------------------------

Every training rollout of both arms is saved, not only the checkpoints, so
the training data can be re-analysed (and reused for offline RL) without
rerunning. One record per advice turn, written as gzipped JSON Lines, one
file per training step:
`<run_dir>/trajectories/step-<NNNN>.jsonl.gz`.

  Identity  run id, step, issue id, group index (0–3), rollout index (0–7),
            turn index, student step at which the advice was given
  State     the advisor's full input at that turn: the issue text and the
            student's conversation so far (its actions and the command
            outputs), exactly as the advisor saw it; prompt token count
  Action    the advice text, its token ids and per-token log-probabilities
            under the policy that sampled it and under the reference
  Reward    on the rollout's last record: resolved (0/1), student steps,
            the scalar reward, `zero_reward_on_non_stop` applied or not;
            every record carries the rollout's final reward too
  Training  the advantage given to this turn's tokens; for P the critic's
            value at this turn and the GAE return; for G the group mean and
            std
  Student   per rollout, the full student trajectory (mini-SWE-agent's own
            trajectory file) and the test report, saved beside the records

Evaluation passes save the same records (no advantage or value fields).
Nothing secret is written: no API key is used anywhere in E10.

Size is measured at G2 and recorded. Disk: the Spark has ~757 GB free on
`/` (12 Nov); if G2 projects more than 300 GB for both arms, older steps'
files are copied off (G3) and then removed from the Spark, never deleted
before the copy is verified.

7 Gates and order
-----------------

  G0  Spark environment. On `spark` (aarch64, GB10, 128 GB unified; tmux,
      logs to file, no sudo, `df -h /` before downloads):
        a. Docker usable without sudo.
        b. The Tenacity environment builds as an ARM image. On 10 test
           issues, the gold patch passes and the unpatched repo fails the
           hidden tests, exactly as on E7's x86 image (checked once on
           `hecate-worker`). Any mismatch stops E10.
        c. vLLM serves the FP8 student on the GB10 (NGC container
           preferred); if FP8 does not run, bf16 by amendment.
        d. SkyRL, its LoRA patch and the PPO critic build on aarch64.
           If SkyRL cannot run on the Spark, E10 stops.
  G1  Memory: student + advisor vLLM + policy + critic loaded together,
      one training step of each arm on 4 training issues. Peak memory
      recorded. If P does not fit: the advisor's vLLM sleeps during
      updates (SkyRL colocated mode); then the student drops to
      `Qwen/Qwen3-8B` for both arms, by amendment before any full run.
  G2  Smoke: 3 training steps per arm with trajectory saving on. Checks
      every §6 field is present and records size per step. Fixes the step
      count (295 or 150) by amendment.
  G3  Durability: each run dir (manifest, `CODE_SHA`, config, logs,
      trajectories, exports) is copied to
      `gs://hecate-506120-artifacts/runs/<run_id>/` through a machine with
      bucket access (the Spark has no GCP credentials). A run without that
      copy is incomplete.
  G4  Offline tests (CI, no GPU, network or model): the LoRA merge round
      trip, the GAE advantage on a fixture trajectory, and the trajectory
      writer's schema on a fixture rollout.

Order: A and U eval passes; G training then its eval passes; P training
then its eval passes. One trainer at a time. Joins only after all passes
exist.

8 Cost
------

  Item                                   Cost
  Student and advisor inference          $0 (local, on the Spark)
  Spark GPU                              $0 (lab-owned)
  OpenRouter / other APIs                $0 (none used)
  hecate-worker, once, for G0b           ~$2
  GCS storage for runs and trajectories  ~$1–5 a month
  Electricity                            a few tens of dollars at most

Cap: $50 total. No OpenRouter key or cost-cap change is needed.

9 Constitution check (`.specify/memory/constitution.md`)
--------------------------------------------------------

  I   Execution-grounded validity: every reward and result is a hidden-test
      outcome; G0b shows the ARM tests agree with the x86 ones.
  II  Reproducibility by manifest: run id, `CODE_SHA`, config, student and
      vLLM versions, checkpoints and every rollout's trajectory (§6),
      copied off the Spark (G3).
  III Offline-testable CI: G4.
  IV  Spec-driven: this document precedes any code or run.
  V   Budget discipline: $50 cap; no paid inference.
  VI  Secrets hygiene: no API key in E10; trajectories hold only issue
      text, student actions, command outputs and advice.
  VII Shared-scaffold fairness: both arms share the student, harness,
      issues, reward, rollouts per step, steps and LoRA shape; only the
      advantage (and P's critic) differs.

10 Risks and scope
------------------

  - One seed, 49 test issues, passes that vary by up to ~19 points (E7):
    "no detectable difference" is the most likely rule-1 outcome. The
    training curves (Q10.4) are the lower-noise result.
  - Not comparable with E7's numbers: different student, LoRA instead of
    full fine-tuning, a different serving stack.
  - ARM containers: a pass/fail mismatch with x86 stops E10 (G0b).
  - Memory: the four models share ~114 GiB; G1's fallbacks are fixed above.
  - One machine: the Spark runs only one E10 trainer at a time, and E11
    waits for it.
  - Out of scope: other students, repos or harnesses; advise-or-escalate;
    full fine-tuning.

11 Not authorized by this document
----------------------------------

Any code, any Spark or worker run (including G0), and any download of model
weights. Authorization comes after review, as an amendment below.
