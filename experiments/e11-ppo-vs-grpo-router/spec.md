Experiment 11 — PPO vs GRPO for the M1/M2 router, on the DGX Spark
Hecate Lab
E2's LoRA router retrained with GRPO and with PPO; same model, split and reward · rev 4 — PLANNED
November 12, 2026

Status: PLANNED. Nothing in this document is authorized to run.

Revision history (all before any code or run):
  rev 1  `f9d6f42`  as E10: router, four objectives, new two-token trainer
  rev 2  `12a141e`  E10 redefined as PPO vs GRPO for the E7 advisor
  rev 3  `2eca0c1`  as E10: router again, two RL arms plus a cross-entropy
                    reference, built on E2's existing router code and run on
                    the Spark by a lab member over SSH (`runbook.md`)
  rev 4  this       renumbered E10 -> E11 on 12 Nov, unchanged otherwise:
                    Scott made the advisor study (all on the Spark, local
                    student) Experiment 10 (`experiments/e10-ppo-vs-grpo-advisor/`)

Position in slate: Experiment 11. Does not start, stop, or overwrite E1–E10.

  E2  Specialist django (this experiment reuses its split, model and code)
  E7  Route-then-Advise (its advisor was trained with GRPO)
  E10 PPO vs GRPO for the E7-style advisor, all on the Spark (runs first)
  E11 PPO vs GRPO for the M1/M2 router (this document; the Spark runs one
      trainer at a time, so E11 waits until the Spark is free of E10)

Abstract
--------
E7 trained an LLM with GRPO, which drops PPO's learned critic and scores
each sample against the average of its group. E11 asks whether that choice
matters on a small, fully controlled problem that Hecate already has: the
router that sends an SWE-bench task to the cheap model (M1, Qwen3-Coder-480B)
or the strong one (M2, Claude 4 Opus). E2's router is retrained on E2's
django split three ways: with E2's cross-entropy loss (reference), with
GRPO, and with PPO. Model, input, split, reward, sampled actions and
training budget are shared; only the objective differs.

Both models' outcomes and costs are already logged for every task, so no
agent runs live: the experiment needs no API calls and no containers, and
it runs on the lab's DGX Spark in about 2–3 days. It also sets up the
Spark's training stack.

Q11.1  Does GRPO (group-mean baseline) or PPO (learned critic) give the
       better router on Route-AUC, at the same sample budget?
Q11.2  Does either RL objective beat E2's cross-entropy objective on the
       same model? (Secondary.)
Q11.3  Does any arm reach always-Opus quality on the holdout (33/46) with
       fewer than 46 Opus calls? (Descriptive.)
Q11.4  What does each arm cost to train on the Spark: GPU-hours, peak
       memory, epochs to the best checkpoint? (Descriptive.)

1 What is already known
-----------------------

E2 holdout, seed 0, 46 django issues (`experiments/e02-specialist-django/results.md`):

  Always M1 (Qwen3-Coder)        27/46   $8.97
  Always M2 (Claude 4 Opus)      33/46   $49.75
  Oracle                         37/46   10 Opus calls, $19.72
  Complementarity: both 23, M1-only 4, M2-only 10, neither 9.

  E2 arm (score head, cross-entropy, L4, QLoRA)   Route-AUC   Opus calls to 33
  A frozen logreg                                 0.373       46
  B K=0 LoRA (`_run-3`)                           0.489       46
  D K=1 LoRA (`_run-3`)                           0.583       36

These are context. E11's own cross-entropy arm is rerun on the Spark so
that all three E11 arms share hardware and settings. Every number turns on
about 10–14 issues, so intervals will be wide (§11).

2 Data and split
----------------

E2's specialist split, unchanged: `--split specialist --hold-repo
django/django` (`assign_specialist_split`, split seed 0), 185 train / 46
test. Inside the 185, `carve_fit_val` holds out 20 validation issues per
training seed, the same 20 for every arm at that seed. The 46 test issues
are not read by training, validation or early stopping.

Labels: `data/external/qwen3coder_vs_claude4opus_with_text.csv` (M1/M2
resolved, problem statement), as in E2. Input: K=0, the issue text only
(arm `k0`), so E2's trajectories are not used for features.

Costs (new data step, no new numbers): each issue's logged `cost` for M1 and
M2 from the two 2025-08-02 SWE-bench `per_instance_details.json` files whose
URLs are in `hecate.data.external_miniswe` (the source of E2's matched-quality
table). A small script writes them once to
`data/external/qwen3coder_vs_claude4opus_costs.csv` (instance_id, m1_cost,
m2_cost). The script fails if any of the 231 django issues lacks a cost.

Training seeds 0, 1, 2 (the split seed stays 0).

3 Model
-------

E2's router, unchanged in shape (`TrajLoraBackend` in
`src/hecate/router/traj_lora.py`, settings from `configs/router_traj.yaml`):

  Backbone   Qwen/Qwen2.5-Coder-7B-Instruct
  LoRA       r 32, alpha 64, dropout 0.05, q/k/v/o/gate/up/down projections
  Quant      QLoRA (4-bit NF4) as in E2 if bitsandbytes runs on the Spark
             (gate G0); otherwise bf16 LoRA for every arm, recorded
  Input      K=0 issue text, 8,192-token cap
  Head       E2's score head: a linear layer from the last token's hidden
             state to 2 logits, zero-initialized

The two logits are read as a policy over two actions: route to M1 or route
to M2. π(M1 | x) = softmax(logits)[M1]. This is the same number E2's router
outputs as P(M1 resolves), so every arm is scored by the same Route-AUC code
(`hecate.router.metrics`). Because the head starts at zero, every arm
starts from π = (0.5, 0.5).

4 Reward
--------

  r(x, a) = solved(x, a) − μ · cost(x, a) / c̄_M2

solved is 1 if the chosen model resolved issue x, else 0; cost is that
model's logged cost on x; c̄_M2 is the mean M2 cost over that seed's
training issues. μ = 0.5, fixed.

Why 0.5: on this split M1 costs about 0.18× M2 per issue. For any 0 < μ <
~1.2, the reward's best deterministic choice is the oracle route (M1 unless
only M2 solves the issue), so μ sets the margin, not the answer. μ is not
tuned. (μ is a cost weight; the λ in Hecate's Route-AUC is a threshold on
the score. They are unrelated.)

5 Arms
------

  CE    E2's objective: cross-entropy on "M1 resolves", early stopping on
        validation CE. Reference arm.
  GRPO  For each training issue, sample G = 4 actions from π (seeded).
        Advantage of sample i: (r_i − mean_G) / (std_G + 1e-6); 0 when the
        4 rewards are equal. Loss: −mean_i A_i · log π(a_i | x).
  PPO   The same 4 samples per issue. Advantage: r_i − V(x), normalized over
        each optimizer batch. V is a critic: a separate linear head on the
        same last-token hidden state, detached, so the critic does not train
        the LoRA. Critic loss: mean squared error to r_i, its own Adam
        optimizer at LR 1e-3, value-loss coefficient 1 (it has its own
        parameters). Policy loss: −mean_i A_i · log π(a_i | x).

Shared by the two RL arms:
  - Same sampled actions: the same seed and the same π draw the samples, so
    GRPO and PPO see identical (issue, action, reward) data in epoch 1.
  - KL to the starting policy: π_ref = (0.5, 0.5) because the head starts at
    zero, so KL(π || π_ref) = log 2 − H(π) needs no reference forward pass.
    Coefficient β = 0.001 (E7's KL coefficient).
  - One gradient update per sample batch. The PPO ratio is therefore 1 and
    its clip never binds; that is E7's setting (`update_epochs_per_batch=1`).
    The arms differ only in the baseline: group mean against learned
    critic.

Shared by all three arms (E2's settings): batch 1 with gradient
accumulation 16, AdamW, LR 5e-5, weight decay 0.01, grad clip 1.0, at most
5 epochs, gradient checkpointing. Early stopping, patience 2, restoring the
best adapter and heads: CE on validation CE (min_delta 0.01, as E2); GRPO
and PPO on validation expected reward Σ_a π(a|x)·r(x,a) (min_delta 0.005).
Nothing is tuned.

Code changes (the only new code):
  - `--objective {ce,grpo,ppo}` in `scripts/run_train_traj.py`, threaded
    through `traj_runner.py` to `TrajLoraBackend.fit()`. `ce` is today's
    path, byte for byte.
  - In `fit()`: the GRPO and PPO losses, the critic head, the KL term, the
    validation expected reward, and the critic saved with the adapter.
  - `scripts/fetch_miniswe_costs.py` (§2).
  - `configs/router_traj_e11_smoke.yaml`: `configs/router_traj.yaml` with
    `epochs: 1`, for the G2 smoke only.
  - Unit tests (§10.III), in `tests/test_router_rl.py`.

Run ids (`hecate.utils.run_ids.make_run_id`, split `specialist`):
  `exp-11_arm-ce_split-specialist_seed-{0,1,2}`
  `exp-11_arm-grpo_split-specialist_seed-{0,1,2}`
  `exp-11_arm-ppo_split-specialist_seed-{0,1,2}`

Each run writes what E2's runs write (adapter via `.save()`,
`training_summary.json`, 46-row `holdout_scores.jsonl`), plus for GRPO and
PPO the per-epoch mean reward, mean advantage magnitude, share of
zero-advantage groups (GRPO), critic loss and explained variance (PPO).

6 Metrics
---------

Primary: Route-AUC on the 46 holdout issues (`hecate.router.metrics`,
score = π(M1|x)), per seed; arm value = mean over seeds.

Paired comparison of two arms: 10,000 bootstrap resamples over the 46
issues; each resample recomputes every seed's Route-AUC on the resampled
issues and takes the seed mean; the 95% interval is on the difference of
seed means.

Secondary, matched quality (E2 rev 3): sweeping the score threshold, the
fewest Opus calls that reach ≥ 33 resolved, and that policy's dollar cost.
Per seed, with the median.

Diagnostic: AUROC and Brier (never read as routing results), validation
curves, and the RL training statistics in §5.

Compute (Q11.4): wall-clock hours per run, epochs to the restored
checkpoint, peak GPU memory.

7 Decision rules (fixed before any E11 run)
-------------------------------------------

For a difference X − Y in seed-mean Route-AUC: "X better" if the point
estimate > 0 and the 95% lower bound > 0; "Y better" if < 0 and the upper
bound < 0; otherwise "no detectable difference at n = 46, 3 seeds", which
is not a positive result for either.

  1. Q11.1: GRPO − PPO. Primary.
  2. Q11.2: GRPO − CE and PPO − CE, each read on its own. Secondary.
  3. Q11.3 and Q11.4: descriptive.
  4. Predictions, recorded now and not rules: no detectable GRPO − PPO
     difference; neither RL arm beats CE; most seeds of every arm still need
     46 Opus calls to reach 33 (E2's K=0 router never found a cheaper 33);
     PPO and GRPO cost about the same to train (the critic is one linear
     head).
  5. E11 says nothing about PPO vs GRPO for long-text, multi-turn training.
     That is E10's question, whatever E11 finds.

8 Gates and order
-----------------

  G0  Spark environment (runbook §2). On `spark` (aarch64, GB10, 128 GB;
      tmux, logs to a file, no sudo, `df -h /` before downloads): the
      repo's Python environment, with torch, transformers and peft for
      aarch64 + CUDA (NGC PyTorch container preferred). Check whether
      bitsandbytes 4-bit loads; record the answer, which fixes QLoRA or
      bf16 for every arm (§3).
  G1  Offline tests pass (§10.III), including `ce` unchanged.
  G2  Smoke: one epoch of seed 0 for each arm on the training issues, with
      `--allow-unsynced` and no holdout scoring. Records time per epoch and
      peak memory. If the projected total exceeds 72 Spark hours, seeds
      drop to 0–1 by amendment.
  G3  Durability: `HECATE_ARTIFACTS_URI` points at a directory on the
      Spark outside the repo (the runner's local copy), and every finished
      run is copied from there to `gs://hecate-506120-artifacts/runs/`
      through a machine with bucket access (the Spark has no GCP
      credentials). A run without that copy is incomplete.

Order: seed 0 for CE, GRPO, PPO; then seeds 1 and 2. Arms may run two at a
time if G2 shows they fit in memory. Holdout scores are written after each
run's restore, but no comparison is computed until all nine runs exist.

9 Budget and time
-----------------

Time per epoch scales from E6's measured L4 epoch (≈5.4 s per row, median
prompt ~1,900 tokens): 165 rows ≈ 15–17 min. GRPO and PPO add only cheap
work per issue (4 samples from 2 logits, one linear critic), so all three
arms are assumed to cost about the same per epoch. G2 replaces this with a
measurement.

  Runs                        Epochs (ES)   Per run      Total
  CE, 3 seeds                 3–5           ~45–85 min   ~2–4 h
  GRPO, 3 seeds               3–5           ~45–85 min   ~2–4 h
  PPO, 3 seeds                3–5           ~45–85 min   ~2–4 h
  Smoke (G2)                                             ~1 h
  Total Spark                                            ~7–13 h

  Item                      Cost
  Spark GPU                 $0 (lab-owned)
  Electricity               a few dollars
  API, worker, containers   $0 (none used)
  GCS (9 adapters + heads)  cents per month

Wall time: about 2–3 days from approval: half a day of code and tests,
half a day of Spark setup and smoke, about a day of runs (overnight), half
a day of analysis and write-up.

10 Constitution check (`.specify/memory/constitution.md`)
---------------------------------------------------------

  I   Execution-grounded validity: every label and reward comes from the
      logged mini-SWE-agent v1.0.0 resolved/unresolved outcomes and costs
      of the two 2025-08-02 submissions; nothing is relabelled.
  II  Reproducibility by manifest: run id, `CODE_SHA`, config, seed,
      adapter, heads and per-issue holdout scores for every run (G3).
  III Offline-testable CI: unit tests for the cost join, the reward, GRPO
      advantages (including all-equal groups), the PPO advantage and
      critic step, the KL term, validation expected reward, and that
      `--objective ce` reproduces today's loss on a fixture. No test needs
      a GPU, network or provider.
  IV  Spec-driven: this document precedes any code.
  V   Budget discipline: no spend beyond electricity; the G2 72-hour cut.
  VI  Secrets hygiene: no keys involved; the lab member uses their own SSH
      key; none written to logs or the repo.
  VII Shared-scaffold fairness: one code path, model, prompt, split, reward
      and training budget; the arms differ only in the loss.

11 Risks and scope
------------------

  - Small n: 46 test issues, 10 M2-only. Expect "no detectable
    difference" (rule 1); the training statistics and compute are the
    low-noise results.
  - Weak features: K=0 issue text never beat always-Opus at matched quality
    in E2. All arms may route like "always M2" at the 33 bar.
  - The Spark is aarch64 with a new GPU: wheels and bitsandbytes may need
    the NGC container; G0 catches this before any run.
  - Small learning signal: the RL gradients (advantage × log-prob) are
    smaller than CE's. If an RL arm's policy stays near (0.5, 0.5) after 5
    epochs, that is reported as a result, not fixed by retuning.
  - Out of scope: the advisor (E10), the trajectory arms K=1/K=3, other
    repos, the SB3 MLP router, λ-conditioned policies.

12 Not authorized by this document
----------------------------------

Any code beyond review, any Spark run (including G0), and any change to E2's
runs or results. Authorization comes after review, as an amendment below.
