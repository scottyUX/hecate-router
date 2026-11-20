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
