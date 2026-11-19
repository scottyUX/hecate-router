# TASK-006 — Qwen3-Coder-30B-A3B-Instruct in Codex on Spark

- **Status:** Authorized for implementation, compatibility fixture and the fixed20-task pilot.
- **Date:** 2026-11-19.
- **Authorization:** Scott requested running `Qwen/Qwen3-Coder-30B-A3B-Instruct` in Codex in parallel with the ongoing14B mini-SWE-agent arm. This authorizes local preparation, download, compatibility checks, the same20 training tasks, independent grading and artifact mirroring. No paid API or model training.

## Description

Screen a stronger candidate for economical model M1 with the existing Codex execution
path. Retain the TASK-002/005 outcomes unchanged. This is a new model/compatibility
arm, not a claim that larger parameter count guarantees better routing performance.

## Specifications

- Exact model `Qwen/Qwen3-Coder-30B-A3B-Instruct`, revision
  `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`, BF16 (30,532,122,624 parameters).
  No silent substitution with the FP8/AWQ checkpoint.
- Pinned existing ARM vLLM0.20 image and Codex0.164.0, same sandbox/evaluator.
- Same ordered20 TASK-002 training IDs and source hash, no replacements.
- Context16,384; temperature0, top_p1, seed0;2,048 output tokens/request;
  40 coding-model requests/task;2,700s episode,120s command,360s request,
  two transient transport retries. Independent control grading as already corrected.
- Native `qwen3_coder` tool parser with auto tool choice, explicit shell editing.
  This is a declared model-specific interoperability change relative to TASK-002's
  schema-constrained required-tool workaround; do not claim perfectly identical
  decoding across model arms. No protocol/prompt fallback after pilot results.
- Read/edit/test-repair + isolation capability gates must pass before the20 tasks.
- Preserve every request, raw output, command, patch and outcome. Stop after three
  consecutive infrastructure errors. One attempt/task; regrade saved patches if
  evaluator correction is required, never regenerate for a better score.

## Parallel preparation and memory guard

Download/configuration proceed alongside TASK-005. GPU inference may overlap only
if a documented resource guard permits it without changing existing14B settings.
BF16 weights alone are about56.9GiB; the standalone server reserves65% of119GiB.
Require90GiB physically free and100GiB available before its GPU launch, and reject
any active GPU process. With the current14B server this guard cannot pass, so queue
inference until14B finishes; explicitly report this practical deviation from the
requested overlap. No model quantization is introduced just to force concurrency.

Before launch evict only clean cached pages of task-owned7B/14B/Qwen3 snapshots
using posix_fadvise(DONTNEED), never delete weights or drop caches globally.
While loading, periodically advise eviction of this task's own Qwen3 weight cache
to avoid holding a second full copy in unified memory. No sudo or other workloads
are touched. Preserve `diflh-ollama`. Stop the task-owned server on exit.

## Requirements and edge cases

- Reuse pinned assets/code with commit snapshots and task-owned roots, ports and logs.
- Scope validation must explicitly admit TASK-006 with the fixed TASK-002 selection;
  existing TASK-001 smoke/TASK-002 gates remain unchanged.
- Unsupported Qwen3 parser/kernel, OOM, failed fixture or context/tool mismatch:
  preserve the failed run and report; no silent precision/parser/model changes.
- Unknown usage and infrastructure outcomes remain missing, not invented zeros.
- No hidden evaluator inputs enter the coding sandbox. Same protected tests/Git,
  no shell network, no host home/Docker socket and source-only edits policy.
- If measured runtime projects beyond the lab's one-hour notice threshold, obtain
  the scheduling notice before starting the long pilot; no external message is sent
  automatically. Read-only setup and fixtures can complete first.

## Acceptance criteria and tests

- [ ] Source/config/task manifest and exact model revision recorded before inference.
- [ ] Scope/parser/launcher configuration checks and existing compatibility tests pass.
- [ ] Fresh runtime environment and pinned binary/model artifacts verified.
- [ ] Spark memory preflight and read/edit/repair/isolation fixtures pass.
- [ ]20 selected task records retained with solved/unresolved/infra denominators.
- [ ] Raw artifacts, code and metadata checksum-mirrored off Spark.
- [ ] Task-owned server stopped and result compared descriptively to prior arms.

Tests cover scope isolation, exact20 selection, model identity, no precision/parser
fallback, command/result lifecycle, corrected grading and mirror integrity. Timing
must disclose any actual GPU overlap, model-specific decoding and setup differences.

## Diagnostic regrade D1 — authorized 2026-11-19

Scott requested a manual pass/fail check of the first three attempts rejected for
new test files. Preserve the automated policy rejections unchanged. For only
combine_file__s0bcdks5, combine_module__yjmtlc2r and func_basic__7azvfd3s, derive a
separate patch by removing exactly the new-file blocks for the recorded rejected
test paths; do not repair or otherwise modify source hunks. Rerun patched/unpatched
controls and independently grade that saved source-only patch in a fresh evaluator.
No new model attempts, prompt changes, budget increases or ongoing-run mutation.
Record original/derived hashes, excluded paths, evaluator outcomes and durable
artifacts under a distinct diagnostic run ID. Report this as correctness of the
saved source edits with added tests excluded, not a revised official pilot score.

D1 outcome: **1/3 source-only patches passes**, after fresh patched/unpatched
controls and with only the added test files excluded. Wait strategies: fail
(121 passed,2 failed,1 skipped), due to an off-by-one wait_chain index.
AsyncRetrying: fail (122 passed,1 failed,1 skipped), due to RuntimeError in
__iter__ where TypeError is required. stop_never: pass (123 passed,1 skipped).
Original policy scores remain unchanged. Run `task006-source-only-diagnostic-01`
is checksum-mirrored off Spark (30 files), with hashes for original/derived
patches, excluded paths, controls and complete pytest logs. No new model calls.

## Diagnostic regrade D2 — authorized 2026-11-19

Scott requested checking all eight attempts from the earlier snapshot. Audit
exactly the first eight selected tasks, including the existing solve, three
unresolved patches, three new-test-file rejections and one context/gateway error.
Regrade saved patches only; exclude only added rejected test blocks as in D1.
Reuse D1 evidence only after full checksum/config and original/derived patch-hash
verification; independently evaluate other saved patches with fresh controls.
Keep all automated outcomes unchanged and report diagnostic correctness separately.
