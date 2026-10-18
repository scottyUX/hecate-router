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
