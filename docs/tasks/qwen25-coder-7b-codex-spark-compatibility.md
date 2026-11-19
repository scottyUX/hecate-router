# Task: Qwen2.5-Coder-7B compatibility with Codex on Spark

- **Task ID:** TASK-001
- **Status:** Approved for implementation and scoped compatibility execution
- **Created:** 2026-11-19
- **Scope:** Establish a working local coding-agent integration before measuring a large task-resolution baseline or training a router.
- **Authorization:** Scott approved implementation on a new branch on 2026-11-19 ("open an new branch and implement this"). Includes the scoped preflight, local setup, compatibility fixtures and three-task smoke; excludes the larger baseline and all router training.

## Description

Run `Qwen/Qwen2.5-Coder-7B-Instruct` as the coding model inside the Codex agent harness, with inference and isolated task execution on the DGX Spark. Demonstrate actual file inspection, editing, test execution, and orderly termination. Then run a small executable SWE-smith Tenacity smoke to verify integration with independent grading.

The deliverable is a reusable execution path with auditable evidence, not a favorable model score. No prior Tenacity resolution rate has been established for this exact model and harness. Qwen2.5-7B-Instruct advisor results and Qwen2.5-Coder-7B router metrics are not coding-agent baselines.

## Specifications

### Architecture and code organization

```text
Codex harness in task sandbox
    → Hecate model gateway
    → local inference server on Spark
    → Qwen2.5-Coder-7B-Instruct

Codex tool events + gateway usage → session logs
Final repository diff → independent SWE evaluator → task outcome
```

Proposed Hecate modules, subject to the reuse assessment:

```text
src/hecate/execution/
  codex_session.py       # launch, lifecycle, event capture, execution limits
  model_gateway.py       # local endpoint adapter and usage accounting
  task_environment.py    # clean sandbox, patch collection, evaluator boundary
configs/
  codex_qwen7b.yaml      # pinned model/harness/serving/task settings
scripts/
  run_codex_baseline.py  # one reusable entry point; no advisor or router
```

Keep model selection in configuration rather than a model-specific Python module. This task implements only the functionality needed for compatibility and smoke execution. Checkpoint pause/resume, switching, advisor assessment and PPO remain later work.

Before introducing modules, inspect the existing implementation and tests in `/Users/scottdavis/advisor-models`:

- `advisor_models/swe_smith/codex_proxy.py`
- `advisor_models/swe_smith/eval_codex.py`
- `tests/test_codex_proxy.py`

Record what is reused, adapted or rejected, and why. Existing code targets OpenRouter; do not assume it supports a local inference endpoint. Hecate must not silently depend on an unversioned sibling checkout. Pin any retained external dependency or port the required code with provenance. Do not modify advisor-models or existing experiment artifacts as part of this task.

### Execution protocol

1. Read-only Spark preflight: record active jobs/services, hardware, free memory, disk, container runtime and installed software. Do not interrupt E10 or other workloads. If resources are occupied, report and defer the smoke.
2. Pin exact Codex build, model revision, serving stack/container, precision, tokenizer/chat template, context cap and decoding settings. Check native ARM support and memory before loading the model.
3. Start one local inference endpoint and a gateway that meets the pinned Codex request/streaming/tool contract. If translation is needed, explicitly specify and test it. Do not assume an OpenAI-compatible chat endpoint is Responses-compatible.
4. Execute deterministic capability fixtures: inspect a file, edit source, run a test, read its result and terminate. Grade these fixtures independently of the model's final prose.
5. Run three preselected Tenacity training/pilot tasks sequentially, at most one attempt per task. Use independent evaluation and record every outcome, including errors.
6. Save a compatibility report, exact commands/configuration, event logs, patches and manifests. Verify an off-Spark artifact copy before marking the task complete.

### Proposed limits and task selection

- One coding session at a time; no concurrent experiment training.
- Capability fixture: maximum 10 model requests and 10 minutes per fixture.
- Tenacity smoke: maximum 40 model requests and 45 minutes per task.
- Per-command timeout: 120 seconds; model-request timeout: 180 seconds; at most two retries for transient transport/server failures. Retries count toward wall time and logged usage but are distinguished from new agent decisions.
- Select and record the three task IDs before model execution from a designated training/pilot pool. Record advisor-training overlap for future experiment planning. Do not draw from the reserved final evaluation pool or select tasks based on observed Qwen success.
- This task does not authorize a 50-task baseline. Its measured timings and compatibility results inform that separately reviewed task.

These are proposed bounds for review, not settings already validated on Spark. Record any approved change before the affected run.

## Requirements

- **R1 — Local execution:** Inference, Codex and task sandboxes run on Spark. No paid coding-model APIs or cloud execution fallback. Artifact transfer to existing durable storage is permitted only after approval of this task.
- **R2 — Fixed model:** Use Qwen2.5-Coder-7B-Instruct, not the non-Coder advisor model or a silent substitute. Record revision and precision.
- **R3 — Actual tool execution:** Support repository read/search, source edits and visible test execution. Capture the actual exposed tool schemas. Printed commands, prose patches and claimed test results do not count as executed actions.
- **R4 — Editing contract:** Test Codex's patch tool if exposed. A declared shell-based editing mode may be accepted if patch-tool interoperability fails; pin the effective tools and instructions. Mark this limitation and do not claim native patch-tool compatibility.
- **R5 — Isolation:** Restrict tool execution to clean disposable task environments. No host home-directory access, unnecessary credentials, browsing, external connectors, subagents, or agent network egress. Allow only required inference plumbing. Keep evaluator tests and reference patches inaccessible during execution.
- **R6 — Lifecycle:** Distinguish completed, budget-exhausted, tool/protocol failure, model/server failure, sandbox failure and evaluator failure. Agent completion is not evidence of resolution. Kill timed-out owned child processes and release owned resources.
- **R7 — Evaluator boundary:** Agent-visible tests are allowed; hidden benchmark evaluation runs separately after execution. Validate grading infrastructure with patched/unpatched controls before attributing failures to the model. Reject agent test modifications under the existing source-only task policy.
- **R8 — Measurements:** Record model requests, retries, tool calls, tokens when supplied, inference wall time, episode wall time, patch, evaluator outcome and termination reason. Missing usage stays explicitly missing. Zero API charges must not be reported as zero compute cost.
- **R9 — Reproducibility:** Each run records task/base revision, Hecate commit, Codex build, serving/model revisions, effective tools/prompt, configuration, seed/decoding settings and artifact checksums. Preserve all attempts, including failures.
- **R10 — Durability:** Persist artifacts locally and verify a second copy off Spark using an approved existing artifact route. Do not introduce credentials or a new storage service. If copying fails, the run remains incomplete.
- **R11 — Shared-machine safety:** Follow `CLAUDE.md` and `docs/SPARK_GUIDE.md`. Do not stop unrelated services, use sudo, delete model caches, or replace shared environments to make the smoke fit. Reuse or isolate environments and ports deliberately.

## Edge cases

- **Tool call printed as text / premature final answer:** Preserve the response; mark the relevant capability incomplete. Do not invent a successful action or silently add a retry conversation outside the pinned protocol.
- **Unsupported custom patch tool:** Exercise the declared fallback editing contract, or stop with a compatibility failure. Log any schema translation.
- **Unknown Codex model metadata:** Explicitly configure context and tool capabilities. Do not silently inherit another model's reasoning features or incompatible instructions.
- **Context overflow or compaction:** Record it. Truncation must not drop required instructions or tool-call/output pairing silently. Long-context performance is outside this smoke.
- **OOM, unsupported precision, ARM dependency failure or occupied Spark:** Stop and report; no automatic model substitution, quantization change or eviction of unrelated jobs.
- **Transient failure after an edit:** Retry transport only with bounded, recorded behavior. Never replay a completed shell/edit action automatically.
- **No tests run / zero commands:** Treat measurements as absent, not zero failure rate or successful completion.
- **Task unresolved with valid execution:** Count it as a real unresolved outcome. It is not automatically an integration failure.
- **All smoke tasks unresolved:** Do not proceed to the large baseline automatically. Review logs, grading controls and compatibility evidence before deciding whether this is model weakness.
- **Invalid evaluator result:** Preserve patch and logs; distinguish infrastructure failure from unresolved. Report both attempted and evaluable denominators.
- **Interrupted run:** Preserve partial evidence, clean up owned processes and use a new attempt ID on rerun; do not overwrite the original.

## Acceptance criteria

- [ ] **AC1:** Reviewed specification, chosen task IDs and effective configuration recorded before execution.
- [ ] **AC2:** Reuse assessment documents the existing Codex integration and final code ownership; no hidden sibling-checkout dependency.
- [ ] **AC3:** Exact local model executes through the pinned Codex harness on Spark without hosted-model fallback.
- [ ] **AC4:** Every capability fixture demonstrates the requested action in tool events and filesystem/test evidence, ending within its limits. A shell-edit fallback is clearly identified if used.
- [ ] **AC5:** Three selected Tenacity tasks reach a recorded terminal state with final patches and independent outcome or explicit infrastructure failure. Patched/unpatched grading controls behave as expected. Any infrastructure failure blocks readiness until resolved and rerun under a new attempt ID.
- [ ] **AC6:** Isolation checks demonstrate no evaluator-answer access or unauthorized host/network access; existing Spark workloads remain intact.
- [ ] **AC7:** Offline protocol/lifecycle tests and the live smoke checks below pass; actual resolution is reported without a minimum success claim or omitted failed tasks.
- [ ] **AC8:** Manifest, effective config, transcripts/events, usage, patches, evaluation evidence and report exist and have a verified off-Spark copy.
- [ ] **AC9:** Report gives a clear verdict: compatible, compatible with declared limitations, or blocked. Include measured task times, context/memory constraints, attempted/evaluable/resolved counts, and a recommendation for a separately reviewed larger baseline.

## Tests

### Offline automated tests — no model, network or Spark required

- **T1 — Gateway contract:** Fixture requests/responses preserve messages, tool schemas, call IDs and tool outputs; streaming reconstructs valid completed calls, including fragmented arguments. Unsupported fields and malformed responses fail explicitly.
- **T2 — Usage and retry accounting:** Usage is recorded when present; absent values remain missing. Bounded transient retries are counted, permanent errors terminate, and completed tool actions are not duplicated.
- **T3 — Session limits:** Simulate normal termination, request cap, command/request/episode timeout, process failure and cancellation. Check reasons, partial logs and owned-process cleanup.
- **T4 — Task/environment boundary:** Fixture tasks reset cleanly; patches are collected; hidden evaluator material is not mounted during agent execution; test modifications are rejected; evaluator infrastructure errors differ from unresolved outcomes.
- **T5 — Artifact integrity:** Config/provenance fields are present, attempt IDs do not overwrite prior attempts, and failed second-copy verification prevents a complete status.

### Live checks — require approval and available Spark capacity

- **T6 — Read/search fixture:** Provide a repository containing a known symbol/value; require inspection and verify the corresponding executed action and correct answer.
- **T7 — Edit fixture:** Request a specific small source change; verify the actual diff and an independent assertion. Record whether editing used the patch tool or declared shell fallback.
- **T8 — Test-and-repair fixture:** Supply a small failing visible test; require the model to execute it, change source, rerun and observe a passing result. Preserve both test outputs and the final diff.
- **T9 — Restricted-access fixture:** From the same sandbox policy, check that a harmless marker outside the allowed workspace and a disallowed network destination are inaccessible. Do not probe real secrets or unrelated systems.
- **T10 — Grading controls:** Verify a known patched Tenacity fixture passes and its unpatched counterpart fails in the separate evaluation environment; never expose the control patch to the agent session.
- **T11 — Three-task smoke:** Execute the fixed task manifest with no advisor/router, evaluate independently and report resolution, errors, timings and usage for all attempts.

## Out of scope

PPO, actor/critic training, Execution Advisor assessment, M2 serving or switching, production routing, a full baseline sweep, new cloud resources, changes to E7/E10/E11 results, and deployment changes to the lab website.

## Review decisions

  Confirm or amend before implementation:q

1. Effective edit interface: attempt native patch-tool support, with explicitly declared shell editing as an acceptable fallback?
2. Model serving stack, precision, context cap and decoding settings, after a read-only environment assessment.
3. Three eligible Tenacity task IDs and the limits proposed above.
4. Existing off-Spark artifact destination/transfer route and available Spark scheduling window.

**Approval record:** Approved by Scott on 2026-11-19. Branch: `codex/task-001-qwen7b-codex`.

Implementation decisions recorded before model execution:

- Codex 0.164.0 ARM64; vLLM 0.20.0 existing ARM image; BF16 model revision `c03e6d358207e414f1eca0bb1891e29f1db0e242`; 16,384-token context, greedy decoding, 2,048 maximum output tokens.
- Attempt Codex custom patch tool through an explicit JSON-function translation; permit the documented shell-edit fallback. No silent claims of native upstream custom tools.
- Three task IDs selected in `configs/codex_qwen7b_tasks.json` before inference, lexical first three of the E7 training pool. All overlap earlier advisor training; none come from its validation/final evaluation pool.
- Spark preflight: 114 GiB available, 618 GB free disk, no experiment containers or GPU compute jobs observed. The unrelated `diflh-ollama` container is left intact. Recheck before GPU launch.
- Agent containers use no network and a local-only Unix-socket inference relay. Export only the selected working tree into a new one-commit repository so hidden tests and gold-fix history cannot be recovered through git. Grade in a separate no-network container.
- Keep run artifacts under a dedicated TASK-001 directory on Spark; copy and checksum-verify on Scott's Mac under `data/outputs/runs/`. Do not require Spark cloud credentials or modify E10 resources.


### Compatibility attempts (2026-11-19)

- Attempts 01–02 stopped before inference: the existing task image has no `/usr/bin/python3`. Startup is now checked explicitly and uses its installed testbed Python. No model/task outcomes were generated.
- Attempt 03 passed host/network/history isolation. Qwen received the advertised exec/patch tools but printed a fenced bash block instead of a tool call on the read fixture; this is a failed capability check, not an unresolved SWE task.
- Before attempt 04, clarify the fixed instructions and read fixture to name `exec_command` and native JSON tool calls explicitly. No model, precision, sampling, limits or selected SWE tasks change. Preserve attempt 03 without rewriting its result.

- Attempt 04 again printed a tool call as text. A bounded direct vLLM diagnostic reproduced this with automatic tool selection, while `tool_choice=required` returned a valid native function call. Before attempt 05, pin `serving.tool_decoding=required_with_finish`: the gateway advertises the permitted tools plus `hecate_finish(response)`, requests schema-constrained function selection, and maps that finish action to a Codex final message. This is declared compatibility adaptation, not evidence of reliable unconstrained/native automatic tool selection. No tool-call text is heuristically executed.

- Attempt 05 passed the read fixture through real `exec_command` execution, but exhausted 10 requests producing invalid Codex `apply_patch` syntax on the edit fixture. Before attempt 06, select the pre-approved shell-edit fallback (`serving.editing_mode=shell`), remove the patch tool from the advertised upstream toolset and state this explicitly in the fixed instructions. Native/custom patch-tool compatibility remains unproven.

- Attempt 06 passed reading but Qwen requested the forbidden `sandbox_permissions=require_escalated` option while editing; the gateway rejected it and the attempt stopped. Before attempt 07, remove escalation-only parameters from the advertised shell-tool schema (rather than merely instructing the model not to use them). Keep rejecting forged escalation requests; no sandbox privilege is broadened.

- Attempt 07 passed reading and actual source editing, but failed the repair fixture: Qwen tried to change the test and did not fix addition. Before attempt 08, mount existing test files read-only (enforcing the already specified source-only policy), and make the capability fixture's requested source change explicit: replace subtraction with addition. This fixture tests execution plumbing, not an estimate of autonomous SWE capability. Preserve all unsuccessful attempts. The gateway also restores original tool arguments in model-visible history so its timeout wrapper is not repeatedly copied into subsequent commands.

- Attempt 08 passed all three capability fixtures plus the host/network/history isolation check. The first benchmark smoke attempt then stopped at the independent grader controls, before any coding-model call: the existing task image rejects `git checkout --detach <instance>`. Before smoke attempt 02, use its supported `git checkout <instance>` interface (as the earlier E10 controls do). Record model attempts separately from tasks whose grading preflight failed. This changes no model settings or selected tasks.

- Smoke attempt 02 passed the patched/unpatched controls but stopped before model execution because the task tree contains the legitimate internal link `README.rst → doc/source/index.rst`. Before smoke attempt 03, allow only relative symlinks whose normalized target is a regular file in the same archive; extract regular files first. Continue rejecting external links, hardlinks, git metadata and traversal paths.

- Smoke attempt 03 executed the first selected coding task. Its patch broke imports and caused pytest collection errors after both grading controls passed. Before continuing, classify this explicit patch-caused collection failure as unresolved, not infrastructure failure; unknown/missing evaluation output remains an error. Re-evaluate the checksum-verified saved patch in a new run and reuse its original agent artifacts, without rerunning the model on that task. The remaining two selected tasks still receive at most one model attempt each.

- Smoke attempt 04 completed all three distinct agent attempts (reusing the first from attempt 03), with 0/3 resolved and passing unpatched/gold controls for every task. All reached a Codex final response. The final code additionally mounts `.git` read-only and hashes symlink targets without following host paths. Validate this hardened configuration with fresh capability/isolation fixtures before completion. Preserve agent and evaluator exit codes in separate fields; the original smoke-04 top-level `exit_code` was overwritten by the grader and must be read from each `agent/result.json` for the agent's actual status.
