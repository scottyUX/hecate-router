# Three-model SWE-bench Verified: analysis

Generated 2026-10-05T22:05:46Z. Tasks: 100 (`configs/three_model_tasks.json`). Resolved rates exclude infra failures and ungraded runs; brackets are Wilson 95% CIs.

## Coverage

| model | attempted | infra failures | missing | ungraded | exit statuses |
|---|---|---|---|---|---|
| opus | 70 | 0 | 30 | 0 | Submitted 70 |
| gemini | 100 | 0 | 0 | 0 | LimitsExceeded 5, Submitted 95 |
| minimax | 87 | 0 | 13 | 0 | LimitsExceeded 1, Submitted 86 |

## Resolved rate

| model | overall | <15 min fix | 15 min - 1 hour | 1-4 hours | >4 hours |
|---|---|---|---|---|---|
| opus | 57/70 (81.4%, 71–89) | 21/27 (77.8%, 59–89) | 31/37 (83.8%, 69–92) | 5/6 (83.3%, 44–97) | – |
| gemini | 63/100 (63.0%, 53–72) | 28/40 (70.0%, 55–82) | 32/50 (64.0%, 50–76) | 3/10 (30.0%, 11–60) | – |
| minimax | 67/87 (77.0%, 67–85) | 28/35 (80.0%, 64–90) | 34/45 (75.6%, 61–86) | 5/7 (71.4%, 36–92) | – |

### By repo

| repo | opus | gemini | minimax |
|---|---|---|---|
| django/django | 44/50 (88.0%, 76–94) | 30/50 (60.0%, 46–72) | 39/50 (78.0%, 65–87) |
| sympy/sympy | – | 7/11 (63.6%, 35–85) | – |
| matplotlib/matplotlib | 5/8 (62.5%, 31–86) | 4/8 (50.0%, 22–78) | 4/8 (50.0%, 22–78) |
| sphinx-doc/sphinx | – | 5/8 (62.5%, 31–86) | 5/6 (83.3%, 44–97) |
| scikit-learn/scikit-learn | 1/1 (100.0%, 21–100) | 6/7 (85.7%, 49–97) | 7/7 (100.0%, 65–100) |
| astropy/astropy | 2/5 (40.0%, 12–77) | 2/5 (40.0%, 12–77) | 3/5 (60.0%, 23–88) |
| pydata/xarray | 3/3 (100.0%, 44–100) | 4/5 (80.0%, 38–96) | 4/5 (80.0%, 38–96) |
| psf/requests | 2/3 (66.7%, 21–94) | 2/3 (66.7%, 21–94) | 2/3 (66.7%, 21–94) |
| pylint-dev/pylint | – | 2/2 (100.0%, 34–100) | 2/2 (100.0%, 34–100) |
| pytest-dev/pytest | – | 1/1 (100.0%, 21–100) | 1/1 (100.0%, 21–100) |

## Efficiency

| model | total $ | $/task | $/resolved | API calls (mean / median) | steps (mean) | runtime s (mean / median) |
|---|---|---|---|---|---|---|
| opus | 59.0358 | 0.8434 | 1.0357 | 37.24 / 30.0 | 37.24 | 173.0 / 129.1 |
| gemini | 16.5526 | 0.1655 | 0.2627 | 57.44 / 35.0 | 57.2 | 124.0 / 83.3 |
| minimax | 5.6425 | 0.0649 | 0.0842 | 52.2 / 38 | 52.2 | 190.7 / 126.7 |

## Cross-model (n=70 tasks graded for all models)

- Solved by all: **38**
- Solved by none: **10**
- Solved by only one: opus **5**, gemini **1**, minimax **1**
- Solved by exactly two: opus+gemini **2**, opus+minimax **12**, gemini+minimax **1**

| pair | agreement | Cohen's κ | discordant | McNemar p |
|---|---|---|---|---|
| opus vs gemini | 72.9% | 0.379 | opus 17 / gemini 2 | 0.0007 |
| opus vs minimax | 87.1% | 0.63 | opus 7 / minimax 2 | 0.1797 |
| gemini vs minimax | 77.1% | 0.494 | gemini 3 / minimax 13 | 0.0213 |

**Oracle router** (per task, cheapest model that resolves it): 85.7% resolved for $17.0745, vs. single models: opus 81.4% for $59.0358, gemini 60.0% for $12.1416, minimax 74.3% for $4.5951. This is the routing headroom on this task set.

## Trajectory features vs. outcome

AUROC of each process feature for resolved vs. unresolved (0.5 = no signal; >0.5 = higher with resolved). Top 10 by distance from 0.5. Small n per model: treat as exploratory.

### opus

| feature | AUROC | mean resolved | mean unresolved | n |
|---|---|---|---|---|
| prompt_tokens | 0.386 | 913767.14 | 739211.077 | 70 |
| search_actions | 0.395 | 3.228 | 3.846 | 70 |
| max_prompt_tokens | 0.398 | 27085.175 | 27883.462 | 70 |
| steps | 0.404 | 37.123 | 37.769 | 70 |
| api_calls | 0.404 | 37.123 | 37.769 | 70 |
| cost_usd | 0.406 | 0.865 | 0.75 | 70 |
| actions | 0.411 | 40.316 | 40.615 | 70 |
| test_runs_passed | 0.414 | 3.965 | 4.615 | 70 |
| tracebacks | 0.586 | 1.737 | 1.077 | 70 |
| script_runs_passed | 0.419 | 8.86 | 10.0 | 70 |

### gemini

| feature | AUROC | mean resolved | mean unresolved | n |
|---|---|---|---|---|
| max_prompt_tokens | 0.3 | 16250.127 | 24025.324 | 100 |
| prompt_tokens | 0.324 | 551960.937 | 1156015.216 | 100 |
| first_test_frac | 0.657 | 0.817 | 0.691 | 49 |
| cost_usd | 0.345 | 0.132 | 0.223 | 100 |
| completion_tokens | 0.345 | 5118.778 | 8552.757 | 100 |
| runtime_s | 0.358 | 103.283 | 159.309 | 100 |
| first_edit_frac | 0.63 | 0.38 | 0.285 | 97 |
| steps | 0.382 | 48.032 | 72.811 | 100 |
| api_calls | 0.382 | 48.286 | 73.027 | 100 |
| actions | 0.382 | 48.032 | 72.811 | 100 |

### minimax

| feature | AUROC | mean resolved | mean unresolved | n |
|---|---|---|---|---|
| time_to_first_edit_s | 0.319 | 41.521 | 75.615 | 87 |
| first_edit_step | 0.322 | 13.985 | 24.45 | 87 |
| search_actions | 0.338 | 3.328 | 5.6 | 87 |
| first_test_step | 0.339 | 26.188 | 43.15 | 84 |
| steps | 0.343 | 46.328 | 71.85 | 87 |
| api_calls | 0.343 | 46.328 | 71.85 | 87 |
| actions | 0.343 | 46.328 | 71.85 | 87 |
| prompt_tokens | 0.347 | 886671.776 | 2622316.2 | 87 |
| completion_tokens | 0.348 | 10474.328 | 17692.0 | 87 |
| time_to_first_test_s | 0.348 | 89.119 | 158.478 | 84 |

### pooled

| feature | AUROC | mean resolved | mean unresolved | n |
|---|---|---|---|---|
| prompt_tokens | 0.359 | 782167.246 | 1497551.871 | 257 |
| api_calls | 0.371 | 44.182 | 66.143 | 257 |
| steps | 0.372 | 44.096 | 66.029 | 257 |
| actions | 0.375 | 45.07 | 66.557 | 257 |
| max_prompt_tokens | 0.376 | 22452.406 | 29108.443 | 257 |
| helper_files_written | 0.406 | 5.813 | 7.043 | 257 |
| completion_tokens | 0.407 | 8222.749 | 11039.614 | 257 |
| inspect_actions | 0.413 | 19.021 | 30.271 | 257 |
| runtime_s | 0.414 | 147.126 | 194.079 | 257 |
| first_edit_frac | 0.584 | 0.366 | 0.322 | 253 |

