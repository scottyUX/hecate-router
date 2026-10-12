# Three-model run vs. SWE-bench leaderboard

Leaderboard entries (mini-SWE-agent, bash only, reasoning effort **high**): `20260217_mini-v2.0.0_claude-4-5-opus-high`, `20260217_mini-v2.0.0_gemini-3-flash-high`, `20260217_mini-v2.0.0_minimax-2-5-high`.

## Resolved rate, per model

| model | leaderboard on our 100 | tasks we graded | ours | leaderboard | agreement | κ | ours-only / lb-only | McNemar p |
|---|---|---|---|---|---|---|---|---|
| opus | 74/100 (65–82) | 70 | 57 (81.4%) | 53 (75.7%) | 88.6% | 0.66 | 6 / 2 | 0.289 |
| gemini | 73/100 (64–81) | 100 | 63 (63.0%) | 73 (73.0%) | 82.0% | 0.59 | 4 / 14 | 0.031 |
| minimax | 72/100 (63–80) | 87 | 67 (77.0%) | 64 (73.6%) | 82.8% | 0.54 | 9 / 6 | 0.607 |

### opus

| difficulty | n | ours | leaderboard |
|---|---|---|---|
| <15 min fix | 27 | 21 | 21 |
| 15 min - 1 hour | 37 | 31 | 28 |
| 1-4 hours | 6 | 5 | 4 |

Cost/task: ours $0.843, leaderboard $0.793. API calls/task: ours 37.2, leaderboard 32.6.

Only we resolved: `django__django-11734`, `django__django-12273`, `django__django-14053`, `django__django-15732`, `django__django-15957`, `matplotlib__matplotlib-24870`

Only the leaderboard resolved: `astropy__astropy-13033`, `psf__requests-6028`

### gemini

| difficulty | n | ours | leaderboard |
|---|---|---|---|
| <15 min fix | 40 | 28 | 30 |
| 15 min - 1 hour | 50 | 32 | 38 |
| 1-4 hours | 10 | 3 | 5 |

Cost/task: ours $0.166, leaderboard $0.355. API calls/task: ours 57.4, leaderboard 55.9.

Only we resolved: `pylint-dev__pylint-6528`, `pylint-dev__pylint-7277`, `scikit-learn__scikit-learn-14087`, `sympy__sympy-14976`

Only the leaderboard resolved: `astropy__astropy-14365`, `django__django-11119`, `django__django-11138`, `django__django-11149`, `django__django-12754`, `django__django-13023`, `django__django-14351`, `django__django-14672`, `django__django-15503`, `django__django-16100`, `django__django-16136`, `pydata__xarray-6938`, `scikit-learn__scikit-learn-9288`, `sphinx-doc__sphinx-9658`

### minimax

| difficulty | n | ours | leaderboard |
|---|---|---|---|
| <15 min fix | 35 | 28 | 27 |
| 15 min - 1 hour | 45 | 34 | 33 |
| 1-4 hours | 7 | 5 | 4 |

Cost/task: ours $0.065, leaderboard $0.089. API calls/task: ours 52.2, leaderboard 61.3.

Only we resolved: `astropy__astropy-13033`, `django__django-11138`, `django__django-11141`, `django__django-11433`, `django__django-12273`, `pylint-dev__pylint-6528`, `pylint-dev__pylint-7277`, `pytest-dev__pytest-7324`, `scikit-learn__scikit-learn-14087`

Only the leaderboard resolved: `astropy__astropy-14365`, `django__django-12965`, `django__django-13023`, `django__django-13401`, `django__django-14351`, `pydata__xarray-6938`

## Trajectories (medians, tasks both sides ran)

| model | feature | ours | leaderboard |
|---|---|---|---|
| opus | steps | 30.0 | 28.5 |
| opus | test_runs | 4.0 | 4.0 |
| opus | script_runs | 7.0 | 7.0 |
| opus | edit_actions | 2.0 | 1.0 |
| opus | tracebacks | 1.0 | 4.0 |
| opus | files_inspected | 3.0 | 2.0 |
| opus | first_edit_step | 11.0 | 11.0 |
| opus | max_prompt_tokens | 21873.5 | 22772.5 |
| opus | reasoning_tokens | 0.0 | 1661.0 |
| opus | runtime_s | 129.1 | 151.3 |
| opus | leaderboard model config | | `anthropic/claude-opus-4-5-20251101` {"drop_params": true, "temperature": null, "parallel_tool_calls": true, "reasoning_effort": "high", "extra_headers": {"anthropic-beta": "interleaved-thinking-2025-05-14"}} |
| gemini | steps | 35.0 | 52.0 |
| gemini | test_runs | 0.0 | 3.0 |
| gemini | script_runs | 11.0 | 13.0 |
| gemini | edit_actions | 3.0 | 4.0 |
| gemini | tracebacks | 2.0 | 5.0 |
| gemini | files_inspected | 2.0 | 4.0 |
| gemini | first_edit_step | 10.0 | 16.0 |
| gemini | max_prompt_tokens | 16901.5 | 51711.0 |
| gemini | reasoning_tokens | 0.0 | 14508.0 |
| gemini | runtime_s | 83.3 | 359.2 |
| gemini | leaderboard model config | | `gemini/gemini-3-flash-preview` {"drop_params": true, "temperature": null, "parallel_tool_calls": true, "reasoning_effort": "high"} |
| minimax | steps | 38.0 | 50.0 |
| minimax | test_runs | 5.0 | 5.0 |
| minimax | script_runs | 10.0 | 13.0 |
| minimax | edit_actions | 2.0 | 2.0 |
| minimax | tracebacks | 3.0 | 5.0 |
| minimax | files_inspected | 3.0 | 3.0 |
| minimax | first_edit_step | 12.0 | 17.0 |
| minimax | max_prompt_tokens | 19819.0 | 23722.0 |
| minimax | reasoning_tokens | 2663.0 | 3138.0 |
| minimax | runtime_s | 126.7 | 380.8 |
| minimax | leaderboard model config | | `minimax/minimax-m2.5` {"drop_params": true, "temperature": null, "parallel_tool_calls": true, "reasoning": {"effort": "high"}} |

## Leaderboard's own cross-model view on our 100

- All three: 64; none: 18; only one: opus 4, gemini 2, minimax 3
- Oracle (cheapest resolving model): 82% for $13.99; always-opus 74% for $80.42, always-gemini 73% for $35.46, always-minimax 72% for $8.43
- opus vs gemini: κ 0.72, opus-only 6 / gemini-only 5, McNemar p 1.000
- opus vs minimax: κ 0.65, opus-only 8 / minimax-only 6, McNemar p 0.791
- gemini vs minimax: κ 0.72, gemini-only 6 / minimax-only 5, McNemar p 1.000
