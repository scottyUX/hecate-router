Experiment 4 — Lookahead-conditioned router: imagining the trajectory instead of reading it
Hecate Lab
SWE-bench Verified (500) · leave-django-out (n=231) · rev 1 — PLANNED, not yet run
September 13, 2026

Status: specification only. No code written, no runs executed. This is the
heaviest new implementation in the slate; see §3.9.

Position in slate: Experiment 4 of 5.
  E1  Second-repo replication (leave-sympy-out)
  E2  Specialist holdout (train on django, test on django)
  E3  Cross-pair transfer
  E4  Lookahead-conditioned router                              — this document
  E5  Non-oracle repo-structure gate

Question labeling: Q<experiment>.<n>, per E2's header.

Abstract
--------
v3 rejected H1: a router reading three turns of the weak model's own
mini-SWE-agent trajectory (K=3, Route-AUC 0.587) lost to a trajectory-blind
control (K=0, 0.686) under repository shift, a gap of −0.099. That result admits
two readings. Either partial-execution signal does not transfer across
repositories, or it does but Hecate's representation of it — raw packed trajectory
text — is the wrong vehicle. This experiment separates them. Following Lookahead
Routing [10], it trains the router with an auxiliary objective that supervises a
placeholder token's hidden state to *reconstruct* the weak model's real trajectory,
while at inference supplying no trajectory at all. The resulting arm has K=0's
input, K=0's inference cost, and K=3's training signal. A win closes a practical
gap as well as a scientific one: K=3 must spend weak-model inference before it can
decide to avoid the weak model, and this arm does not.

1 Background
------------

1.1 The ambiguity left by H1

v3, django holdout, n=231:

  Arm                        Route-AUC      AUROC        Accuracy     Brier
  v1 frozen text             0.477 ±0.030   0.516 ±0.015 0.519 ±0.060 0.250 ±0.008
  v3 K=0 LoRA (1 seed)       0.686          0.563        0.450        0.288
  v3 K=3 LoRA (1 seed)       0.587          0.573        0.455        0.409

H1 is closed and stays closed. But "K=3 lost" is a statement about one
representation of trajectory, not about trajectory as a source of information. A
reader can reasonably object that packed raw text is a poor encoding: it is long,
saturated with repository-specific surface detail (file paths, module names,
framework-flavored tracebacks) that cannot transfer across repositories, and it
consumes context budget that was carrying the issue statement. Under that
objection, H1's rejection is an implementation result wearing the clothes of a
mechanism result.

E4 removes the objection by giving trajectory information its best available shot
in a form that does not depend on repository-specific surface text surviving
transfer, and by making the comparison cost-matched.

1.2 The method being adapted

Lookahead Routing [10] observes that routers conditioned only on the query ignore
what the candidate responses would contain, and that generating those responses to
find out is prohibitive. Their solution: insert a placeholder token per candidate
model, train that token's hidden state to reconstruct the model's real response via
an auxiliary loss, and read the routing decision off the same hidden state. The
joint objective is

  L = L_route + λ · L_resp

with L_route a binary cross-entropy on the routing score and L_resp a
reconstruction loss — teacher-forced next-token prediction over the real response
in their causal-LM variant, masked-token recovery in their masked-LM variant. They
use λ = 0.5 (CLM) and λ = 0.2 (MLM), and report +7.7% average over RouterDC for the
MLM variant and +4.5% over SMOOTHIE for the CLM variant, plus a 6.3× data
efficiency gain.

The asymmetry is the point. Training requires real sampled responses from each
candidate model. Inference requires none: one forward pass over the query and the
placeholders, read the hidden states, classify. Nothing is generated.

1.3 Why this maps onto Hecate cleanly

The expensive ingredient in Lookahead's recipe — real responses from the model
being predicted — is the one thing Hecate already has. The K=3 arm reads packed
first-three-turn mini-SWE-agent trajectories from `--traj-dir`. Those same files
become the reconstruction target here. No new generation, no new labels.

The substitution is: Lookahead's "response" becomes "the weak model's own partial
agent trajectory." The placeholder's hidden state is trained to encode what Qwen
would do on this issue, and the routing head reads that encoding — without the
trajectory ever being supplied at decision time.

1.4 Independent signal that trajectory representation is the live variable

Advisor Models [6] runs a 7B (Qwen2.5 7B Instruct) over accumulated mini-SWE-agent
actions and observations, in a single repository, and gets usable behavior out of
it — so a 7B *can* extract signal from partial trajectories in that setting (E2
§1.3 covers this in full). Their Appendix B.2 then names the open problem directly:
longer advisor intervals make training cheaper but weaken the signal, and they flag
"summarization or truncation of student actions and observations" as an unresolved
design consideration for supporting lower-frequency interaction.

That is the same problem from the other side. They could not decide how to compress
accumulated trajectory; E4 proposes learning the compression instead of
hand-designing it.

1.5 The deployment argument, stated independently of the metric

K=3 has a structural awkwardness for any real system: the weak model must execute
three turns before the router can decide whether to route away from the weak model.
A meaningful share of the cost the router exists to save has already been spent by
the time it decides. This is not a criticism of v3 — the arm was built to answer a
scientific question, not to ship — but it means that even a K=3 victory would have
required a deployment story that E4's arm does not need. E4's arm decides before
any weak-model inference occurs.

This argument holds whatever the Route-AUC turns out to be, and belongs in the
write-up regardless of outcome.

2 Research questions
--------------------

Q4.1 (primary) — Does a router trained with a trajectory-reconstruction auxiliary
objective, and given no trajectory at inference, beat a plain K=0 router under
repository shift? Both arms see identical information at decision time and cost the
same to run; the only difference is what the training objective asked the model to
encode.

Q4.2 (secondary) — How does that arm compare to K=3, which reads a real trajectory
at inference? Matching or exceeding K=3 without needing the trajectory is the
strongest available outcome.

2.1 Pre-registered validity condition on Q4.1

A gain of the lookahead arm over plain K=0 is *not* by itself evidence that the
router learned anything trajectory-specific. Adding any auxiliary objective to a
small training set can act as multi-task regularization, improving generalization
for reasons unrelated to trajectories. Those two explanations imply different
claims, and a Route-AUC number cannot separate them.

Therefore Q4.1 is answered affirmatively only if both hold:

  (a) the lookahead arm clearly beats plain K=0, and
  (b) that gain does *not* survive the shuffled-target control (arm E, §3.4),
      in which the reconstruction target is a trajectory drawn from a different,
      randomly chosen instance.

If the gain persists with mismatched targets, the finding is "an auxiliary
reconstruction objective regularizes this router," which is a real but much weaker
and differently-framed result, and must be reported as such rather than as
trajectory imagination.

2.2 What this cannot do

E4 does not reopen H1. H1 concerns whether reading a packed trajectory at inference
beats not reading one, and it is closed. E4 asks a different question about a
different arm. A positive E4 result means a learned encoding of trajectory
information helps where raw packed text did not — which is a statement about
representation, not a reversal of H1.

3 Setup
-------

3.1 Data

Unchanged from v3 and E1: the matched-scaffold external label set,
Qwen3-Coder-480B-A35B-Instruct (weak, m1) against Claude-4-Opus-20250514 (strong,
m2), both under mini-SWE-agent v1.0.0 [3], SWE-bench Verified [1][2] bash-only
track, 500 instances.

Reconstruction targets: the existing K=3 trajectory files (`--traj-dir`), in the
same packed first-three-turn representation the K=3 arm consumes. Using the
identical content as target makes E4 an exact contrast with C — same information,
different access mode (imagined versus read) — rather than a comparison confounded
by target choice.

Gold `patch` / `test_patch` are neither stored nor read.

3.2 Split

Leave-django-out: train on 269 non-django tasks, evaluate on 231 django tasks,
`--hold-only`. This is where H1 was scored and where the ambiguity in §1.1 lives,
so it is where the ambiguity must be resolved.

Secondary, contingent on E2 having run: repeat the same arms on E2's specialist
django split (185/46). If in-distribution K=3 wins there while lookahead helps
under shift, the two results together give a clean account of when each form of
trajectory access pays. Not part of the primary run.

3.3 Architecture

Causal-LM variant of Lookahead [10], on Hecate's existing backbone.

  Placeholder        one special token appended after the issue text, standing for
                     the weak model. Hecate routes a binary pair, not among T
                     models, so T = 1 placeholder — not the T-way block Lookahead
                     uses for their five-model pool.
  Representation     hidden state at the placeholder position, r̃, as in their CLM
                     variant (r̃_t = h^MID_t).
  Routing head       existing last-token-logit value head, reading r̃.
  Reconstruction     teacher-forced next-token prediction over the packed
                     trajectory, conditioned on the placeholder hidden state —
                     their Eq. 6 form, L_rec = −Σ log P(y_j | x, MID, y_<j).
  Objective          L = L_route + λ · L_resp

At inference the trajectory is not supplied. The input is the issue text plus the
placeholder: identical shape and cost to arm B.

3.4 Arms

  A  Frozen floor    v1 head refit on cached ModernBERT CLS embeddings, same
                     split. Standing reference (0.477 ±0.030). No GPU.
  B  K=0 LoRA        plain, no auxiliary objective. The matched-cost control and
                     the Q4.1 comparator. Reuse E3's retrained pair-S adapter if
                     available (§3.8) rather than retraining a third time.
  C  K=3 LoRA        reads the real packed trajectory at inference. The Q4.2
                     reference.
  D  L0 lookahead    K=0 input at inference, trajectory-reconstruction auxiliary
                     loss during training. The test arm.
  E  L0 shuffled     identical to D except each instance's reconstruction target
                     is a trajectory sampled from a different instance. Required
                     by §2.1. Same compute cost as D.

3.5 Hyperparameters

Inherited unchanged from v3 wherever they exist, so that the auxiliary objective is
the only new variable:

  Backbone              Qwen2.5-Coder-7B-Instruct
  Adapter               LoRA, r=32, alpha=64
  Quantization          QLoRA (4-bit base)
  Value head            last-token logits
  Context length        8192
  Trajectory packing    unchanged from v3 K=3 (used as target, not input, in D/E)
  Seeds                 0 (smoke); config default 0,1,2
  Epochs                5 (v3 schedule; watch validation loss)

New to this experiment:

  λ (reconstruction weight)   0.5, Lookahead's CLM value [10]. A single value is a
                              smoke, not a tuned setting — see §6.2.
  Placeholder token           one added special token; record whether it is a new
                              embedding or a repurposed unused token in the
                              manifest, since initialization affects trainability.
  Placeholder width m         1 for the CLM variant, per [10]. A wider block (their
                              MLM design uses m repeated tokens for capacity) is a
                              variant, not the default — see §6.3.

Remaining hyperparameters from `configs/router_traj.yaml`; arm A from
`configs/router_text.yaml`. Resolved values read from the run manifest.

3.6 Cost profile, stated precisely

Training cost for D and E is comparable to C's, because the reconstruction loss
processes the trajectory tokens. Inference cost for D and E equals B's, because no
trajectory is supplied. The saving this experiment chases is entirely at decision
time. Any write-up must say this plainly rather than implying the method is
cheap overall.

3.7 Environment

  Training host   GCP `hecate-traj-l4` (L4 GPU). Restarted by E2, reused here.
  Python deps     train extras from pyproject.toml — torch, transformers, peft,
                  bitsandbytes, accelerate. Core: swebench==4.1.0, datasets,
                  httpx, pyyaml, unidiff, GitPython.
  Entry points    scripts/run_train_traj.py with a new `--arm l0` (and `--arm
                  l0-shuffled`); scripts/run_train_text.py for arm A.

3.8 Training runs required

Four LoRA runs (B, C, D, E), reducible to three if E3 has already retrained the
leave-django-out K=0 adapter, which is the same configuration as arm B. Neither B
nor C currently exists as a checkpoint: v3's adapters were never saved. Retraining
them here also re-measures two known quantities (0.686 and 0.587) at seed 0, which
is a free consistency check on the pipeline.

3.9 Code gap

The largest in the slate.

  1. A reconstruction head and loss branch on `TrajLoraBackend` — teacher-forced
     next-token prediction over target trajectory tokens, conditioned on the
     placeholder hidden state.
  2. A combined training step summing L_route and λ·L_resp, with both components
     logged separately every epoch. Logging both is not optional: §5.3 depends on
     being able to see whether reconstruction is actually learning.
  3. Placeholder-token handling — tokenizer addition, embedding initialization,
     and the inference path that omits trajectory input entirely while keeping the
     placeholder.
  4. `--arm l0` and `--arm l0-shuffled` wired through `run_train_traj.py`, with
     the shuffling seeded and recorded so the control is reproducible.
  5. Manifest fields for λ, placeholder configuration, and target-shuffling seed.

3.10 Artifacts that must be persisted

Per the v3 postmortem (E1 §3.6, E2 §3.9): `.save()` on every adapter, per-task
holdout scores written out, everything copied off the VM on completion. E4 adds
one requirement: the per-epoch reconstruction-loss trace must be persisted, because
§5.3's diagnostic cannot be reconstructed after the fact.

4 Metrics
---------

Primary: Route-AUC on the django holdout.
Diagnostic: AUROC, accuracy, Brier — reported, never gated (SWE-Router [4] find
AUROC weakly correlated with routing quality; v3 reproduces the decoupling).
Endpoints: always-Opus 70.6%, always-Qwen 58.0%, oracle 74.5% on this holdout.
Secondary: CPT(50%), CPT(80%) per RouteLLM [5], for comparability.

Experiment-specific: final and per-epoch reconstruction loss for arms D and E, and
the correlation across checkpoints between reconstruction loss and holdout
Route-AUC. See §5.3.

5 Decision rules (pre-registered)
---------------------------------

5.1 Q4.1 passes only if both conditions in §2.1 hold — arm D clearly above arm B,
*and* arm E failing to reproduce that gain. Either alone is insufficient.

5.2 Q4.2 is reported as the signed gap (D − C), with no threshold. D ≥ C is the
headline-worthy outcome; D between B and C is a partial result and is reported as
one.

5.3 Mechanism diagnostic. Report whether reconstruction loss decreased
meaningfully over training and whether it tracks holdout Route-AUC across
checkpoints. A D-over-B gain accompanied by a reconstruction loss that never
improved is evidence for the regularization reading even if arm E is ambiguous.
This is a diagnostic, not a gate.

5.4 Seeds: single seed (0) first pass, treated as a smoke. Escalate to seeds 1 and
2 on arms B, D, E only if D's margin over B sits inside plausible noise.

5.5 λ: one value (0.5). If Q4.1 fails, a λ sweep is a legitimate follow-up and must
be reported as a follow-up rather than folded silently into the primary result.

6 Risks and caveats (pre-registered)
------------------------------------

6.1 Training-set size is the dominant risk, and it is severe. Lookahead [10] train
on 59,281 samples; even their data-efficiency result uses 16% of that, roughly
9,500. Hecate's leave-django-out training set is 269 tasks — two orders of
magnitude smaller. An auxiliary objective that needs data to teach a hidden state
what trajectories look like may simply have no opportunity to do so at this scale.

This must be stated before results, because it governs how a null result is read.
If E4 fails, "the mechanism does not work" and "the mechanism was never given
enough data to work" are both live, and they are not distinguishable from a single
run at n=269. The honest fallback is that a fair test of this mechanism may require
a training set one to two orders of magnitude larger, which points at SWE-smith
[9] (52k instances, 250+ repositories) as a scale-up path — with the significant
caveat that SWE-smith tasks are synthetically injected bugs rather than real
issues, and that using it requires generating pair labels rather than borrowing
them, which is a separate track.

6.2 λ is unswept. One value from a different domain, model scale, and target type.
A null at λ = 0.5 is weak evidence about the mechanism.

6.3 Target difficulty. Lookahead reconstructs chat responses. A packed
mini-SWE-agent trajectory is longer, more structured, and far more heterogeneous —
reasoning, shell commands, tracebacks, file contents. Their curriculum-masking
device exists precisely because full blind reconstruction is hard even for chat
responses; the CLM variant has no such device. Reconstruction may fail to train at
all, which §5.3's diagnostic is designed to detect rather than mask.

6.4 Scale mismatch with the source method. Lookahead's CLM variant uses
SmolLM2-135M; this adapts the idea to a 7B with LoRA. Larger capacity is not
obviously better here — more of the objective may be absorbed by the adapter
without changing what the placeholder encodes.

6.5 Construct validity. Addressed by arm E and §5.3, not eliminated by them. Report
the ablation outcome in the same breath as the headline number, never separately.

6.6 Single seed, single split. The 0.589 trap stands. n=231 is the larger of
Hecate's holdouts, which helps, but one seed remains a smoke.

7 Relation to prior work
------------------------

Lookahead Routing [10] is the method adapted here. Differences worth stating in any
write-up: their setting is single-turn instruction-following, math and code
generation across five chat models; ours is multi-turn agentic SWE with a binary
weak/strong pair. Their target is a chat response; ours is a partial agent
trajectory. They never evaluate under distribution shift of any kind, so the
question E4 asks — whether a learned latent survives repository shift where raw
packed text did not — is outside what their results speak to.

SWE-Router [4] supplies the mechanism E4 contrasts against: conditioning on partial
trajectory at inference. E4 keeps the information source and changes only how the
router gains access to it.

Advisor Models [6] supplies §1.4's open problem (their Appendix B.2 on
summarization and truncation of accumulated student actions) and, in their SWE
domain, evidence that a 7B can act usefully on partial mini-SWE-agent trajectories
in-distribution.

RouteLLM [5] contributes the CPT metrics in §4.

8 Deliverables
--------------

  results.json     aggregate + per-task holdout scores, arms A-E
  loss traces      per-epoch L_route and L_resp for arms D and E, persisted
  manifest         λ, placeholder configuration, shuffling seed, resolved
                   hyperparameters, seeds, git SHA
  adapters         arms B-E, saved and copied off the VM
  README           run notes, ablation outcome reported alongside the headline,
                   deviations, validation-loss trace

9 Sequencing note
-----------------

E4 is fourth deliberately. It is the most new code, it introduces the only
untuned hyperparameter in the slate, and its motivation sharpens considerably once
E1 has established whether the repository-shift result replicates at all. Building
a better representation to attack a pattern that has not been confirmed to exist
would be the wrong order. If E1 shows the shift result is django-specific, E4's
framing needs revisiting before it is built.

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
[9] Yang, J. et al. (2025). SWE-smith: Scaling Data for Software Engineering
    Agents. NeurIPS D&B. arXiv:2504.21798.
[10] Huang, C., Shi, T., Zhu, Y., Chen, R., Quan, X. (2025). Lookahead Routing for
    Large Language Models. NeurIPS.
