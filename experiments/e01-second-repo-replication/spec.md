Experiment 1 — Second-repo replication: leave-sympy-out generalist holdout
Hecate Lab
SWE-bench Verified (500) · sympy/sympy holdout (n=75) · rev 1 — PLANNED, not yet run
September 13, 2026

Status: specification only. No code written, no runs executed. Spec precedes
implementation, per standing project practice.

Position in slate: Experiment 1 of 5.
  E1  Second-repo replication (leave-sympy-out)          — this document
  E2  Specialist holdout (train on django, test on django)
  E3  Cross-pair transfer (train on one model pair, test on another)
  E4  Lookahead-conditioned router (imagined trajectory)
  E5  Non-oracle repo-structure gate

Abstract
--------
Every routing result Hecate has produced — v1 (frozen text), v2 (frozen + oracle
AST fusion), v3 (LoRA K=0 / K=3) — was scored on a single held-out repository,
`django/django`, which is 231 of the 500 tasks (46.2%) in the matched-scaffold
set. The two findings that follow from those runs are therefore claims about one
repository rather than about repository shift as a phenomenon: RQ1, that
trajectory conditioning (K=3) does not beat a trajectory-blind control (K=0)
under repository shift; and RQ2, that a fine-tuned 7B LoRA beats a frozen-encoder
floor under that same shift. This experiment repeats the generalist protocol on
`sympy/sympy` (n=75), the second-largest repository in the set, holding out all 75
sympy tasks and training on the remaining 425. It adds no new data, no new labels
and no new model inference, and the split it needs is already implemented. Its
purpose is replication, not discovery.

1 Background
------------

1.1 What has been run

All three completed rounds share one split family (leave-django-out or
grouped-by-repo) and one model pair. Reported on the django holdout, n=231:

  Arm                        Route-AUC      AUROC        Accuracy     Brier
  v1 frozen text             0.477 ±0.030   0.516 ±0.015 0.519 ±0.060 0.250 ±0.008
  v2 CLS + oracle AST        0.482 ±0.020   0.518 ±0.021 0.527 ±0.068 0.250 ±0.010
  v3 K=0 LoRA (1 seed)       0.686          0.563        0.450        0.288
  v3 K=3 LoRA (1 seed)       0.587          0.573        0.455        0.409

Endpoints on the same holdout: always-Opus 70.6% (163/231), always-Qwen 58.0%
(134/231), oracle 74.5% (172/231).

v1 and v2 sit at chance. v2's oracle-AST fusion arm did not beat text alone even
with gold-patch file locations leaked to it, and its metrics-only arm
(0.488 / 0.479) underperformed text, which closed the static-structure direction
in its leaky form. v3 rejected H1 (K=3 did not beat K=0; the gap is −0.099) and
accepted RQ2 (both LoRA arms clear the ~0.48 frozen floor). v3 rev 5's own
summary of RQ2: "the lift is the fine-tune, not the traces."

One further number should never be headlined: grouped 5-fold Route-AUC on v1 was
0.589 ±0.194. The standard deviation is the point. Grouped folds inherit django's
mass and are unstable; this is recorded as the "0.589 trap."

1.2 Why one holdout repository is not enough

The repository distribution of the 500-task matched set, measured today directly
from `data/external/qwen3coder_vs_claude4opus_with_text.csv`:

  django/django            231      astropy/astropy           22
  sympy/sympy               75      pydata/xarray             22
  sphinx-doc/sphinx         44      pytest-dev/pytest         19
  matplotlib/matplotlib     34      pylint-dev/pylint         10
  scikit-learn/scikit-learn 32      psf/requests               8
                                    mwaskom/seaborn            2
                                    pallets/flask              1

django is 46.2% of the set. A finding scored only on django is therefore scored on
a holdout that is simultaneously the largest, the most idiosyncratic, and the one
whose removal most distorts the training distribution. Also confirmed today: all
231 django tasks are the single repository `django/django` (not a family of
django-related packages), carrying 230 distinct `base_commit` values, with issue
`created_at` timestamps spanning 2016-11-08 to 2023-07-17.

The generalization gap this leaves is precisely the one SWE-Router [4] navigates
by using two weak/strong pairs, and the one RouteLLM [5] addresses by transferring
across pairs — and RouteLLM's own limitations section concedes that "real-world
applications may have distributions that differ substantially from these
benchmarks," recommending in-domain data per use case. Hecate currently has one
repository standing in for the entire concept of repository shift. That is the
weakest joint in the current argument and the cheapest one to reinforce.

1.3 Why sympy

It is the second-largest repository in the set at n=75 — large enough that a
holdout produces a usable estimate, and the only non-django repository in the set
for which that is true. At n=75 the holdout is roughly one third of django's,
so wider variance is expected and is priced into the decision rule in §5.

2 Research questions
--------------------

Q1.1 (primary, replication of RQ2) — Under repository shift to a second,
smaller, previously unseen repository, does a fine-tuned 7B LoRA router (K=0,
issue text only) still beat the frozen-encoder floor refit on the identical
split?

Q1.2 (secondary, replication of RQ1) — On that same split, what is the sign of
the K=3 − K=0 gap, and does it match the sign observed on django (−0.099)?

2.1 Pre-registered constraint on Q1.2

v3 rev 5 states: "Do not scale this K=3 recipe to 5-fold × 3-seed or sympy/sympy
as a generalist. RQ1 already failed that gate." That instruction is honored here
in substance, and the distinction must be stated before any number is seen.

Rev 5's instruction exists to prevent re-litigating H1 — hunting for a repository
where K=3 happens to win so the failed gate can be reopened. Q1.2 is not that.
It is a replication check whose *prediction* is the existing finding: the gap
should again be negative. Accordingly, and pre-registered here:

  - Q1.2 cannot reopen, reverse, or soften H1. H1 is closed.
  - If the sympy gap is negative, the finding is "the repo-shift result replicates
    on a second repository."
  - If the sympy gap is positive, the finding is "the repo-shift result is
    repo-dependent," which is a limitation on RQ1's scope — not a pass for H1,
    and not evidence that trajectory conditioning works under shift.
  - Either outcome is reported. Neither triggers a further generalist K=3 run on a
    third repository.

3 Setup
-------

3.1 Data

Source: the existing matched-scaffold external label set — Qwen3-Coder-480B-A35B-
Instruct (small, m1) vs Claude-4-Opus-20250514 (large, m2), both under
mini-SWE-agent v1.0.0 [3], run 2025-08-02, SWE-bench Verified [1][2] bash-only
track, 500 instances. Published rates: small 55.4% (277/500), large 67.6%
(338/500). Complementarity: both 258, large-only 80, small-only 19, neither 143;
oracle 71.4%.

Files (unchanged, no regeneration):
  data/external/qwen3coder_vs_claude4opus_with_text.csv
      columns: instance_id, repo, small_model_resolved, large_model_resolved,
               problem_statement, base_commit
  data/external/metadata.json          provenance, caveats, git commits
  trajectory directory as used by v3's K=3 arm (`--traj-dir`)
  frozen_cls_answerdotai_ModernBERT-base.json    cached v1 CLS embeddings

Gold `patch` and `test_patch` are not stored and are not read. `RouterExample`
carries instance_id, repo, text, truncated, m1_resolves, m2_resolves, prompt_hash.

3.2 Split

Leave-repo-out with `hold_repo = "sympy/sympy"`. Fold 0 holds all 75 sympy tasks
and trains on the remaining 425. The reverse fold is skipped (`--hold-only`),
matching how the django runs were scored.

Generalist arm only. No specialist (in-repo) split is run on sympy: an 80/20 split
of 75 tasks leaves ~15 holdout instances, which is below the point where a
Route-AUC estimate carries information. Specialist work stays on django (E2).

3.3 Arms

Three arms, each scored on the identical sympy holdout:

  A  Frozen floor    v1 recipe: cached ModernBERT-base CLS embeddings, logistic /
                     MLP head refit on this split. No GPU time. Establishes the
                     floor Q1.1 is measured against, on this split rather than
                     django's.
  B  K=0 LoRA        v3 recipe, issue text only.
  C  K=3 LoRA        v3 recipe, packed first-3-turn trajectory, identical packing
                     scheme to v3.

3.4 Model and hyperparameters

Arms B and C inherit v3's recipe without modification. Changing the recipe and the
repository simultaneously would make the comparison uninterpretable.

  Backbone              Qwen2.5-Coder-7B-Instruct
  Adapter               LoRA, r=32, alpha=64
  Quantization          QLoRA (4-bit base)
  Value head            last-token logits
  Context length        8192
  Trajectory packing    unchanged from v3 K=3
  Seeds                 0 (smoke). Config default is 0,1,2 — see §5.3.
  Epochs                5 (v3's fixed schedule) — see §6.2 on early stopping.

All remaining hyperparameters (learning rate, batch size, optimizer, scheduler,
warmup) are inherited unchanged from `configs/router_traj.yaml`; arm A from
`configs/router_text.yaml`. These are not restated here on purpose — the resolved
values must be read from the run manifest rather than from this document, so that
the manifest remains the single source of truth.

3.5 Environment

  Training host   GCP `hecate-traj-l4` (L4 GPU), currently stopped. E1 requires
                  restarting it. Arm A needs no GPU and can run locally.
  Python deps     train extras from pyproject.toml — torch, transformers, peft,
                  bitsandbytes, accelerate. Core: swebench==4.1.0, datasets,
                  httpx, pyyaml, unidiff, GitPython.
  Entry points    scripts/run_train_text.py   (arm A)
                  scripts/run_train_traj.py   (arms B, C)
  Provenance      pass `--provenance` to record trace source on the manifest.

3.6 Artifacts that must be persisted

v3 rev 5's postmortem is explicit: the trained K=0 and K=3 adapters were never
checkpointed. `TrajLoraBackend.save()` exists; the smoke runner never called it.
Both adapters died with their training processes, and K=0's `results.json` exists
only on the stopped L4 disk. Retraining is the only path back to those models.

E1 does not repeat this. Required before a run is considered complete:

  1. `.save()` called on every trained adapter.
  2. Per-task holdout scores written out, not just aggregates — without these no
     routing curve can be drawn, which is why v3 rev 5 has no real Figure 2.
  3. `results.json`, manifest, and adapter copied off the training VM immediately
     on completion, not left on an instance that may later be deleted.

A run that produces a Route-AUC but no persisted adapter and no per-task scores is
treated as not having been run.

3.7 Code status

No new code is required for the generalist arms. `run_train_traj.py` and
`run_train_text.py` already expose `--split leave-repo` with `--hold-repo`, and
`splits.py` already implements `assign_leave_repo_out(examples, repo, seed=0)`.
E1 is a parameter change: `--hold-repo sympy/sympy`.

This is the reason E1 is sequenced first. E2 needs a new single-repo split
function and a `--split specialist` CLI path threaded through both runners; E1
needs neither.

4 Metrics
---------

Primary: Route-AUC, on the sympy holdout.
Diagnostic: AUROC, accuracy, Brier. AUROC is reported but not gated on —
SWE-Router [4] report that AUROC correlates only weakly with routing quality, and
Hecate's own v1/v3 rounds reproduce that decoupling (v3 K=3 has higher AUROC than
K=0, 0.573 vs 0.563, while losing decisively on Route-AUC).

Endpoints to report alongside, computed on the sympy holdout: always-large,
always-small, and oracle resolve rates. These bound what any router on this split
can achieve and are needed to interpret Route-AUC at all.

Secondary, new: CPT(50%) and CPT(80%) — the fraction of strong-model calls needed
to recover 50% and 80% of the always-small-to-always-large gap, following
RouteLLM's call-performance-threshold formulation [5]. These cost at most a few
lines over scores already computed, and they make Hecate's numbers directly
comparable to the routing literature, which reports curve metrics rather than
ranking metrics. Reported, not gated.

5 Decision rules (pre-registered)
---------------------------------

5.1 Q1.1 replicates if arm B's Route-AUC is clearly above arm A's on the identical
sympy split — the same qualitative bar used for H1, meaning outside plausible
single-seed noise rather than a nominal tick. Given n=75, "clearly" is a wider
band than it was on django's n=231.

5.2 Q1.2 is reported as the signed gap (arm C − arm B) with no pass/fail
attached, subject to §2.1.

5.3 Seeds. The first pass is a single seed (0), treated as a smoke, consistent with
how v3's own K=0/K=3 numbers are treated. If arm B clears arm A but by a margin
inside plausible noise at n=75, the escalation is seeds 1 and 2 on arms A and B
only — not a broader protocol, and not additional repositories.

6 Risks and caveats (pre-registered)
------------------------------------

6.1 Small holdout. n=75 is roughly one third of django's holdout. Expect wider
Route-AUC variance. A single split at this size is a smoke, not a confirmatory
number, and must be labeled as such in any write-up — the 0.589 trap is the
standing reminder of what happens when a high-variance number gets headlined.

6.2 Larger training set, same schedule. Holding out sympy leaves 425 training
tasks, more than leave-django-out's 269. v3 showed overfitting signatures late in
a fixed 5-epoch schedule on the smaller set; with more data the same schedule may
behave differently in either direction. Watch validation loss and record it. Do
not silently change the schedule — if early stopping is used, it is a documented
deviation from the v3 recipe and must be reported as one.

6.3 Non-replication is a result, not a failure. If sympy diverges from django, the
correct conclusion is that RQ1/RQ2 are narrower than currently stated. That is
information worth more than the cost of the run, and it is better discovered here
than in review.

6.4 Confounded comparison. sympy differs from django in size, domain (symbolic
mathematics vs web framework), and representation in the training set. A
divergence cannot be attributed to repository shift magnitude alone. State this
rather than explain it away.

6.5 This does not address pair generality. E1 varies the repository while holding
the model pair fixed. The single-pair limitation is E3's subject and is untouched
here.

7 Relation to prior work
------------------------

SWE-Router [4] is the direct predecessor: same backbone family
(Qwen2.5-Coder-7B-Instruct with a LoRA classification head), same mechanism
(conditioning on partial agent trajectory), and the same contrast between a
same-distribution setting where K-turn conditioning gains and a repo-disjoint
setting where it does not. Their repo-disjoint check runs on SWE-smith [9], a
different dataset from their headline SWE-bench Verified results. Hecate's
contribution on this axis is a genuine single-repository holdout inside Verified
itself — and E1 is what makes that a claim about holdouts rather than about
django.

RouteLLM [5] demonstrates cross-pair generalization on MT-Bench, MMLU and GSM8K,
and explicitly flags distribution mismatch as a limitation of that evidence. Their
CPT/APGR metrics are adopted here as secondary reporting (§4). Their setting is
single-turn chat, knowledge and math with human-preference supervision; Hecate's
is multi-turn agentic SWE with execution-verified labels.

Triage [8] claims static code-quality signal drives cost-effective tier routing,
which stands in tension with v2's null result. E1 does not adjudicate that; E5
does. Noted here only so the tension is not mistaken for an open question this
experiment addresses.

8 Deliverables
--------------

  results.json                aggregate + per-task holdout scores, all three arms
  manifest                    resolved hyperparameters, seeds, provenance, git SHA
  adapters                    arms B and C, saved and copied off the VM
  README                      run notes, deviations, validation-loss trace

9 Open item
-----------

RQ labeling across the project is now inconsistent: v3 uses RQ1/RQ2/H1/H2, the
v4 spec uses RQ3/RQ4, this document uses Q1.1/Q1.2 (legacy RQ-E1/RQ-E2), and
`claude/router-preprint-outline.md` still carries a separate scheme of one
unlabeled research question plus a contributions list, written 2026-08-27 and
never reconciled with v3 rev 5 or with any of the five planned experiments. A
single labeling pass is owed before drafting, and that outline's "Open decisions"
item 1 (wait for a full 5-fold × 3-seed protocol) directly contradicts v3 rev 5's
instruction not to scale that recipe. Flagged here; not resolved by this document.

References
----------
[1] Jimenez, C. E. et al. (2024). SWE-bench: Can Language Models Resolve
    Real-World GitHub Issues? ICLR. arXiv:2310.06770.
[2] Chowdhury, N. et al. (2024). Introducing SWE-bench Verified. OpenAI.
[3] Yang, J. et al. (2025). mini-SWE-agent. Princeton NLP / SWE-agent.
[4] Son, S., Yoon, S., Tang, J., Wang, S., Wolf, L., Bogunovic, I. (2026).
    SWE-Router: Routing in Multi-turn Agentic Software Engineering Tasks.
    arXiv:2607.00053.
[5] Ong, I., Almahairi, A., Wu, V., Chiang, W.-L., Wu, T., Gonzalez, J. E.,
    Kadous, M. W., Stoica, I. (2025). RouteLLM: Learning to Route LLMs with
    Preference Data. ICLR. arXiv:2406.18665.
[8] Madeyski, L. (2026). Triage: Routing Software Engineering Tasks to
    Cost-Effective LLM Tiers via Code Quality Signals. arXiv:2604.07494.
[9] Yang, J. et al. (2025). SWE-smith: Scaling Data for Software Engineering
    Agents. NeurIPS D&B. arXiv:2504.21798.
