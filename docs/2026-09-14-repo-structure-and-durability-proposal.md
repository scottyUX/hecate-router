Repo structure and artifact-durability recommendation
Hecate Lab
September 14, 2026

Status: **partially applied** (2026-09-14). Landed: `experiments/e0N-*/spec.md`
(not spec-kit 016), `TRAJ_ARMS` including `k1`, GCS bucket
`gs://hecate-506120-artifacts` with fail-closed LoRA sync. Rejected from this
write-up: continuing spec-kit numbering as `016-020`; a second `config.yaml`
per experiment. BIDS-style run IDs (`exp-02_arm-k1_split-specialist_seed-0`)
are the naming rule.

The sections below are the original recommendation and are left in place as
the design record. Do not treat “nothing has been applied” as current.

---

Repo structure and artifact-durability recommendation
Hecate Lab
September 14, 2026

Status: recommendation only. Nothing in this document has been applied to the
repo. Written after reading the actual codebase (`src/hecate/router/`,
`scripts/`, `configs/`, `specs/`, `.specify/`, `data/`, `.gitignore`) rather
than in the abstract.

Why this is being written now: five experiments (E1–E5) are specified and about
to run, at least one more arm (K=1, added to E2) has already been added
mid-stream, and v3's LoRA adapters were already lost once because they lived
only on a stoppable VM's local disk with no automated copy elsewhere. Both
problems get worse, not better, as more experiments run. This document is a
recommendation to review, not a change that has been made.

1 What's actually causing risk today
-------------------------------------

Confirmed directly against the repo, not assumed:

1.1 No durable copy of anything produced by a run. `.gitignore` excludes
`data/raw/` (fetched trajectories), `data/cache/` (frozen embeddings), and
`data/outputs/` (every run's results.json, manifest.json, holdout_scores.jsonl,
and LoRA checkpoints). All three live only on whatever disk they were written
to. `scripts/sync_exec_vm.sh` exists but only pushes code and a generations
file *onto* the exec VM — nothing in the repo ever pulls artifacts back off
`hecate-traj-l4` (or any VM) to a second location. The v3 postmortem already
documented in the E1/E2 docs — "K0/K3 adapters died with their training
processes... `results.json` exists only on the stopped L4 disk" — is the
predictable result of this gap, not a one-off mistake.

1.2 The "must be persisted" requirement is prose, not code. Every experiment
doc (E1 §3.6, E2 §3.9, E3 §3.9-equivalent, E4 §3.10, E5 §3.9) repeats a
checklist: call `.save()`, write per-task scores, copy `results.json` +
manifest + adapter off the VM immediately. `require_lora_checkpoint()` in
`traj_runner.py` already fail-closes on the *local* checkpoint (adapter dir +
score.pt must exist), which is good — but nothing fail-closes on the *off-VM
copy* step. That step is currently a sentence in a markdown file, enforced by
whoever remembers to run it by hand.

1.3 Arm/split registries are hardcoded tuples that already needed manual
extension once. `ARMS = ("k0", "k3")` in `traj_runner.py`; `--split
choices=("grouped", "leave-repo")` and `--arm choices=("k0", "k3")` in
`run_train_traj.py`; `train_rows_for_arm()` in `traj.py` has an if/elif on the
arm name. Adding E2's specialist split and the K=1 diagnostic arm each meant
touching several files by hand. E3 (pair selection), E4 (l0/l0-shuffled), and
E5 (feature arms via `run_train_text.py`'s `--features` flag) will each want to
do the same thing again.

1.4 `data/outputs/runs/` is a flat, hand-named bucket with no index. 23+
entries today (`pilot-20x1-v5-repair-llama8b-tail`, `v3-smoke-k3`,
`router-v2-oracle-metrics-ldo`, ...). The only way to know which
experiment/arm/seed/split produced a given run is to open its `manifest.json`
one at a time. Every comparison table in every experiment doc (v1/v2/v3
numbers, repeated in E1 through E5) is hand-transcribed from those files —
which is exactly the kind of process that produced the RQ-labeling collision
already flagged as an open item in the docs (v3's RQ1/H1, the superseded v4's
RQ3/RQ4, E1's RQ-E1/RQ-E2, E2's Q2.1/Q2.2/Q2.3 — four schemes because nothing
forces one).

1.5 Experiment specs live outside the repo entirely. The E1–E5 documents exist
only in the Claude project's knowledge base, not as files in this git history.
There is no commit that ties "this is the spec" to "this is the code that
implements it" to "these are the results it produced." A spec can be amended
(as E2 was, adding Q2.3/arm D) without that amendment being reviewable as a
diff against the code changes it motivated.

2 Recommended structure (not applied)
----------------------------------------

2.1 Experiment directories, mirroring the existing spec-kit pattern. You
already have `specs/001-...` through `specs/015-router-training/` — numbered
feature specs with `spec.md`, `plan.md`, `tasks.md`, `data-model.md`,
`contracts/`. Recommendation: a parallel `experiments/` tree using the same
numbering continuation, one directory per experiment:

  experiments/
    016-second-repo-replication/       (E1)
      spec.md                          — committed copy of the experiment doc
      config.yaml                      — machine-readable: split, arms, seeds
      results.md                       — filled in after running; points at
                                          run IDs in data/outputs/runs/
    017-specialist-django/             (E2)
    018-cross-pair-transfer/           (E3)
    019-lookahead-router/              (E4)
    020-repo-structure-gate/           (E5)

The Claude-project docs stay the authoring surface (that workflow is working
well — detailed, pre-registered, well-disciplined) but get committed into
`spec.md` once each doc stabilizes, so spec and implementing code move through
git together and an amendment (like E2's Q2.3) is a reviewable diff instead of
a silent edit in a separate system. This directly resolves the RQ-labeling
mess too: the directory number is the one canonical experiment ID, and every
question becomes `<experiment-number>.<n>` project-wide — no more parallel
schemes.

2.2 A small registry instead of hardcoded tuples. In `traj.py`, replace the
`"k0"`/`"k3"` if/elif in `train_rows_for_arm()` (and the matching pieces in
`traj_runner.py`: `ARMS`, `_eval_k`) with a dict keyed by arm name, e.g.
`{"k0": ArmSpec(train_k_max=0, eval_k=0), "k1": ArmSpec(1, 1), "k3":
ArmSpec(4, 3)}`. Adding an arm becomes one registry entry instead of edits
across three files and four functions — which is exactly the pattern that
already needed doing once for K=1 and will need doing again for E4's l0/
l0-shuffled arms.

2.3 A run index, not just a naming convention. Keep `data/outputs/runs/<id>/`
as the on-disk layout, but have `run_traj_train`/`run_text_train` append one
line to `data/outputs/runs/index.jsonl` when a run completes: run_id,
experiment_id (from the new registry, e.g. `"017"`), arm, split, seeds,
mean_route_auc, git_sha, timestamp. That index is what a
`scripts/build_results_table.py` reads to regenerate the Route-AUC/AUROC/
Accuracy/Brier comparison tables that currently get hand-copied into every new
experiment doc — removing the transcription-drift risk rather than just
managing it.

2.4 Run-ID convention. Tie the run ID to the experiment: `e2-armD-seed0`
rather than a free-text label like `pilot-20x1-v5-repair-llama8b-tail`. Several
existing runs already do something like this informally (`v3-smoke-k3`,
`v3-django-k0`) — this just makes it the rule rather than a habit.

3 Recommended durability plan (not applied)
---------------------------------------------

3.1 A durable store outside any VM's local disk. Recommended: a GCS bucket in
the same GCP project (`hecate-506120`) already used for `hecate-traj-l4` and
`hecate-exec` — no new vendor, `gcloud`/`gsutil` are already the toolchain in
`provision_traj_l4.sh` and `sync_exec_vm.sh`. Suggested name:
`gs://hecate-506120-artifacts` (confirm before creating — bucket names are
global). Enable object versioning (and ideally a soft-delete retention window)
so an overwrite or accidental delete is recoverable, not just an off-VM copy.

Suggested layout:

  gs://hecate-506120-artifacts/
    runs/<run_id>/           mirror of data/outputs/runs/<run_id>/ —
                              results.json, manifest.json, holdout_scores.jsonl,
                              checkpoints/, README.md
    data/raw/trajs/           archival copy of fetched trajectories, keyed by
                              provenance (s3|docent|hf|re-run) so a re-fetch is
                              never the only path back to this data
    data/cache/               frozen embeddings and other derived caches —
                              reproducible in principle, but cheap insurance
                              against re-paying the compute

3.2 Automate the copy; don't rely on remembering. Two layers, not one:

  - Push-on-completion: extend `run_traj_train` (and the text-runner
    equivalent) so that once `require_lora_checkpoint()` passes locally, the
    run directory is synced to `gs://.../runs/<run_id>/` as part of what "a
    run is considered complete" means — the same concept every experiment doc
    already states in prose (E1 §3.6, E2 §3.9, E4 §3.10, E5 §3.9), just
    enforced in code instead of left to a person.
  - Safety net: a periodic sync (cron or systemd timer on the training VM) of
    the whole `data/outputs/runs/` tree, in case a run's own push step is
    interrupted (VM preempted, script killed).

3.3 Make incompleteness fail loudly, not silently. `require_lora_checkpoint()`
already fail-closes on the local adapter + score.pt. Recommend a matching
check — either inline in the runner or a standalone
`scripts/verify_artifacts_synced.py` — that treats "trained locally but never
confirmed present in the bucket" the same way the docs already treat "no
persisted adapter": not a completed run. This is the direct fix for how v3's
adapters were lost: the requirement already existed in words, it just wasn't
anything that could fail a run.

3.4 Datasets, not just weights. `data/external/*.csv|json` (the joined labels)
are already tracked in git — good, no change needed there. The at-risk data is
`data/raw/trajs/` (fetched trajectories — gitignored, pulled from an external
source that may not be available forever) and `data/cache/` (embeddings —
regenerable but not free). Both belong in the same bucket under `data/raw/`
and `data/cache/` as above, so "keep the datasets" and "keep the weights" are
the same mechanism rather than two separate things to remember.

4 What this would take, if you decide to proceed
-----------------------------------------------------

Roughly independent pieces, in a reasonable order:

  1. Create the bucket and confirm its name/region (one gcloud command, needs
     your approval — bucket names are a real external resource, not something
     to guess).
  2. Registry generalization in `traj.py`/`traj_runner.py` (contained, unlocks
     K=1 cleanly and every future arm after it).
  3. Push-on-completion sync wired into the runners, plus the safety-net timer
     on the VM.
  4. The run index + `build_results_table.py`.
  5. `experiments/` directories + migrating E1–E5 into `spec.md` files,
     renumbering questions to `<experiment-number>.<n>` as part of the move.

None of this has been started. Let me know which pieces you want built, and in
what order — (2) and (3) are the ones that most directly prevent a repeat of
losing v3's weights, so I'd suggest those first if you want to prioritize.
