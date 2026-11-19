# TASK-001 compatibility report

Date: 2026-11-19. Implementation branch: `codex/task-001-qwen7b-codex`.
Implementation commit: `6c615e747eea1e02b1f7b10f000dd22f45f22a5e`.

## Verdict

**Compatible with declared limitations.** Qwen2.5-Coder-7B-Instruct can execute
through the Codex harness on Spark, read files, edit source with shell commands,
run a failing test, repair source and observe a passing test. Isolation and
independent grading are working. This is not a claim of out-of-the-box native
automatic tool calling or Codex `apply_patch` compatibility.

The three selected Tenacity training tasks all ran and were independently graded:
**0 resolved out of 3 evaluable tasks**. Each had exactly one coding-model
attempt. A saved patch from the first task was re-graded after correcting an
infrastructure/model-failure distinction; its coding agent was not rerun.
This is an integration smoke, not a representative completion-rate estimate or
an authorization to launch the larger baseline.

## Pinned setup

- Spark: ARM64 GB10; 119 GiB reported system memory; approximately 114 GiB
  available before inference and again after cleanup. One task at a time.
- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`, revision
  `c03e6d358207e414f1eca0bb1891e29f1db0e242`, BF16.
- Inference: existing vLLM 0.20.0 ARM image, exact image ID pinned in
  `configs/codex_qwen7b.yaml`; 16,384-token context, one sequence,
  temperature 0, top-p 1, seed 0, maximum 2,048 output tokens.
- Codex: official npm ARM package 0.164.0, SHA-512 integrity verified during
  installation; executable SHA-256 recorded per run.
- Runner: a fresh task-owned venv with httpx 0.28.1 and PyYAML 6.0.3. No
  shared E10 environment or checkout was changed.
- No advisor, M2, router, training step, hosted coding-model API or cloud VM.

## Compatibility evidence

Final verification: `task001-fixtures-attempt-09`, on the implementation commit.
All three capability fixtures passed:

1. **Read:** a real `exec_command` retrieved the known source marker.
2. **Edit:** the model changed source; separate containerized assertions verified
   addition on two input pairs.
3. **Test and repair:** recorded pytest failure, actual source edit, then recorded
   pytest success; tests remained unchanged. The fixture explicitly specified
   the intended subtraction-to-addition repair, so it measures plumbing rather
   than autonomous problem-solving ability.

The final isolation fixture also passed: no external network, no host-only marker
access, a one-commit repository without remotes, read-only `.git` and test files.
Agent containers had a read-only root filesystem, dropped capabilities and no
Docker socket/home-directory mount. Inference was available through a task-owned
Unix socket and container-loopback relay only.

Earlier unsuccessful attempts are retained. Automatic decoding produced printed
commands/tool-call text rather than executed calls. Constrained decoding made
function calls valid, but the custom patch fixture exhausted its budget with
invalid patch syntax. The accepted configuration therefore uses:

- `tool_choice=required` and explicit `hecate_finish(response)` mapped to a Codex
  final message;
- a declared shell-edit interface; `apply_patch` is not advertised upstream;
- no escalation-only shell parameters; forged escalation calls are rejected;
- 120-second command timeouts, with original arguments restored in model-visible
  history so timeout wrappers are not repeatedly copied into commands.

No text resembling a command is heuristically executed.

## Three-task smoke

The task selection was fixed before inference: lexical first three IDs in the
56-task E7 Tenacity training pool, with the source dataset SHA-256 recorded in
`configs/codex_qwen7b_tasks.json`. All overlap earlier advisor training; none are
from its reserved validation/evaluation pool. No result was used to select tasks.

- `jd__tenacity.0d40e76f.combine_file__4gcf36bk`: unresolved; 5 model requests,
  4 command completions, 20.65 seconds of agent execution. The patch broke imports,
  producing pytest collection errors. This is a model failure after validated
  controls, not missing evaluation infrastructure.
- `jd__tenacity.0d40e76f.combine_file__mged6jg2`: unresolved; 8 model requests,
  7 command completions, 50.64 seconds of agent execution.
- `jd__tenacity.0d40e76f.combine_file__oicq97rw`: unresolved; 4 model requests,
  3 command completions, 70.14 seconds of agent execution.

All three Codex agents exited normally with a final response and no test edits.
All three unpatched controls were unresolved and all three known-fix controls
resolved. Grading ran independently in fresh, networkless containers with hidden
tests restored only there. The agent saw a fresh working-tree export, not the
original bug/fix history.

Total agent execution time was approximately 141 seconds, excluding setup,
capability debugging, grading and artifact transfer. These short, unsuccessful
runs do not justify extrapolating a full-baseline runtime or solve rate.

Authoritative aggregate: `task001-smoke-attempt-04/results.json`. The first
agent's original execution is preserved in `task001-smoke-attempt-03` and reused
in smoke-04. Earlier smoke attempts stopped before coding-model execution due to
grader checkout/archive preparation issues. Native patch support and unconstrained
tool selection were not established.

**Artifact field caveat:** smoke-04's top-level per-task `exit_code` was overwritten
by the evaluator result in that iteration. Each task's `agent/result.json` has
the actual agent exit code (0). Final code keeps evaluator outcomes nested and
preserves the agent exit code. Final read-only-git hardening was verified in
fixture-09 after the three one-attempt benchmark episodes; those episodes were
not repeated to refresh provenance.

## Tests, artifacts and cleanup

- `tests/test_codex_compatibility.py` plus legacy `tests/test_execution.py`:
  **37 passed, 1 skipped** (the opt-in legacy live-evaluation test).
- Targeted static checks and Python compilation passed.
- Fresh Spark runner install and imports/CLI smoke passed. Model loading and
  all GPU work occurred on Spark, not the Mac.
- Fourteen run directories were copied to Scott's Mac under
  `data/outputs/runs/task001-*` and checksum-verified against the received source.
  Every copy has `sync_receipt.json`; includes failed attempts, final fixtures,
  smoke attempts, setup evidence, exact source/config snapshots, transcripts,
  model usage, patches, hidden-grader evidence and evaluator-only task records.
- Earlier integration iterations identify their baseline commit plus captured
  source/config evidence. Early failed fixture attempts 01–04 predate full source
  snapshot capture; they are diagnostic records, not accepted compatibility runs.
  Final fixture-09 identifies implementation commit
  `6c615e7`. No run directory was overwritten.
- TASK-001's inference container was stopped and removed. No task agent/grader
  container remained. The unrelated `diflh-ollama` service was left running,
  and approximately 114 GiB became available again. Model weights remain cached
  in the task-owned directory for a future approved run.

## Next decision

Review this smoke and its limitations before approving a larger baseline or
selecting M1. The integration works in the declared adapter mode, but 0/3 gives no
positive evidence yet that this model is a useful cheap tier. A different M1 or a
larger, separately specified baseline remains a research decision, not an automatic
next action.
