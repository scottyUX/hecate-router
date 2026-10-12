# Implementation Plan: Three-Model Verified Rerun (r2)

**Branch**: `feat/mini-swe-agent` | **Date**: 2026-10-12 | **Spec**: [spec.md](./spec.md)

## Summary

Add an r2 path beside r1 in the existing three-model runner: a
leaderboard-matched config file, an r2 model table, a 50-task file, committed
leaderboard reference configs, and an offline check that diffs the resolved
r2 config against those references. Launch, grading and analysis scripts
take the r2 paths through flags and env vars whose defaults stay r1's.

Commit `b58bd82` pinned 2.0.0 and added Gemini `reasoning.effort=high` to
r1's model table. The 2.0.0 pin stays. The Gemini override moves out of the
r1 table into the r2 table, so r1 stays reproducible (FR-008).

## Technical Context

**Dependencies**: `mini-swe-agent==2.0.0`, swebench 4.1.0, datasets 3.6.0.
No new packages.

**Checked against 2.0.0**: `OpenRouterModel` (`model_class: openrouter`)
accepts `model_kwargs`, `set_cache_control`, `cost_tracking`,
`format_error_template` and `observation_template`. It POSTs `model_kwargs`
as top-level JSON (so `reasoning`, `provider`, `temperature: null` and
`extra_headers` go into the payload as-is), always adds
`usage: {include: true}`, and takes cost from `usage.cost`. Request timeout
is a hard-coded 60 s inside `retry`.

**Open point, `extra_headers` with `OpenRouterModel`.** litellm turns
`extra_headers` into HTTP headers; `OpenRouterModel` would put it in the
JSON body, where OpenRouter ignores it. Sending the Opus beta header as an
HTTP header needs a small subclass, `hecate.agent.openrouter_headers.OpenRouterModel`,
that pops `extra_headers` from the kwargs into the request headers. Whether
OpenRouter forwards `anthropic-beta` to Anthropic is unverified; T015 checks
for reasoning between tool calls.

**Storage**: `data/outputs/runs/three-model-verified-r2/<model>/`
(gitignored); write-up in `docs/runs/three-model-verified-r2/`.

## Constitution Check

| Principle | Verdict | Basis |
|---|---|---|
| I. Execution-Grounded Validity | PASS | Same swebench grading path as r1. |
| II. Reproducibility by Manifest | PASS | Manifest adds leaderboard entry, reference-config hash, provider settings, image digests; version pinned and guarded. |
| III. Offline-Testable, Zero-Spend CI | PASS | Reference configs committed; config check, task draw and runner wiring unit-tested offline. |
| IV. Spec-Driven Development | PASS | This spec/plan/tasks. |
| V. Budget Discipline | PASS | $3/task and $130 total; dry run and 2-task smoke per model first. |
| VI. Secrets Hygiene | PASS | `OPENROUTER_API_KEY` from `.env` only. |
| VII. Shared-Scaffold Fairness | PASS | All three get the same config, high reasoning and $3 cap; only the per-model provider/cache settings differ, as on the leaderboard. |

## Changes

```text
configs/
├── miniswe_leaderboard.yaml               # new: 2.0.0 built-in swebench.yaml + r2 model block
├── three_model_tasks_r2.json              # new: 50 tasks, seed 20261012
└── leaderboard_reference/                 # new: extracted from leaderboard trajectories
    ├── 20260217_mini-v2.0.0_claude-4-5-opus-high.json
    ├── 20260217_mini-v2.0.0_gemini-3-flash-high.json
    ├── 20260217_mini-v2.0.0_minimax-2-5-high.json
    └── minimax_provider_mix.json          # 20-traj provider counts

scripts/
├── fetch_leaderboard_reference.py         # new: writes leaderboard_reference/
├── draw_three_model_subset.py             # new
├── check_leaderboard_config.py            # new: resolved r2 config vs reference
├── run_three_model.py                     # --experiment r1|r2; version guard; manifest fields
├── launch_three_model.sh                  # EXPERIMENT env var; sessions ${RUN_ID}-<model>; /N
├── grade_three_model.sh                   # RUN_ROOT / RUN_ID env vars
└── compare_three_model_leaderboard.py     # /N labels; --baseline-per-task (r1)

src/hecate/agent/openrouter_headers.py     # new: OpenRouterModel + extra_headers as HTTP headers

tests/
├── test_three_model_r2.py                 # task draw, experiment presets, version guard
└── test_check_leaderboard_config.py       # config check passes on r2, fails on r1
```

## Design notes

**Experiment presets.** `run_three_model.py --experiment r1|r2` (default
`r1`) selects a preset of config path, model table, task file, run root, run
id and default caps. r1's preset is r1 exactly (b58bd82's Gemini override is
removed from it). r2's model table:

```python
R2_COMMON = {"drop_params": True, "temperature": None,
             "parallel_tool_calls": True, "reasoning": {"effort": "high"}}
opus:    model_name="anthropic/claude-opus-4.5",
         kwargs = R2_COMMON | {"provider": {"order": ["anthropic"], "allow_fallbacks": False},
                               "extra_headers": {"anthropic-beta": "interleaved-thinking-2025-05-14"}},
         set_cache_control="default_end", cap=75
gemini:  model_name="google/gemini-3-flash-preview",
         kwargs = R2_COMMON | {"provider": {"order": ["google-ai-studio"], "allow_fallbacks": False}},
         set_cache_control=None, cap=40
minimax: model_name="minimax/minimax-m2.5",
         kwargs = R2_COMMON | {"provider": {"only": ["novita", "minimax/fp8", "atlas-cloud"]}},
         set_cache_control=None, cap=15
```

These are passed as one JSON `-c model.model_kwargs=…` override per model
(plus `model.model_name`, `model.set_cache_control`, `model.model_class`), so
the shared YAML has no per-model fields.

**Config file.** `configs/miniswe_leaderboard.yaml` is 2.0.0's
`minisweagent/config/benchmarks/swebench.yaml` byte for byte, with
`model.model_kwargs.temperature` changed from `0.0` to `null`,
`agent.cost_limit: 3.0` kept, and `model.model_class: openrouter`. A test
asserts the agent and environment blocks and the templates equal the
installed built-in.

**Config check.** `check_leaderboard_config.py --experiment r2` resolves
each model's config with mini-swe-agent's own `get_config_from_spec` and
`recursive_merge`, normalizes pydantic defaults on both sides (fields the
reference records with default values), and diffs against the reference.
Allowlist: `model.model_name`, `model_type`, `model.model_kwargs.reasoning`
vs `reasoning_effort`, `model.model_kwargs.provider`,
`model.litellm_model_registry`, `environment.image`. Anything else fails.

**Version guard.** `EXPECTED_MINISWE = "2.0.0"`; checked before any model
call (skipped on `--dry-run`); written to manifests and records alongside
`leaderboard_mini_version: "2.1.0"` and a note.

**Manifest additions (r2).** `experiment`, `leaderboard_entry`,
`reference_config_sha256`, `model_kwargs`, `per_task_cost_limit_usd: 3.0`,
and `docker_image_digests` for the 50 images (`docker image inspect`).

**Launch.** `EXPERIMENT` (r1|r2) selects task file, run root, tmux session
prefix (`3m-` / `3m-r2-`) and expected mini-swe-agent version in both shell
scripts; caps come from the runner's preset.

```bash
export EXPERIMENT=r2
bash scripts/launch_three_model.sh preflight   # 2.0.0, OpenRouter balance ≥ $130, docker auth, disk
python scripts/check_leaderboard_config.py --experiment r2
bash scripts/launch_three_model.sh pull
bash scripts/launch_three_model.sh start
```

## Risks

- **60 s timeout.** Opus at high reasoning on long contexts may exceed it;
  retries cost a full re-request. If the smoke run shows retries, switch
  Opus to litellm `openrouter/…` with a longer timeout and record that as a
  difference.
- **Header pass-through.** If OpenRouter drops `anthropic-beta`, Opus runs
  without interleaved thinking; record it as a residual difference.
- **Pinned provider outage.** No fallbacks by design; a long outage stalls
  that model.
