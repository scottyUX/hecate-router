Experiment 3 — Cross-pair transfer: does a router trained on one model pair route another?
Hecate Lab
SWE-bench Verified (500) · multiple matched-scaffold pairs · rev 1 — PLANNED, CONDITIONAL
September 13, 2026

Status: specification only. No code written, no runs executed.

CONDITIONAL. Unlike E1 and E2, this experiment depends on a precondition that has
not been verified: that additional mini-SWE-agent v1.0.0 submissions on SWE-bench
Verified exist with retrievable per-instance results. §0 specifies that check. If
it fails, E3 is not runnable as written and should be deferred rather than run on
mismatched scaffold versions.

Position in slate: Experiment 3 of 5.
  E1  Second-repo replication (leave-sympy-out)
  E2  Specialist holdout (train on django, test on django)
  E3  Cross-pair transfer                                      — this document
  E4  Lookahead-conditioned router
  E5  Non-oracle repo-structure gate

Question labeling: Q<experiment>.<n>, per E2's header.

Abstract
--------
Every Hecate result to date is scored on one weak/strong model pair:
Qwen3-Coder-480B-A35B-Instruct against Claude-4-Opus-20250514. "One model pair" is
the limitation a reader will press hardest, and it is the axis SWE-Router [4]
covers with two pairs and RouteLLM [5] addresses directly by transferring routers
across pairs without retraining. RouteLLM report that a router trained on
GPT-4/Mixtral preference data transfers to Claude 3 Opus/Sonnet (APGR 0.772, +56.6%
over random) and to Llama 3.1 70B/8B (APGR 0.767, +49.8%). Their evaluation is
single-turn chat, knowledge and math, supervised by human preference. This
experiment asks the same question in the setting they did not test: multi-turn
agentic software engineering, supervised by execution-verified resolution, and on a
pair that is not a within-family capability ladder. It requires no new label
generation — only additional submissions from the same matched-scaffold pool
Hecate's existing labels came from.

0 Precondition (must be satisfied before anything else)
-------------------------------------------------------

0.1 Why this is gated

Hecate's labels are borrowed, not generated. Their validity rests entirely on two
submissions having run the *identical* scaffold — mini-SWE-agent v1.0.0 [3], dated
2025-08-02 — on the identical 500 tasks. swebench.com states plainly that "results
of release 1.x and 2.x are not necessarily comparable to each other." Pairing a
v1.0.0 run against a v2.x run would silently destroy the matched-scaffold property
that makes any of this meaningful, while still producing numbers.

0.2 What was established today

The SWE-bench Verified leaderboard carries an agent filter isolating mini-SWE-agent
runs in a minimal bash-only environment, described as existing specifically so that
different language models can be compared without tooling differences confounding
the result. That is, by construction, a matched-scaffold multi-model pool.

A third-party aggregation of that track lists roughly a dozen models: Claude Opus
4.5 (64.8%), GPT-5.2 (61.6%), Claude 3.7 Sonnet (52.2%), DeepSeek V3 (52.1%), o3
(43.7%), GPT-4.1 (41%), Grok-3 mini (38.6%), o4-mini (34.6%), GPT-4.1 mini (32.8%),
Qwen Plus (28%), GPT-4o (25.4%), Gemini 2.5 Pro (22%). That listing does not
include either of Hecate's two models, so it is incomplete, stale, or drawn from a
different release — it establishes that the pool is multi-model, not which entries
are usable.

Repository structure, per the experiments repo: each submission folder holds
`metadata.yaml` (including an `assets` block pointing at the submitter's own
repository), `README.md`, and `results/` with resolved instance IDs broken down per
repository and per year. Bulk artifacts (`all_preds.jsonl`, `logs/<instance_id>/`,
`trajs/<instance_id>.*`) live in the submitter's repository rather than centrally.
Note also that bash-only runs previously filed under `evaluation/bash-only/` are
described as having moved to `evaluation/verified/` with a leaderboard filter —
Hecate's own metadata records the older path
(`evaluation/bash-only/20250802_mini-v1.0.0_claude-4-opus-20250514/`), so the
enumeration must handle both layouts.

0.3 The check

  1. Enumerate submission folders under `evaluation/verified/` and, for legacy
     entries, `evaluation/bash-only/`.
  2. Read each `metadata.yaml`; record the mini-SWE-agent release version, the
     model, and the date.
  3. Filter to release v1.0.0 — the release Hecate's labels use. Record, but
     exclude, any other release.
  4. For each survivor, confirm a per-instance resolved list is actually
     retrievable (from `results/` or via the `assets` block), not merely an
     aggregate resolve rate.
  5. Recompute each candidate's aggregate rate from the per-instance list and check
     it reproduces the published leaderboard number. A mismatch means the artifact
     is not what it claims and the candidate is dropped.
  6. Audit each candidate's own caveats. Hecate's existing metadata records seven
     Opus trajectories flagged for git-peek, two of which resolved; other
     submissions will carry their own. These must be read, not assumed absent.

0.4 Outcome

  - Two or more usable v1.0.0 companions, forming at least one clean weak/strong
    pair besides Hecate's: proceed to §1.
  - Fewer: E3 is deferred. Do not substitute a v2.x run, and do not generate
    labels in-house — that is a separate first-party generation track, out of
    scope for this slate.

The check is read-only, costs no GPU time, and should be run before E3 is
scheduled.

1 Background
------------

1.1 What is being tested

RouteLLM's transfer claim rests on an implicit assumption: that query difficulty is
largely a model-agnostic property. If a task is hard, most weak models fail it and
most strong models handle it; if easy, the weak model suffices. Under that
assumption a router is really learning a property of the *query*, so swapping in a
different pair at inference costs little. Their results support this for chat,
knowledge and math.

Two features of Hecate's setting put that assumption under more strain than
RouteLLM's own tests did.

First, both of RouteLLM's transfer targets are within-family capability ladders —
Claude 3 Opus above Claude 3 Sonnet, Llama 3.1 70B above 8B. Competence nests
cleanly. Hecate's pair does not: Qwen3-Coder-480B is a coding specialist and
Claude-4-Opus is a generalist, so their competencies overlap irregularly instead of
nesting.

Second, the complementarity structure confirms this is not a ladder. Across the
full 500: both resolve 258, large-only 80, small-only 19, neither 143. On django
alone (measured today, see E2 §3.2): both 125, large-only 38, small-only 9, neither
59. The small-only counts are the diagnostic — under a pure difficulty axis they
should be near zero. They are not, which means the routing problem carries
pair-specific structure that a transferred router has no way to know about.

1.2 Prior transfer evidence

RouteLLM [5], Table 4, MT-Bench, routers applied to unseen pairs with no retraining
and only the target models swapped at inference:

  Claude 3 Opus / Claude 3 Sonnet    CPT(50%) 23.27%  CPT(80%) 51.85%  APGR 0.772
  Llama 3.1 70B / Llama 3.1 8B       CPT(50%) 21.18%  CPT(80%) 29.39%  APGR 0.767

against random-router baselines of CPT(50%) 49.89% / 47.52%. They also state in
their limitations that "real-world applications may have distributions that differ
substantially from these benchmarks," recommending in-domain data per use case.

Advisor Models [6] supplies a second, independent transfer precedent, and this one
is in an agentic setting. Their SWE advisor, trained with a Gemini 2.5 Flash
student under mini-SWE-agent, transferred to a Gemini 3 Pro student and still cut
5.4 average steps without hurting resolve rate; Appendix D.1 further shows
cross-*family* transfer, including a Gemini-trained SWE advisor guiding GPT-5 to
the same resolve rate as its standalone baseline (79.6% vs 78.4%) while removing
about one step (7.1 from 8.1, p ≈ 0.02). Their object of transfer is advice rather
than a routing decision, but it is the same underlying bet: something learned
against one model remains useful against another.

Two precedents, both positive, neither in Hecate's exact setting. That is the
appropriate prior — expect transfer to work somewhat, and make the experiment
capable of measuring how much is lost rather than only whether it survives.

1.3 What this does not test

E3 varies the model pair while holding the split fixed. Repository generality is
E1's subject and regime is E2's.

2 Research questions
--------------------

Q3.1 (primary) — Does a K=0 LoRA router trained on one weak/strong pair retain
routing skill when applied, without retraining, to a different weak/strong pair on
the same tasks and the same split?

Q3.2 (secondary) — How much is lost relative to a router trained natively on the
target pair? That is: what is the cost of transfer, not merely whether transfer
beats chance?

Q3.2 matters because RouteLLM benchmark transfer against a *random* router. Beating
random is a low bar and says little about whether transfer is a practical
substitute for in-domain training. The native-trained router is the honest ceiling.

3 Setup
-------

3.1 Pairs

Source pair (S): Qwen3-Coder-480B-A35B-Instruct (weak) → Claude-4-Opus-20250514
(strong). Hecate's existing pair. Specialist-versus-generalist.

Target pairs: selected from §0's survivors, choosing, where the pool allows:

  T1  a within-family capability ladder (e.g. a mini/full sibling pair), the
      easiest case for the difficulty-is-model-agnostic assumption and the closest
      analogue to RouteLLM's own transfer targets;
  T2  a second specialist-versus-generalist pair, the harder case.

If only one target pair is available, prefer T1 — it is the case where a negative
result is most informative, because failure there cannot be blamed on irregular
complementarity.

Selection constraint: a target pair must not share a model with the source pair.
Near-relatives (e.g. two Claude Opus revisions) are permitted but must be recorded,
since partial dependence weakens the independence of the transfer claim.

3.2 Per-pair characterization, required before any transfer number

For every pair, on both the full 500 and the django holdout, report: resolve rate
of each model; complementarity (both / weak-only / strong-only / neither); oracle
rate; and headroom over always-strong. Use E2 §3.2's django table as the template.

This is not bookkeeping. If a transfer fails and the two pairs turn out to have
very different complementarity structure, the failure is attributable to the
routing problem having changed shape rather than to the router failing to
generalize. Without these tables that distinction cannot be made after the fact.

3.3 Split

Leave-django-out, unchanged from v3 and E1: train on the 269 non-django tasks,
evaluate on the 231 django tasks. Holding the split fixed is what makes E3's
numbers comparable to v3's 0.686 and to E1's sympy figures. Varying pair and split
simultaneously would be uninterpretable.

3.4 Arms

  A  Transfer          Train K=0 LoRA on pair S's labels (269 non-django tasks),
                       evaluate on pair T's labels (231 django tasks). No
                       retraining, no adaptation — the RouteLLM protocol.
  B  Native ceiling    Train K=0 LoRA on pair T's labels, same split, evaluate on
                       pair T. The upper bound Q3.2 measures against.
  C  Frozen floor      v1 head refit on cached CLS embeddings against pair T's
                       labels, same split. No GPU.
  D  Random            Uniform router on pair T. RouteLLM's own baseline, included
                       for direct comparability with their Table 4.

3.5 Why K=0 only

K=3 is excluded deliberately. Trajectories are pair-specific: each weak model
produces its own. Transferring a K=3 router would vary the router's training pair
*and* the trajectory source simultaneously, confounding two effects in one number.
K=0 conditions on issue text alone, which is identical across pairs, isolating pair
transfer cleanly. Trajectory representation is E4's subject.

3.6 Model and hyperparameters

Inherited unchanged from v3, identical to E1 §3.4 and E2 §3.5:

  Backbone              Qwen2.5-Coder-7B-Instruct
  Adapter               LoRA, r=32, alpha=64
  Quantization          QLoRA (4-bit base)
  Value head            last-token logits
  Context length        8192
  Seeds                 0 (smoke); config default 0,1,2
  Epochs                5 (v3 schedule; watch validation loss per E1 §6.2)

Remaining hyperparameters inherited from `configs/router_traj.yaml` (arms A, B) and
`configs/router_text.yaml` (arm C); resolved values read from the run manifest.

3.7 Training runs required

  1. Pair S router (arm A's vehicle). Note this must be *retrained*: v3's K=0
     adapter scoring 0.686 was never checkpointed and no longer exists. Retraining
     it also yields a second seed-0 measurement of a known quantity, which is a
     free consistency check on the pipeline.
  2. Pair T1 native router (arm B).
  3. Pair T2 native router, if T2 is available.

Three LoRA runs for two target pairs; two if only one target pair survives §0.
Arms C and D need no GPU. No new label generation, no new inference.

3.8 Environment

  Training host   GCP `hecate-traj-l4` (L4 GPU). E2 restarts it; E3 reuses it.
  Python deps     train extras from pyproject.toml — torch, transformers, peft,
                  bitsandbytes, accelerate. Core: swebench==4.1.0, datasets,
                  httpx, pyyaml, unidiff, GitPython.
  Entry points    scripts/run_train_traj.py (arms A, B),
                  scripts/run_train_text.py (arm C), `--split leave-repo
                  --hold-repo django/django --hold-only --arm k0`.

3.9 Code gap

Modest. The training path already exists; what is missing is label plurality. The
loader currently assumes one labels CSV with fixed `small_model_resolved` /
`large_model_resolved` columns. Needed:

  1. An ingest path for additional per-instance result files, joined on
     `instance_id`, producing one `RouterExample` set per pair.
  2. A `--pair` (or `--labels`) argument selecting which pair's labels to train
     against and which to evaluate against, since arm A trains and evaluates on
     *different* pairs — the two must be separately specifiable.
  3. Provenance fields on the manifest recording both pairs, their submission
     identifiers, and the mini release version, so a transfer run can never be
     confused for a native one after the fact.

4 Metrics
---------

Primary: Route-AUC on the django holdout against the target pair's labels.

Transfer-specific, following RouteLLM [5] for direct comparability with their
Table 4: APGR, CPT(50%), CPT(80%). APGR is the headline transfer metric in their
paper, so reporting it puts Hecate's numbers on the same axis as 0.772 and 0.767
rather than requiring a reader to translate.

Retention ratio: arm A's APGR divided by arm B's. This is Q3.2's answer in one
number — the fraction of native-training performance that survives transfer — and
is not a metric RouteLLM report, because they do not train a native comparison.

Diagnostic: AUROC, accuracy, Brier. Reported, never gated — SWE-Router [4] find
AUROC correlates weakly with routing quality and v3 reproduced the decoupling.

Endpoints per pair: always-weak, always-strong, oracle, on the holdout.

5 Decision rules (pre-registered)
---------------------------------

5.1 Q3.1 is answered affirmatively if arm A clearly beats arms C and D on the
target pair — that is, a transferred router retains real skill rather than
collapsing to the frozen floor or to chance.

5.2 Q3.2 is reported as the retention ratio, with no threshold attached. It is a
measurement, not a gate. State it plainly whatever it is.

5.3 If the two pairs' complementarity structures (§3.2) differ substantially, that
must be reported *alongside* any transfer result and any interpretation must
acknowledge it. A low retention ratio between structurally dissimilar pairs is weak
evidence about router generality and strong evidence that pair structure matters —
those are different claims.

5.4 Seeds: single seed (0) first pass, treated as a smoke. Escalate to seeds 1 and
2 only if arm A's margin over arm C sits inside plausible noise.

6 Risks and caveats (pre-registered)
------------------------------------

6.1 The precondition may fail. §0 may find no usable v1.0.0 companions. That is a
legitimate outcome and the experiment is then deferred, not forced. Do not mix
scaffold releases to make it runnable.

6.2 Borrowed labels, multiplied. Every additional pair imports its own provenance
risk — sampling settings not recorded in submission metadata, flagged trajectories,
harness configuration drift within a release. Hecate's existing metadata already
documents two such issues for its own pair (greedy-decoding configuration that
vendor guidance contradicts; seven git-peek-flagged Opus trajectories, two
resolving). Each new pair needs the same audit, and the audit belongs in the
write-up, not in a footnote.

6.3 Shared or related models. If a target pair's strong model is a revision of the
source pair's strong model, transfer is measured across partially dependent
systems. Record it; prefer independent pairs where the pool allows.

6.4 Direction is not symmetric. Transfer from a specialist/generalist pair to a
ladder pair is a different test than the reverse. If both directions are runnable,
run both; if only one, state which and do not generalize past it.

6.5 Small effective sample. The holdout remains 231 django tasks with a headroom
over always-strong of 3.9pp on Hecate's pair. Target pairs may have more or less
headroom; where headroom is small, APGR is sensitive to a handful of instances.
Report endpoint rates so this is visible.

6.6 Single seed. As with E1 and E2, the first pass is a smoke. The 0.589 trap
remains the standing reminder.

7 Relation to prior work
------------------------

RouteLLM [5] is the direct target. E3 replicates their transfer protocol — train on
one pair, swap models at inference, no retraining — in a setting they explicitly
did not evaluate: multi-turn agentic SWE rather than MT-Bench / MMLU / GSM8K, with
execution-verified labels rather than human preference, and on a pair that is not a
within-family ladder. It also adds the native-trained ceiling their evaluation
omits.

Advisor Models [6] provides the agentic-setting transfer precedent in §1.2,
including cross-family results in their Appendix D.1.

SWE-Router [4] addresses pair generality by evaluating two pairs independently
rather than by transferring between them; E3 is the stronger version of that check
and covers the axis Hecate currently cannot claim.

CoDyn [7] fine-tunes low-cost LLMs as routers across coding tasks and reports
substantial cost savings; relevant as background on trained-router viability, not
as a transfer result.

8 Deliverables
--------------

  precondition report    enumerated submissions, release versions, retrievability,
                         reproduced aggregate rates, per-pair caveats
  pair tables            complementarity and endpoints for every pair, full 500
                         and django holdout
  results.json           aggregate + per-task scores, all arms, both directions
                         where applicable
  manifest               both pairs' submission identifiers, mini release version,
                         resolved hyperparameters, seeds, git SHA
  adapters               pair S and pair T routers, saved and copied off the VM
                         (v3 postmortem; see E1 §3.6, E2 §3.9)
  README                 run notes, deviations, provenance audit

9 Sequencing note
-----------------

E3 is third because its precondition is unverified, not because it is less
valuable. If §0 comes back clean, E3 arguably addresses the limitation a reviewer
will press hardest — harder than repository generality, since one pair is a
narrower base than one repository. The §0 check is cheap and read-only and can be
run at any time, including before E1 and E2 complete. Running it early is
recommended: a clean result would justify promoting E3, and a failed one would let
the slate be replanned without wasted GPU time.

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
[7] J.P.Morgan AI Research (2024). CoDyn: Dynamic LLM Routing.
