Experiment 10 — PPO vs GRPO for the M1/M2 router
Hecate Lab
Same backbone, same split, same reward; four training objectives · rev 1 — PLANNED
November 11, 2026

Status: PLANNED. Nothing in this document is authorized to run. Path 1 of
the PPO-vs-GRPO discussion (11 Nov): LoRA for every arm, on the lab's DGX
Spark. Path 2 (full fine-tune, to match E7's GRPO) is not part of E10; it
needs its own spec and is only considered under rule 7 (§8).

Position in slate: Experiment 10. Does not start, stop, or overwrite E1–E9.

  E2  Specialist django (this experiment reuses its split and labels)
  E7  Route-then-Advise (its advisor was trained with GRPO, full fine-tune)
  E8  Handoff modes (plan, not yet in `experiments/`)
  E9  Route or Advise (plan)
  E10 PPO vs GRPO for the router (this document)

Abstract
--------
Hecate's routers are trained with cross-entropy on "did the cheap model
solve it". E7 trained an LLM with GRPO. E10 asks, on one fixed router
problem, whether the training objective matters: the same Qwen2.5-Coder-7B
LoRA policy, the same django specialist split as E2 (165 train, 20 val, 46
test), the same input (issue text only, K=0) and the same reward, trained
four ways: label cross-entropy, a full-information expected-reward loss,
GRPO, and PPO with a learned critic.

The router's action is one token (M1 or M2) and both models' outcomes and
costs are known for every training task. That makes this the simplest
setting in which to compare PPO and GRPO, and it makes a supervised arm that
uses both known outcomes the natural ceiling. The predictions in §8 say so
before any number is seen.

Q10.1  Does GRPO (group-mean baseline) or PPO (learned critic) give the
       better router on Route-AUC, at the same sample budget?
Q10.2  Does either RL objective beat the full-information expected-reward
       loss, which uses both known outcomes and samples nothing?
Q10.3  Does a cost-aware objective beat E2-style label cross-entropy?
       (Diagnostic.)
Q10.4  Does any arm reach always-Opus quality on the holdout (33/46) with
       fewer than 46 Opus calls? E2's K=0 LoRA did not.
Q10.5  What does each objective cost to train: GPU-hours and peak memory?

1 What is already known
-----------------------

E2 holdout, seed 0, 46 django issues (`experiments/e02-specialist-django/results.md`):

  Always M1 (Qwen3-Coder)        27/46   $8.97
  Always M2 (Claude 4 Opus)      33/46   $49.75
  Oracle                         37/46   10 Opus calls, $19.72
  Complementarity: both 23, M1-only 4, M2-only 10, neither 9.

  E2 arm (score head)            Route-AUC   Opus calls to reach 33
  A frozen logreg                0.373       46
  B K=0 LoRA (`_run-3`)          0.489       46
  D K=1 LoRA (`_run-3`)          0.583       36

Every number turns on about 10–14 issues, so intervals will be wide (§10).

E7's GRPO was a full fine-tune (FSDP2, Qwen2.5-7B-Instruct, lr 1e-6, 4×
A100). E10 uses LoRA throughout because a full 7B fine-tune with a critic
(~240 GB) does not fit the Spark's 128 GB. E10 therefore says nothing about
PPO vs GRPO for full fine-tuning or for the advisor. That limit is stated
next to every E10 result.

2 Data and split
----------------

E2's specialist split, unchanged: `assign_specialist_split` on django,
split seed 0, 185 train / 46 test, with E2's 20-issue validation carve (the
same instance IDs), so 165 issues train. Labels from
`data/external/qwen3coder_vs_claude4opus_with_text.csv` (M1 = Qwen3-Coder-
480B-A35B-Instruct, M2 = Claude 4 Opus, mini-SWE-agent v1.0.0). Per-issue
costs are the 2025-08-02 `per_instance_details.json` `cost` field read by
`hecate.data.external_miniswe`, as in E2's matched-quality table. The 46
test issues are not read by any training, validation or early-stopping
step.

Training seeds 0–4 (the split seed stays 0). Seeds reduce to 0–2 only by
amendment at gate G1 (§9), before any holdout number exists.

3 Policy
--------

All four arms train the same policy:

  Backbone   Qwen/Qwen2.5-Coder-7B-Instruct, bf16 (no 4-bit; recorded
             difference from E2's QLoRA, which the Spark's memory makes
             unnecessary)
  LoRA       r 32, alpha 64, dropout 0.05, the target modules of
             `configs/router_traj.yaml` (E2's adapter shape)
  Input      the K=0 issue text exactly as E2's arm B builds it, 8,192-token
             cap, followed by a fixed instruction asking for one letter:
             A (cheap model) or B (strong model)
  Action     one token, restricted to {A, B}: the two logits are taken from
             the last position and normalized over those two tokens only,
             so there are no invalid outputs
  Score      π(A | x), the probability of routing to M1. This is the score
             Hecate's Route-AUC sweeps (`hecate.router.metrics`), so every
             arm is scored with the same code as E2

Because the action is one token, the log-probability of both actions comes
from one forward pass over the prompt. Sampling G actions per issue costs no
extra forward passes, which keeps the RL arms close to supervised cost (§10).

4 Reward
--------

  r(x, a) = solved(x, a) − μ · cost(x, a) / c̄_M2

solved is 1 if the chosen model resolved issue x, else 0; cost is that
model's logged cost on x; c̄_M2 is the mean M2 cost over the 165 training
issues. μ = 0.5, fixed.

Why 0.5: on this split M1 costs about 0.18× M2 per issue. With 0 < μ < ~1.2
the reward's best deterministic choice is the oracle route (M1 unless only
M2 solves the issue), so μ sets the margin, not the answer. μ is not tuned.
(μ is a cost weight in the reward. The λ in Hecate's Route-AUC is a score
threshold; the two are unrelated.)

5 Arms
------

  A  Label CE         cross-entropy on E2's label (target A iff M1
                      resolves), through the route token. E2's objective
                      with a generative head instead of a score head.
  B  Full-information loss  −Σ_a π(a|x)·(r(x,a) − r̄(x)), r̄ the mean of
                      the two rewards. Uses both known outcomes; samples
                      nothing. Exact expected-reward gradient.
  C  GRPO             per issue, G = 4 actions sampled from π_old;
                      advantage (r_i − mean_G) / (std_G + 1e-6), 0 when
                      std_G = 0; PPO clip 0.2; KL to the base model
                      (adapter disabled), β = 0.001.
  D  PPO              same 4 samples per issue, each its own one-step
                      rollout; advantage r − V(x), V a critic (a second LoRA
                      adapter on the same frozen base with a scalar head on
                      the last prompt token), advantages normalized per
                      batch; one-step GAE (γ = 1, λ_GAE = 1); clip 0.2; same
                      KL and β; value-loss coefficient 0.5.

C and D see the same sampled actions per epoch (same seeds, same π_old
draws), so they differ only in the baseline: group mean against learned
critic. That is the PPO-vs-GRPO question in its cleanest form.

E2's arm B (score head, Route-AUC 0.489, seed 0) is cited as context only. It
is not an E10 arm and no rule compares against it.

6 Training
----------

Shared: 16 issues per optimizer update (E2's effective batch), AdamW,
weight decay 0.01, grad clip 1.0, at most 10 epochs, early stopping on the
20 validation issues with patience 2, restoring the best adapter.

  Arm   LR (policy)  Val metric (early stopping)        min_delta
  A     5e-5         val CE                             0.01
  B     5e-5         val expected reward Σ_a π(a|x) r   0.005
  C     1e-5         val expected reward                0.005
  D     1e-5         val expected reward                0.005
  D critic LR 5e-5.

LRs follow E2 (5e-5, supervised) and E7's Spark plan (1e-5 for LoRA RL).
None is tuned.

Code: one trainer, `src/hecate/router/rl_route.py`, with the four arms as
loss functions over the same batches, data path and evaluation. A and B
reuse it so all four share prompt building, token restriction and scoring.
Not SkyRL: with a one-token action there is no generation to schedule, and
SkyRL's LoRA path on aarch64 is unverified. The GRPO arm follows the
DeepSeekMath/SkyRL `grpo` advantage definition above. Unit tests (§11.III)
pin the advantages, the zero-std case and the reward.

Run IDs (`hecate.utils.run_ids.make_run_id`):
`exp-10_arm-{ce,fullinfo,grpo,ppo}_split-specialist_seed-{0..4}`.

Each run saves: the adapter (`.save()`; and the critic for D),
`training_summary.json` (per-epoch train/val metrics, restored epoch, wall
time, peak memory), and `holdout_scores.jsonl` (46 rows: instance_id,
π(A|x), M1/M2 resolved, M1/M2 cost). A run without its off-machine copy is
incomplete (§9, G0).

7 Metrics
---------

Primary: Route-AUC on the 46 holdout issues, `hecate.router.metrics`
(score = π(A|x)), per seed. Arm value = mean over seeds.

Paired comparison of two arms: 10,000 bootstrap resamples over the 46
issues. Each resample recomputes every seed's Route-AUC on the resampled
issues and takes the seed mean; the 95% interval is on the difference of
seed means.

Secondary, matched quality (E2 rev 3): sweeping the score threshold, the
fewest Opus calls that reach ≥ 33 resolved, and that policy's dollar cost
from the per-issue costs. Reported per seed, with the median.

Diagnostic: AUROC, Brier, val curves, and for C and D the mean advantage
magnitude and the share of GRPO groups with zero std.

Compute (Q10.5): wall-clock GPU-hours to the restored epoch and in total,
and peak memory, per arm.

8 Decision rules (fixed before any E10 run)
-------------------------------------------

  1. Q10.1. "GRPO better": C − D Route-AUC > 0 with 95% lower bound > 0.
     "PPO better": C − D < 0 with 95% upper bound < 0. Otherwise "no
     detectable difference at n = 46", which is not a positive result for
     either.
  2. Q10.2, for C and for D separately against B. "RL beats full
     information" only if (RL − B) has a 95% lower bound > 0. "Full
     information beats RL" if the upper bound < 0. Otherwise no detectable
     difference.
  3. Q10.3 (B − A): signed gap and interval, no pass/fail.
  4. Q10.4: per arm, the number of seeds whose matched-quality policy uses
     fewer than 46 Opus calls, and the median call count. Descriptive.
  5. Q10.5: per-arm compute, descriptive.
  6. Predictions, recorded now and not rules: B ≥ C ≥ D on Route-AUC; D
     costs more compute than C; most seeds of every arm still need 46 Opus
     calls (the features are E2 K=0's, which never found a cheaper 33).
  7. Path 2 (full fine-tune on 4× A100, ~$200–400) is proposed in a new
     spec only if rule 1 returns "PPO better". Any other outcome closes the
     question for the router.

With 46 issues and 5 seeds a null result is a power statement, not
evidence that the objectives are equal. Route-AUC is primary; AUROC is not
reinterpreted as a routing result.

9 Gates and order
-----------------

  G0  Spark environment. On `spark` (aarch64, GB10, 128 GB; tmux, logs to
      file, no sudo): the trainer runs one update for each arm on 4
      training issues; peak memory recorded (D holds base + policy LoRA +
      critic LoRA). aarch64 wheels for torch/transformers/peft checked
      first, NGC PyTorch container preferred. The Spark has no GCP
      credentials (CLAUDE.md), so the artifact route is settled here: run
      dirs are copied off the Spark to `gs://hecate-506120-artifacts/runs/`
      through a host that has bucket access. `finalize_run_artifacts()`
      fail-closes until that copy exists.
  G1  Timing smoke: one epoch of seed 0 for C and for D on the 165 training
      issues. No holdout scoring. If the projected total exceeds 100 Spark
      hours, seeds drop to 0–2 by amendment.
  G2  Offline tests pass (§11.III).
  Run order: A, B, C, D for seed 0; then seeds 1–4 in the same order.
  Holdout scoring happens after each run's restore, but no cross-arm
  comparison is computed until every planned run has finished.

10 Budget and time
------------------

Time scales from E6's measured L4 LoRA epoch (≈5.4 s per row, ~1,900-token
median prompt) to 165 rows ≈ 15–17 min per supervised epoch, assuming the
Spark runs about as fast as an L4. G1 replaces this with a measurement.

  Arm           Per epoch vs CE   Epochs (ES)   Per seed     5 seeds
  A label CE    1×                3–5           ~1–1.5 h     ~5–8 h
  B full-info   1×                3–5           ~1–1.5 h     ~5–8 h
  C GRPO        ~1.7× (+ ref)     3–10          ~1.5–5 h     ~8–24 h
  D PPO         ~2.5× (+ critic)  3–10          ~2–7 h       ~10–35 h
  Total Spark                                                ~30–75 h

  Item                       Cost
  Spark GPU                  $0 (lab-owned)
  Electricity (~240 W)       ~$2–5
  API                        $0 (labels and costs already in the repo)
  GCS (≈20 adapters + D's critics, ~160 MB each)  cents per month
  Engineering                2–3 days (trainer, tests, G0)

Wall time: about 1–1.5 weeks after review (2–3 days build and gates, 2–4
days of Spark runs, 2 days analysis and write-up).

11 Constitution check (`.specify/memory/constitution.md`)
---------------------------------------------------------

  I   Execution-grounded validity: every label and reward comes from the
      logged mini-SWE-agent v1.0.0 resolved/unresolved outcomes; nothing
      is relabelled.
  II  Reproducibility by manifest: run id, code SHA, config, seed, adapter
      and per-issue holdout scores for every run, copied off the Spark.
  III Offline-testable CI: unit tests for the reward, the two-token
      restriction, GRPO advantages (including zero std), the one-step PPO
      advantage and Route-AUC on fixtures. No test needs a GPU, network or
      provider.
  IV  Spec-driven: this document precedes any code.
  V   Budget discipline: no API spend; GPU is the lab's Spark; the G1
      100-hour cut-off.
  VI  Secrets hygiene: no keys involved; none written to logs or the repo.
  VII Shared-scaffold fairness: one trainer, one backbone, one prompt, one
      split, one reward; arms differ only in the loss.

12 Risks and scope
------------------

  - Small n: 46 test issues, 10 M2-only. Expect rule-1 "no detectable
    difference"; the compute comparison (Q10.5) is the low-noise result.
  - Weak features: K=0 issue text alone never beat always-Opus at matched
    quality in E2. All arms may tie at "always M2" for matched quality.
  - LoRA only: results do not carry to full fine-tuning or to E7's
    advisor (long text, multi-step reward), where a critic could matter
    more.
  - Speed: Spark-vs-L4 throughput is assumed until G1.
  - Out of scope: the step-level escalate decision (needs E8), λ-conditioned
    policies, other repos, the SB3 MLP baseline.

13 Not authorized by this document
----------------------------------

Any code beyond review, any Spark run (including G0), and any change to E2's
runs or results. Authorization comes after review, as an amendment below.
