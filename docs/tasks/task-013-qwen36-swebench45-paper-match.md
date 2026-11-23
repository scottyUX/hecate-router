# TASK-013 — SWE-bench-45 paper match: remove our own caps

Status: implemented; awaiting Spark throughput check, preflight and gate.

## Request and purpose

TASK-012 checkpoint 2 (2026-11-23) had 13 graded rep-0 attempts and 0 solves.
Most attempts were ended by limits we chose, not by the model. Scott asked to
remove those limits so the environment matches the paper: Qwen3.6-35B-A3B +
Codex CLI on SWE-bench-45 (arXiv:2610.32483v1, Mean-of-4 26.67%, Best-of-4
44.44%, VCR 98.33%). TASK-012 was stopped at 2026-11-23T02:24-08:00
(`~/work/hecate-task012/STOPPED.txt` on Spark). Its attempts are kept and are not
pooled with TASK-013.

## What ended TASK-012 attempts (13 graded rep-0 attempts)

| Cause | Attempts | Our limit |
|---|---|---|
| Wall-clock cap (`budget_exhausted` at 3600 s, 56–92 requests) | 5 | `task_wall_s: 3600` |
| Labelled `tool_protocol_failure`; actually httpx `ReadTimeout` on one request | 4 | `request_timeout_s: 600` |
| `model_output_budget_exhausted` (finish_reason `length`) | 2 | `max_tokens: 8192` |
| Normal stop | 2 | — |

All four "protocol" failures are `upstream_failure` records with
`type: ReadTimeout` and `failure_kind: model_server_failure`. vLLM was decoding at
5–27 tok/s across three concurrent requests (`--enforce-eager`, no prefix cache,
0% prefix-cache hit rate), so one 8K-token reply could exceed 600 s.

## The paper is silent on all of these

Appendix A reports no Codex version, serving stack, sampling, output cap, context
limit, wall-clock, request or command budget for SWE-bench-45. It says each
harness keeps "its native prompts and internal agent policy". Where the paper is
silent, TASK-013 uses the native or model default instead of a Hecate limit.

## Protocol changes (config `configs/qwen36_swebench45_paper_match.yaml`)

| Setting | TASK-012 | TASK-013 | Why |
|---|---|---|---|
| Wall clock per attempt | 3600 s | none | Not reported; ended 5/13 attempts |
| Per-request timeout | 600 s | none (connect 30 s) | Not reported; ended 4/13 attempts |
| Codex `stream_idle_timeout_ms` | 600000 | 86400000 (1 day) | Must outlast an unbounded request; Codex needs a finite value |
| Per-command kill (`timeout 120s` wrapper) | 120 s | none | Not native Codex behaviour |
| `max_tokens` | 8192 | not sent (vLLM: remaining context) | Not reported; ended 2/13 attempts |
| Sampling | 0.6 / 0.95 / 20, presence 0 | not sent: model `generation_config` (1.0 / 0.95 / 20) | Paper silent; this is the server default and Qwen's own SWE-bench setting (model card: temp 1.0, top_p 0.95) |
| vLLM `--generation-config` | `vllm` (ignores model defaults) | `auto` | Needed for the line above |
| `--enforce-eager` | on | off (CUDA graphs) | Serving speed only |
| Prefix caching | off | on (`mamba_cache_mode=align`) | Serving speed only |
| sphinx-7590, sphinx-8548 | excluded | run, with `docutils==0.21.2` env pin | Official x86 images ship 0.21.2; 0.22+ drops `docutils.utils.roman` |

Unchanged: model and revision, BF16, 262144 context, Codex 0.164.0, native prompt
profile, single-system-prefix layout, gateway recovery and explicit finish
(Amendment 6), per-repetition seed, 4 repetitions, evaluator swebench 4.1.0,
controls rule (Amendment 2/3), selection manifest.

Kept as a runaway guard: `task_model_requests: 200`. No TASK-011/012 attempt
reached it (maximum 114). If any TASK-013 attempt hits it, that is reported
separately and the cap is revisited before the next checkpoint.

## Remaining known deviations from the paper

1. **x86 tasks** (pydata__xarray-3993, pydata__xarray-6992, sympy__sympy-14248):
   Spark is arm64. Options: the GCP x86 `hecate-worker` (paid) or amd64 emulation
   on Spark (needs a privileged binfmt install). Until decided they score as
   unresolved in `all_45` and the run also reports `arm_42`.
2. **Explicit finish tool** (`hecate_finish`, Amendment 6) is a Hecate
   compatibility change. Native Codex ends a turn on any text-only reply.
3. **Serving**: the paper does not state Qwen's serving; we use vLLM 0.20 on one
   GB10, not SGLang on H200s.

## Run layout

Fresh root `~/work/hecate-task013` on Spark (model weights, toolchain and venv
linked from TASK-012). Run IDs keep the TASK-012 naming
(`task012-<iid>-rep<r>-v2`); every manifest records
`execution_protocol: paper-match-v3`. Phase A controls are rerun (sphinx images
change; all controls are validated against the new protocol). Then the native
gate, then checkpoints. Checkpoint 1 is 15 attempts; from checkpoint 2,
`checkpoint_attempts: 42` (scheduling-only, excluded from protocol validation)
so one rep-0 pass over the 42 ARM tasks is not split by model reloads.

## Validation

- `tests/test_task013_paper_match.py`: config drops our caps and keeps scope;
  sphinx pins; Codex idle timeout outlasts unbounded requests; no wall cap; no
  read deadline.
- `tests/test_codex_compatibility.py::test_null_command_timeout_leaves_native_command_unwrapped`.
- Spark: throughput check with CUDA graphs + prefix caching before launch.

## Amendment 1 — Invalid patch-tool arguments get a tool error (2026-11-23 ~04:05 PT)

`django__django-10554` rep 0 ended with `model_output_failure` after 77 requests:
Qwen called `apply_patch` with `{"input": ..., "workdir": "/testbed"}` and the gateway
ended the episode ("Custom patch tool requires exactly one input string"). Native Codex
answers invalid tool arguments with a tool error and continues. The gateway now does the
same through the existing bounded recovery path (`invalid_arguments`, at most 3 per
request, counted against the request cap); nothing is executed or rewritten.

Deployed mid-checkpoint 1. Attempts started after the deploy run the fix; their
`source_snapshot/model_gateway.py` contains `invalid_arguments`, but their manifest
`git_commit` still shows the scheduler's start commit (`HECATE_CODE_SHA` is inherited).
Earlier attempts, including django-10554 rep 0, are kept as recorded and are not rerun.
Whether harness-ended attempts may be superseded is Scott's decision.
