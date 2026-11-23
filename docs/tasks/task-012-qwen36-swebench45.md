# TASK-012 — Qwen3.6 + Codex on the full SWE-bench-45 (paper comparison)

Status: draft for Scott's review. No code, image build or model call yet.

## Request and purpose

Scott asked to run all 45 SWE-bench-45 tasks with Codex CLI and Qwen3.6-35B-A3B
on Spark and compare against When Agents Fail: Model or Harness—Who's to Blame?
(arXiv:2610.32483v1). TASK-010/011 ran ten tasks once each as development
pilots. Their attempts are not pooled with TASK-012, and django__django-16560 is
already an exposed development case.

## Paper targets (Qwen3.6-35B-A3B + Codex CLI, SWE-bench-45, R=4)

| Metric | Paper | Source |
|---|---|---|
| Mean-of-4 | 26.67% (48/180 attempts) | Table 13 |
| Best-of-4 | 44.44% (20/45 tasks) | Table 13 |
| Valid completion rate (VCR) | 98.33% | Table 14A |
| Token load per attempt | 4.770M | Table 30 |
| Tokens per success | 17.889M | Table 30 |

The paper does not give instance IDs, per-task outcomes, Qwen serving, sampling,
context, Codex version, tool adapter or SWE budgets. Our values for these are
declared replication choices, not claimed paper settings. "Matching" means our
estimate's 95% task-cluster bootstrap interval contains the paper value. A single
45-task run cannot show anything finer than that.

## Scope

1. Exact 45 IDs from `configs/kimi_codex_swebench45_tasks.json` (dataset revision
   c104f840, parquet hash pinned). Four independent attempts per task: 180 scheduled.
2. 42 ARM-compatible tasks run on Spark. The three x86-only tasks
   (pydata__xarray-3993, pydata__xarray-6992, sympy__sympy-14248): decision D2.
3. All scheduled attempts stay in the denominators. Setup/evaluator unknowns are
   reported separately and also scored as unresolved in the paper-comparison
   column (the paper's "all scheduled attempts enter the averages").

## Frozen protocol (inherits TASK-011 at 8499c1a unless stated)

- Qwen/Qwen3.6-35B-A3B rev 345d467b, BF16, pinned vLLM 0.20 image, qwen3_coder
  parser, native 262144 context, single-system-prefix layout, native prompt profile.
- Codex 0.164.0 (linux-arm64, pinned hash), apply_patch via function-tool adapter
  with native grammar preserved, gateway recovery enabled (at most 3 per request).
- Sampling 0.6 / top_p 0.95 / top_k 20, max output 8192 tokens.
- Budgets: 200 model requests and 3600 s per attempt, 120 s per command, 600 s
  per request, 2 transport retries. Evaluator swebench 4.1.0, 900 s timeout.
- **Change: per-repetition seed.** TASK-010/011 send `seed: 0` on every request.
  vLLM then samples identically for identical prompts, so four attempts would
  largely replay one trajectory and Best-of-4 would be meaningless. Attempt r
  (0..3) uses seed r. Recorded in each attempt manifest.
- Each attempt starts from a fresh original-base workspace. No network in task
  containers, no host secrets or Docker socket, gold/test patches hidden.

## Phases

**Phase A — preflight, no model calls.** For each of the 42 ARM tasks: build the
official arm64 environment/instance images, prepare the offline wheelhouse, and
run the unpatched and reference-patch controls once. Write one control record per
task. Known exceptions are carried over unchanged: Astropy 13398's
setuptools==68.0.0 pin, Pylint 4551's collection-error negative control, and
scikit-learn 25102's pip==24.0/setuptools==68.0.0 environment. Any new
ARM/build failure is preserved with its log and listed for Scott. No silent
patching, no dropped tasks, and no further per-instance exception without
approval. This phase needs CPU and disk only, so it can run while the TASK-011
model run is still going.

**Phase B — gate.** Rerun the TASK-011 native gate (injected/live recovery,
read, edit, repair, apply_patch) on the TASK-012 config. Stop if it fails.

**Phase C — attempts.** Repetition-major order: all tasks at r=0, then r=1, etc.
That way a partial run still yields a complete Mean-of-1 over 45 tasks. Resume
reuses checksum-verified attempts and never regenerates one. Every 15 attempts,
copy the checkpoint off Spark and verify it. Stop on a failed gate, resource
failure, or 3 consecutive infrastructure faults. Unsolved tasks are normal and
do not stop the run.

**Phase D — scoring and report.** Per-attempt rows record termination, patch
hash, patch applied, strict status, `official_resolved` (already written by
`grade()`), valid completion, requests, tokens and wall time. Report:
- Mean-of-4 and Best-of-4 computed both ways (official label with unknowns =
  unresolved, as in the paper; strict label with unknowns separate).
- VCR, token load and tokens per success.
- Each metric for 45 tasks and for the 42 ARM tasks, with 2,000-replicate
  task-cluster bootstrap 95% intervals.
- A per-repository table and every deviation from the paper.

## Declared deviations from the paper

Spark ARM64/vLLM serving rather than the paper's (unstated) Qwen serving. Gateway
recovery and the function-tool apply_patch adapter are needed because plain Codex
had Qwen output failures in TASK-010 (3 of 4 graded cases), while the paper
reports Qwen terminating normally in all Codex runs. Plus our own budgets, our
own sampling, and the x86 handling from D2.

## Decisions for Scott (proposed defaults in bold)

- D1 Repetitions: **all 4 (180 attempts)**, or stop after r=0 (45 attempts) and review.
- D2 x86 tasks: **run on hecate-worker (x86 GCP) with the same model endpoint
  tunneled from Spark**, or score them as not run (unresolved in the paper column).
- D3 Concurrency: vLLM runs with `--max-num-seqs 1`. Measured TASK-011 attempts
  took 1.5–25+ minutes, which puts 180 attempts at about 75 h sequential.
  **Allow 3 concurrent attempts on one server after a throughput check**, or stay
  sequential.
- D4 TASK-011: **let it finish its ten tasks** (it reuses the same images), or
  stop it to free the Spark.

## Acceptance criteria and tests

- Tests: exact 45-ID scope and per-repo counts; repetition-major scheduling;
  per-repetition seed reaches the request payload; resume never re-calls the
  model for a saved attempt; Mean/Best/VCR math with unknowns handled both ways;
  bootstrap is deterministic under a fixed seed; legacy TASK-010/011 configs unchanged.
- Phase A: 42 control records (pass or documented failure) before any attempt.
- Completion: 180 attempt records or explicit blocked/unknown records, a
  verified off-Spark copy, and a results table against the paper targets.
- No run starts until code and config are committed; owned servers are stopped on exit.

## Sources

- https://arxiv.org/html/2610.32483v1 (Tables 13, 14, 30; Appendix A.1–A.3)
- docs/tasks/task-008-kimi-codex-swebench45.md (task selection and manifest)
- docs/tasks/task-010-qwen36-ten-task.md, docs/tasks/task-011-gateway-recovery.md

## Approval and implementation record

Scott approved the proposed defaults D1–D4 on 2026-11-22.

Implementation (`scripts/run_qwen36_swebench45.py`, `configs/qwen36_swebench45.yaml`):
- **Modes:** `preflight` (Phase A), `gate`, `schedule`, `attempt`, `score`.
  `schedule` starts each attempt as its own process because the SWE-bench builders
  and grader write relative to the working directory. It runs at most
  `checkpoint_attempts` (15) new attempts per invocation, three at a time, and
  refuses to start while any finished attempt lacks an off-Spark receipt.
- **Serving:** `--max-num-seqs` now comes from `serving.max_num_seqs`. It defaults
  to 1, so earlier configs serve unchanged. TASK-012 uses 3 on port 8136 with
  container `hecate-task012-model`.
- **Images:** all images use tag `task012`. Docker's layer cache reuses the
  identical TASK-009/010/011 build steps.
- **Halt rule:** an evaluator "unknown" that the official verifier still scored
  does not count toward the three-consecutive-infrastructure-failure halt. Only
  missing official outcomes, infrastructure failures and interruptions do.
- **Off-Spark copy:** `scripts/mirror_task012.py` runs on the Mac. It copies each
  finished run except `workspace/` (the agent's final checkout, about 80 MB per
  attempt, reproducible from base commit + `agent/patch.diff`, kept on Spark).
  The Mac has 36 GiB free. Every other checksummed file must match before a
  receipt is written back to Spark.
- **Deferred:** D2's x86 path on hecate-worker is not built yet. It is a separate
  step after the 42 ARM tasks are running. Until then `score` counts the three
  x86 tasks as unresolved in `all_45` and also reports `arm_42`.

## Amendment 1 — Astropy build pin for all versions (approved 2026-11-22)

Preflight of astropy__astropy-14369 failed the image-tree check: its official
image commits the same one-line `requires = ["setuptools==68.0.0",` change in
`pyproject.toml` that TASK-011 approved for Astropy 5.0 only. Scott approved
accepting that exact change for any Astropy version. Any other change, or any
other file, still fails. The agent still receives the dataset's original base.
The failed record `task012-control-astropy__astropy-14369` is kept. A rerun after
an approved fix writes `task012-control-<id>-retry-NN` and records which record
it supersedes (`preflight --retry <id>`). Attempts use the latest control record.

## Harness fix — git auto-gc race (before any model call)

Preflight of django__django-10554 failed with `No such file or directory: 'gc.pid'`.
The workspace export's commit started a detached `git gc --auto`, which was
still writing while the export check was deleted. The same race could change
an attempt's `.git` after its checksums were taken. The runner and its attempt
processes now set `gc.auto=0` through `GIT_CONFIG_*`. Task containers and grading
are unaffected. Preflight was stopped and restarted. The failed (10554) and
interrupted (11138) records are kept and superseded with `--retry`, as is
astropy-14369 under Amendment 1.

## Amendment 2 — Controls follow the paper's official verifier (approved 2026-11-22)

Scott asked for controls to match the paper. The paper grades with the official
verifier, which counts a required test with no reported status as not passing.
django__django-10554's unpatched run crashes Django's test runner inside
`printErrors` (`DatabaseError: ORDER BY term does not match any column...`), so
its two FAIL_TO_PASS tests never report. Our strict grader marked that unknown,
while the official verifier marks it unresolved.

New TASK-012 control rule, replacing per-instance exceptions such as Pylint 4551:
- The reference patch must pass under both the strict and the official grader.
- The unpatched run must be officially unresolved, with no timeout and no
  offline-setup error. It must either fail its required tests, or leave required
  tests without a status while the evaluator's test markers are present.

Candidate grading is unchanged. The paper column uses the official label, and the
strict column keeps unknowns separate.

## Amendment 3 — Official image recipe replay (approved 2026-11-22)

The full preflight at dd81002 passed 37 of 42 ARM controls. All five Sphinx tasks
(7590, 8548, 9229, 9461, 11510) failed the image-tree check because their
official images commit SWE-bench's own pre_install edits: dependency pins in
`setup.py` and `pytest -rA` in `tox.ini`. The paper ran in these same images.
Scott approved one general rule in place of Amendment 1's Astropy-specific check:
- An image tree that differs from the base is accepted only if replaying the
  pinned swebench 4.1.0 `pre_install` source edits (`sed`/`grep` commands only)
  on the base commit, in a scratch worktree, reproduces the image tree exactly.
- Anything else fails closed, including package-install steps, which cannot run
  offline.
- The replayed commands and changed files are recorded in the export provenance.
  The agent still receives the dataset's original base.

## Amendment 4 — D4 changed: TASK-011 closed at batch 1 (approved 2026-11-22)

TASK-011 finished batch 1 (5 tasks). Batch 2 halted at case 06, where
sphinx-8548's control hit the same image-tree check. Scott chose to close
TASK-011 there rather than port this fix and finish it. TASK-012 reruns all
of those tasks four times. TASK-012 now takes the GPU.

## Amendment 5 — Exclude sphinx-7590 and sphinx-8548 (approved 2026-11-22)

After Amendment 3, both tasks passed the image check but their reference patch
fails: `No module named 'docutils.utils.roman'`. Fresh ARM builds install
docutils 0.23, while the official x86 images (inspected without running) have
0.21.2. Scott chose exclusion over pinning. They are listed in `excluded_ids`,
are never scheduled, and score as unresolved in `all_45`. `score` also reports
`runnable_40` (ARM tasks with usable controls) and `arm_42`.

Saved records are now validated against the protocol configuration, excluding
scheduling-only keys (`excluded_ids`, `concurrency`, `checkpoint_attempts`).
Adding the exclusion therefore does not invalidate earlier controls. Any model,
serving, sandbox, limit or evaluator change still fails validation.
