# TASK-009 — Local Qwen3.6 + Codex evaluator pilot

Scott approved a one-task pilot using the paper's Qwen3.6-35B-A3B model,
Codex CLI0.164.0, and one task from the exact SWE-bench-45 subset. Run only
on Spark, with no paid API. This is an evaluator/compatibility check, not a
replication score. The paper's precise Codex version and serving budgets are unknown.

## Selection and configuration fixed before results

Task django__django-16560: lexically first Django5.0 task in the pinned45,
chosen for its official Python3.11/ARM-compatible recipe before reading outcomes.
Dataset/parquet hashes and exact45 IDs remain in the TASK-008 manifest.
Qwen/Qwen3.6-35B-A3B revision345d467b117d1fd5eda9b879a5988de9ae5f47a7,
BF16, single GPU,32768 context,8192 max output, temperature0.6,top_p0.95,
top_k20,min_p0,presence_penalty0,repetition_penalty1,seed0. Native qwen3_coder
auto tool parser, qwen3 reasoning parser, text-only, no quantization/MTP.
Reuse our declared Codex shell-edit compatibility configuration and three
read/edit/repair fixtures; this prompt/config difference from paper is disclosed.
At most40 task requests,2700s episode,120s commands,360s inference requests,
2 transport retries. No fallback model/prompt/precision changes after outcomes.

## Requirements and order

1. Prepare task-owned branch/source/root/images/logs/config, immutable manifest,
   exact model/data/Codex versions and dependency freeze. Download CPU assets;
   do not start inference until controls pass and GPU/memory guards pass.
2. Build the official SWE-bench4.1.0 ARM64 task recipe. Preserve generated
   Dockerfiles, setup scripts, build logs, image IDs and environment package list.
   If ARM source compilation needs system headers, record the failed original
   build and any minimal image-only dependency amendment before rebuilding.
   Never change test assertions or omit dependencies/tests to force a pass.
3. Run the official task eval script and official report parser in independent
   fresh evaluator containers: unpatched must fail designated tests, gold patch
   must pass required failing and regression tests. All required outcomes must
   be present; setup/missing-test failures remain unknown. Controls must validate
   before any model task attempt. No gold/test metadata enters agent sandbox.
4. Export only the prescribed base commit's tracked tree to a fresh one-commit
   workspace. Agent sees original issue, source and visible tests, not history,
   reference solution, hidden test patch, host credentials or Docker socket.
   Sandbox and evaluator run network-none; only the Unix model relay is available.
5. Start model only with idle GPU and at least90GiB physically free/100GiB
   available. Evict only clean pages of task-owned model files via fadvise while
   loading; no global cache dropping, sudo or changes to other workloads.
6. Pass read/edit/repair/isolation fixtures, then perform one model task attempt.
   Preserve its raw patch and independently grade source even if it terminates
   abnormally. TASK-007 projection excludes only recorded new test files and
   retains policy/termination separately. Missing grading is unknown, not failure.
7. Save manifest, per-step raw logs and patches, hashes, official parser report,
   test-status coverage, usage/timing and explicit zero API cost. Mirror and verify
   off Spark, then stop owned containers. Preserve diflh-ollama.

## Acceptance and tests

- Exact model/task/config guard tests prevent silently substituting the old30B
  model, a training task, a different checkpoint or dropping required outcomes.
- Patched/unpatched controls pass independently before inference.
- Official evaluator statuses match expected F2P/P2P requirements; absent statuses,
  setup errors or timeouts fail closed; source-caused test failures remain failures.
- Three capability fixtures pass; one saved model patch receives independent grade
  with correctness, completion and policy reported separately.
- No new paid API, no training, no multi-task benchmark launch. Scope expansion
  beyond the approved task requires a new explicit instruction.
- Raw artifacts/source/config and off-Spark checksum receipt persist even if
  serving/build/fixture gates fail. No lost logs or silent compatibility workarounds.

Preparation run01: official base and environment images built successfully.
The controller called SWE-bench4.1.0 build_instance_image without its required
logger/nocache arguments. Preserve that TypeError and all build logs. Correct the
API call, reuse unchanged completed image layers, and rerun preparation with a
new run ID/source snapshot. No model calls occurred and no task/model settings changed.

Preparation run02 validates unpatched failure and gold success, covering all8F2P
and66P2P outcomes. Official setup adds an empty SWE-bench commit, so image HEAD
is not the dataset base SHA even though its source tree is identical. Before any
model task attempt, verify tree identity and export the exact dataset base commit
to a fresh one-commit workspace; record both tree and image HEAD. This preserves
the required source state and prevents exporting evaluator history.

Compatibility amendment before any benchmark inference: Qwen3.6 loaded in BF16
and served successfully, but fixture run01 was rejected before generation with
HTTP400 "System message must be at the beginning." The adapter had translated
multiple developer messages into multiple system messages. Declare a Qwen3.6-only
single_system_prefix encoding: concatenate existing instruction strings in order
at the beginning, preserving all non-system history and tool contracts unchanged.
This is not an instruction rewrite or a native-paper prompt reproduction. Existing
models retain native message layout. Preserve the failed fixture and server log;
run a new controls/fixture run under the amended config. No benchmark task attempt
has occurred, and no model, precision, sampling or budget change is introduced.

## Completed pilot and verification

Run task009-qwen36-codex-one-task-run-02, runtime8987d33, used the exact specified
Qwen3.6 checkpoint and Codex0.164.0 locally. All3 read/edit/repair fixtures passed.
One benchmark attempt on django__django-16560 ran38 model requests/37 shell tools
over527.86seconds. Its saved source patch was independently graded after a
context_budget_exhausted stop:3/8F2P pass,5ERROR,66/66P2P pass; task unresolved.
The five errors are missing violation_error_code keyword support in CheckConstraint
and UniqueConstraint constructors. Official and strict required-test verdicts agree.
No test-file modifications, source repair or additional benchmark attempts occurred.

The cap was our pilot choice:32768 context with8192 reserved output leaves24576
input tokens. The rejected request had at least24577 input tokens. This is not
Qwen3.6's native context limit and cannot support a model-capability conclusion.

One setup limitation remains before comparative runs: the official eval script's
redundant editable reinstall emitted an offline setuptools build-dependency warning
in controls03 and the model grade. The existing editable installation loaded the
actual patched source: every required test produced an outcome, gold passed74,
unpatched failed all8F2P, and the model's five constructor TypeErrors identify its
incomplete implementation. Preserve the warning rather than silently discard it;
provide a clean offline build-dependency supply before a broader replication.

79 targeted tests and Ruff F checks passed. Off-Spark verification includes6741
files for the final attempt;29 for initial failed preparation;42/39 for successful
controls02/03;41 for the pre-generation failed fixture; and the controller evidence
bundle (model logs/config, environment, package versions and cleanup). All owned
containers and GPU processes stopped; diflh-ollama remains untouched. API cost$0.
Summary: main checkout data/outputs/task009-qwen36-local-summary-run-01.json.

## Paper comparison prerequisite — user clarification after pilot

Scott explicitly requested matching the paper's settings before further comparison.
Keep this completed run labeled evaluator compatibility only, not replication.

Reported settings to match: exact45 task rule,4 independent trajectories per task,
Qwen3.6-35B-A3B, native harness prompts/internal policy, prescribed task base and
official regression scoring, with correctness separate from operational validity.

Unspecified in the paper's published methods: Codex version, exact Qwen checkpoint
hash/serving configuration, SWE context/output limits, sampling and request/wall
budgets. A targeted public code search did not locate the authors' runnable config.
Do not claim262144 tokens was their setting merely because it is Qwen's native
limit. Recover author configuration if available; otherwise preregister each
assumption and describe an approximate replication.

Our custom shell-edit instructions/disabled apply_patch,32K context,40 requests,
8192 output cap and single task/attempt do not establish matching harness behavior.
Resolve those differences, offline setup and hardware/context feasibility before
launching another comparative run. No larger-context or45-task inference is
authorized by this record, and no such run was launched.
