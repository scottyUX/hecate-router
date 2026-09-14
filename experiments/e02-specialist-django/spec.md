Experiment 2 — Specialist holdout: train on django, test on django
Hecate Lab
SWE-bench Verified (500) · django/django in-distribution (n=231) · rev 2 — PLANNED, not yet run
September 13, 2026 (amended September 14, 2026)

Status: specification only. No code written, no runs executed.

Supersedes: `claude/2026-09-13-specialist-django-router-spec.md` (rev 1, earlier
today). That document's RQ3 and RQ4 are carried forward here as Q2.1 and Q2.2
without change of meaning, extended with hyperparameters, environment, label
composition measured from the CSV, and corroborating literature read since.

Amendment (rev 2, September 14, 2026): added Q2.3 and arm D, a K=1 LoRA
diagnostic, motivated purely by training cost. Confirmed against the actual
implementation (`hecate/router/traj.py`, `traj_runner.py`,
`scripts/run_train_traj.py`): the "k3" arm does not train on three turns of
trajectory — `train_rows_for_arm()` packs *every* prefix K=0..min(k_max=4,
n_turns) as a separate training row per instance, so arm C trains on up to 5
rows per instance instead of 1, and the higher-K rows are also the longest
(more turns packed in, up to the 8192-token cap). That is what makes arm C slow
to train, independent of anything about django. Q2.3 / arm D is exploratory
only. It does not substitute for arm C and does not answer Q2.2, which remains
pre-registered against the identical K=3 recipe used in v3 so that its result
stays comparable to the −0.099 gap already measured under repository shift. See
§2.2, §3.6, §3.6.1, §3.8, §5.4, §5.5, §6.7.

Question labeling: this slate labels experiment questions Q<experiment>.<n>, so
E2's questions are Q2.1, Q2.2, and (added in this amendment) Q2.3. Legacy labels
remain valid in their own documents — v3 rev 5's RQ1/H1/H2/RQ2, the superseded
v4 spec's RQ3/RQ4. E1's document now labels its questions Q1.1 and
Q1.2 (legacy RQ-E1/RQ-E2). See §9.

Position in slate: Experiment 2 of 5.
  E1  Second-repo replication (leave-sympy-out)
  E2  Specialist holdout (train on django, test on django)    — this document
  E3  Cross-pair transfer
  E4  Lookahead-conditioned router
  E5  Non-oracle repo-structure gate

Abstract
--------
v1, v2 and v3 all answered a generalist question: train on repositories the router
will never route, then route a repository it has never seen. That regime produced
two findings — trajectory conditioning does not beat a trajectory-blind control
under repository shift (H1 rejected, gap −0.099), and a fine-tuned 7B LoRA does
beat a frozen-encoder floor under that same shift (RQ2 accepted). Neither speaks to
the case a deployed router actually faces most often: routing a repository it was
trained on. This experiment supplies that missing condition, splitting django's own
231 tasks into train and holdout and training only on django. It is the
mix-1 analogue in SWE-Router's terms [4] — the regime where their K-turn
conditioning gained substantially, in contrast to their repo-disjoint setting where
it did not, and which Hecate's v3 result matches. Advisor Models [6], published
since the v4 spec was written, independently supports the premise: a Qwen2.5 7B
reading accumulated mini-SWE-agent actions and observations produces usable signal
in a single-repository, in-distribution setting. This amendment adds a fourth,
lightweight arm (K=1) purely as a fast, low-cost diagnostic read ahead of arm C's
more expensive K=3 training run; it is reported alongside the primary result, not
in place of it.

1 Background
------------

1.1 The missing cell

Hecate has measured K=0 versus K=3 exactly once, under repository shift. The
literature has measured the same contrast in both regimes and finds the sign
depends on which regime you are in:

  Setting                              K=0 → K=3/K=4        Direction
  SWE-Router, mix-1 (same-dist) [4]    rises substantially  trajectory helps
  SWE-Router, repo-disjoint [4]        falls / flat         trajectory does not
  Hecate v3, leave-django-out          0.686 → 0.587        trajectory does not

Two of three cells are filled by SWE-Router and the third by Hecate, all pointing
the same way. The cell Hecate has never filled is its own same-distribution
condition. Until it is filled, "trajectory conditioning fails under repository
shift" is supported by the contrast in someone else's dataset and by a single
Hecate datapoint that has no in-distribution counterpart to be contrasted against.

1.2 What the completed rounds established

On the django holdout, n=231 (generalist, leave-django-out):

  Arm                        Route-AUC      AUROC        Accuracy     Brier
  v1 frozen text             0.477 ±0.030   0.516 ±0.015 0.519 ±0.060 0.250 ±0.008
  v2 CLS + oracle AST        0.482 ±0.020   0.518 ±0.021 0.527 ±0.068 0.250 ±0.010
  v3 K=0 LoRA (1 seed)       0.686          0.563        0.450        0.288
  v3 K=3 LoRA (1 seed)       0.587          0.573        0.455        0.409

The frozen arms sit at chance; the fine-tuned arms clear them. v3 rev 5's summary
of RQ2 — "the lift is the fine-tune, not the traces" — is the claim Q2.1 tests in
the opposite split.

1.3 Independent support from Advisor Models

Advisor Models [6] is not a routing paper, but its SWE Agent Efficiency domain
overlaps Hecate's setup closely enough to be evidence about the premise here. They
use mini-SWE-agent [3] as the harness and a Qwen2.5 7B Instruct model that reads
the student agent's accumulated actions and observations every 5 steps and emits
natural-language advice. Their setting is a single repository (Tenacity, sourced
from SWE-smith [9]), 149 issues split 100 train / 49 test, with the training split
filtered to 56 by removing problems an unadvised agent failed on all 5 attempts.
Reward is 0 if unresolved and 0.5 + 0.5·(40 − steps)/40 if resolved, trajectories
capped at 40 interactions; 30 training epochs, GRPO on 8×H100.

Result: the student alone resolved 61.2% in 19.1 average steps; with the trained
advisor, 61.2% in 14.4 steps. An *untrained* advisor degraded resolve rate to
52.6%, so the gain comes from training rather than from the presence of advice.

What this is evidence for: a 7B model can extract actionable signal from partial
mini-SWE-agent trajectories when train and test share a repository. The output
differs (advice, not a routing score) and the training differs (RL, not supervised
classification), but the underlying question — is there usable signal in a partial
trajectory for a 7B, in-distribution — is answered yes.

What it is not evidence for: that this transfers to django. Their repository is
Tenacity, chosen explicitly for "its reasonable size and test cases to control
training costs." That is a small retry library, not a 13,000-LLOC ORM. Treat it as
corroboration of the mechanism, not as a prediction of the magnitude.

Their Appendix B.2 is also relevant to how K is chosen at all: they name the same
tension Hecate faces — longer advisor intervals make training cheaper but weaken
the signal — and flag "summarization or truncation of student actions and
observations" as an unresolved design consideration. That open problem is E4's
subject, not E2's, but it confirms the representation of partial trajectory is a
live question rather than a settled detail.

2 Research questions
--------------------

Q2.1 (primary gate; ≡ RQ3 in the superseded spec) — Does a 7B LoRA router (K=0,
issue text only) trained *and* evaluated in-distribution on django beat the frozen
v1 head refit on the identical split? This is RQ2's question asked in the
specialist regime rather than the generalist one.

Q2.2 (secondary, diagnostic; ≡ RQ4) — On that same specialist split, what is the
sign of the K=3 − K=0 gap, and does it differ from the −0.099 measured under
repository shift?

Q2.3 (diagnostic, added in this amendment) — Does a much cheaper K=1 LoRA router
(issue text plus the first packed turn only) show the same directional pattern
relative to K=0 that K=3 shows, and can it stand in as a fast, low-cost read
before arm C's full training run is scheduled? Q2.3 is not a replication of Q2.2
at a different K — it is a cost-motivated proxy check, scoped accordingly in
§2.2.

2.1 Pre-registered constraint on Q2.2

Q2.2 is not a retry of H1. H1 was scored under repository shift and is closed. A
positive gap here does not revive it, reverse it, or soften it. Fine-tuning helping
in-distribution while trajectory conditioning fails under shift are compatible
outcomes — that is precisely SWE-Router's own mix-1-versus-repo-disjoint pattern,
not a contradiction of it. Q2.2 is reported as a signed gap with no pass/fail
attached.

2.2 Pre-registered scope of Q2.3

Q2.3 is exploratory and non-gating, and it must not be reported as if it were
Q2.2 measured at a different K. Three constraints, pre-registered before any
number is seen:

  - Arm D (K=1) is not a substitute for arm C (K=3) anywhere in this document.
    Q2.2's decision rule (§5.2) is evaluated on arm C only.
  - Arm D's training regime differs from arm C's in more than just K: arm C
    packs K=0..4 (up to 5 rows/instance, per §3.6.1); arm D packs only K=0..1
    (up to 2 rows/instance). A divergence between D's gap and C's gap is
    therefore not, by itself, evidence about mechanism — it may simply reflect
    how much packed-K augmentation each arm receives during training, not
    something about django or the specialist regime. This is the same caveat
    E4 raises about H1 (E4 §1.1): an arm's result is a statement about its own
    representation, not automatically about trajectory conditioning in general.
  - Arm D's absolute Route-AUC is not comparable to v3's K=3 number (0.587) or
    to arm C's result in this split; only its own sign and its own comparison
    to arm B are reported.

3 Setup
-------

3.1 Data

The existing matched-scaffold external label set: Qwen3-Coder-480B-A35B-Instruct
(small, m1) vs Claude-4-Opus-20250514 (large, m2), both under mini-SWE-agent
v1.0.0 [3], run 2025-08-02, SWE-bench Verified [1][2] bash-only track. Filtered to
`repo == "django/django"`, n=231. No new data, labels, or inference.

Files unchanged from E1 (§3.1 there): the joined text CSV, metadata.json, the K=3
trajectory directory, and the cached ModernBERT CLS embeddings
(`frozen_cls_answerdotai_ModernBERT-base.json`). Gold `patch` / `test_patch` are
neither stored nor read.

3.2 Label composition on django, measured from the CSV today

  both resolve        125   54.1%
  large-only           38   16.5%
  small-only            9    3.9%
  neither              59   25.5%

  small resolves      134   58.0%     (m1_resolves positive rate 0.580)
  large resolves      163   70.6%
  oracle              172   74.5%

Two features of this table govern the experiment's interpretation.

First, small-only is 9 tasks. Headroom over always-large on django is therefore
3.9 percentage points. Routing value on this split is overwhelmingly *cost* —
sending the 125 both-win tasks to the cheap model — not accuracy lift. Any
Route-AUC reported here must be read against that ceiling; a router cannot buy
much accuracy on django because there is little to buy.

Second, 59 tasks (25.5%) are resolved by neither model. For an accuracy-oriented
router these carry no routing-relevant signal: the outcome is identical whichever
model is chosen. Advisor Models [6] handled the analogous situation by filtering
such problems out of training entirely. That option is considered in §3.4 and
deliberately not taken in the primary run.

3.3 Split

Filter to `repo == "django/django"`, then a single label-stratified 80/20 split on
`m1_resolves`: 185 train / 46 holdout, one seed.

Chosen deliberately small-first. A 46-task holdout is the same order as one
grouped-5-fold fold, and grouped folds produced Route-AUC standard deviations of
±0.18–0.19 in v1/v2 — the "0.589 trap." This first pass is a smoke, on the same
terms v3 rev 5 applies to its own single-seed numbers, and is not a number to
headline without a variance check.

3.4 The 59 no-signal tasks: decision

The primary run **keeps all 231 tasks**. Two reasons. Comparability: v1, v2 and v3
all included them, and the frozen floor Q2.1 is measured against must be computed
over the same population as the arm being tested. Statistical power: excluding them
drops the pool to 172 and the holdout from 46 to 34, which at this scale costs more
than the noise removal buys.

A secondary analysis restricted to the 172 routing-informative tasks (both,
large-only, small-only) is reported alongside, as a diagnostic only. Changing both
the population and the regime in one step would make the result uninterpretable —
the same reasoning that fixes the hyperparameters in §3.5.

3.5 Model and hyperparameters

Arms B, C and D inherit v3's recipe without modification.

  Backbone              Qwen2.5-Coder-7B-Instruct
  Adapter               LoRA, r=32, alpha=64
  Quantization          QLoRA (4-bit base)
  Value head            last-token logits
  Context length        8192
  Trajectory packing    unchanged from v3 K=3 for arm C; see §3.6.1 for arm D
  Seeds                 0 (smoke). Config default 0,1,2 — see §5.3.
  Epochs                5 (v3's fixed schedule) — see §6.2.

Remaining hyperparameters (learning rate, batch size, optimizer, scheduler,
warmup) are inherited unchanged from `configs/router_traj.yaml`; the frozen arm
from `configs/router_text.yaml`. Resolved values are read from the run manifest,
which remains the single source of truth rather than this document.

3.6 Arms

  A  Frozen floor    v1 recipe refit on cached ModernBERT-base CLS embeddings,
                     restricted to the identical 185/46 split. No GPU time.
  B  K=0 LoRA        issue text only. The Q2.1 test arm.
  C  K=3 LoRA        packed first-3-turn trajectory (trained on packed K=0..4
                     rows, per v3's recipe; see §3.6.1). The Q2.2 arm.
  D  K=1 LoRA         (diagnostic, added in this amendment) trained on packed
                     K=0..1 rows only, evaluated at K=1. The Q2.3 arm. Cheaper
                     to train than C by construction (§3.6.1) and intended as a
                     fast read, not a gate.

3.6.1 Why arm D, and why it is not arm C at a different K

Confirmed directly against the implementation before writing this amendment.
`train_rows_for_arm()` (`hecate/router/traj.py`) does not train the "k3" arm on
three turns of trajectory text per instance — for `arm="k3"` it emits one
training row for *every* prefix K=0..min(k_max, n_turns), where `k_max` defaults
to 4 (`K_MAX = 4`). That means arm C trains on up to 5 rows per instance instead
of 1, and the higher-K rows are also the longest, since each additional turn
appends more assistant/observation text up to the 8192-token cap. This — not
merely "reading a longer trajectory" — is what makes arm C the slow arm to
train, independent of anything about django or the specialist regime.

`ARMS = ("k0", "k3")` is currently hardcoded in `traj_runner.py`, and `--arm` in
`scripts/run_train_traj.py` accepts only those two values; there is no "k1" arm
today. Arm D requires the code change in §3.8 item 3: generalizing arm parsing
so that a "k1" arm packs only K=0..1 (up to 2 rows/instance, much shorter
sequences) and evaluates at k=1 rather than at `config.k_eval` (fixed at 3).

Note also that once arm C has actually been trained and checkpointed once, a
K=1 (or K=2) read is available for free by re-scoring that same checkpoint's
holdout at a different k via `eval_examples(hold, k=1)` — no retraining
required, since the packed-row training already exposed the adapter to K=0..4
prefixes. That free post-hoc read is a useful cross-check once C exists, but it
does not help before C has been trained, which is the gap arm D is meant to
fill: a genuinely cheaper *training* run, usable as an early signal while
deciding whether/when to spend the GPU time on arm C.

3.7 Environment

  Training host   GCP `hecate-traj-l4` (L4 GPU), currently stopped. E2 is the
                  reason to restart it — v3 rev 5's instruction was to "leave it
                  stopped unless the specialist split needs GPU time." Arm A needs
                  no GPU.
  Python deps     train extras from pyproject.toml — torch, transformers, peft,
                  bitsandbytes, accelerate. Core: swebench==4.1.0, datasets,
                  httpx, pyyaml, unidiff, GitPython.
  Entry points    scripts/run_train_text.py (arm A), scripts/run_train_traj.py
                  (arms B, C, D), both with the new `--split specialist` path.

Sequencing suggestion (non-binding): because arm D trains on far fewer and
shorter rows than arm C, it can be scheduled first on the same L4 instance as a
readiness/sanity check — confirming the pipeline, split, and label join are all
correct — before committing to arm C's longer run. This is a practical ordering
choice, not a substitute for running arm C.

3.8 Code gap

Unlike E1, this experiment requires new code. Today `splits.py` implements
`assign_folds`, `assign_grouped_repo_folds`, `assign_label_stratified_folds`,
`repo_histogram`, and `assign_leave_repo_out(examples, repo, seed=0)`. There is no
single-repo train/holdout split, and both runners' `--split` arguments accept only
`grouped` and `leave-repo`.

Needed:
  1. A split function: filter to one repo, label-stratify on `m1_resolves`, emit a
     single train/holdout partition at a configurable fraction and seed.
  2. `--split specialist` plus `--repo` threaded through `run_train_traj.py` and
     `run_train_text.py`.
  3. (Added in this amendment) Arm D support: extend `ARMS` in `traj_runner.py`
     to include `"k1"`; generalize `train_rows_for_arm()` in `traj.py` so a
     `"k1"` arm packs K=0..1 rather than K=0..k_max; extend `_eval_k()` to
     return 1 for arm `"k1"`; add `"k1"` to the `--arm` choices in
     `run_train_traj.py`. Scoped narrowly so arms `"k0"` and `"k3"` are
     unaffected — v1/v2/v3 and E1/E3/E4's existing runs must remain
     reproducible from the same flag set.

Written as a spec first, per standing practice; implementation follows approval.

3.9 Artifacts that must be persisted

v3 rev 5's postmortem stands as the governing precedent: the trained K=0 and K=3
adapters were never checkpointed because `TrajLoraBackend.save()` was never called
by the smoke runner, both died with their processes, and K=0's `results.json`
exists only on the stopped L4 disk.

Required before a run counts as complete:
  1. `.save()` called on every trained adapter, arm D included.
  2. Per-task holdout scores written out, not only aggregates — without them no
     routing curve can be drawn, which is why v3 rev 5 has no real Figure 2.
  3. `results.json`, manifest and adapter copied off the VM immediately.

A run producing a Route-AUC but no persisted adapter and no per-task scores is
treated as not having been run.

4 Metrics
---------

Primary: Route-AUC on the 46-task holdout.
Diagnostic: AUROC, accuracy, Brier. AUROC is reported, never gated on — SWE-Router
[4] report it correlates only weakly with routing quality, and v3 reproduces the
decoupling directly (K=3 has the higher AUROC, 0.573 vs 0.563, while losing
decisively on Route-AUC).

Endpoints on the holdout: always-large, always-small, oracle. Given §3.2's
composition these are essential, not decorative — they bound what any router can
achieve on a split where headroom over always-large is 3.9pp.

Secondary: CPT(50%) and CPT(80%), following RouteLLM's call-performance-threshold
formulation [5], for comparability with the routing literature. Reported, not
gated.

Diagnostic split-by-era: holdout Route-AUC broken down by issue `created_at`
period. See §6.4.

Arm D (diagnostic, added in this amendment): Route-AUC and the signed gap
(D − B) only. No CPT, no era breakdown — those are reserved for the arms this
experiment gates on (A/B/C).

5 Decision rules (pre-registered)
---------------------------------

5.1 Q2.1 passes if arm B's Route-AUC is clearly above arm A's on the identical
split — the same qualitative bar as H1, meaning outside plausible single-seed noise
rather than a nominal tick. At n=46 that band is wide.

5.2 Q2.2 is reported as the signed gap (C − B), no pass/fail, subject to §2.1.

5.3 Seeds. First pass is single-seed (0), treated as a smoke. If arm B clears arm A
by a margin inside plausible noise at n=46, the escalation is seeds 1 and 2 on arms
A and B only — not a broader protocol and not additional repositories.

5.4 (Added in this amendment) Q2.3 is reported as the signed gap (D − B), with no
pass/fail threshold and no seed escalation — a single seed (0) only, regardless of
what §5.3 triggers for arms A/B. It is not used to gate, inform, or override Q2.1
or Q2.2, and per §2.2 it never substitutes for arm C.

5.5 (Added in this amendment) If arm D fails to train or produces a degenerate
result (e.g. collapses to the always-majority prediction), that is reported as a
pipeline diagnostic and, if warranted, a reason to check the split/label join
before running arm C — not as a scientific finding about K=1 trajectory
conditioning.

6 Risks and caveats (pre-registered)
------------------------------------

6.1 Small holdout. n=46, comparable to a single grouped fold, which produced
±0.18–0.19 in v1/v2. A single split at this size is a smoke, not a confirmatory
number, and must be labeled as such wherever reported.

6.2 Smaller training set, same schedule. 185 in-repo training tasks is fewer than
v3's 269 cross-repo tasks, and v3 already showed overfitting signatures late in a
fixed 5-epoch schedule. Watch and record validation loss. If early stopping is
used it is a documented deviation from the v3 recipe and reported as one.

The first patched LoRA loop (shuffle + monitor slice + grad clip + zero-init
score head) does **not** invoke early stopping. The trigger is pre-registered
here before any patched run, and stays off (`early_stopping: false` in
`configs/router_traj.yaml`) unless a patched B/D validation curve still dives.
If it is turned on, it applies identically to arms B, C, and D:

  metric       mean validation cross-entropy (`val_ce`) on the monitor slice
  patience     2 epochs
  min_delta    0.01
  slice        20 tasks, label-stratified on `m1_resolves`, seeded, carved from
               the 185-task train pool — never from the 46-task holdout
  keep         best checkpoint by `val_ce` (lower is better)

`n_train` in `results.json` is the count that receives gradients (~165), not
the 185-task split size. The split pin remains 185/46. The 46-task holdout is
never used to choose a checkpoint.

6.3 Low headroom. With small-only at 9 tasks, django admits almost no accuracy
lift over always-large. A router can look poor on accuracy while being valuable on
cost. Report cost-side metrics (§4) rather than treating Route-AUC as the whole
picture. Advisor Models [6] names the general form of this limit: their method
produced no improvement on MATH-500 because the frontier model already knew
everything, and they state plainly that there must be something available to learn.

6.4 "In-distribution" is weaker here than the label suggests. Confirmed today: the
231 django tasks carry 230 distinct `base_commit` values with issue `created_at`
spanning 2016-11-08 to 2023-07-17 — roughly seven years of repository history. A
pilot run today measured how much the codebase moved across that span: six tasks
sampled roughly one per year, each checked out at its exact `base_commit` from a
blobless sparse clone of `django/django`, with `radon` run over `django/db/models`
(a core module present at every one of those commits). LLOC grew from 10,015 to
13,725 (+37%), maintainability index fell from 50.77 to 45.75, average cyclomatic
complexity moved 3.25 → 3.35, and file count grew 31 → 39.

A random 80/20 split therefore trains and tests across structurally different
versions of nominally the same repository. This is a milder shift than leave-repo-
out, but it is not zero, and it means a negative result here cannot be read as
"even in-distribution, nothing works" without qualification. Mitigation: report
holdout scores broken down by era (§4). A deliberate temporal split — train on
pre-2021 issues, test on post-2021 — would isolate this cleanly and is a natural
follow-up, not part of the primary run. The full structural-metrics pilot belongs
to E5 and is only cited here for the caveat it supports.

6.5 A positive result does not revive H1. Restated from §2.1 because it is the
most likely misreading of a positive Q2.2.

6.6 Single pair. E2 varies the regime while holding the model pair fixed. Pair
generality is E3's subject.

6.7 (Added in this amendment) Arm D's training regime differs from arm C's in
more than K. Arm C packs K=0..4 (up to 5 rows/instance); arm D packs K=0..1 (up
to 2 rows/instance). If D's gap and C's gap point in different directions, the
most likely explanations are differences in packed-row count and sequence
length between the two arms — not a discovery about how much trajectory a
router can use in django specifically. Any write-up that reports both gaps
side by side must repeat this caveat rather than imply the two arms are
comparable measurements of the same underlying quantity at different K.

7 Relation to prior work
------------------------

SWE-Router [4] supplies the framing: their mix-1 setting is what E2 reproduces in
Hecate's own data, and their repo-disjoint setting is what v3 already matched.
Their repo-disjoint check runs on SWE-smith [9] rather than on their headline
SWE-bench Verified results; Hecate's contribution on this axis is that both cells
are measured inside one dataset, on one model pair, with one recipe.

Advisor Models [6] provides the independent premise support described in §1.3, and
its training-set filtering practice motivates §3.4. Its limits section supplies the
headroom framing in §6.3.

RouteLLM [5] contributes the CPT metrics in §4. Its generalization evidence is
about model pairs rather than repositories and belongs to E3.

Triage [8] claims static code-quality signal drives cost-effective tier routing,
in tension with v2's null. E5 adjudicates that; E2 does not.

8 Deliverables
--------------

  results.json     aggregate + per-task holdout scores, all four arms (A-D), plus
                   the 172-task informative-subset diagnostic
  manifest         resolved hyperparameters, seeds, provenance, git SHA
  adapters         arms B, C and D, saved and copied off the VM
  README           run notes, deviations, validation-loss trace, era breakdown,
                   and the D-vs-C training-regime caveat (§6.7)

9 Open item
-----------

The question-labeling collision noted in the header needs a single pass across the
project. Current state: v3 rev 5 uses RQ1/H1/H2/RQ2; the superseded v4 spec uses
RQ3/RQ4; E1 now uses Q1.1/Q1.2; this document uses Q2.1/Q2.2/Q2.3. Additionally
`claude/router-preprint-outline.md` (2026-08-27) still carries a separate scheme —
one unlabeled research question plus a contributions list — never reconciled with
v3 rev 5 or with any of the five planned experiments, and its "Open decisions"
item 1 (wait for a full 5-fold × 3-seed protocol) contradicts v3 rev 5's
instruction not to scale that recipe. Owed before drafting; not resolved here.

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
[6] Asawa, P., Zhu, A., O'Neill, A., Zaharia, M., Dimakis, A. G., Gonzalez, J. E.
    (2026). How to Train Your Advisor: Steering Black-Box LLMs with Advisor
    Models. arXiv:2510.02453.
[8] Madeyski, L. (2026). Triage: Routing Software Engineering Tasks to
    Cost-Effective LLM Tiers via Code Quality Signals. arXiv:2604.07494.
[9] Yang, J. et al. (2025). SWE-smith: Scaling Data for Software Engineering
    Agents. NeurIPS D&B. arXiv:2504.21798.
