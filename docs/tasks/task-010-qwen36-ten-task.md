# TASK-010 — Ten-task local Qwen3.6/Codex comparison pilot

Scott requested10 tasks first, one attempt each, and dropped training-data
collection. Retain ordinary reproducibility logs only; no self-assessment prompt,
telemetry feature export, router training, API inference or cloud workers.

Use the exact pinned TASK-008 SWE-bench-45 dataset. Fix ten IDs before outcomes:
repeat django__django-16560 to check the corrected configuration; choose one task
per other repository from a seed0 shuffled ID-sorted pool, then fill to ten from
that same pool. Exclude only the three tasks marked x86-only by SWE-bench4.1.0;
do not substitute selected tasks after control/build/model outcomes. All8 repos
except xarray are represented (seven repositories): both paper xarray tasks are
in the x86-only set. The repeat is an exposed development case, not a fresh holdout.

Qwen3.6-35B-A3B checkpoint345d467b117d1fd5eda9b879a5988de9ae5f47a7, BF16,
vLLM0.20 pinned image and Codex0.164.0 stay fixed. Validate native262144 context
on Spark. Remove the custom model-instructions override and advertise apply_patch
through the existing API tool adapter. Keep the single-system-prefix encoding
required by Qwen's template. No silent shell-only fallback if capability gates fail.

Paper-unspecified assumptions: retain vendor coding sampling0.6/top_p0.95/top_k20,
8192 max output, seed0; permit200 model requests and3600s/task, command timeout120s,
request timeout600s and2 transport retries. These are declared safety budgets, not
claimed paper settings. One attempt on ten tasks cannot reproduce Mean/Best-of-4.

Before inference, pass read/edit/test-repair/isolation checks with the amended
native-prompt/tool configuration. For every task, build its official ARM recipe
and validate reference-patch success and unpatched failure. Supply pinned local
build-dependency wheels through a read-only evaluator wheelhouse so the official
eval script can reinstall offline without modifying test assertions or commands.
Treat setup failures and missing outcomes as unknown; do not score them as failures.

Fresh original-base workspace per task, evaluator labels/patches hidden, no network
inside task containers, no host secrets or Docker socket. Preserve raw patch and
independently grade source regardless of session exit. Correctness, policy and
termination are separate. Keep all10 selected tasks in reporting denominators.

Run in two batches of five. Finalize immutable per-task manifests, traces, usage,
patches, test reports, versions and checksums. Verify copies off Spark before
continuing past the five-attempt boundary. Reuse only checksum-verified completed
attempts when resuming; never regenerate them for a better result. Stop on a failed
capability/control gate, resource failure, or3 consecutive infrastructure faults.
Normal unsolved tasks continue. Preserve incomplete runs and stop owned servers
on exit; leave diflh-ollama untouched. No run starts until code/config is committed.

Acceptance: exact10-ID scope tests; native-instruction profile leaves legacy
behavior unchanged; patch-tool fixture passes; native-context readiness passes;
offline evaluation has no build-dependency error;10 attempt/control records or
explicit blocked records retained; per-task source grading, batch checkpoint and
off-Spark verification work without new model calls on resume. Any failed gate is
reported with evidence rather than bypassed.
