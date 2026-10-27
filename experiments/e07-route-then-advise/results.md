# Results — E07 Route-then-Advise

Status: Phase 0a pipe smoke complete (`_run-2`). Spec: [`spec.md`](spec.md).
Cannot headline. Not Q7.1.

Student: `openrouter/google/gemini-2.5-flash-lite` on SWE-smith Tenacity,
1 train issue, mini-SWE-agent on `hecate-exec`. VM TERMINATED after the GCS copy.

| run_id | n | instance_id | resolved | steps | `$` | artifacts_uri |
| --- | ---: | --- | --- | ---: | ---: | --- |
| `exp-07_arm-weakalone_split-tenacity_seed-0` | 1 | `jd__tenacity.0d40e76f.pr_425` | no (empty patch; eval aborted) | 40 | 0.00 | none — cost registry missing; eval_server self-loop |
| `exp-07_arm-weakalone_split-tenacity_seed-0_run-2` | 1 | `jd__tenacity.0d40e76f.pr_425` | **unknown** (agent finished; harness reward not trusted) | 7 | 0.0031 | `gs://hecate-506120-artifacts/runs/exp-07_arm-weakalone_split-tenacity_seed-0_run-2` |

`_run-2` is the Phase 0a row. Agent produced a non-empty patch in 7 steps.
`resolved=false` in `results.json` is **not** a harness fail: `eval_server`
still called its own `evaluate_sync` (python-dotenv / `.env` reloaded
`EVAL_SERVER_URL` into that process). Do not treat this as a Tenacity
baseline.

## What Phase 0a is allowed to mean

- Docker worker + agent server + OpenRouter student can complete a run.
- LiteLLM needs `configs/litellm_openrouter_registry.json` via
  `LITELLM_MODEL_REGISTRY_PATH` or cost calculation throws / reports $0.
- `eval_server` must start with `EVAL_SERVER_URL` unset **and** must not
  load `.env`. That is the next code fix before any 3-issue or 49-issue pass.

Forbidden: quoting 7 steps or `$0.0031` as a paper comparison.

## Train-set probe, 18 Oct 2026

Student: `openrouter/google/gemini-2.5-flash-lite`. One pass, `--max_workers 1`.
Worker: `hecate-worker` in `whatsapp-sales-agent`. Not a paper comparison.
The paper's 61.2% is Gemini 2.5 Flash on the 49 test issues.

| run_id | n | resolved | not resolved | errors | `$` | artifacts |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `exp-07_arm-weakalone_split-tenacitytrain_seed-0_run-9` | 56 | 3 (5.4%) | 8 | 45 (80.4%) | 0.45 | `gs://hecate-506120-artifacts/runs/exp-07_arm-weakalone_split-tenacitytrain_seed-0_run-9` |

Earlier rows in this file stay in that same bucket. A second copy of `_run-9` is also in `gs://whatsapp-sales-agent-hecate-artifacts`.

This does **not** pass the training gate. The gate is errors about 0 and at least 9 of 56 resolved. Here 45 issues died before a score. OpenRouter returned: the request needs more credits, or fewer max tokens (it could only afford 1518 of 8192). The 3 resolves are real Docker scores. The 5.4% is not a student baseline.

Steps on the 3 resolves averaged 22.3. The other 53 rows averaged 4.5 steps because most of them aborted.

`_run-8` is the trusted one-issue check that preceded this probe: `jd__tenacity.0d40e76f.pr_425`, resolved, 8 steps, $0.0038, one Docker eval. `_run-6` was a Gemini-key 404 (`gemini-2.5-flash-lite` is closed to new keys). `_run-7` died because the OpenRouter price file was not loaded. Do not use those as baselines.

The 49-issue Flash-Lite pass (`…_split-tenacityval_seed-0_run-4`) then ran and returned 49 errors and $0. Flash was stopped after it started, for the same empty balance. Neither 49-issue file is a model comparison.

## One pass after credits, 18 Oct 2026

OpenRouter balance was topped up. Student calls use `openrouter/google/…` with the price file set. One pass each, `--max_workers 1`, 0 errors except the single training-set error below. Artifacts are in `gs://hecate-506120-artifacts/runs/<run_id>`.

| run | split | model | resolved | steps | `$` |
| --- | --- | --- | ---: | ---: | ---: |
| `_run-10` | 56 train | Flash-Lite | 17/56 (30.4%) | 20.7 (solved 14.1) | 2.30 |
| `_run-5` | 49 test | Flash-Lite | 22/49 (44.9%) | 23.8 (solved 21.1) | 2.97 |
| `_run-2` | 49 test | Flash | 31/49 (63.3%) | 19.4 (solved 16.8) | 3.76 |

Paper, same 49 test issues, Flash, repeated-run average: 61.2% and 19.1 steps. This Flash pass is one run, not that average. It is the harness check. The 56-row is the training gate (errors about 0, at least 9/56). It passes. It is not the paper comparison.

## Untrained advisor vs Flash-Lite alone, joined 23 Oct 2026

`compare_swe_arms.py` on the two session maps. Kept 49. Dropped 0. An issue that errored in either file would have been dropped from both.

| arm | file | errors in file | resolved | mean steps | steps on solved |
| --- | --- | ---: | ---: | ---: | ---: |
| weakalone | `exp-07_arm-weakalone_split-tenacityval_seed-0_run-5` | 0 | 22/49 (44.9%) | 23.8 | 21.1 |
| untrained | `exp-07_arm-untrained_split-tenacityval_seed-0_run-3` | 0 | 7/49 (14.3%) | 21.9 | 15.9 |

Paired difference, weakalone minus untrained: resolve +30.6% [+16.3%, +44.9%], steps +1.9 [−3.3, +7.1]. The script's check-1 step gap is 1.94. That is one pair of passes, not the six-file mean. Code: run-5 is `3ada694`. Run-3 was the uncommitted tree later committed as `93678ef`. The `CODE_SHA` file in that run directory was written after the pass, once that commit existed. It does not mean run-3 executed a checkout of `93678ef` at the time. Untrained cost on run-3 was $3.16. The unsuffixed untrained attempt (26 errors) and untrained `_run-2` are not in this join. Maps for run-3 and student-alone run-6 are in `gs://whatsapp-sales-agent-hecate-artifacts/runs/`.

## Check 1, six-file join, 24 Oct 2026

`compare_swe_arms.py` on the six files named in `spec.md` (three-pass rule, recorded before the extra passes). Student: `openrouter/google/gemini-2.5-flash-lite`. Advisor (untrained): base `Qwen/Qwen2.5-7B-Instruct`, short-context eval (task, last advice, latest observation, 1,024-token replies). `--max_workers 1`, one pass per file.

| arm | file | CODE_SHA | errors in file | resolved | mean steps | `$` |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| weakalone | `exp-07_arm-weakalone_split-tenacityval_seed-0_run-5` | `3ada694` | 0 | 22/49 | 23.8 | 2.97 |
| weakalone | `exp-07_arm-weakalone_split-tenacityval_seed-0_run-6` | `93678ef` | 1 | 13/49 | 24.4 | 2.69 |
| weakalone | `exp-07_arm-weakalone_split-tenacityval_seed-0_run-7` | `93678ef` | 1 | 13/49 | 27.2 | 3.24 |
| untrained | `exp-07_arm-untrained_split-tenacityval_seed-0_run-3` | `93678ef` | 0 | 7/49 | 21.9 | 3.16 |
| untrained | `exp-07_arm-untrained_split-tenacityval_seed-0_run-4` | `93678ef` | 0 | 6/49 | 21.5 | 2.85 |
| untrained | `exp-07_arm-untrained_split-tenacityval_seed-0_run-5` | `93678ef` | 0 | 6/49 | 24.9 | 3.98 |

Per-file mean steps here include errored rows; the join below drops them. Run-3's `CODE_SHA` was written after the pass (see above).

Kept 47. Dropped 2, from both arms, because they errored in a student-alone file:

- `jd__tenacity.0d40e76f.combine_file__1n8ql04e`: `_run-6`, "Agent step timeout after 600s"
- `jd__tenacity.0d40e76f.func_pm_ctrl_shuffle__6vzkm0lh`: `_run-7`, "Agent step timeout after 600s"

Both are the agent server's 600 s idle-session cleanup on a single 40-step request (student-alone arm only), not student failures.

Three-pass means on the 47 kept issues:

| arm | repeats | resolve | mean steps | steps on resolved |
| --- | ---: | ---: | ---: | ---: |
| weakalone | 3 | 34.0% | 25.7 | 19.9 |
| untrained | 3 | 13.5% | 22.0 | 16.8 |

Paired difference, weakalone minus untrained (bootstrap over issues): resolve +20.6% [+12.1%, +29.8%], steps +3.7 [+0.6, +6.7].

**Verdict: check 1 passes.** Rule (`spec.md` §5 and the three-pass amendment): the untrained mean is at least 2 steps below student-alone (3.7) and untrained resolve is below student-alone (−20.6 points). The step gap's lower 95% bound (+0.6) is under 2; the rule is on the point estimate. This is a pass for the short eval context only.

Untrained `_run-5` is attempt 3. Attempt 1 was stopped by hand at 22/49 (VM stop, 23 Oct 23:00 PDT). Attempt 2 was preempted at 43/49 (Spot, 24 Oct 01:09 PDT). Attempt 3 ran all 49 on on-demand provisioning, same commit and flags, exit 0. Attempt logs are kept as `eval.attempt1.log` and `eval.attempt2.log` in that run dir. Only attempt 3's map is a gate file.

Artifacts: the six maps are in `gs://whatsapp-sales-agent-hecate-artifacts/runs/<run_id>/` (student-alone `_run-5` as `exp-07_arm-weakalone_split-tenacityval_seed-0_run-5.json` in its run dir). Join output: `gs://whatsapp-sales-agent-hecate-artifacts/runs/exp-07_check1_split-tenacityval_seed-0/check1.json` and `check1_stdout.txt`. After the join, `gpu-advisor` and `hecate-worker` were stopped. Training has not started.

## Codex harness, GPT-5-nano with the step-295 advisor, 28 Oct 2026

Exploratory transfer, not Q7.1. Student `openai/gpt-5-nano` (medium reasoning) in Codex CLI 0.164.0 through the E7 proxy (40-step cap, mini-swe-agent's `<advice>` wrapper, advice every 5 requests). Advisor `global_step_295` on one L4 (vLLM 0.9.2, bf16, E7 sampling). 49 Tenacity test issues, three passes per arm, 0 errors. Details and rule: `spec.md`, "GPT-5-nano stage 2 result".

| arm | resolved per pass | resolve | mean steps | steps on resolved |
| --- | --- | ---: | ---: | ---: |
| alone | 32, 25, 29 | 58.5% | 11.1 | 10.5 |
| advised | 32, 35, 32 | 67.3% | 10.1 | 9.3 |

Advised minus alone: resolve +8.8 points [+2.7, +15.6], steps −0.94 [−1.93, +0.05]. "Raises resolve" holds; "cuts steps" does not. Earlier Codex students: gpt-6-luna 42/49 (too strong), Flash-Lite 7/49 after the harness fixes (too weak in Codex; `apply_patch` does not reach Gemini as a callable tool). Artifacts: `gs://hecate-506120-artifacts/runs/` and `gs://whatsapp-sales-agent-hecate-artifacts/runs/` (`exp-07_arm-codex5nano*`, `exp-07_codex5nano_split-tenacityval_seed-0`). VMs `advisor-l4` and `hecate-worker` stopped; disk `advisor-ckpt-clone` kept.
