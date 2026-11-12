Experiment 10 — PPO vs GRPO for the E7 advisor, with LoRA
Hecate Lab
Retrain the Experiment 7 advisor twice on the DGX Spark: GRPO and PPO · rev 2 — PLANNED
November 11, 2026

Status: PLANNED. Nothing in this document is authorized to run.

Rev 2 (11 Nov, before any code or run): at Scott's direction E10 is about
the E7 advisor, not the M1/M2 router. Rev 1 (commit `f9d6f42`, directory
`e10-ppo-vs-grpo-router/`) trained a one-token router four ways on E2's
django split; it is withdrawn in full and nothing from it was built or run.
The directory is renamed to `e10-ppo-vs-grpo-advisor/`.

Position in slate: Experiment 10. Does not start, stop, or overwrite E1–E9.

  E7  Route-then-Advise: trained this advisor with GRPO (full fine-tune)
  E8  Handoff modes (plan, not yet in `experiments/`)
  E9  Route or Advise (plan)
  E10 PPO vs GRPO for the E7 advisor, with LoRA (this document)

Relation to the E7 follow-up proposal ("Does advice transfer?", 26 Oct):
that proposal's Phase C bridge retrains the Flash-Lite advisor with LoRA
GRPO. E10's GRPO arm is exactly that run. If both are approved, the run is
done once, under E10's run id, and both documents read it.

Abstract
--------
E7 trained a Qwen2.5-7B advisor with GRPO (Advisor Models' recipe) to give
advice to Gemini 2.5 Flash-Lite in mini-SWE-agent on SWE-smith Tenacity.
GRPO drops PPO's learned critic and scores each run against the average of
8 runs on the same issue. E7's advisor brought Flash-Lite back from 13.5%
(untrained advice) to 31.9% resolved, but did not beat Flash-Lite alone
(34.0%) or cut its steps. E7's notes name one reason: Flash-Lite resolves
about a third of issues, so many groups of 8 hold no resolved run and give
GRPO no signal.

E10 asks whether PPO, with a critic that scores each turn of advice, trains
a better advisor than GRPO under the same budget. Both arms use LoRA on the
lab's DGX Spark, because a full fine-tune with a critic does not fit there.
Everything else is E7's recipe: the same base model, student, training
issues, reward, turns, token limits, group of 8 rollouts per issue and 295
steps.

Q10.1  With LoRA, does the PPO advisor beat the GRPO advisor? Advised-by-PPO
       against advised-by-GRPO, on resolve and steps, on the 49 test issues.
Q10.2  Does each LoRA advisor beat Flash-Lite alone (E7's check 2 and 3
       question, asked again)?
Q10.3  Does LoRA GRPO land where E7's full-fine-tune GRPO did (31.9%
       resolved, 26.3 steps)? This is the proposal's bridge question; it
       says whether LoRA, rather than the algorithm, could explain a
       difference.
Q10.4  Training: reward, KL and the share of zero-signal groups per step,
       critic quality (explained variance), wall time and peak memory per
       arm. Descriptive.

1 What is already known (E7)
----------------------------

49 Tenacity test issues, Flash-Lite student, mini-SWE-agent, 40-step cap,
three passes per arm (E7 results and final write-up, 26 Oct):

  Arm                                   Resolve   Mean steps   Steps on resolved
  Flash-Lite alone                      34.0%     25.7         19.9
  + untrained Qwen2.5-7B advisor        13.5%     22.0         16.8
  + E7 GRPO advisor (full FT, step 295) 31.9%     26.3         16.7
  + E7 GRPO, epoch 10 (step 140)        27.7%     26.4         15.4

E7 GRPO minus alone: resolve −2.1 points [−11.3, +7.1], steps +0.6
[−2.3, +3.6]. 47 issues kept in E7's join. Passes of one arm vary by up to
19 points.

E7's recipe (`scripts/train_swe_smith_advisor.sh` in the advisor-models
fork, as amended by the E7 spec): SkyRL, Qwen/Qwen2.5-7B-Instruct, GRPO,
batch 4 issues × 8 rollouts, KL loss on (coefficient 0.001), max 9 advisor
turns (advice every 5 student steps), 28,672-token prompt and 4,096-token
generation limits, `zero_reward_on_non_stop`, training temperature 1.0,
56 training issues, 295 steps (21 epochs), full fine-tune at LR 1e-6 on
4× A100 (FSDP2). Reward: 0.5 + 0.5 × (40 − steps)/40 if the patch passes the
hidden tests, else 0.

2 Data, student and harness
---------------------------

  Training   the 56 Tenacity training issues (`train_jd__tenacity.json`),
             as in E7
  Test       the 49 Tenacity test issues (`validation_jd__tenacity.json`);
             never seen in training by either arm
  Student    `openrouter/google/gemini-2.5-flash-lite`, E7's student, in
             training and test
  Harness    mini-SWE-agent through E7's agent server and eval server on
             the x86 `hecate-worker` (SWE-smith containers are x86); the
             Spark reaches them over an SSH tunnel (CLAUDE.md), no new
             firewall rule
  Eval       E7's short-context eval, unchanged: advice every 5 steps,
             1,024-token replies, temperature 0.7, top_p 0.8, top_k 20,
             min_p 0, three `--num_runs 1` passes per arm

The student, harness and eval are E7's so that both arms and E7's existing
passes sit in one table.

3 Arms
------

Shared by both arms (fixed, not tuned):

  Base       Qwen/Qwen2.5-7B-Instruct, bf16
  LoRA       rank 32, alpha 32, dropout 0, all linear layers (attention and
             MLP); reference model = the base with the adapter disabled;
             adapter merged into the weights before each sync to vLLM and
             before each HF export (the E7 Spark plan)
  Policy LR  1e-5 (10× E7's full-fine-tune 1e-6, the usual LoRA/full ratio
             for RL; Schulman et al., "LoRA Without Regret", 2025)
  Recipe     everything else in §1: batch 4 × 8 rollouts, KL 0.001, 9
             turns, token limits, zero_reward_on_non_stop, temperature 1.0,
             56 issues, 295 steps, same reward
  Seed       0, one training run per arm (as E7)

  G  GRPO   `advantage_estimator=grpo`: each rollout's reward minus the
            mean of its group of 8, divided by the group's std; the same
            advantage on every advice token of that rollout. This is E7's
            algorithm with LoRA.
  P  PPO    `advantage_estimator=gae`, SkyRL defaults γ = 1, λ = 1: a
            critic predicts the final reward from the conversation so far,
            and each advice turn's tokens get (final reward − critic value
            at that point), so turns are scored separately. Critic: a
            second Qwen2.5-7B-Instruct with its own LoRA (same shape) and
            SkyRL's value head, LR 5e-5 (10× SkyRL's full-fine-tune 5e-6),
            value clip 0.2, advantages not batch-normalized (SkyRL
            default). P draws the same 4 × 8 rollouts per step as G, so both
            arms make the same number of student runs; P simply does not
            use the group to form its baseline.

The arms differ only in how the advantage is computed and in P's critic.
Same rollouts per step, same steps, same student calls.

Checkpoints: HF export of the merged policy every 14 steps (one epoch) and
at step 295, copied off the Spark (§9). Only step 295 is evaluated for the
rules. Step 140 (epoch 10) of each arm may be evaluated as an exploratory
pass, as in E7, labelled as such.

Run ids (`hecate.utils.run_ids`):
  Training  `exp-10_arm-grpolora_split-tenacitytrain_seed-0`,
            `exp-10_arm-ppolora_split-tenacitytrain_seed-0`
  Eval      `exp-10_arm-grpolora_split-tenacityval_seed-0`, `_run-2`,
            `_run-3`; the same for `ppolora`
  Flash-Lite alone: E7's three passes (`exp-07_arm-weakalone_split-
  tenacityval_seed-0_run-5/6/7`), reused, not rerun; their commits are
  recorded as in E7 check 1.

4 Metrics
---------

Per issue and arm: resolve rate (mean of three 0/1 passes), mean steps,
steps on resolved issues, student API cost, advice deliveries.

Paired comparisons with `compare_swe_arms.py` (bootstrap over issues,
95% intervals). An issue that errors in any pass of any arm in a join is
dropped from that join. Joins:
  P vs G             (Q10.1)
  G vs alone, P vs alone   (Q10.2)
  G vs E7 full-FT GRPO     (Q10.3)

Training (Q10.4), per step, from SkyRL's logs and `steps.csv`
(`scripts/e07_steps_csv.py`): mean reward, share of rollouts resolved,
share of groups with zero reward std (no GRPO signal), KL, policy entropy,
for P the critic's value loss and explained variance, and wall time per
step; peak Spark memory per arm.

5 Decision rules (fixed before any E10 run)
-------------------------------------------

Reading rule (E7's Flash rule) for a difference X − Y:
  "X raises resolve": resolve 95% lower bound > 0.
  "X keeps resolve and cuts steps": steps 95% upper bound < 0 and resolve
  95% lower bound > −10 points.
  Anything else: no detectable difference at n = 49.

  1. Q10.1 (P − G). "PPO trains a better advisor" if either reading holds
     for P − G. "GRPO trains a better advisor" if either holds for G − P.
     Otherwise "no detectable difference at n = 49, one training seed".
  2. Q10.2. Each arm against Flash-Lite alone with the same reading rule;
     reported for both arms whatever rule 1 says.
  3. Q10.3. LoRA GRPO "lands with E7" if its resolve is within ±10 points
     of 31.9% and its steps show no cut versus alone (the proposal's bridge
     criterion). If it does not, any P − G result is read as a LoRA result
     only, and the write-up says LoRA changed the GRPO outcome.
  4. Q10.4 is descriptive. A prediction is not a rule.
  5. Predictions, recorded now: no detectable P − G difference; neither arm
     beats Flash-Lite alone; P's share of non-zero advantages is higher than
     G's (by construction) without a resolve gain; P takes more wall time
     and memory per step.
  6. A full-fine-tune PPO run (4× A100, ~$1,500+ including student calls)
     gets its own spec only if rule 1 returns "PPO trains a better advisor".

One training seed per arm, as in E7: a difference can come from the seed,
and the write-up says so next to every rule-1 result. A second seed is a
follow-up by amendment, not a reinterpretation.

6 Gates and order
-----------------

  G0  Spark stack. On `spark` (aarch64, GB10, 128 GB unified; tmux, logs to
      file, no sudo, `df -h /` before downloads): SkyRL and vLLM build; the
      SkyRL LoRA patch (policy LoRA, reference = adapter disabled, merge
      before sync and export) and the PPO critic with LoRA run one training
      step each on 4 training issues against the worker's agent and eval
      servers. Peak memory recorded. If PPO's policy + critic + vLLM do not
      fit, the critic drops to Qwen2.5-1.5B-Instruct (SkyRL's PPO example)
      by amendment before any full run. If SkyRL cannot run on the Spark,
      E10 stops: the E7 proposal's fallback (OpenPipe ART) has no PPO.
  G1  Timing and cost smoke: 3 full training steps per arm. Measured step
      time and student cost per step replace §8's estimates. If either arm
      projects over its cap (§8), stop and amend.
  G2  Offline tests (advisor-models `tests/`): the LoRA merge round-trip,
      the GAE advantage on a fixture trajectory, and that both arms read
      the same rollout batch format. No test calls a provider.
  G3  Durability: the artifact route off the Spark is in place before the
      first full run. The Spark has no GCP credentials (CLAUDE.md); exports
      and run dirs go to `gs://whatsapp-sales-agent-hecate-artifacts/`
      through a host with bucket access. A run without that copy is
      incomplete.

Order: G (GRPO) full training, its three eval passes; then P (PPO) full
training, its three eval passes. One arm at a time: the Spark holds one
trainer. Joins only after both arms' passes exist.

7 Infrastructure
----------------

  Trainer + vLLM   the DGX Spark (both arms; advice generated by the
                   policy's vLLM during training)
  Agents + tests   `hecate-worker` (x86, `whatsapp-sales-agent`), agent
                   server 8081 and eval server 8082, through the SSH tunnel
  Eval advisor     each arm's step-295 export served by vLLM on the Spark
                   with E7's eval flags (bf16, `--max-model-len 32768`)
  Keys             `OPENROUTER_API_KEY` in `.env` on the worker and the
                   Spark, never in git or logs

The worker runs only while a training or eval arm is active, and is
stopped otherwise.

8 Budget and time
-----------------

Student calls dominate. Per training step: 4 issues × 8 rollouts = 32
Flash-Lite runs at E7's ~$0.062 per issue ≈ $2.0. 295 steps ≈ $585 per arm.

  Item                                   G (GRPO)     P (PPO)      Notes
  Student API, training (9,440 runs)     ~$585        ~$585        E7 per-issue cost
  Student API, eval (3 × 49)             ~$10         ~$10
  Smokes (G0, G1)                        ~$15         ~$15
  hecate-worker (~$1.55/h)               ~$110–230    ~$140–290    3–6 days G, 4–8 days P
  Spark GPU                              $0           $0           lab-owned
  Per arm                                ~$720–840    ~$750–900
  Total                                  ~$1,470–1,740

Caps: $900 per arm, $1,800 total OpenRouter + worker. An arm stops and
reports at its cap. The OpenRouter key's current limit ($250) must be raised
by Scott before G1; Claude does not change cost caps.

Time per step is unknown on the Spark until G1. E7 took ~7.5 min per step
on 4× A100, mostly student rollouts; with one GB10 and LoRA, 10–20 min per
step is assumed, so 295 steps ≈ 2–4 days for G and 3–6 days for P (critic
updates). With G0–G3 (about 4–6 days), evals and the write-up: about 3–4
weeks from approval.

9 Durability and artifacts
--------------------------

Every run writes, under its run id: `CODE_SHA`, the SkyRL config, the
training log and `steps.csv`, the per-epoch HF exports (merged weights;
the step-295 export kept, older ones moved to the bucket as in E7), the
critic's final LoRA for P, and per eval pass the session map. All copied to
`gs://whatsapp-sales-agent-hecate-artifacts/runs/<run_id>/` and
`exports/<run_id>/` (G3).

10 Constitution check (`.specify/memory/constitution.md`)
---------------------------------------------------------

  I   Execution-grounded validity: every reward and every result is a
      resolved/unresolved outcome from the SWE-smith eval server running
      the hidden tests.
  II  Reproducibility by manifest: run id, `CODE_SHA`, config, checkpoint
      and session maps for every run, copied off the Spark (G3).
  III Offline-testable CI: G2's tests run without a GPU, network or
      provider.
  IV  Spec-driven: this document precedes any code or run.
  V   Budget discipline: per-arm and total caps (§8), smoke-measured costs
      before full runs, the key's limit raised only by Scott.
  VI  Secrets hygiene: the OpenRouter key stays in `.env` files on the
      worker and the Spark; nothing in logs, maps or this repo.
  VII Shared-scaffold fairness: both arms use the same student, harness,
      issues, reward, rollouts per step, LoRA shape and eval; only the
      advantage (and P's critic) differs.

11 Risks and scope
------------------

  - One seed per arm, 49 test issues, passes varying by up to 19 points:
    expect "no detectable difference" (rule 1); the training curves
    (Q10.4) are the lower-noise result.
  - LoRA, not full fine-tuning: rule 3 checks whether LoRA GRPO lands
    with E7; if not, the comparison is a LoRA result only.
  - Student availability: OpenRouter has returned 404 for
    `gemini-2.5-flash-lite` on some requests since late October ("no longer
    available to new users"). E7's harness retries; if the model becomes
    unavailable, E10 pauses. Changing the student mid-experiment breaks the
    comparison with E7 and needs an amendment.
  - Spark stack: SkyRL, its LoRA patch and the PPO critic are unverified
    on aarch64 (G0). There is no PPO fallback outside SkyRL.
  - Memory: PPO adds a 7B critic beside the policy and vLLM; G0 measures
    it, with a 1.5B critic as the recorded fallback.
  - Out of scope: the M1/M2 router (rev 1), other students or repos, other
    harnesses, advise-or-escalate (Q7.2), full fine-tuning.

12 Not authorized by this document
----------------------------------

Any code, any Spark or worker run (including G0), any OpenRouter spend, and
the key-limit change. Authorization comes after review, as an amendment
below.
