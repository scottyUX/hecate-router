# Feature Specification: Three-Model Verified Rerun (r2) — leaderboard-matched setup, 50 tasks

**Feature Branch**: `feat/mini-swe-agent`

**Created**: 2026-10-12

**Status**: Draft

**Input**: Rerun the three-model SWE-bench Verified experiment
(`docs/runs/three-model-verified/`, run 2026-10-05, "r1") on a seeded random
**50 of r1's 100 tasks**, with the agent, model and environment configuration
matched to the SWE-bench "bash only" leaderboard entries for the same three
models, as recorded in those entries' own trajectories. All three models go
through OpenRouter, using the providers the leaderboard runs used.

Reference entries:

| model | leaderboard entry | resolved (500) | $/task | calls/task |
|---|---|---|---|---|
| Claude Opus 4.5 | `20260217_mini-v2.0.0_claude-4-5-opus-high` | 76.8% | 0.754 | 32.9 |
| Gemini 3 Flash | `20260217_mini-v2.0.0_gemini-3-flash-high` | 75.8% | 0.356 | 56.1 |
| MiniMax M2.5 | `20260217_mini-v2.0.0_minimax-2-5-high` | 75.8% | 0.073 | 60.5 |

## Why

On r1's 100 tasks, Gemini 3 Flash resolved 63 against its leaderboard
entry's 73 (McNemar p = 0.031) at under half the leaderboard's cost per task.
Opus and MiniMax agreed with their entries within noise. r1 differed from
the leaderboard in scaffold version, prompt details, reasoning effort, cost
cap and provider routing (table below). r2 removes those differences, so a
remaining gap can be attributed to OpenRouter routing, model drift or
sampling noise rather than to our setup.

## Source of truth

The leaderboard configuration is taken from the trajectories each entry
published (`info.config`, `info.mini_version`, per-call
`extra.response`), not from the website or `metadata.yaml`. Three
trajectories per entry were checked (`astropy__astropy-13033`,
`django__django-14608`, `sympy__sympy-24539`) and agree on every config
field; 20 MiniMax trajectories were checked for providers. The extracted configs are
committed under `configs/leaderboard_reference/` (T001) so the pre-spend
config check runs offline.

## Configuration: leaderboard vs r1 vs r2

| | leaderboard | r1 | **r2** |
|---|---|---|---|
| mini-swe-agent | 2.1.0 (labeled 2.0.0, see below) | 2.4.6 | **2.0.0** |
| Agent config | 2.x built-in `swebench.yaml` | ours, copied from 2.4.6 | **2.0.0 built-in `swebench.yaml`** |
| Instance template | built-in | step list numbered 2–4 | built-in (steps 3–5) |
| Format-error template | built-in | extra "output token limit" branch | built-in |
| `BASH_ENV=/root/.bashrc` | absent | set | absent |
| `temperature` | `null` (overrides built-in `0.0`) | not set | **`null`** |
| `step_limit` | 250 | 250 | 250 |
| Per-task `cost_limit` | **$3.00** | 0 (none) | **$3.00** |
| Request timeout | class default | 600 s (litellm) | class default (60 s, `OpenRouterModel`) |
| Environment | docker, `/testbed`, 60 s command timeout, `--rm`, `swebench/sweb.eval.x86_64.*:latest` | same | same |
| `environment.pull_timeout` | **300** (set explicitly; 2.0.0 and 2.1.0 default to 120) | 120 | **300** |
| Reasoning, all three | high | provider default | **`reasoning: {effort: high}`** |
| Cost tracking | `default` | `ignore_errors` (Gemini) | `default` |

Per model:

| | leaderboard | r1 | **r2** |
|---|---|---|---|
| **Opus** model class / name | `LitellmModel`, `anthropic/claude-opus-4-5-20251101` (direct) | litellm, `openrouter/anthropic/claude-opus-4.5` | `OpenRouterModel`, `anthropic/claude-opus-4.5` |
| Opus provider | Anthropic API | anthropic → bedrock → vertex | **`order: [anthropic]`, no fallbacks** |
| Opus kwargs | `reasoning_effort: high`, header `anthropic-beta: interleaved-thinking-2025-05-14` | — | `reasoning: {effort: high}`, same `anthropic-beta` header (pass-through unverified) |
| Opus cache control | `default_end` | `default_end` | `default_end` |
| **Gemini** model class / name | `LitellmModel`, `gemini/gemini-3-flash-preview` (direct) | litellm, `openrouter/google/gemini-3-flash-preview` | `OpenRouterModel`, `google/gemini-3-flash-preview` |
| Gemini provider | Google AI Studio | ai-studio → vertex | **`order: [google-ai-studio]`, no fallbacks** |
| Gemini cache control | off | `default_end` | **off** |
| **MiniMax** model class / name | `OpenRouterModel`, `minimax/minimax-m2.5` | litellm, `openrouter/minimax/minimax-m2.5` | `OpenRouterModel`, `minimax/minimax-m2.5` |
| MiniMax provider | unpinned (load-balanced, mix below) | `order: [minimax]` | **`only: [novita, minimax/fp8]`** |
| MiniMax cache control | off | `default_end` | **off** |

### Decisions and known residual differences

- **mini-swe-agent version.** The website and `metadata.yaml` say 2.0.0;
  every trajectory's `mini_version` (written at runtime from
  `minisweagent.__version__`) says 2.1.0. 2.1.0 was released one day after
  2.0.0 (2026-02-12 vs 02-11). Apart from the version string, the only file
  that differs between the two releases is `agents/interactive.py`, which the
  batch `swebench` runner does not use, and both built-in `swebench.yaml`
  files match the leaderboard's templates exactly. r2 pins **2.0.0**, the
  published label; the 2.1.0 record is noted in the manifest.
- **OpenRouter for Opus and Gemini.** The leaderboard called Anthropic and
  Google AI Studio directly. r2 routes through OpenRouter pinned to those
  same providers. Residual differences: OpenRouter's translation of
  `reasoning.effort: high` versus litellm's `reasoning_effort: high`, and
  whether OpenRouter forwards the `anthropic-beta` interleaved-thinking
  header. Both are checked in the smoke run (T015).
- **`OpenRouterModel` for all three.** It is the class the leaderboard used
  for MiniMax. It sends `model_kwargs` as top-level request fields, which is
  OpenRouter's native shape. It takes cost from OpenRouter's billed
  `usage.cost`, so `cost_tracking: default` works for Gemini (r1's litellm
  $0-cost crash goes away) and the $3 per-task cap is enforced on real cost.
  Its request timeout is hard-coded at 60 s with retries. Long Opus
  responses may hit it, so the smoke run counts retries.
- **MiniMax providers.** Across 1,252 calls in 20 leaderboard trajectories,
  MiniMax was served by Novita 46%, Minimax 37%, Fireworks 13%, SiliconFlow
  2% and AtlasCloud 2%; 18 of the 20 tasks switched provider mid-task.
  Fireworks and SiliconFlow no longer list MiniMax M2.5 on OpenRouter
  (checked 2026-10-12). r2 first allowed the three remaining providers;
  in the smoke run OpenRouter sent 100% of calls to AtlasCloud (cheapest),
  so r2 restricts routing to Novita and Minimax with `only` and no
  `order`. OpenRouter load-balances between them, as it did for the
  leaderboard; they served 83% of the leaderboard's calls. `minimax/fp8` excludes the `minimax/highspeed`
  endpoint, which may not have existed in February. The realized mix is
  reported from per-call `provider` fields.
- **Docker images** use `:latest`, as the leaderboard did. Image digests are
  recorded in the manifest.
- **Preview model.** Gemini 3 Flash is a preview slug and may have changed
  since February.

## Fixed Task Set

`configs/three_model_tasks_r2.json`: 50 instance ids drawn uniformly at random
without replacement from the 100 in `configs/three_model_tasks.json` (sorted
by `instance_id` first), seed **`20261012`**. Committed before any model
call. Records seed, method, source file and commit, difficulty and repo
counts.

## User Scenarios & Testing

### User Story 1 - Verify the config matches before spending (Priority: P1)

Before any model call, the operator runs a check that loads r2's fully
resolved config for each model (config file plus runner overrides, merged
the way mini-swe-agent merges them) and compares it field by field against
`configs/leaderboard_reference/<entry>.json`.

**Independent Test**: the check passes offline. Every difference it reports
is on an allowlist that names the reason (model name/class/provider routing,
the reasoning-param shape, Opus beta header shape). Any other difference
fails the check.

### User Story 2 - Run three models on the 50 tasks (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the installed mini-swe-agent is not 2.0.0, **When** a run
   starts, **Then** it exits before any model call.
2. **Given** a finished model run, **When** its manifest is read, **Then** it
   records scaffold version 2.0.0 (with the 2.1.0 note), the r2 config and
   task file, the 50 ids, the per-model cap, the per-task cap, provider
   settings, the leaderboard entry id and Docker image digests.
3. **Given** r2 runs, **Then** nothing under
   `data/outputs/runs/three-model-verified/` changes.

### User Story 3 - Grade and compare (Priority: P1)

Per model, on the 50 tasks: r2 vs leaderboard (primary) and r2 vs r1
(secondary), paired, with resolved rate, Wilson 95% CI, agreement,
discordant pairs and exact McNemar p, plus cost/task, calls/task,
reasoning tokens/task and the realized provider mix.

### Edge Cases

- A task hits the $3 per-task cap → `LimitsExceeded`, a model outcome, as on
  the leaderboard.
- OpenRouter balance runs out → 402 is an infra failure; prune and re-queue.
- A pinned provider is down → with no fallbacks, calls fail and retry. If it
  persists, stop and decide; do not silently widen routing.
- OpenRouter returns `usage.cost` of 0 for a call → `OpenRouterModel` raises.
  Treat it as an infra failure and investigate before setting
  `ignore_errors`.

## Requirements

- **FR-001**: mini-swe-agent MUST be `2.0.0`, guarded at runtime. The
  guard is per experiment: r1 expects 2.4.6, so r1's queued tasks can only
  be finished from a 2.4.6 venv.
- **FR-002**: The agent config MUST be mini-swe-agent 2.0.0's built-in
  `swebench.yaml` verbatim, plus the model block in the table above, in a
  new `configs/miniswe_leaderboard.yaml`, with `environment.pull_timeout: 300`
  added (found by the config check). `configs/miniswe_three_model.yaml`
  (r1) MUST stay unchanged.
- **FR-003**: Model kwargs MUST include `drop_params: true`,
  `temperature: null`, `parallel_tool_calls: true` and
  `reasoning: {effort: high}`, plus the per-model `provider` setting.
  Opus MUST also send `anthropic-beta: interleaved-thinking-2025-05-14`.
- **FR-004**: `agent.cost_limit` MUST be 3.0 and `step_limit` 250.
- **FR-005**: Per-model process caps: Opus $75, Gemini $40, MiniMax $15
  ($130), via `MSWEA_GLOBAL_COST_LIMIT`.
- **FR-006**: The task set MUST be the 50 ids in
  `configs/three_model_tasks_r2.json`.
- **FR-007**: r2 outputs MUST go to
  `data/outputs/runs/three-model-verified-r2/`, with run ids
  `three-model-verified-r2-<model>`.
- **FR-008**: r1 MUST stay reproducible: the runner's r1 path uses r1's
  config, model table (provider-default reasoning), task file and caps.
- **FR-009**: The pre-spend config check (US1) MUST pass before `start`.
- **FR-010**: Grading MUST use the existing `run_execution.py` /
  swebench 4.1.0 path against `SWE-bench/SWE-bench_Verified`.

## Success Criteria

- **SC-001**: Config check passes, with only allowlisted differences.
- **SC-002**: All 50 tasks graded for all three models (or the remaining
  infra failures are listed explicitly).
- **SC-003**: Total OpenRouter-billed spend ≤ $130.
- **SC-004**: Report has r2-vs-leaderboard and r2-vs-r1 rows for all three
  models and the realized MiniMax provider mix.

## Analysis plan (pre-registered)

- **Primary**: per model, r2 vs leaderboard on the 50 tasks. Report
  agreement and McNemar on discordant pairs. The question is whether r1's
  Gemini gap persists once the setup matches.
- **Secondary**: r2 vs r1 per model (all setup changes together); cost,
  calls and reasoning tokens per task vs the leaderboard.
- **Power**: n = 50 gives about ±13 points on a resolved rate. r1's Gemini
  gap came from 18 discordant tasks in 100, so expect about 9 here, too few
  for a reliable test. Report direction and discordant counts, not just
  p < 0.05.

## Assumptions

- The leaderboard's per-task config, sampled on 3 tasks per entry, was the
  same for all 500 tasks.
- OpenRouter's `google-ai-studio` and `anthropic` providers serve the same
  model versions as the direct APIs did in February.
- `hecate-exec` runs Python 3.10.12, so the Python 3.14 `dill` issue does not
  apply there.
