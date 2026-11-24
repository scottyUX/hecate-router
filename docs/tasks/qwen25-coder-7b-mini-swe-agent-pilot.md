# TASK-003 — Qwen2.5-Coder-7B with mini-SWE-agent

## Description and authorization

Scott requested running 7B in mini-SWE-agent in parallel with the ongoing
TASK-002 Codex experiment (2026-11-19). This authorizes this additional arm.
The question is whether the poor 7B result depends on the execution harness.
This is a diagnostic on training tasks, not a held-out benchmark result.

## Specification and requirements

- Same ordered 20 task IDs and dataset hash as TASK-002; no replacement tasks.
- Same pinned 7B revision, BF16, 16,384 context, temperature 0, top-p 1,
  seed 0, 2,048 output tokens/request, 40 requests, 2,700 seconds/task,
  120 seconds/command, 360 seconds/request and two transport retries.
- Actual upstream mini-SWE-agent v1.0.0 core at commit
  `a2b0efee5fd9c1d3bc9fdfc6fe88036a2235d74d`, historically packaged as
  `microsweagent`. Unmodified core, prompts and license are vendored with hashes.
  Hecate adapters supply local Chat Completions and isolated Docker shell execution.
  No advisor, router, function-tool forcing, or hand repair of model outputs.
- Same task-tree isolation, read-only test/config files and Git metadata,
  no shell network, and independent corrected TASK-002 evaluator. Gold and
  unpatched controls must pass first. Grade the final patch even after budget
  exhaustion; preserve failures as failures, not silent replacements.
- Persist raw model responses, usage, messages, command outputs, patches,
  control/evaluator outcomes, config/code/dependency snapshots and manifest.
  Copy and checksum-verify artifacts off Spark before calling the run complete.

## Parallel execution amendment

The explicit user request permits concurrent execution of our own TASK-002
14B and TASK-003 7B workloads. It does not authorize touching other workloads.
Only permit the already identified TASK-002 model GPU process alongside this
server. Reserve 20% unified memory for TASK-003 rather than TASK-002's 35%;
record this serving difference. Context, precision and request budgets stay fixed.
Before launch, require at least 32 GiB physically free and 48 GiB available.
If needed, evict only clean cached pages of our own downloaded 7B weight files
using `posix_fadvise(DONTNEED)`; no sudo, global cache drops or file deletion.
If the guard fails, prepare the arm and defer GPU launch rather than disrupt 14B.
Do not compare latency or throughput between concurrent and sequential runs.
No further concurrent GPU workload may be started by this experiment.

## Edge cases

Malformed bash output uses upstream format-error feedback and consumes a request.
Truncated completions are logged and consume the same budget. Context overflow,
transport failure, grader failure and model-budget exhaustion stay distinguishable.
The pr_390 collection-error control uses TASK-002 A1's verified-gold rule.
Stop after three consecutive infrastructure failures, preserving every record.
Never regenerate an existing agent attempt when repairing grading.

## Acceptance criteria and tests

1. Vendored hashes match the pinned upstream files.
2. Fresh adapter environment imports the upstream agent successfully.
3. Unit checks cover bash parsing/submission, command timeout, model request
   budget, immutable tests/Git bindings and concurrent-server resource guards.
4. Live capability fixture reads, edits and tests a small source file before
   benchmark attempts; host isolation is checked inside the shell sandbox.
5. All 20 records are retained, with solved/unsolved/infrastructure counts and
   paired outcomes against 7B Codex; no causal claim beyond this harness setup.
6. Task-owned containers stop after completion and artifacts have off-Spark receipts.
