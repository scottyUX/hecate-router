Experiment 9 — Route or Advise
Hecate Lab
Per-task choice between a cheap student, an advised student, and stronger models · rev 1 — PLANNED
October 25, 2026

Status: PLANNED. Nothing in this document is authorized to run. E9 starts
only after E7's final evaluation (checks 2 and 3, three passes of the final
trained advisor on the 49 Tenacity test issues) is written up, and after
this spec is reviewed. No number below comes from an E9 run; the pilot
facts in §1 are from E7 runs already in
`gs://whatsapp-sales-agent-hecate-artifacts/runs/`.

Position in slate: Experiment 9. Does not start, stop, or overwrite E1–E8.

  E7  Route-then-Advise (Advisor Models reproduction; Q7.2 reserved)
  E8  Handoff modes (plan, Claude Doc; not yet in `experiments/`)
  E9  Route or Advise (this document)

Relation to E7 Q7.2: Q7.2 asks whether an advisor that can *escalate
mid-run*, trained with a dollar reward, beats a one-shot router. E9 builds
that one-shot router, over the treatments that already exist, with no new
training. It is Q7.2's baseline and a result in its own right. E9 does not
train an escalate action.

Abstract
--------
Routing papers choose a model per task. Advisor papers always advise. E9
asks whether choosing per task among four treatments — the cheap student
alone, the cheap student with the E7 trained advisor, a mid-price model,
and a premium model — gives a better cost–quality frontier than any single
treatment or fixed mix of them, on the 49 SWE-smith Tenacity test issues.

Q9.1  How often is advice enough? On how many issues does the advised
      student resolve where the student alone does not, and what share of
      the premium model's extra resolves does advice recover?
Q9.2  Does a router trained on pre-run features beat the best fixed mix of
      treatments on Route-AUC (§6)?
Q9.3  How much headroom is there? Oracle router (per-issue best treatment
      in hindsight) against the best fixed mix.
Q9.4  Is the advisor on the frontier at all once a mid-price model is an
      option? (§1 is why this is a question.)

1 Pilot facts that shape the design
-----------------------------------

Per-issue OpenRouter cost on the 49 test issues, from E7 session maps
(`agent_cost`, LiteLLM prices in `configs/litellm_openrouter_registry.json`
in the fork):

  Arm                               Passes  Resolved    $/issue   Steps
  Gemini 2.5 Flash-Lite alone       run-6/7  13, 13/49  0.055–0.066  24.4–27.2
  Flash-Lite + untrained advisor    run-3–5  6–7/49     0.058–0.081  21.5–24.9
  Gemini 2.5 Flash alone            run-2    31/49      0.077     19.4

Flash costs about 1.4× Flash-Lite per issue (3× the input price, 6× the
output price, but fewer, shorter steps) and resolves about twice as many
issues. With Flash as the only stronger option, "always Flash" would
dominate and routing would have little to do. So:

  - Flash is an *action* (the mid-price model), not the strong model.
  - The strong model is a premium model with a per-token price at least
    10× Flash-Lite's (§3, arm D).
  - The advisor arm must be compared against Flash on cost, not only
    against Flash-Lite. Q9.4 is a real question.

2 Data and split
----------------

Primary: the 49 Tenacity test issues (`validation_jd__tenacity.json`). The
E7 advisor never trained on them, so every arm is out of sample.

Router evaluation: stratified 7-fold cross-validation over the 49 issues,
repeated 5 times with different fold seeds (35 fits). Strata: whether the
student alone resolved the issue in at least 2 of 3 passes. Folds and seeds
are fixed in `data/e09_folds.json` before any router is fit.

Secondary, labelled in-sample: the 56 training issues. The advisor trained
on them, so the advisor arm there is optimistic. They may be used to fit a
router that is then tested on the 49; that result is reported separately
and never as the headline.

Issues that error in any pass of any arm are dropped from every arm, as in
`compare_swe_arms.py`.

3 Treatments (router actions)
-----------------------------

Same harness for every arm: mini-SWE-agent through the E7 agent server,
40-step cap, one issue at a time, `--max_workers 1`, three separate
`--num_runs 1` passes per arm.

  A  Flash-Lite alone        `openrouter/google/gemini-2.5-flash-lite`
                             Reuse E7 weakalone run-5, run-6, run-7.
  B  Flash-Lite + advisor    E7 final trained checkpoint, short-context eval.
                             Reuse E7's three final passes
                             (`exp-07_arm-trained_split-tenacityval_seed-0`,
                             `_run-2`, `_run-3`).
  C  Flash alone             `openrouter/google/gemini-2.5-flash`.
                             Three new passes, `exp-09_arm-flash_split-tenacityval_seed-0`,
                             `_run-2`, `_run-3`. E7's single Flash pass ran
                             on an older commit and is kept as a check only.
  D  Premium alone           One premium model, fixed before any D run and
                             recorded here by amendment. Default: Gemini 2.5
                             Pro (same family and provider as A and C).
                             Requirement: per-token price ≥ 10× Flash-Lite.
                             `exp-09_arm-premium_split-tenacityval_seed-0`,
                             `_run-2`, `_run-3`.

A's run-5 is on fork `3ada694`, the rest on later commits; this is
recorded, not rerun (as in E7 check 1).

4 Cost model
------------

Per issue and pass:

  cost = student/model API cost (LiteLLM `agent_cost`)
       + advisor cost (arm B only)

Advisor cost, primary: advisor input and output tokens from the eval log,
priced at a hosted Qwen2.5-7B-Instruct per-token rate snapshotted once into
`experiments/e09-route-or-advise/prices.yaml` before any run. Secondary,
reported alongside: measured advisor GPU-seconds × the on-demand A100 hourly
rate. The primary rate stands for a shared serving deployment; the secondary
is what a single-tenant GPU would cost. Router features are computed before
the run starts and cost nothing extra.

Cost per arm and issue is the mean over its three passes; resolve per arm
and issue is the mean of three 0/1 outcomes.

5 Router
--------

Input: features available before any agent step. Output: one action per
issue.

Features:
  - Frozen text embedding of the problem statement (the same frozen encoder
    as Hecate's v1 text arm, `configs/router_text.yaml`).
  - Problem-statement length in tokens; counts of code blocks, tracebacks,
    and file paths mentioned.
  - SWE-smith bug-type tag from the instance id (`func_basic`,
    `combine_file`, `lm_rewrite`, `pr_*`, …).

Model: one L2-regularized logistic regression per action predicting the
expected resolve rate from these features (C fixed at 1.0, not tuned).
Expected cost per action is that action's mean training-fold cost. For a
price of quality λ (dollars per resolved issue), the router picks the
action maximizing  E[resolve] − cost / λ.  Sweeping λ traces the router's
cost–quality curve.

Baselines:
  - Each single action (four points).
  - Best fixed mix: the upper-left convex hull of the four single-action
    points (randomized mixtures of actions).
  - Oracle: per issue, the action that maximizes resolve − cost/λ using the
    issue's measured outcomes.
  - Two-action router: the same router restricted to {A, D} (classic
    cheap/strong routing), to isolate what the advice and mid-price actions
    add.

No hyperparameter is chosen by looking at test-fold results.

6 Metrics
---------

Route-AUC (primary, following Hecate's convention): area under the
resolve-vs-cost curve between the cheapest and most expensive single
action, normalized by that cost range. Reported for the router, the best
fixed mix, the oracle, and the {A, D} router. Paired bootstrap over issues
(10,000 resamples) for router minus best fixed mix.

Also reported: resolve and cost at three operating points (the router's λ
matching arm B's cost, arm C's cost, and the knee of its curve); per-action
selection shares; per-issue AUROC of each action's resolve predictor
(diagnostic only, as in Hecate).

Q9.1 is descriptive: counts of issues where B resolves (≥ 2/3 passes) and A
does not, and B's share of the issues D gains over A.

7 Decision rules (fixed before any E9 run)
------------------------------------------

  1. Router wins (Q9.2 positive): router Route-AUC minus best-fixed-mix
     Route-AUC > 0 and its 95% bootstrap lower bound > 0.
  2. Router ties: the point estimate is > 0 but the lower bound is ≤ 0.
     Reported as "no detectable gain at n = 49". Not a positive result.
  3. Router loses: point estimate ≤ 0.
  4. Headroom (Q9.3): reported as oracle minus best fixed mix, whatever
     the router does. If the headroom's lower bound is ≤ 0, routing among
     these four actions has nothing to gain on Tenacity, and that is the
     finding.
  5. Advisor on the frontier (Q9.4): B is on the frontier if no fixed mix of
     A, C, D has resolve ≥ B's at cost ≤ B's. If B is off the frontier,
     that is reported plainly, including if C (Flash alone) dominates it.
  6. E7 outcome: E9 runs whether or not E7 checks 2 and 3 pass. The E7
     verdict is stated next to every E9 number that uses arm B.

With 49 issues the bootstrap intervals will be wide. A null result here is
a power statement, not evidence of no effect; a multi-repo follow-up (§9)
is the remedy, not a reinterpretation.

8 Budget and time
-----------------

  Item                                      Est. cost      Notes
  C: Flash alone, 3 × 49                    ~$12           $0.077/issue (§1)
  D: premium alone, 3 × 49                  ~$45–150       Gemini 2.5 Pro est.
                                                           $0.3–1.0/issue (about
                                                           4× Flash per token,
                                                           more with thinking)
  A, B: reuse E7 passes                     $0
  Advisor token accounting (B)              $0             computed offline
  Router fits and bootstrap                 ~$0            CPU, laptop
  Buffer (reruns, errored issues) ~25%      ~$15–40
  Total                                     ~$75–200

Cap: $400 of OpenRouter spend for E9. Arm D stops and reports if its first
pass costs more than $100.

Time: about 1.5 weeks after E7's write-up — spec review 2–3 days; arms C
and D about 2 days (passes run one at a time, about 2–3 h each); router,
bootstrap and write-up 3–4 days.

No GPU is needed: A and B reuse E7 passes, C and D are API models.

9 Risks and scope
-----------------

  - Small n. 49 issues, three passes. Expect wide intervals (rule 2).
  - Advisor from one seed. B uses E7's single trained run.
  - Price drift. Prices are snapshotted once; a later price change does not
    re-run the analysis, only an added sensitivity table.
  - Feature weakness. Hecate's v1 frozen-text router was near chance on
    SWE-bench Verified (Route-AUC 0.477). If the router is weak, the oracle
    headroom (Q9.3) carries the result.
  - One repo. Tenacity only. A follow-up (two more SWE-smith repos, advisor
    retrained or transferred) is a separate experiment with its own spec,
    estimated $2,500–4,600 and 3–4 weeks; it is not authorized here.

Out of scope: training an escalate action (E7 Q7.2), KV or summary handoff
between models (E8), any change to the E7 advisor or its eval.

10 Constitution check (`.specify/memory/constitution.md`)
---------------------------------------------------------

  I   Execution-grounded validity: every label is a resolved/unresolved
      outcome from the SWE-smith eval server running the hidden tests.
  II  Reproducibility by manifest: each pass writes a session map,
      `CODE_SHA`, model id and flags under its run id, copied to
      `gs://whatsapp-sales-agent-hecate-artifacts/runs/<run_id>/`.
  III Offline-testable CI: the router, fold assignment, cost model and
      Route-AUC code get unit tests on fixture session maps; no test calls
      a provider.
  IV  Spec-driven: this document precedes any code or run.
  V   Budget discipline: $400 cap, arm-D stop rule (§8), prices
      snapshotted before runs.
  VI  Secrets hygiene: keys stay in `.env` on the worker; nothing in logs,
      maps, or this repo.
  VII Shared-scaffold fairness: every arm uses the same mini-SWE-agent
      harness, step cap and agent server; only the model (and, for B, the
      advice) differs.

11 Not authorized by this document
----------------------------------

Any E9 pass, the arm-D model choice (by amendment), the prices snapshot,
and any spend. Authorization comes after review, as an amendment below.
