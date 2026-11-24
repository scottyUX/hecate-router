# TASK-007 — Separate saved-patch correctness from agent completion

## Description and authorization

Scott requested fixing the evaluation pipeline after TASK-006's independent audit
found10/20 correct saved source patches versus3 originally scored successes.
This specification precedes implementation. Review against the original records
and D3 establishes two concrete gates: added tests suppress grading and abnormal
termination suppresses grading. This is an explicit scoring-protocol amendment,
not a silent change to TASK-006 or previous results.

## Scope and requirements

- Correctness protocol `source-patch-v2`: independently grade every available
  saved patch after patched/unpatched controls, regardless of session termination.
- Keep the raw patch unchanged. Remove only newly added protected test/config
  file blocks from a separately persisted evaluation patch. Record excluded paths
  and SHA256 of both patches. Reject malformed/unsafe projection or edits/deletes/
  renames of existing protected files as ungradable, never an automatic failure.
  New tests never enter the evaluator. Source code is never repaired.
- Persist independent axes: correctness (`resolved`, nullable), evaluator status,
  session completion/termination, policy compliance, execution infrastructure
  failure, and clean success (correct AND completed AND policy compliant).
- Correctness must not erase execution failures. Consecutive infrastructure halt
  uses execution/evaluator failures even when their patches pass. Request/context
  budget exhaustion is an episode limit rather than an infrastructure failure.
- Gateway evidence must distinguish explicit context-limit HTTP400 responses,
  request caps, genuine protocol errors and server/transport failures, including
  the race where Codex exits before the polling stop callback sees the failure.
- Keep evaluator controls, missing tests and setup failures fail-closed. A saved
  patch that breaks imports/collection after valid controls remains a failure.
- Apply to the shared run_task path used by Codex and mini, without changing
  prompts, models, sampling, budgets, fixture gates or protected file isolation.
- Summaries/progress expose correctness, policy, completion and infra separately;
  legacy summaries retain their original semantics when reading old artifacts.
- Regrade all20 immutable TASK-006 attempts through the production pipeline in a
  new run, using checksummed agent reuse only; generate zero model calls. Mirror
  all artifacts off Spark, retain old runs and compare per-task verdicts to D3.
  Replay must fail closed if a saved attempt is missing, never generate a fallback
  attempt. Historical execution errors do not stop replay because no inference is
  occurring; new evaluator infrastructure failures still trigger the halt rule.
  Historical HTTP400s whose response bodies were not retained stay conservatively
  classified; only explicit saved request-cap evidence is relabeled automatically.

## Schema

Each v2 task result contains `evaluation_protocol`, `resolved: bool|null`,
`status`, `evaluation`, `termination_reason`, `session_completed: bool`,
`policy_compliant: bool`, `execution_infrastructure_failure: bool`,
`clean_success: bool`, `patch_projection` (original/evaluation SHA256 and
excluded paths). Unsupported projection has an explicit error and null correctness.
`status` describes evaluation, never substitutes for termination or policy.

## Edge cases

Empty patch: grade the unmodified workspace. Missing patch: unknown, not fail.
Added tests only: omit them and grade the resulting empty patch. Existing protected
test/config edits: unknown projection, retain evidence. Binary source patches:
retain verbatim. Unsafe paths or ambiguous headers: fail closed. Model error after
a correct patch: correct=true, completed=false. Server failure after a correct
patch: still counts toward the infrastructure halt. All-null usage remains null.

## Acceptance criteria and tests

1. Regression tests cover correct patch + new test, correct patch + abnormal
   termination, broken/empty patch, missing patch, protected file changes and
   evaluator failures, with raw artifacts unchanged.
2. Gateway tests cover context400 versus unrelated400, request cap race and server
   errors; halt tests cover passing patches with infrastructure failures.
3. Summaries distinguish patch correctness from clean successes on TASK-006.
4. Production replay matches all20 D3 verdicts without regenerating agents, with
   immutable manifests, source/config snapshots, hashes and off-Spark receipt.
5. Relevant existing compatibility/mini tests and new regressions pass.

## Out of scope

Increasing context, fixing model patches, restarting inference, selecting new
models or benchmarks, changing historical scores in place, publishing/deploying.

## Verification and outcome

Runtime commit `6bad9d0`, replay `task007-task006-source-v2-replay-01`:
20/20 graded,10pass/10fail,0ungraded. Every per-task verdict and projected-patch
hash matches D3. All20 copied agent artifact trees match their immutable originals;
the replay generated zero model attempts.361 checksum files were verified off
Spark; receipt copied back. Only the unrelated diflh-ollama container remains.

Completion clarification: the initial acceptance wording incorrectly anticipated
three clean successes from the original three graded passes. Raw evidence shows
lm_rewrite__3rty13vw ended at budget_exhausted. The unchanged rule (correct AND
normally completed AND policy compliant) gives **two clean successes**, ten
normally completed sessions, and five policy violations. This corrects the
expected count, not the definition of success. Historical context-error records
without response bodies conservatively retain execution-error classification;
they do not affect independently verified correctness.

Validation:66 compatibility/mini/evaluation tests passed across targeted runs,
plus16 external-label compatibility tests. Ruff F checks and diff checks pass.
The production replay tested the actual runner and Docker evaluator, not the
diagnostic-only script. Original results were not overwritten.

Local evidence: `data/outputs/runs/task007-task006-source-v2-replay-01/` and
`data/outputs/task007-replay-validation.json` in the main checkout.
Implementation and runbook live on branch `codex/task-007-evaluation-correctness`
in `/private/tmp/hecate-task007`; no unrelated main-workspace changes were edited.
