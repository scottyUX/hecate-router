# TASK-002 — Paired 20-task Qwen2.5-Coder size pilot in Codex

- **Status:** Authorized; protocol recorded before pilot inference.
- **Date:** 2026-11-19.
- **Authorization:** Scott requested: “lets run 20 on Qwen2.5-Coder-7B and Qwen2.5-Coder-14B-Instruct.” This authorizes local setup, necessary runner changes, capability checks, 20 model attempts per arm, independent evaluation, artifact copying and reporting. No advisor/PPO/M2 experiment, paid API, or website deployment.

## Description

Compare the 7B and 14B instruction-tuned Qwen2.5-Coder models on the same 20
fresh Tenacity training tasks in the existing restricted Codex harness on Spark.
Determine their observed completion rates, tool/lifecycle failures, latency and
inference work before choosing M1. This is a model-screening pilot, not a test of
PPO routing or a population-wide resolution-rate estimate.

## Specifications

- Configurations: `configs/codex_qwen_size_pilot_7b.yaml` and
  `configs/codex_qwen_size_pilot_14b.yaml`.
- Models/revisions: 7B `c03e6d358207e414f1eca0bb1891e29f1db0e242`;
  14B `aedcc2d42b622764e023cf882b6652e646b95671`.
- Both BF16; existing pinned ARM vLLM 0.20.0 image and Codex 0.164.0.
- Shared 16,384-token context; greedy temperature 0, top-p 1, seed 0;
  maximum 2,048 output tokens per request.
- Shared schema-constrained tools with explicit finish action and shell editing.
  No claim of native unconstrained tools or validated `apply_patch` support.
- Shared task limits: 40 model requests, 45-minute episode cap, 120-second
  command timeout, 360-second upstream-request timeout and at most two transient
  transport retries. The longer request timeout, applied to both arms, allows
  slower 14B decoding without silently favoring 7B.
- Run sequentially: fresh 7B capability checks, 7B pilot, stop its model server;
  fresh 14B capability checks, 14B pilot, stop its model server. No concurrent
  coding sessions, experiment training or model servers.

## Task selection

The fixed manifest is `configs/codex_qwen_size_pilot_tasks.json`, including the
training-source SHA-256, seed, exclusions, ordered IDs and type counts. Draw from
the 56 E7 Tenacity training tasks; exclude the three already used in TASK-001.
Within each bug type, shuffle lexically sorted IDs with Python Random(0), then
round-robin across lexically ordered types until 20 are selected. The composition
is 3 combine_file, 1 combine_module, 4 func_basic, 3 control-flow invert-if,
3 control-flow shuffle, 3 lm_rewrite and one each of pr_390/pr_406/pr_425.

This deliberately covers all nine available types rather than matching their
population proportions. Both arms receive the exact same ordered IDs and fresh
isolated working trees. All are training-pool tasks and overlap earlier advisor
training; no advisor is used here. The validation/final evaluation pool is not
read or used. Selection precedes every new pilot outcome and never uses solve
labels. The three TASK-001 outcomes are not reused as pilot observations.

## Requirements

1. Preserve TASK-001 code/provenance and all prior artifacts. New source, logs,
   run IDs and model-server container belong to TASK-002. Reuse only pinned
   read-only tool assets and the explicit model cache, not mutable sibling code.
2. Recheck Spark memory, disk and active jobs before serving each model. Leave
   the unrelated Ollama service and other users' resources untouched. No sudo,
   shared-environment changes or cloud compute. If a long job exceeds the lab's
   one-hour announcement threshold, obtain the required scheduling notice before
   continuing; no unsolicited messages are sent by the runner.
3. Require matching passing read/edit/test-repair and isolation fixtures per arm.
   A failed gate blocks that arm; do not change prompts/sampling after inspecting
   pilot outcomes to improve its score.
4. Hidden tests and reference patches remain evaluator-only. Agent sees a clean
   one-commit task tree, read-only git/test files, no external network, host home
   or Docker socket. Independent patched/unpatched controls must pass before
   scoring each task.
5. One coding-model attempt per selected task per arm. Log transport retries
   separately. If evaluation code needs correction, re-grade saved patches;
   do not regenerate model attempts or select replacement tasks after outcomes.
6. Record every task and failure. A budget-exhausted episode's saved patch can be
   graded. Source-only policy violations are unresolved outcomes, not dropped
   observations. Infrastructure failures remain explicitly separate. Continue
   isolated failures; halt after three consecutive infrastructure errors to avoid
   consuming an entire arm on a broken environment.
7. Persist per-task results immediately, plus complete manifests, source/config
   snapshots, model usage, tool events, diffs and grader evidence. Verify a copy
   off Spark before considering each arm complete. Stop owned model servers on
   success, failure or interruption.

## Measurements and interpretation

- Primary descriptive result: resolved out of the fixed 20 selected tasks for
  each arm, accompanied by attempted, evaluable, unresolved and infrastructure
  failure counts. Also report resolved/evaluable when errors make these differ.
  Errors are not silently asserted to be code failures or silently dropped.
- Pairwise counts: both solved, 7B-only, 14B-only and neither, on mutually
  evaluable tasks; show exact task IDs for differences.
- Timing: agent wall time and inference wall time per task, totals and medians;
  token counts, requests, retries, tool events and termination reasons.
- Local inference has zero provider API charges; time/compute is not free.
- With one seeded execution per task and a balanced diagnostic sample of 20,
  use descriptive comparisons. Do not claim statistical superiority or a precise
  overall Tenacity success rate. Do not choose a model from parameter count alone.
- No minimum success threshold or M1 selection is imposed retroactively. A zero
  or disappointing result remains the result. Any follow-up is separately reviewed.

## Edge cases

- Invalid/truncated calls, long context, OOM, serving errors or evaluator failures:
  preserve evidence and classify distinctly; no model/precision/context fallback.
- Read-only test mutation attempts fail; a newly created test/policy violation
  invalidates the model solution and is counted unresolved.
- Missing test reports remain infrastructure errors. Explicit patch-induced
  collection errors after passing controls count as unresolved.
- A task failure does not select a substitute task. Interrupted partial arms
  resume from checksum-verified saved agent attempts under a fresh run ID.
- If the 14B capability gate fails, report the block; do not present it as 0/20.
- Existing unrelated local edits and previous experiment outputs are preserved.

## Acceptance criteria

- [ ] Fixed, identical 20-ID manifest, configurations and protocol recorded before inference.
- [ ] Generalized pilot runner retains TASK-001's three-task smoke guard and enforces the new 20-task scope.
- [ ] Offline selection, failure-accounting and resume tests pass; existing compatibility tests remain green.
- [ ] Per-arm capability/isolation gates pass using the shared interface.
- [ ] Both arms contain 20 selected task records, with no hidden replacements or repeated generation.
- [ ] Independent grading and all failures/denominators are documented.
- [ ] Source, manifests, events, patches and results have verified off-Spark copies.
- [ ] Both owned servers are stopped, shared workloads preserved, and a paired report is written.

## Tests

- Deterministic selection: exactly 20 unique training IDs, disjoint from the prior
  smoke IDs and covering the recorded nine types; identical manifest for both arms.
- Scope guards: smoke still requires three tasks; pilot requires TASK-002 and
  exactly 20; malformed or mismatched selection/configuration fails before inference.
- Continuation: retain one-off infrastructure failures, halt at three consecutive,
  keep model failures and policy violations distinct from infrastructure errors.
- Resume: validate source checksums/configuration and reuse saved agent outputs
  without re-running those agents. Preserve attempt IDs and evaluator/agent statuses.
- Live: per-model capability/isolation checks, independent controls and the paired
  20-task runs under the fixed settings. No tuning on pilot outcomes.


## Grader amendment A1 — recorded during the first pass, before corrective execution

The selected `pr_390` unpatched control aborts collection with a source NameError;
its known-fix control passes all named tests. PASS_TO_PASS is empty and the dataset
labels the entire suite FAIL_TO_PASS. Requiring individual failed node IDs from an
aborted collection incorrectly treats this expected bug behavior as infrastructure
failure. No coding-model attempt has occurred for that task at detection.

Correct the grader narrowly: after a verified passing gold control, accept explicit
pytest collection errors as an unresolved unpatched control only when PASS_TO_PASS
is empty. Preserve missing node outcomes as missing; do not fabricate test statuses.
With nonempty PASS_TO_PASS, unknown output, missing gold validation or unrelated
runner errors, remain fail-closed. Model patches that break collection after valid
controls continue to count unresolved, as previously specified.

Keep the active first-pass source unchanged for both arms. After it completes, run
a corrected continuation per arm using checksum-verified saved agent artifacts.
Re-evaluate saved patches, generate only selected tasks which never reached an
agent, and never regenerate prior model attempts. Both arms use the same corrected
grader for final reporting. Disclose any resulting task execution-order difference;
models, task IDs, prompts, tool interface, budgets and sampling remain fixed.


## Accounting amendment A2 — fixed output-budget/model failures

The first-pass `pr_406` request reached the local model but produced no complete
action; its gateway reports “Missing, ambiguous or truncated completion” and the
7B server records one `finished_reason=length`, zero server errors and zero aborts.
The original bridge classified all protocol failures as infrastructure failures.
A model exhausting the fixed output-token budget is instead a model-budget event,
not a serving outage: grade its saved patch (including an empty patch) under valid
controls. Do not retry generation, raise the token budget, repair partial JSON or
change the model prompt. Other model-generated invalid actions are retained as
model-output failures; unsupported incoming Codex contracts and transport/serving
failures remain infrastructure errors.

For corrective continuations, preserve successful and failed raw upstream output
before translation and record usage for failed completions. For historical
first-pass failures with that exact recorded completion error, reuse the original
agent attempt and record its original classification, missing raw-output caveat
and unknown token usage. Recover elapsed request wall time from the saved request
and error timestamps, explicitly marked as derived. No model call is regenerated.
Apply the same accounting rule to both arms; final comparison discloses missing
token accounting and any continuation-order effects. Active first-pass source is
left unchanged until its sequence ends.

## Grader amendment A3 — singular and plural collection summaries

During the 14B first pass, `func_basic__1avsmufn` passed both evaluator controls,
then its saved model patch renamed an exported function and broke a test import.
Pytest reported `1 error during collection`. The grader recognized only the plural
`errors during collection`, incorrectly recording an infrastructure failure.

Recognize both positive-count singular and plural pytest collection summaries
under the existing validation requirements. A model patch that breaks collection
after passing controls remains unresolved; an unpatched collection failure still
requires a verified gold control and empty PASS_TO_PASS. Other missing test reports
remain evaluator failures. This corrects spelling-dependent accounting and does
not change the decision rule, tasks, model attempts, prompts or budgets.

Regression tests cover singular/plural summaries in both validated model-patch and
verified-gold unpatched-control paths. Regrade immutable saved patches using a fresh
source snapshot; leave both active first-pass sources and the earlier corrected
snapshot unchanged. Do not regenerate any existing agent attempt.
