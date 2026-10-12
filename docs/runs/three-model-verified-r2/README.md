# three-model-verified-r2: leaderboard-matched rerun

Claude Opus 4.5, Gemini 3 Flash and MiniMax M2.5 through mini-SWE-agent on 50
SWE-bench Verified tasks, with the agent, model and environment configuration
matched to the SWE-bench "bash only" leaderboard entries for the same three
models. Run 2026-10-12 on `hecate-exec`. Spec:
[`specs/018-three-model-r2/`](../../../specs/018-three-model-r2/spec.md).

**Result: with the setup matched, all three models reproduce their leaderboard
entries.** Each is within 1–2 tasks of the leaderboard on the same 50 tasks,
with 90–94% per-task agreement and no significant difference. Gemini's
10-point gap from r1 ([`../three-model-verified/`](../three-model-verified/README.md))
closes.

## Context

In r1, Gemini 3 Flash resolved 63/100 against its leaderboard entry's 73/100
on the same tasks (McNemar p = 0.031). r1 differed from the leaderboard in
scaffold version, prompt details, reasoning effort, cost cap and provider
routing, and its trajectories showed Gemini running with no reasoning at all.
r2 removes those differences, so any remaining gap would point at routing,
model drift or noise rather than our setup.

## Method

**Source of truth.** The leaderboard configuration was taken from the
entries' own published trajectories (`info.config`, `info.mini_version`,
per-call `extra.response`), not the website. Snapshots are committed in
[`configs/leaderboard_reference/`](../../../configs/leaderboard_reference/).
Before any spend, `scripts/check_leaderboard_config.py` resolves the exact
config each model runs with and diffs it field by field against those
snapshots. It passes with only the listed differences below.

**Tasks.** 50 of r1's 100, drawn uniformly at random (seed `20261012`) and
committed before any model call:
[`configs/three_model_tasks_r2.json`](../../../configs/three_model_tasks_r2.json).
Difficulty 20 `<15 min` / 25 `15 min – 1 h` / 5 `1–4 h`, exactly half of r1's
mix; 26 django.

**Configuration.**

| | leaderboard | r1 | r2 |
|---|---|---|---|
| mini-swe-agent | 2.1.0 (labeled 2.0.0) | 2.4.6 | 2.0.0 |
| agent config | built-in `swebench.yaml` | ours, copied from 2.4.6 | 2.0.0 built-in |
| temperature | `null` | not set | `null` |
| step limit / per-task cost cap | 250 / $3 | 250 / none | 250 / $3 |
| `environment.pull_timeout` | 300 | 120 | 300 |
| reasoning | high, all three | provider default | high, all three |
| Opus | Anthropic API direct, `reasoning_effort: high`, interleaved-thinking beta, cache control | OpenRouter, providers anthropic → bedrock → vertex | OpenRouter pinned to Anthropic, `reasoning.effort: high`, same beta header, cache control |
| Gemini | Google AI Studio direct, `reasoning_effort: high` | OpenRouter, ai-studio → vertex, cache control | OpenRouter pinned to Google AI Studio, `reasoning.effort: high` |
| MiniMax | OpenRouter, unpinned | OpenRouter pinned to minimax, cache control | OpenRouter `only: [novita, minimax/fp8]` |

Leaderboard trajectories report `mini_version: 2.1.0` although the entries
are labeled 2.0.0. 2.1.0 differs from 2.0.0 only in `agents/interactive.py`,
which batch runs do not use.

**Models.** OpenRouter `anthropic/claude-opus-4.5` (the only Opus 4.5 version,
`claude-opus-4-5-20251101` on the leaderboard), `google/gemini-3-flash-preview`
(a preview; no dated version to pin), and `minimax/minimax-m2.5` (open weights,
same slug as the leaderboard). Every call was served by its intended provider:
Opus 1,890/1,890 Anthropic, Gemini 3,250/3,250 Google AI Studio, MiniMax
3,148/3,148 Novita. Every call ended in a tool call; none was truncated.

**Execution.** Three concurrent `mini-extra swebench` processes, 6 workers
each, on an e2-standard-8 (8 vCPU, 31 GB). Images were already cached. A
2-task smoke run per model came first; it sent MiniMax 100% to AtlasCloud
(2% of the leaderboard's calls), so MiniMax was narrowed to Novita and
Minimax before launch (`b4c9643`). Graded with
`swebench.harness.run_evaluation` (swebench 4.1.0) against
`SWE-bench/SWE-bench_Verified`. Code at `b4c9643` throughout.

**Budget.** Per-process caps $75 / $40 / $15. Spend $64.44 (+ $2.40 smoke):
Opus $46.44, Gemini $14.52, MiniMax $3.48. No per-model cap was reached;
no infra failures.

## Result

### vs. the leaderboard (same 50 tasks)

| model | r2 | leaderboard | agreement | κ | r2-only / lb-only | McNemar p |
|---|---|---|---|---|---|---|
| Opus 4.5 | 37/50 (74%) | 39/50 (78%) | 92% | 0.78 | 1 / 3 | 0.63 |
| Gemini 3 Flash | 37/50 (74%) | 38/50 (76%) | 94% | 0.84 | 1 / 2 | 1.00 |
| MiniMax M2.5 | 34/50 (68%) | 35/50 (70%) | 90% | 0.77 | 2 / 3 | 1.00 |

Discordant tasks:

- Opus: r2 only `pylint-dev__pylint-6528`; leaderboard only
  `astropy__astropy-13033`, `pytest-dev__pytest-7324`, `sympy__sympy-12489`.
- Gemini: r2 only `django__django-12273`; leaderboard only
  `django__django-12754`, `pydata__xarray-6938`.
- MiniMax: r2 only `django__django-11138`, `django__django-11433`;
  leaderboard only `django__django-11149`, `django__django-14351`,
  `pydata__xarray-6938`.

Trajectories match too (medians, ours vs leaderboard):

| model | steps | test runs | first edit step | peak context | reasoning tokens / task | $/task (mean) |
|---|---|---|---|---|---|---|
| Opus 4.5 | 32 vs 30 | 5 vs 4 | 11 vs 11 | 26.3k vs 25.2k | 2,699 vs 1,850 | 0.93 vs 0.84 |
| Gemini 3 Flash | 59.5 vs 54.5 | 2 vs 3 | 21 vs 15 | 37.3k vs 51.7k | 15,125 vs 13,246 | 0.29 vs 0.38 |
| MiniMax M2.5 | 54 vs 54 | 6 vs 5 | 18 vs 15.5 | 25.9k vs 24.6k | 3,280 vs 3,159 | 0.07 vs 0.09 |

Full report: [`leaderboard-comparison.md`](leaderboard-comparison.md).

### vs. r1 (same tasks, graded in both)

| model | n | r2 | r1 | r2-only / r1-only | McNemar p | reasoning tokens / task (median), r2 vs r1 |
|---|---|---|---|---|---|---|
| Opus 4.5 | 36 | 28 | 30 | 0 / 2 | 0.50 | 2,699 vs 0 |
| Gemini 3 Flash | 50 | **37** | **33** | 6 / 2 | 0.29 | **15,125 vs 0** |
| MiniMax M2.5 | 44 | 30 | 35 | 1 / 6 | 0.13 | 3,280 vs 2,756 |

r1's Opus and MiniMax covered only 70 and 87 of the 100 tasks, so their n is
smaller.

### Within r2

| model | resolved | $/task | $/resolved | API calls (median) |
|---|---|---|---|---|
| Opus 4.5 | 37/50 (74%, 60–84) | 0.93 | 1.26 | 32 |
| Gemini 3 Flash | 37/50 (74%, 60–84) | 0.29 | 0.39 | 60 |
| MiniMax M2.5 | 34/50 (68%, 54–79) | 0.07 | 0.10 | 54 |

Solved by all three 31, by none 8; only Opus 2, only Gemini 4, only MiniMax 1.
No pair differs significantly (all McNemar p ≥ 0.375). **Oracle router**
(cheapest model that resolves each task): 84% for $7.51, vs always-Opus 74%
for $46.44. Full tables, per-repo rates and trajectory-feature AUROCs:
[`analysis.md`](analysis.md).

## Interpretation

- **Our harness reproduces the leaderboard when the setup matches.** All
  three models land within 1–2 tasks of their entries, agree on 90–94% of
  tasks, and their process statistics (steps, tests, first edit) line up.
  This validates r1's harness as well: r1's Gemini gap was configuration, not
  pipeline.
- **Reasoning effort was the Gemini gap.** r1's Gemini used no reasoning
  tokens; at `effort: high` it uses ~15k per task, close to the leaderboard's
  13k, and resolves 37 vs r1's 33 on the same tasks (6 vs 2 discordant). The
  per-task test is not significant at n = 50, but every signal points the
  same way and r1's trajectories already showed the mechanism.
- **Opus thinks more over OpenRouter than direct.** ~1.5x the leaderboard's
  reasoning tokens and 11% higher cost per task, with no measurable effect on
  outcomes. The likely cause is that OpenRouter and litellm map "high" to
  different Anthropic thinking budgets (unverified). One Opus task
  (`django__django-12273`) hit the $3 cap after 78 calls; the leaderboard
  hits the cap on 8 of its 500 Opus tasks.
- **r1's MiniMax was, if anything, better** (35 vs 30 on 44 common tasks,
  p = 0.13). Its r1 setup (provider default reasoning, pinned to MiniMax's
  own endpoint) differs from the leaderboard's; not significant.
- **For routing, the three are tied on accuracy and far apart on cost.** At
  full strength Gemini matches Opus at under a third of the cost, and the
  oracle's headroom is almost entirely cost (84% for 16% of always-Opus).

## Caveats

- **n = 50.** A resolved rate's 95% CI is about ±13 points. Agreement with
  the leaderboard is strong evidence of a faithful setup; the r2-vs-r1
  differences are directional only.
- **Single attempt per (model, task), temperature `null`** (provider
  default), as on the leaderboard. Expect a few tasks of noise per
  model in any rerun.
- **OpenRouter instead of direct APIs for Opus and Gemini.** Same serving
  provider, but the reasoning request goes through OpenRouter's translation
  (see the Opus point above). Whether OpenRouter forwards the
  interleaved-thinking header was not verified directly; Opus reasoned on
  every call.
- **Gemini 3 Flash is a preview.** Google may have updated it between the
  leaderboard run (February) and this one; that cannot be tested.
- **MiniMax served by Novita only.** OpenRouter balances toward the cheapest
  allowed provider; the leaderboard's calls were spread over five providers
  (Novita 46%, Minimax 37%, Fireworks 13%, SiliconFlow 2%, AtlasCloud 2%).
  Fireworks and SiliconFlow no longer serve M2.5.
- **CPU load and command timeouts.** 18 agent containers on 8 vCPUs; load
  peaked at 14.5 (1-minute) during the run. Across all 50 tasks r2 had fewer
  60-second command timeouts than the leaderboard (34 vs 58 over 18 vs 29
  trajectories), so contention did not add timeouts overall. One discordant
  task, MiniMax `django__django-14351`, timed out in r2 but not on the
  leaderboard; it was not rerun.

## Files

| file | contents |
|---|---|
| `analysis.md` | generated report (per-repo rates, cross-model, feature AUROCs) |
| `summary.json` | every number in `analysis.md` |
| `per_task.csv` | one row per (model, task): status, resolved, cost, trajectory features |
| `leaderboard-comparison.md` | per-task comparison with the leaderboard and with r1 |
| `manifests/` | per-model run manifests (config, overrides, model kwargs, reference-config hash, image digests) and grading manifests |

Not committed (on the VM at `~/hecate-r2/data/outputs/runs/three-model-verified-r2/`):
trajectories, `preds.json`, `generations.jsonl`, `executions.jsonl`, harness
logs and reports.

## Reproduce

```bash
pip install -e ".[agent]"                                  # mini-swe-agent 2.0.0
python scripts/check_leaderboard_config.py --experiment r2  # must PASS
export EXPERIMENT=r2 WORKERS=6
bash scripts/launch_three_model.sh preflight
bash scripts/launch_three_model.sh pull
bash scripts/launch_three_model.sh start
bash scripts/grade_three_model.sh start opus gemini minimax
bash scripts/grade_three_model.sh analyze-when-done
python scripts/compare_three_model_leaderboard.py \
  --per-task data/outputs/runs/three-model-verified-r2/analysis/per_task.csv \
  --tasks-file configs/three_model_tasks_r2.json \
  --baseline-per-task docs/runs/three-model-verified/per_task-interim.csv \
  --trajectories --out data/outputs/runs/three-model-verified-r2/analysis/leaderboard-comparison.md
```
