# TASK-008 — Kimi K2.7 Code with Codex CLI on SWE-bench-45

## Request and purpose

Scott requested running Kimi K2.7 with Codex CLI on SWE-bench-45 to compare with
When Agents Fail: Model or Harness—Who's to Blame? (arXiv:2610.32483v1), and
asked to use Spark. This task is distinct from the20-task Tenacity training pilot.
The paper names Kimi K2.7; its cited model card identifies Kimi-K2.7-Code.

Status update: Scott clarified that the immediate goal is local evaluator
verification. Kimi benchmark execution is deferred; no paid model calls or worker
provisioning were performed. Preparation recovered and hash-pinned the exact45
tasks, validated the paper's counts, and passed6 selection regressions. TASK-007
already provides a local production replay of20 saved Qwen+Codex patches with
10pass/10fail, matching the independent audit. No budget/worker choice is required
to review or reuse that existing evidence.

## Evidence reviewed before implementation

- Paper Appendix A.2: every Verified task with difficulty1–4hours or>4hours.
  Dataset revision c104f840cc67f8b6eec6f759ebc8b2693d585d4a reproduces45 tasks:
  42 labeled1-4hours and3 labeled>4hours, across8 repos (Django22,SymPy7,Sphinx5).
- Appendix A.1: Kimi was locally served by SGLang on8H200s. An OpenRouter API
  endpoint is an explicitly disclosed serving deviation, not exact reproduction.
- Paper uses4 independent attempts per task:180 total. Mean-of-4 is successes/180;
  Best-of-4 is tasks solved at least once/45. Reference Kimi+Codex:10.56% mean,
  28.89% best. Report official task correctness separately from operational validity.
- Exact Codex version, Kimi checkpoint hash, SWE wall/request/output budgets and
  model sampling are not stated in Appendix A. Do not invent matching settings.
- Current OpenRouter model is moonshotai/kimi-k2.7-code; preserve exact identity.
  Prefer Moonshot AI provider, no provider/model fallback, and snapshot returned
  provider, effective model, pricing, quantization metadata and all usage.
- Spark is ARM64, has no registered x86 emulation, and has~518GiB disk free.
  Official harness4.1.0 USE_X86 marks3 selected tasks: pydata__xarray-3993,
  pydata__xarray-6992, sympy__sympy-14248. Do not silently omit/replace them.
  Choice of x86 worker versus Spark compatibility work is pending user input.

## Requirements

1. Keep orchestration/artifacts on Spark. Use task-owned source, configs, ports,
   containers and directories; never modify unrelated services or install system
   emulation/privileged containers. Record any remote worker chosen by Scott.
2. Freeze exact45 IDs from pinned official dataset in a committed manifest with
   download hash and repository/difficulty counts. Fail if any count differs.
3. Use actual Codex CLI, pin its version/hash per architecture. Preserve native
   agent prompts and tool loop where supported. No TASK-001 Qwen prompt/schema
   workaround or custom mini-SWE-agent prompt may be silently introduced.
4. API capability/read-edit-test fixture and official task-image evaluator controls
   must pass before benchmark inference. Fixture tasks are not benchmark results.
   API credentials stay outside model sandboxes and logs, in ignored secret storage.
5. Use official per-instance containers/base commits and SWE-bench regression
   verifier. Hide gold/test patches and evaluator internals from coding agents.
   Snapshot image digests and evaluator version. Do not reuse the Tenacity grader.
6. Score saved patches even after abnormal termination. Keep correctness,
   termination, patch acceptance and VCR separate; missing evaluation is unknown.
   Preserve raw patches. Any secondary source-only diagnosis must be separately
   labeled and must never modify raw official submissions.
7. Four independent fresh-workspace attempts for each task. No manual source
   repair, selective retries or replacing failed attempts. Transport retries are
   bounded and separately recorded. Unknown costs/tokens stay unknown.
8. Freeze our explicit context/sampling/request/wall/output settings and spending
   cap before paid execution. Disclose these as replication choices where paper
   settings are unspecified. Stop at spend cap or3 consecutive infrastructure
   errors, retain incomplete attempts and report the full scheduled denominator.
9. Persist manifest, source/config snapshots, raw outputs, tool traces, patch
   hashes, final states, evaluator reports and resource/cost metrics. Mirror and
   checksum-verify off Spark; stop owned resources on exit.

## Run schema

Manifest: run_id, UTC times, code SHA, config SHA, exact dataset revision/hash,
selection hash, Codex version/hash, provider/model metadata, worker architecture,
image digests, CLI args, dependency freeze, planned_attempts180, status and costs.
Task row: instance_id, repetition0..3, base_commit, termination_reason,
session_completed, patch SHA, patch_accepted, official_resolved(bool|null),
evaluation_status, valid_completion(bool|null), tool/request counts, token usage,
costUSD(nullable), retained evidence paths. Never substitute zero for unknown.

## Edge cases and acceptance criteria

- Different task counts/difficulty/repo distribution: fail before model calls.
- Missing exact Kimi version/provider: stop; do not substitute newer Kimi.
- ARM image incompatibility: preserve build logs; no dropped tasks or unapproved
  architecture changes. Test controls before billing coding attempts.
- Native Codex tool/Responses incompatibility: preserve fixture evidence and
  identify the minimal adapter, with declared protocol amendment before use.
- Incorrect patch, collection error due to patch, malformed/unappliable patch,
  timeout and API error must retain distinct reasons and evidence.
- Completion requires180 retained attempt records, official evaluable outcomes or
  explicit unknowns, mean/best/VCR denominators, actual spending and durable copies.
- Tests cover deterministic exact selection, metadata isolation, denominator and
  aggregate math, cost enforcement, no secret logging, and correct patches after
  abnormal termination. Run end-to-end fixture/evaluator controls on chosen host.

## Sources

- https://arxiv.org/html/2610.32483v1#A1
- https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified
- https://huggingface.co/moonshotai/Kimi-K2.7-Code
- https://openrouter.ai/docs/cookbook/coding-agents/codex-cli
- https://github.com/SWE-bench/SWE-bench/issues/523
