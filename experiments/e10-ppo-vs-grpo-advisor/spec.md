Experiment 10 — PPO vs GRPO for the advisor, all on the DGX Spark
Hecate Lab
A Qwen2.5-7B LoRA advisor trained three ways, GRPO and two PPO critics, for a local Qwen3-Coder-30B student · rev 5 — PLANNED
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
  rev 5  this       Scott's choice, 12 Nov: add Sagnik's six-feature state
                    (from his SB3 PPO escalation-router proposal) twice: as
                    an offline critic baseline read from the saved
                    trajectories (§4, Q10.4), and as a third trained arm,
                    P6, whose PPO critic is a small MLP on the six features
                    (§3). Multiple-comparison handling added (§5).

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
a better advisor than GRPO under the same budget, and whether that critic
needs to read the text: P's critic is a 1.5B LLM that reads the whole
conversation, P6's is a small MLP on six numbers describing the student's
progress (Sagnik's state, §3). To spend almost nothing,
everything runs on the lab's DGX Spark: the advisor's trainer, the advisor's
vLLM, a local student (Qwen3-Coder-30B-A3B-Instruct, FP8, which resolved
58.5% of the test issues alone in E7's pilot), and the test containers. No
API calls and no cloud machines, apart from a one-time check of the ARM
containers against the x86 ones.

Q10.1  Does the PPO advisor (LLM critic) beat the GRPO advisor, on resolve
       or steps, on the 49 test issues?
Q10.5  Does the PPO advisor with the six-feature critic (P6) beat the GRPO
       advisor? (Does any critic help?)
Q10.6  Does P beat P6? (Does reading the text help the critic?)
Q10.2  Does each trained advisor beat the student alone?
Q10.3  Does each trained advisor beat the untrained advisor? (Did training
       teach anything?)
Q10.4  Training: reward, KL, share of zero-signal groups, peak memory per
       arm (descriptive), and critic quality as a comparison: P's 1.5B
       critic and P6's MLP against an offline six-feature model fitted to
       the saved trajectories (§4).

Motivation
----------
E7's GRPO advisor did not beat its student: Flash-Lite resolved 34.0% alone
and 31.9% with the trained advisor. Training did teach something, since
untrained advice dropped Flash-Lite to 13.5%. One likely cause is how GRPO
gives credit. It compares each run with the mean of the 8 runs on the same
issue. Flash-Lite solves about a third of issues, so often all 8 runs fail,
every reward is 0, and that issue teaches nothing. GRPO also gives every
advice turn in a run the same credit, whether that advice helped or not.

PPO gets its signal another way. A critic predicts, after each advice turn,
how the run will end, and each turn is credited by how much the run beat
that prediction. PPO can therefore learn even when all 8 runs fail, and it
credits each turn separately. E10 tests whether that matters, with the same
advisor, student, issues and budget for every arm, all on the Spark, so any
difference comes from the training method.

Two caveats. The student is stronger than E7's (58.5% alone), which gives
GRPO more mixed groups and makes E10 a harder test for PPO to win. A tie is
still informative: if PPO does not beat GRPO here, the critic is not worth
its extra memory and complexity for this task.

The critic's input is the second question. Sagnik's six-feature state (§3.1)
and E10's own state describe the same moment very differently:

                Six-feature state (P6, offline F)   E10 text state (G, P)
  What it is    7 numbers in [0, 1]: steps used,    the advisor's prompt: the
                steps left, failing tests + a       issue text and the
                no-tests flag, command failure      student's conversation so
                rate, steps without progress,       far (commands and their
                advice turn index                   outputs), up to 28,672
                                                    tokens
  Read by       P6's MLP critic (7→64→64→1);        the 7B advisor (policy);
                ridge model F offline               P's 1.5B LLM critic
  Says          how the run is going                what the student is doing
                                                    and why it is stuck
  Used as       critic input only, never the        the policy's input (all
                policy's                            arms) and P's critic input

The advisor always reads the text, because writing useful advice needs it.
What changes between P and P6 is only what the critic reads. If six numbers
predict the final reward as well as the 1.5B critic does (Q10.4, Q10.6), the
critic is not using the text.

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

Shared by all three trained arms (fixed, not tuned): SkyRL; batch 4 issues × 8
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

  P6 PPO, six-feature critic. Identical to P (same 4 × 8 rollouts per
           step, γ = 1, λ = 1, KL, policy LR, steps, seed, value clip 0.2)
           except the critic: an MLP 7 → 64 → 64 → 1 (tanh, the seven
           inputs of §3.1), Adam, LR 1e-3, trained on the same value loss.
           The critic reads no tokens. Its value is computed once per
           advice turn from the features at that turn and applied to every
           token of that turn's advice; with γ = λ = 1 each turn's tokens
           get (final reward − V6(features at that turn)).

The 1.5B critic (SkyRL's PPO example size) is chosen so the policy, critic,
advisor vLLM and student fit in the Spark's ~114 GiB together. If G1 shows
room, it stays 1.5B anyway: the critic is fixed before any run. P6 needs
less memory than P.

New code for P6: a feature-based value function in SkyRL. The trainer needs
the seven inputs at each advice turn's position, so the rollout code
computes them (§3.1) and passes them with the advice turn; the value
function maps them to one value per turn. The same feature code fills the
§6 records.

3.1 Sagnik's six features (definitions fixed before any run)
-------------------------------------------------------------
Source: Sagnik's (sagniknath91) proposal for an SB3 PPO escalation router,
whose state is six numbers per checkpoint. E10 uses that state only as a
critic input, not as a router. Feature 6 replaces his cumulative cost, which
here is a function of steps because the local student costs nothing.

Computed at each advice turn, before the advice is generated, only from
what the student has done and seen in its own run: its commands, their
exit codes and outputs, and the repo's working tree. Never from the hidden
tests or the eval server. Seven inputs, each in [0, 1]:

  1  steps used          s / 40, where s = student steps taken so far
  2  steps remaining     (40 − s) / 40 (kept as Sagnik defined it, though
                         it is 1 − input 1)
  3a failing tests       of the student's most recent command that runs
                         tests (matches `pytest`, `python -m pytest`,
                         `python -m unittest`, `tox` or `nox`), the failed
                         plus errored count parsed from its output,
                         min(count, 20) / 20; 0 if none has run
  3b no tests run yet    1 if no such command has run, else 0
  4  command failures    share of the last 5 student commands with a
                         non-zero exit code (over the commands run, if
                         fewer than 5; 0 if none)
  5  steps without       steps since the last progress event, / 40.
     progress            Progress = the hash of `git diff` in the working
                         tree changes, or input 3a changes. Counted from
                         step 0 if neither has happened.
  6  advice turn index   k / 9, where k = 0 for the first advice turn

If a test command's output cannot be parsed, input 3a keeps its previous
value and the record flags `tests_unparsed`. The parser and the progress
hash are unit-tested on fixture outputs (G4).

Untrained comparisons, on the 49 test issues, three passes each:
  A  the student alone
  U  the student with the untrained Qwen2.5-7B advisor

Evaluation of G, P and P6: the final-step export of each, served by vLLM on the
Spark with E7's eval flags (temperature 0.7, top_p 0.8, top_k 20, min_p 0,
1,024-token replies), three passes on the 49 test issues.

Run ids (`hecate.utils.run_ids`):
  Training  `exp-10_arm-grpolora_split-tenacitytrain_seed-0`,
            `exp-10_arm-ppolora_split-tenacitytrain_seed-0`,
            `exp-10_arm-ppo6feat_split-tenacitytrain_seed-0`
  Eval      `exp-10_arm-{alone,untrained,grpolora,ppolora,ppo6feat}_split-tenacityval_seed-0`,
            `_run-2`, `_run-3`

4 Metrics
---------

Per issue and arm: resolve rate (mean of three 0/1 passes), mean steps,
steps on resolved issues, advice deliveries.

Paired comparisons with `compare_swe_arms.py` (bootstrap over issues, 95%
intervals). An issue that errors in any pass of any arm in a join is dropped
from that join. Joins: P vs G (Q10.1), P6 vs G (Q10.5), P vs P6 (Q10.6);
each trained arm vs A (Q10.2) and vs U (Q10.3).

Training (Q10.4), per step, from the saved trajectories (§6) and SkyRL's
logs: mean reward, share of rollouts resolved, share of groups with zero
reward std (no GRPO signal), KL, policy entropy; for P and P6 the critic's
value loss and explained variance; peak Spark memory per arm.

Critic quality (Q10.4, offline, about $0). From the §6 records:
  - Offline six-feature model F: ridge regression (α = 1.0) from the seven
    inputs to the rollout's final reward, one row per advice turn.
    Fitted and scored with 5-fold cross-validation grouped by issue (the
    56 training issues, folds fixed by issue id, seed 0), separately on
    G's, P's and P6's records.
  - Measure: explained variance of the final reward, 1 − Var(R − V) / Var(R),
    over all advice turns of the run, for F's out-of-fold predictions and
    for each trained critic's own value at those turns (P's 1.5B critic,
    P6's MLP; each value is the one computed before that step's update, so
    it is out-of-sample in time). Also the Brier score of each, clipped to
    [0, 1], against `resolved`.
  - Intervals: 95% bootstrap over issues (10,000 resamples) on the
    difference in explained variance.

5 Decision rules (fixed before any E10 run)
-------------------------------------------

Reading rule (E7's Flash rule) for a difference X − Y:
  "X raises resolve": resolve 95% lower bound > 0.
  "X keeps resolve and cuts steps": steps 95% upper bound < 0 and resolve
  95% lower bound > −10 points.
  Anything else: no detectable difference at n = 49.

Multiple comparisons. The three trained-arm comparisons (P − G, P6 − G,
P − P6) are one family. Each is read with Bonferroni-adjusted two-sided
98.33% bootstrap intervals (α = 0.05 / 3) in place of 95%, in both parts of
the reading rule (the −10-point resolve bound included). The comparisons
against A and U (Q10.2, Q10.3) are secondary, read at 95% and labelled
"unadjusted".

  1. Q10.1 (P − G). "PPO trains a better advisor" if either reading holds
     for P − G; "GRPO trains a better advisor" if either holds for G − P.
     Otherwise "no detectable difference at n = 49, one training seed".
  2. Q10.5 (P6 − G), the same rule: "a six-feature critic trains a better
     advisor than GRPO", the reverse, or no detectable difference.
  3. Q10.6 (P − P6), the same rule: "reading the text helps the critic"
     only if P beats P6; "the six features are enough" is not concluded
     from a null, only "no detectable difference".
  4. Q10.2 and Q10.3: each trained arm against A and against U, same
     reading rule at 95%, reported for all three arms whatever rules 1–3
     say.
  5. Q10.4, critic quality: for the difference in explained variance,
     P's 1.5B critic − F (on P's records): "the LLM critic uses more than
     the six features" if the 95% lower bound > 0; otherwise "the 1.5B
     critic does not beat the six-feature model, so it is not shown to use
     the text". The same comparison is reported for P6's MLP − F
     (descriptive: both read the same inputs). The rest of Q10.4 is
     descriptive.
  6. Predictions, recorded now and not rules: no detectable difference in
     any of the three trained-arm comparisons; no trained arm beats A; all
     three beat U on resolve; P and P6 have a higher share of non-zero
     advantages than G (by construction); P's critic does not beat F on
     explained variance.
  7. A second training seed, or a full-fine-tune PPO run, needs its own
     amendment or spec. It is not a reinterpretation of this one.

One training seed per arm, as in E7: a difference can come from the seed,
and the write-up says so next to every rule-1 result.

6 Saved trajectories (state, action, reward)
--------------------------------------------

Every training rollout of all three arms is saved, not only the checkpoints, so
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
  Features  the seven inputs of §3.1 at this turn, raw counts beside
            the normalized values, and the `tests_unparsed` flag
  Training  the advantage given to this turn's tokens; for P and P6 the
            critic's value at this turn and the GAE return; for G the
            group mean and std
  Student   per rollout, the full student trajectory (mini-SWE-agent's own
            trajectory file) and the test report, saved beside the records

Evaluation passes save the same records (no advantage or value fields).
Nothing secret is written: no API key is used anywhere in E10.

Size is measured at G2 and recorded. Disk: the Spark has ~757 GB free on
`/` (12 Nov); if G2 projects more than 300 GB for all three arms, older steps'
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
        d. SkyRL, its LoRA patch, the PPO critic and P6's feature-based
           value function build on aarch64.
           If SkyRL cannot run on the Spark, E10 stops.
  G1  Memory: student + advisor vLLM + policy + critic loaded together,
      one training step of each arm (G, P, P6) on 4 training issues. Peak
      memory recorded. If P does not fit: the advisor's vLLM sleeps during
      updates (SkyRL colocated mode); then the student drops to
      `Qwen/Qwen3-8B` for all arms, by amendment before any full run.
  G2  Smoke: 3 training steps per arm with trajectory saving on. Checks
      every §6 field is present and records size per step. Fixes the step
      count (295 or 150) by amendment.
  G3  Durability: each run dir (manifest, `CODE_SHA`, config, logs,
      trajectories, exports) is copied to
      `gs://hecate-506120-artifacts/runs/<run_id>/` through a machine with
      bucket access (the Spark has no GCP credentials). A run without that
      copy is incomplete.
  G4  Offline tests (CI, no GPU, network or model): the LoRA merge round
      trip, the GAE advantage on a fixture trajectory, the trajectory
      writer's schema on a fixture rollout, the §3.1 feature code on
      fixture student runs (test-output parser, exit-code window, progress
      hash, the no-tests case), P6's per-turn value broadcast, and the
      offline F fit on a fixture set of records.

Order: A and U eval passes; G training then its eval passes; P training
then its eval passes; P6 training then its eval passes. One trainer at a
time. The offline critic comparison (Q10.4) runs after all three trainings. Joins only after all passes
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

Cap: $50 total. No OpenRouter key or cost-cap change is needed. P6 adds a
third training run and its eval passes on the Spark (about half again the
Spark time of rev 4) but no money; the offline comparison runs on a laptop
or the Spark.

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
  VII Shared-scaffold fairness: all three arms share the student,
      harness, issues, reward, rollouts per step, steps and LoRA shape;
      only the advantage (and P's and P6's critics) differs.

10 Risks and scope
------------------

  - One seed, 49 test issues, passes that vary by up to ~19 points (E7):
    "no detectable difference" is the most likely rule-1 outcome. The
    training curves (Q10.4) are the lower-noise result.
  - Not comparable with E7's numbers: different student, LoRA instead of
    full fine-tuning, a different serving stack.
  - ARM containers: a pass/fail mismatch with x86 stops E10 (G0b).
  - Memory: the four models share ~114 GiB; G1's fallbacks are fixed above.
  - Three pairwise tests at n = 49 with one seed and adjusted intervals:
    nulls are even more likely than in rev 4.
  - P6's features are hand-built (§3.1): a weak P6 can mean weak features,
    not a weak idea. The offline F comparison shows how much reward the
    features predict at all.
  - One machine: the Spark runs only one E10 trainer at a time, and E11
    waits for it.
  - Out of scope: other students, repos or harnesses; advise-or-escalate;
    full fine-tuning.

11 Not authorized by this document
----------------------------------

Any code, any Spark or worker run (including G0), and any download of model
weights. Authorization comes after review, as an amendment below.
