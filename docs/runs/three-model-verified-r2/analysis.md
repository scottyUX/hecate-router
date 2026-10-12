# Three-model SWE-bench Verified: analysis

Generated 2026-10-12T21:49:11Z. Tasks: 50 (`configs/three_model_tasks_r2.json`). Resolved rates exclude infra failures and ungraded runs; brackets are Wilson 95% CIs.

## Coverage

| model | attempted | infra failures | missing | ungraded | exit statuses |
|---|---|---|---|---|---|
| opus | 50 | 0 | 0 | 0 | LimitsExceeded 1, Submitted 49 |
| gemini | 50 | 0 | 0 | 0 | Submitted 50 |
| minimax | 50 | 0 | 0 | 0 | Submitted 50 |

## Resolved rate

| model | overall | <15 min fix | 15 min - 1 hour | 1-4 hours | >4 hours |
|---|---|---|---|---|---|
| opus | 37/50 (74.0%, 60–84) | 16/20 (80.0%, 58–92) | 19/25 (76.0%, 57–89) | 2/5 (40.0%, 12–77) | – |
| gemini | 37/50 (74.0%, 60–84) | 15/20 (75.0%, 53–89) | 19/25 (76.0%, 57–89) | 3/5 (60.0%, 23–88) | – |
| minimax | 34/50 (68.0%, 54–79) | 16/20 (80.0%, 58–92) | 16/25 (64.0%, 45–80) | 2/5 (40.0%, 12–77) | – |

### By repo

| repo | opus | gemini | minimax |
|---|---|---|---|
| django/django | 21/26 (80.8%, 62–91) | 21/26 (80.8%, 62–91) | 19/26 (73.1%, 54–86) |
| sympy/sympy | 3/6 (50.0%, 19–81) | 4/6 (66.7%, 30–90) | 4/6 (66.7%, 30–90) |
| matplotlib/matplotlib | 2/4 (50.0%, 15–85) | 2/4 (50.0%, 15–85) | 2/4 (50.0%, 15–85) |
| astropy/astropy | 2/3 (66.7%, 21–94) | 2/3 (66.7%, 21–94) | 2/3 (66.7%, 21–94) |
| pydata/xarray | 3/3 (100.0%, 44–100) | 2/3 (66.7%, 21–94) | 2/3 (66.7%, 21–94) |
| sphinx-doc/sphinx | 2/3 (66.7%, 21–94) | 2/3 (66.7%, 21–94) | 2/3 (66.7%, 21–94) |
| scikit-learn/scikit-learn | 2/2 (100.0%, 34–100) | 2/2 (100.0%, 34–100) | 2/2 (100.0%, 34–100) |
| psf/requests | 1/1 (100.0%, 21–100) | 1/1 (100.0%, 21–100) | 1/1 (100.0%, 21–100) |
| pylint-dev/pylint | 1/1 (100.0%, 21–100) | 0/1 (0.0%, 0–79) | 0/1 (0.0%, 0–79) |
| pytest-dev/pytest | 0/1 (0.0%, 0–79) | 1/1 (100.0%, 21–100) | 0/1 (0.0%, 0–79) |

## Efficiency

| model | total $ | $/task | $/resolved | API calls (mean / median) | steps (mean) | runtime s (mean / median) |
|---|---|---|---|---|---|---|
| opus | 46.4393 | 0.9288 | 1.2551 | 37.8 / 32.0 | 37.8 | 223.7 / 186.1 |
| gemini | 14.5169 | 0.2903 | 0.3923 | 65.02 / 60.0 | 65 | 228.1 / 206.0 |
| minimax | 3.4836 | 0.0697 | 0.1025 | 62.98 / 54.0 | 62.96 | 265.9 / 207.1 |

## Cross-model (n=50 tasks graded for all models)

- Solved by all: **31**
- Solved by none: **8**
- Solved by only one: opus **2**, gemini **4**, minimax **1**
- Solved by exactly two: opus+gemini **2**, opus+minimax **2**, gemini+minimax **0**

| pair | agreement | Cohen's κ | discordant | McNemar p |
|---|---|---|---|---|
| opus vs gemini | 84.0% | 0.584 | opus 4 / gemini 4 | 1.0 |
| opus vs minimax | 90.0% | 0.758 | opus 4 / minimax 1 | 0.375 |
| gemini vs minimax | 82.0% | 0.565 | gemini 6 / minimax 3 | 0.5078 |

**Oracle router** (per task, cheapest model that resolves it): 84.0% resolved for $7.5086, vs. single models: opus 74.0% for $46.4393, gemini 74.0% for $14.5169, minimax 68.0% for $3.4836. This is the routing headroom on this task set.

## Trajectory features vs. outcome

AUROC of each process feature for resolved vs. unresolved (0.5 = no signal; >0.5 = higher with resolved). Top 10 by distance from 0.5. Small n per model: treat as exploratory.

### opus

| feature | AUROC | mean resolved | mean unresolved | n |
|---|---|---|---|---|
| script_runs_passed | 0.248 | 6.568 | 12.231 | 50 |
| script_runs | 0.264 | 9.486 | 15.538 | 50 |
| reasoning_tokens | 0.308 | 3335.811 | 5155.385 | 50 |
| completion_tokens | 0.31 | 10053.27 | 15068.308 | 50 |
| max_prompt_tokens | 0.32 | 29327.676 | 39006.154 | 50 |
| actions_per_step | 0.323 | 1.114 | 1.188 | 50 |
| cost_usd | 0.331 | 0.834 | 1.197 | 50 |
| runtime_s | 0.343 | 203.901 | 279.956 | 50 |
| actions | 0.348 | 39.946 | 51.0 | 50 |
| steps | 0.359 | 36.027 | 42.846 | 50 |

### gemini

| feature | AUROC | mean resolved | mean unresolved | n |
|---|---|---|---|---|
| time_to_first_test_s | 0.304 | 108.58 | 151.693 | 31 |
| files_inspected | 0.308 | 4.541 | 5.692 | 50 |
| reasoning_tokens | 0.31 | 15496.757 | 20807.923 | 50 |
| completion_tokens | 0.324 | 21053.243 | 27442.462 | 50 |
| max_prompt_tokens | 0.349 | 37816.514 | 46333.846 | 50 |
| edit_actions | 0.352 | 5.432 | 8.0 | 50 |
| failed_run_then_edit | 0.357 | 0.27 | 0.615 | 50 |
| first_test_frac | 0.363 | 0.581 | 0.68 | 31 |
| runtime_s | 0.368 | 214.062 | 268.238 | 50 |
| time_to_submit_s | 0.368 | 213.808 | 268.238 | 50 |

### minimax

| feature | AUROC | mean resolved | mean unresolved | n |
|---|---|---|---|---|
| reasoning_tokens | 0.193 | 3236.059 | 6557.125 | 50 |
| test_runs_failed | 0.208 | 1.088 | 3.5 | 50 |
| max_prompt_tokens | 0.228 | 24390.471 | 42630.875 | 50 |
| cost_usd | 0.241 | 0.047 | 0.117 | 50 |
| completion_tokens | 0.243 | 9693.735 | 17711.938 | 50 |
| prompt_tokens | 0.248 | 820434.118 | 2488845.875 | 50 |
| search_actions | 0.256 | 3.941 | 8.0 | 50 |
| steps | 0.259 | 51.735 | 86.812 | 50 |
| api_calls | 0.259 | 51.765 | 86.812 | 50 |
| actions | 0.259 | 51.735 | 86.812 | 50 |

### pooled

| feature | AUROC | mean resolved | mean unresolved | n |
|---|---|---|---|---|
| max_prompt_tokens | 0.308 | 30681.583 | 42655.095 | 150 |
| runtime_s | 0.32 | 210.872 | 312.145 | 150 |
| time_to_submit_s | 0.327 | 210.785 | 303.928 | 149 |
| prompt_tokens | 0.333 | 956296.352 | 1881070.548 | 150 |
| actions | 0.337 | 51.185 | 71.69 | 150 |
| completion_tokens | 0.341 | 13708.593 | 19905.5 | 150 |
| search_actions | 0.35 | 4.491 | 6.619 | 150 |
| time_to_first_test_s | 0.351 | 131.112 | 189.738 | 118 |
| steps | 0.355 | 49.843 | 69.167 | 150 |
| api_calls | 0.355 | 49.861 | 69.167 | 150 |

