# Three-model run vs. SWE-bench leaderboard

Leaderboard entries (mini-SWE-agent, bash only, reasoning effort **high**): `20260217_mini-v2.0.0_claude-4-5-opus-high`, `20260217_mini-v2.0.0_gemini-3-flash-high`, `20260217_mini-v2.0.0_minimax-2-5-high`.

## Resolved rate, per model

| model | leaderboard on our 50 | tasks we graded | ours | leaderboard | agreement | κ | ours-only / lb-only | McNemar p |
|---|---|---|---|---|---|---|---|---|
| opus | 39/50 (65–87) | 50 | 37 (74.0%) | 39 (78.0%) | 92.0% | 0.78 | 1 / 3 | 0.625 |
| gemini | 38/50 (63–86) | 50 | 37 (74.0%) | 38 (76.0%) | 94.0% | 0.84 | 1 / 2 | 1.000 |
| minimax | 35/50 (56–81) | 50 | 34 (68.0%) | 35 (70.0%) | 90.0% | 0.77 | 2 / 3 | 1.000 |

### opus

| difficulty | n | ours | leaderboard |
|---|---|---|---|
| <15 min fix | 20 | 16 | 16 |
| 15 min - 1 hour | 25 | 19 | 20 |
| 1-4 hours | 5 | 2 | 3 |

Cost/task: ours $0.929, leaderboard $0.835. API calls/task: ours 37.8, leaderboard 35.4.

Only we resolved: `pylint-dev__pylint-6528`

Only the leaderboard resolved: `astropy__astropy-13033`, `pytest-dev__pytest-7324`, `sympy__sympy-12489`

### gemini

| difficulty | n | ours | leaderboard |
|---|---|---|---|
| <15 min fix | 20 | 15 | 15 |
| 15 min - 1 hour | 25 | 19 | 20 |
| 1-4 hours | 5 | 3 | 3 |

Cost/task: ours $0.290, leaderboard $0.382. API calls/task: ours 65.0, leaderboard 59.4.

Only we resolved: `django__django-12273`

Only the leaderboard resolved: `django__django-12754`, `pydata__xarray-6938`

### minimax

| difficulty | n | ours | leaderboard |
|---|---|---|---|
| <15 min fix | 20 | 16 | 15 |
| 15 min - 1 hour | 25 | 16 | 19 |
| 1-4 hours | 5 | 2 | 1 |

Cost/task: ours $0.070, leaderboard $0.090. API calls/task: ours 63.0, leaderboard 65.3.

Only we resolved: `django__django-11138`, `django__django-11433`

Only the leaderboard resolved: `django__django-11149`, `django__django-14351`, `pydata__xarray-6938`

## Trajectories (medians, tasks both sides ran)

| model | feature | ours | leaderboard |
|---|---|---|---|
| opus | steps | 32.0 | 30.0 |
| opus | test_runs | 5.0 | 4.0 |
| opus | script_runs | 10.0 | 8.0 |
| opus | edit_actions | 1.0 | 2.0 |
| opus | tracebacks | 4.0 | 3.5 |
| opus | files_inspected | 3.0 | 2.5 |
| opus | first_edit_step | 11.0 | 11.0 |
| opus | max_prompt_tokens | 26286.5 | 25155.5 |
| opus | reasoning_tokens | 2698.5 | 1849.5 |
| opus | runtime_s | 186.1 | 187.3 |
| opus | leaderboard model config | | `anthropic/claude-opus-4-5-20251101` {"drop_params": true, "temperature": null, "parallel_tool_calls": true, "reasoning_effort": "high", "extra_headers": {"anthropic-beta": "interleaved-thinking-2025-05-14"}} |
| gemini | steps | 59.5 | 54.5 |
| gemini | test_runs | 2.0 | 3.0 |
| gemini | script_runs | 14.0 | 14.5 |
| gemini | edit_actions | 4.0 | 4.5 |
| gemini | tracebacks | 5.0 | 5.0 |
| gemini | files_inspected | 4.0 | 4.0 |
| gemini | first_edit_step | 21.0 | 15.0 |
| gemini | max_prompt_tokens | 37263.0 | 51711.0 |
| gemini | reasoning_tokens | 15124.5 | 13246.0 |
| gemini | runtime_s | 206.0 | 356.3 |
| gemini | leaderboard model config | | `gemini/gemini-3-flash-preview` {"drop_params": true, "temperature": null, "parallel_tool_calls": true, "reasoning_effort": "high"} |
| minimax | steps | 54.0 | 54.0 |
| minimax | test_runs | 6.0 | 5.0 |
| minimax | script_runs | 14.5 | 14.0 |
| minimax | edit_actions | 2.0 | 2.0 |
| minimax | tracebacks | 5.0 | 5.0 |
| minimax | files_inspected | 3.0 | 3.0 |
| minimax | first_edit_step | 18.0 | 15.5 |
| minimax | max_prompt_tokens | 25897.5 | 24618.0 |
| minimax | reasoning_tokens | 3280.0 | 3158.5 |
| minimax | runtime_s | 207.1 | 376.3 |
| minimax | leaderboard model config | | `minimax/minimax-m2.5` {"drop_params": true, "temperature": null, "parallel_tool_calls": true, "reasoning": {"effort": "high"}} |

## Ours vs. baseline run (`docs/runs/three-model-verified/per_task-interim.csv`)

| model | tasks both graded | ours | baseline | agreement | ours-only / baseline-only | McNemar p | cost/task ours / baseline | calls/task ours / baseline |
|---|---|---|---|---|---|---|---|---|
| opus | 36 | 28 (77.8%) | 30 (83.3%) | 94.4% | 0 / 2 | 0.500 | $0.935 / $0.793 | 36.8 / 36.8 |
| gemini | 50 | 37 (74.0%) | 33 (66.0%) | 84.0% | 6 / 2 | 0.289 | $0.290 / $0.172 | 65.0 / 55.6 |
| minimax | 44 | 30 (68.2%) | 35 (79.5%) | 84.1% | 1 / 6 | 0.125 | $0.072 / $0.068 | 63.8 / 55.1 |

## Leaderboard's own cross-model view on our 50

- All three: 34; none: 9; only one: opus 2, gemini 1, minimax 1
- Oracle (cheapest resolving model): 41/50 for $7.40; always-opus 39/50 for $41.76, always-gemini 38/50 for $19.09, always-minimax 35/50 for $4.51
- opus vs gemini: κ 0.83, opus-only 2 / gemini-only 1, McNemar p 1.000
- opus vs minimax: κ 0.69, opus-only 5 / minimax-only 1, McNemar p 0.219
- gemini vs minimax: κ 0.75, gemini-only 4 / minimax-only 1, McNemar p 0.375
