# Hecate — orientation for Claude Code

Read this first in any new session. It's a condensed handoff from a planning
conversation (Cowork, 2026-09-13/14) so a fresh session isn't starting blind.
Full detail for everything summarized here is in `experiments/e0N-*/spec.md`
and `docs/2026-09-14-repo-structure-and-durability-proposal.md` — read those
before touching the areas they cover. Dated `docs/2026-09-13-exp*.md` files are
stubs that point at `experiments/`.

## What Hecate is

A router that predicts whether an SWE task can stay on a cheap/small model or
needs to escalate to an expensive/large one, using execution-grounded labels
(SWE-bench Verified, mini-SWE-agent v1.0.0 scaffold). Current pair: weak =
Qwen3-Coder-480B-A35B-Instruct, strong = Claude-4-Opus-20250514, 500 matched
tasks. Route-AUC is the primary metric; AUROC is diagnostic only (SWE-Router
[arXiv:2607.00053] and Hecate's own v3 both show AUROC decouples from routing
quality).

## Where things stand (rounds completed)

  Arm                        Route-AUC      AUROC        Accuracy     Brier
  v1 frozen text              0.477 ±0.030   0.516 ±0.015 0.519 ±0.060 0.250
  v2 CLS + oracle AST         0.482 ±0.020   0.518 ±0.021 0.527 ±0.068 0.250
  v3 K=0 LoRA (1 seed)        0.686          0.563        0.450        0.288
  v3 K=3 LoRA (1 seed)        0.587          0.573        0.455        0.409

All measured on the django/django holdout (n=231, leave-django-out), the only
holdout used so far — that's the gap E1 exists to close. v3 rejected H1 (K=3
does not beat K=0 under repository shift) and accepted RQ2 (fine-tuned LoRA
beats the frozen floor). **v3's K=0/K=3 adapters were never checkpointed** —
the smoke runner never called `.save()` — so those numbers can't be
reproduced from a saved model, only from source. See the durability doc below
before running anything that trains a new adapter.

## The five planned experiments (all PLANNED, none run yet)

  E1  experiments/e01-second-repo-replication/spec.md
      leave-sympy-out generalist replication. No new code needed — the split
      it needs already exists (`--split leave-repo --hold-repo sympy/sympy`).
      Questions: Q1.1, Q1.2.

  E2  experiments/e02-specialist-django/spec.md   (rev 2, amended 2026-09-14)
      Train AND test on django (specialist split, 185/46). **This is the one
      Scott plans to run first.** Needs new code: a single-repo
      label-stratified split function + `--split specialist` threaded
      through `run_train_traj.py`/`run_train_text.py` (does not exist today).
      Rev 2 added a 4th arm, K=1 (Q2.3), as a cheap diagnostic. `k1` is in
      `TRAJ_ARMS`; the specialist split is the remaining blocker. K=1 is
      exploratory only; it never substitutes for the pre-registered K=3 arm
      (Q2.2).

  E3  experiments/e03-cross-pair-transfer/spec.md
      CONDITIONAL — depends on an unverified precondition (other usable
      mini-SWE-agent v1.0.0 submissions with retrievable per-instance
      results). Run the §0 check before scheduling this one.

  E4  experiments/e04-lookahead-router/spec.md
      Heaviest new implementation: adapts Lookahead Routing (NeurIPS 2025) —
      train a placeholder token to reconstruct the weak model's trajectory,
      supply nothing at inference. Motivation sharpens once E1 has run.

  E5  experiments/e05-repo-structure-gate/spec.md
      No GPU needed — cheapest experiment in the slate. Re-tests whether
      static code structure predicts routability, without oracle (gold-patch)
      localization this time. A 6-task pilot already ran; commit-snapshot
      structural metrics track issue date almost monotonically, so a
      date-only control arm is mandatory, not optional.

**Question IDs:** `Q<experiment>.<n>` (Q1.1, Q2.3, …). Directory numbers are
zero-padded (`e02`) so they sort past nine experiments. Spec-kit `015` is a
product feature, not E5.

Run IDs: `exp-02_arm-k1_split-specialist_seed-0` (`hecate.utils.run_ids`).

## Known code gaps (confirmed against source, not assumed)

Read `src/hecate/router/traj.py`, `traj_runner.py`, and
`scripts/run_train_traj.py` before changing any of this.

- `TRAJ_ARMS` in `traj.py` is the K-arm registry (`k0`, `k1`, `k3`). The
  "k3" arm does not train on 3 turns — `train_rows_for_arm()` packs every
  prefix K=0..min(4, n_turns) as a separate training row per instance (up to
  5 rows/instance, with the longer rows also being the longest sequences).
  That's what makes it slow to train, not "reading a longer trajectory" per se.
- E2's specialist split (single repo, label-stratified 80/20) does not exist
  in `splits.py` yet — only `assign_grouped_repo_folds` and
  `assign_leave_repo_out`. `--split specialist` needs threading through
  both runners.
- LoRA runs require `HECATE_ARTIFACTS_URI=gs://hecate-506120-artifacts`.
  The runner fail-closes if that copy is missing unless `--allow-unsynced`.

## Repo structure and durability (applied in part)

`docs/2026-09-14-repo-structure-and-durability-proposal.md` is the original
write-up. What landed: `experiments/e0N-*/` (not spec-kit `016`), `TRAJ_ARMS`,
and `gs://hecate-506120-artifacts` with push-on-completion from the runners.
What did not: `build_results_table.py`, committed `runs.jsonl` (created on
first real run). Use `--run-id $(python -c "from hecate.utils.run_ids import make_run_id; print(make_run_id(exp=2, arm='k1', split='specialist', seed=0))")`.

## Environment

  GCP project      hecate-506120, zone us-central1-a
  Training VM      hecate-traj-l4 (L4 GPU), currently stopped — restart with
                   scripts/provision_traj_l4.sh, stop when idle
  Exec VM          hecate-exec (CPU) — do not run LoRA training on it
  Config           configs/router_traj.yaml (LoRA/backbone), configs/
                   router_text.yaml (frozen arm)
  Local device     linked Mac at /Users/scottdavis/hecate (this session was
                   bridged to it via Cowork's remote-devices tools)

## Working conventions already in place

- Spec precedes implementation — every experiment doc is written and reviewed
  before any code changes. Don't skip straight to code.
- Every run must persist: `.save()` on the adapter, per-task holdout scores
  (not just aggregates), and the run dir copied to
  `HECATE_ARTIFACTS_URI`. `require_lora_checkpoint()` fail-closes locally;
  `finalize_run_artifacts()` fail-closes on the off-VM copy.
- Decision rules are pre-registered in each experiment doc before any number
  is seen (e.g. E2 §2.1/§2.2 constrain what a positive/negative K=3 or K=1
  gap is allowed to mean). Don't reinterpret results outside those rules
  without flagging it explicitly as a deviation.
