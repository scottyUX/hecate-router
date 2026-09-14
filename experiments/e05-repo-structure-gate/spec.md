Experiment 5 — Non-oracle repo-structure gate: does static structure route when it isn't leaked?
Hecate Lab
SWE-bench Verified (500) · leave-django-out (n=231) + specialist django (n=46) · rev 1 — PLANNED
September 13, 2026

Status: specification only. No code written, no runs executed. A six-task pilot
was run today; its results are in §1.3 and they materially shape the design.

Position in slate: Experiment 5 of 5.
  E1  Second-repo replication (leave-sympy-out)
  E2  Specialist holdout (train on django, test on django)
  E3  Cross-pair transfer
  E4  Lookahead-conditioned router
  E5  Non-oracle repo-structure gate                             — this document

Question labeling: Q<experiment>.<n>, per E2's header.

Abstract
--------
v2 fused frozen text embeddings with AST metrics computed over the files the gold
patch touches, and found no lift: Route-AUC 0.482 ±0.020 against v1 text's 0.477
±0.030, with a metrics-only arm (0.488 / 0.479) underperforming text alone. That
result was recorded as closing the static-structure direction. It should not have
been, because it bundles three things at once — oracle localization, repository
shift, and a frozen encoder — and only the first was named. Triage [8] claims the
opposite, that static code-quality signal does drive cost-effective tier routing.
This experiment separates the confounds by computing structural features without
any reference to the gold patch, two ways, and testing them against a control that
today's pilot showed is essential: a trivial feature encoding only when the issue
was filed.

1 Background
------------

1.1 What v2 actually established

  Arm                        Route-AUC      AUROC        Accuracy     Brier
  v1 frozen text             0.477 ±0.030   0.516 ±0.015 0.519 ±0.060 0.250 ±0.008
  v2 CLS + oracle AST        0.482 ±0.020   0.518 ±0.021 0.527 ±0.068 0.250 ±0.010
  v2 metrics-only            0.488 / 0.479  —            —            —

All at chance on the django holdout. The v2 write-up concluded: "This closes the
static-structure direction, not just the leaky version of it."

That conclusion is stronger than the evidence supports. The v2 metrics were
computed over gold-patch files — which requires knowing the answer to know which
files to measure — under leave-django-out shift, on frozen embeddings with a small
head. A null under those conditions is consistent with at least four readings:
structure carries no signal; oracle localization is the wrong localization;
structure does not survive repository shift; or a frozen encoder cannot exploit it.
E5 addresses the first two directly and the third by running both regimes.

1.2 The tension with Triage

Triage [8] routes software engineering tasks across three cost tiers using code
health and maintainability signals, on SWE-bench Lite (300), and reports that
structural signal works. Hecate's v2 reports that it does not. Both cannot be
unconditionally true, and the difference may lie in localization (Triage does not
need gold-patch knowledge), in regime, or in which metrics are used.

Open check, not yet done: Triage's own evaluation split. Whether they evaluate
in-distribution or with a repository holdout determines which of E5's two regimes
is the fair comparison to their claim. This should be read out of the paper before
E5's results are interpreted, and the answer recorded in the write-up.

1.3 Pilot run today, and the problem it surfaced

A six-task pilot was run to check whether commit-level structural features vary at
all across django tasks, before committing to a design.

Method: sampled six django tasks spread across the full time range the dataset
covers — pulled real `created_at` timestamps from SWE-bench Verified (not just the
commit hash), picked one roughly per year from 2016 to 2023 — then did a
blobless/sparse-checkout clone of `django/django`, checked out each task's exact
`base_commit`, and ran `radon` (the standard Python complexity tool, same family
Triage-style approaches use) on `django/db/models`, a core module present at every
one of those commits.

  instance_id     created_at    CC (avg)   MI (avg)   LLOC     files
  django-7530     2016-11-08    3.25       50.77      10,015   31
  django-10914    2019-01-30    3.19       50.67      11,054   37
  django-12308    2020-01-12    3.18       49.25      12,007   39
  django-14034    2021-02-22    3.27       47.63      12,612   39
  django-15572    2022-04-09    3.30       46.95      12,876   39
  django-17087    2023-07-17    3.35       45.75      13,725   39

Two conclusions, one reassuring and one not.

Reassuring: the features are not degenerate. The earlier worry — that a single
repository-level scalar would be constant across all 231 django tasks and therefore
carry zero discriminative power inside a specialist split — does not materialize.
Because every task pins its own `base_commit` (231 django tasks carry 230 distinct
commits, confirmed today), repository state genuinely varies per task. Logical
lines grew 37%, maintainability index fell about five points, file count grew and
then plateaued.

Not reassuring: every one of those metrics moves close to monotonically with time.
On this sample they are nearly collinear with `created_at` itself. A router fed
these features may be learning nothing more than "which era of django is this,"
which a single scalar — the issue date — encodes more cheaply and more honestly.

That finding is why §3.4's date-only arm is not an optional extra. Without it, a
positive result for commit-snapshot structure is uninterpretable.

2 Research questions
--------------------

Q5.1 (primary) — Does structural signal computed *without* reference to the gold
patch improve routing over text alone, where v2's oracle-localized version did not?

Q5.2 (secondary) — Does the answer differ between the generalist regime
(leave-django-out, v2's split) and the specialist regime (E2's in-repo split)?

2.1 Pre-registered validity condition on Q5.1

Today's pilot shows commit-snapshot structural metrics tracking issue date almost
monotonically. Therefore Q5.1 is answered affirmatively only if both hold:

  (a) a structural arm clearly beats the text-only floor on the same split, and
  (b) that arm also clearly beats the date-only arm (§3.4, arm B).

If a structural arm beats text but not date-only, the finding is "issue era
predicts routability on this pair," which is a real and reportable result but is
not a structural-signal result, and must not be written as one.

3 Setup
-------

3.1 Data

The existing matched-scaffold label set: Qwen3-Coder-480B-A35B-Instruct (weak) vs
Claude-4-Opus-20250514 (strong), mini-SWE-agent v1.0.0 [3], SWE-bench Verified
[1][2], 500 tasks. Structural features are computed from public repository history
at each task's `base_commit`; no gold `patch` or `test_patch` is read at any point,
which is the entire point of the experiment.

3.2 Prerequisite: join `created_at`

`created_at` is present in SWE-bench Verified but is *not* in the local joined CSV
— `metadata.json` records `issue_text_join.fields` as `["problem_statement",
"base_commit"]` only. Arm B cannot be built without it. Re-run the existing join
with `created_at` added as a third field, producing a versioned CSV rather than
overwriting; record the new join's git SHA in metadata as the existing join does.

Confirmed today by sampling the source dataset: django's `created_at` values span
2016-11-08 to 2023-07-17.

3.3 Feature extraction

Two non-oracle localization strategies, computed for every task.

**S1, commit-snapshot.** Check out the repository at the task's `base_commit` and
compute `radon` metrics over a fixed target: the repository's main package where
checkout cost permits, otherwise a documented core module per repository (today's
pilot used `django/db/models`). Features: mean and max cyclomatic complexity, mean
maintainability index, LOC/LLOC/SLOC, file count. Requires no localization at all.

**S2, text-localized.** Extract file and module references from `problem_statement`
— traceback lines of the form `File "...`", backtick-quoted dotted module paths,
import statements, and path-like tokens — resolve them against the repository tree
at `base_commit`, and compute the same `radon` metrics over the resolved files
only. Localization comes from what the *issue* points at, never from what the *fix*
touches. This is the arm that actually tests Triage's claim.

S2 coverage must be measured and reported before any S2 result is interpreted: the
fraction of tasks for which at least one file reference resolves. If coverage is
low, most of the arm is imputation and a null says little. Unresolved tasks get a
zero vector plus an explicit missing-ness indicator feature rather than silent
imputation.

3.4 Arms

All arms share the v1 frozen recipe — cached ModernBERT-base CLS embeddings with a
logistic / MLP head — so that the comparison to v2 is exact and so that E5 needs no
GPU (§3.7).

  A  Text only            v1 recipe refit on the split. The floor.
  B  Date only            `created_at` as a scalar feature, no text, no structure.
                          The validity control required by §2.1.
  C  S1 commit-snapshot   structural features only.
  D  S2 text-localized    structural features only.
  E  Text + best          fusion of A with whichever of C/D performs better. The
                          non-oracle analogue of v2's fusion arm.
  F  Text + date          fusion of A with B, to check whether any fusion gain is
                          attributable to era rather than structure.

v2's oracle fusion result (0.482 ±0.020) is the standing comparison and is not
re-run.

3.5 Splits

Primary: leave-django-out — train on 269 non-django tasks, evaluate on 231 django
tasks. This is v2's split, which makes the comparison to 0.482 apples-to-apples,
and it is the larger holdout of the two.

Secondary: E2's specialist django split (185 train / 46 holdout, label-stratified,
seed 0). This answers Q5.2 and is the regime where repository-specific structure
should have its best chance. Contingent on E2's split function existing (E2 §3.8);
E5 adds no split code of its own.

Note the power asymmetry honestly: n=46 is small for detecting a modest structural
effect. A null in the specialist regime is weak evidence, and the write-up must say
so rather than reporting the two regimes as equally informative.

3.6 Hyperparameters

Frozen-head arms follow `configs/router_text.yaml` unchanged, as v1 and v2 did.
Feature standardization is applied to structural and date features before fusion;
record the scaler in the manifest. Seeds follow the v1/v2 protocol so that the
reported ±std values are comparable to v1's ±0.030 and v2's ±0.020.

New parameters to record:
  radon version, target module per repository, aggregation functions (mean/max/sum),
  S2 extraction patterns, S2 coverage rate, missing-ness encoding, date encoding
  (days since the repository's earliest task in the set).

3.7 Environment and cost

E5 needs **no GPU**. Every arm is a frozen-embedding head fit, which is what makes
this the cheapest experiment in the slate despite being fifth. Its cost is
feature extraction: cloning repositories and running `radon` at up to 500 distinct
commits.

Practical notes from today's pilot, which cost real time to learn:

  - A blobless clone (`git clone --filter=blob:none --no-checkout`) plus
    `git sparse-checkout set <target>` is the workable approach. Checking out a
    historical commit on a blobless clone *without* sparse-checkout scoped to the
    target path attempts to fetch every blob for that commit and effectively hangs
    — a first attempt timed out at five minutes on a single commit.
  - With sparse-checkout scoped to `django/db`, six historical checkouts plus
    `radon` runs completed in well under a minute total.
  - `radon raw -s` prints a `** Total **` block where `LOC` precedes `LLOC`; naive
    line-offset parsing picks up the wrong field.
  - `radon` is not preinstalled (`pip install radon`).

Extraction should be a standalone script writing a versioned feature table keyed on
`instance_id`, so that arms C-F consume a cached artifact rather than recomputing,
and so the features themselves are reviewable independently of any routing result.

3.8 Code gap

  1. Feature extraction script: per-repo blobless sparse clone, per-task checkout
     at `base_commit`, radon over target, emit feature table.
  2. S2 reference extractor and resolver against the tree at `base_commit`, with
     coverage accounting.
  3. Re-run of the issue-text join including `created_at` (§3.2).
  4. A `--features` extension on `run_train_text.py`. It currently accepts
     `text`, `metrics`, `fusion` — `metrics` and `fusion` denote v2's *oracle* AST
     features. New values must be distinct names, not redefinitions, so that v2's
     runs remain reproducible from the same flag set.

3.9 Artifacts

  feature table    versioned, keyed on instance_id, with extraction provenance
  results.json     aggregate + per-task scores, arms A-F, both splits
  manifest         radon version, targets, aggregations, coverage, scaler, seeds
  README           S2 coverage rate, Triage split finding (§1.2), deviations

4 Metrics
---------

Primary: Route-AUC, reported with the same seed protocol as v1/v2 so that ±std
values are directly comparable to 0.477 ±0.030 and 0.482 ±0.020.

Diagnostic: AUROC, accuracy, Brier — reported, never gated (SWE-Router [4]; v3
reproduces the decoupling).

Endpoints on each holdout: always-strong, always-weak, oracle. On the django
holdout these are 70.6% / 58.0% / 74.5%, with headroom over always-strong of 3.9pp
(E2 §3.2) — which bounds what any arm here can demonstrate.

Experiment-specific:
  - S2 coverage rate (§3.3).
  - Correlation between each structural feature and `created_at`, reported for the
    full 500 and per repository. Today's pilot suggests this will be high for S1;
    measuring it on the full set turns an observation from six points into a
    stated property of the feature set.
  - Feature importance or coefficient inspection on arms C/D, to see whether any
    signal concentrates in size-like features (which track time) or in
    complexity-like features (which may not).

5 Decision rules (pre-registered)
---------------------------------

5.1 Q5.1 passes only if both conditions in §2.1 hold — a structural arm clearly
above text-only *and* clearly above date-only, on the same split.

5.2 If arm C ≈ arm B, the conclusion is recorded as "commit-snapshot structure is a
proxy for issue era on this dataset," and arm C is not described as structural
signal anywhere in the write-up.

5.3 If arm D clearly beats both A and B while arm C does not, the conclusion is
that localization is what v2 got wrong — structure computed where the issue points
carries signal that structure computed where the patch lands did not. That is the
outcome that would genuinely reopen the direction v2 declared closed, and it is the
outcome most directly relevant to Triage's claim.

5.4 If no arm beats both A and B on either split, v2's conclusion is upheld, now on
much stronger footing: the direction is closed for oracle-localized, text-localized
and commit-snapshot structure alike. That is a more defensible version of the same
claim and is worth the run on its own.

6 Risks and caveats (pre-registered)
------------------------------------

6.1 Time-collinearity. The central risk, evidenced by §1.3. Mitigated by arm B, not
eliminated by it — structure and era may be genuinely entangled in a way no control
fully separates, in which case the honest report is that they cannot be
distinguished on this dataset.

6.2 S2 coverage may be low. Many issue reports describe symptoms without naming
files. If coverage is poor the arm is mostly missing-ness, and a null is
uninformative. Measure first, interpret second.

6.3 One metric family. `radon` gives cyclomatic complexity, maintainability index
and raw counts. Triage [8] may use different signals; a null with radon is not a
null for all static structure, and the write-up must scope the claim to the metrics
actually computed.

6.4 Specialist power. n=46. See §3.5.

6.5 Low headroom. With small-only at 9 tasks on django, there is little accuracy to
win regardless of features. Report cost-side metrics and endpoints rather than
treating Route-AUC as the whole story (E2 §6.3).

6.6 Extraction correctness is a silent failure mode. A bug in commit checkout or
file resolution produces plausible-looking numbers rather than an error. The
feature table is a reviewable artifact for exactly this reason (§3.7); spot-check a
sample against manual inspection before fitting anything.

6.7 Repository coverage. The 500 tasks span 12 repositories; S1 needs a documented
target per repository and S2 needs the tree at each `base_commit`. Repositories
with 1-2 tasks (flask, seaborn) contribute negligibly and may be dropped from
extraction if cost demands, provided the drop is recorded and the same task set is
used across all arms.

7 Relation to prior work
------------------------

Triage [8] is the direct counterparty: it claims static code-quality signal drives
cost-effective tier routing, which stands against v2's null. E5 is the experiment
that adjudicates that tension on Hecate's data, and arm D is the arm that does it,
because Triage's signals do not require gold-patch knowledge either. The open
question about their evaluation split (§1.2) must be resolved before comparing
numbers.

Routesplain [11] routes software-related tasks through an interpretable concept
bottleneck, another instance of structured, inspectable features for routing rather
than raw text embeddings. Relevant as context for why interpretable feature sets
are pursued at all; its task mix (code generation, repair, I/O prediction, CS QA)
is broader and less agentic than Hecate's.

v1 and v2 are the internal comparisons; v2's 0.482 ±0.020 is the number E5 is
re-examining, and E5's primary split is chosen to match v2's for that reason.

SWE-Router [4] contributes the metric discipline in §4 (Route-AUC primary, AUROC
diagnostic).

8 Sequencing note
-----------------

E5 is fifth by expected value, not by cost — it is in fact the cheapest experiment
in the slate, requiring no GPU at all. Its hypothesis was weakened before it
started: v2 already found a null for the leaky version, and today's pilot showed
the cheapest non-leaky version is largely a proxy for issue date. It stays in the
slate for two reasons. Arm D is a genuinely untested idea and the only one that
directly adjudicates the Triage tension. And §5.4's outcome — no arm beats text or
date, across three localization strategies — would convert v2's overreaching
conclusion into one the paper can actually defend.

Because it needs no GPU, E5 can run concurrently with any GPU-bound experiment
rather than competing for the L4.

References
----------
[1] Jimenez, C. E. et al. (2024). SWE-bench: Can Language Models Resolve
    Real-World GitHub Issues? ICLR. arXiv:2310.06770.
[2] Chowdhury, N. et al. (2024). Introducing SWE-bench Verified. OpenAI.
[3] Yang, J. et al. (2025). mini-SWE-agent. Princeton NLP / SWE-agent.
[4] Son, S., Yoon, S., Tang, J., Wang, S., Wolf, L., Bogunovic, I. (2026).
    SWE-Router: Routing in Multi-turn Agentic Software Engineering Tasks.
    arXiv:2607.00053.
[8] Madeyski, L. (2026). Triage: Routing Software Engineering Tasks to
    Cost-Effective LLM Tiers via Code Quality Signals. arXiv:2604.07494.
[11] Routesplain: Towards Faithful and Intervenable Routing for Software-Related
    Tasks (2026). arXiv:2511.09373.
