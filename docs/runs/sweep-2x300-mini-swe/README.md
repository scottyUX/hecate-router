# sweep-2x300-mini-swe — results and post-mortem

First agent-scaffold sweep. 300 SWE-bench Lite tasks x {Qwen2.5-7B, Qwen2.5-72B}
through mini-SWE-agent 2.4.6, replacing Stage-1 single-shot generation and the
unified-diff parser. Run 2026-09-18 on `hecate-exec`.

**Read the caveats before quoting any number.** The run was cut short by a
Docker Hub pull limit and grading was interrupted, so this is a partial,
repo-skewed sample — not a SWE-bench Lite result.

Pipeline design: [`../../agent-pipeline.md`](../../agent-pipeline.md).
Runbook: [`../../running-the-agent-sweep.md`](../../running-the-agent-sweep.md).

---

## Headline

| | 7B | 72B |
|---|---|---|
| attempted | 300 | 300 |
| **actually ran** | **82** | **136** |
| reached `Submitted` | 25 | 76 |
| produced a non-empty patch | 17 | 58 |
| graded | 17 | 55 |
| **patch applied cleanly** | **17 / 17 (100%)** | **55 / 55 (100%)** |
| **RESOLVED** | **2** | **10** |
| cost | $0.30 | $15.24 |

Total spend **$15.54** against a $35 ceiling and a $38 target.

**Every patch that was produced applied cleanly.** That is the clearest result
here, and it is the whole point of the scaffold change. On the parser path,
**269 of 600** generations were discarded before execution because the model's
hand-written `@@` hunk headers did not parse. On the agent path `git diff`
computes the headers, so the arithmetic failure class cannot occur: 72 of 72
graded patches applied.

Failures moved from "we could not read the patch" to "the patch was wrong,"
which is the honest failure and the one the router should learn from.

## What happened

### Docker Hub pull limit killed ~64% of the run

Both arms died mid-run with bursts of:

```
Error processing instance <id>: Command '['docker', 'run', '-d', ... ,
  'docker.io/swebench/sweb.eval.x86_64.<id>:latest', 'sleep', '2h']'
  returned non-zero exit status 125
```

~200 instances failed in **37 seconds** (7B at 04:42, 72B at 06:49). Exit 125
is the daemon refusing before the container starts — the image pull failed.
Anonymous Docker Hub pulls are capped at 100 per 6 hours per IP; the sweep
needed ~600 distinct images and ran both arms concurrently.

Disk was not the cause (239G free, 39% used).

These 382 instances **never called a model**. They have `preds.json` entries
with empty patches but no trajectory, no cost, no exit status. They are
absences, not failures, and must not be counted as unresolved.

### The surviving sample is ~85% django

Instances process in dataset order, so the cut fell on a repo boundary:

| repo | in Lite | ran |
|---|---:|---:|
| django/django | 114 | **114 (100%)** |
| astropy, requests, seaborn, flask | 19 | 19 (100%) |
| sympy/sympy | 77 | 1 (1%) |
| scikit-learn | 23 | 0 |
| pytest, sphinx, pylint | 39 | 0 |
| matplotlib | 23 | 1 |
| xarray | 5 | 1 |

**All 12 resolved instances are django.** This is close to a django specialist
evaluation, on the repo most likely to be well represented in pretraining.

### Grading was interrupted

Killed at 57/58 of the 72B pass (one instance hung; `configs/execution.yaml`
sets `timeout: 1800`, so it should have self-terminated). Hecate writes
`executions.jsonl` only after the harness returns, so **that file does not
exist** — the numbers here are reconstructed from the per-instance
`report.json` files the harness wrote as it went. 72 graded, 3 patches ungraded.

## Failure funnel

```
600 attempted
 ├─ 382  never ran            docker pull limit (exit 125)
 └─ 218  ran
     ├─  75  BadRequestError      context exhausted, submission ""
     ├─  39  RepeatedFormatError  3 consecutive replies with no tool call
     ├─   3  TimeExceeded / RateLimitError
     └─ 101  Submitted
         ├─  26  submitted an EMPTY patch (diffed unedited files)
         └─  75  produced a patch
             ├─   3  ungraded (interrupt)
             └─  72  graded → 72 applied → 12 resolved
```

Exit status predicts patches almost perfectly: only `Submitted` ever yields
one (68% of 7B's, 76% of 72B's).

## Per-arm detail (instances that ran)

| | 7B (n=82) | 72B (n=136) |
|---|---|---|
| patch rate | 20.7% | 42.6% |
| median api_calls | 42 | 19 |
| median cost | $0.0036 | $0.0647 |
| `BadRequestError` share | **57%** | 21% |
| `RepeatedFormatError` share | 12% | 21% |

72B is both more productive and more efficient — roughly 2x the patch rate in
under half the turns.

7B's `BadRequestError` rate is a context artifact, not difficulty. Its context
fills with its own output (84% of tokens, measured on a trajectory), so a task
needing many turns exhausts the 32k window and dies. Direct probes against the
provider: 50,000 chars (25,030 prompt tokens) succeeds, 70,000 fails. Capping
`max_tokens` does not help — at that size the input alone exceeds the window.
mini-SWE has no history trimming (`AgentConfig` exposes only step/cost/wall-time
limits), so there is no config fix.

**7B failures therefore correlate with turn count, not only with difficulty.**
A task it finishes in ~6 turns succeeds; one needing 40+ fails regardless of
whether it could have solved it. Any cross-paper comparison needs this stated —
another paper's 7B number on a long-context model measures something else.

## Routing signal

This is where the partial run hurts most.

Only **6 instances were graded on both arms**: 0 both resolved, 1 only-7B,
1 only-72B, 4 neither. That is far too thin to say anything about routability.

The unverified patch data is more suggestive — of 82 instances both arms ran,
35 disagreed on whether a patch was produced, and **11 went the "wrong" way**
(7B produced one, 72B did not). Non-dominance is what routing needs. But
"produced a patch" is not "resolved," and the resolve-level pairing is n=6.

**A usable Route-AUC needs the full matrix.** That is the main reason to re-run.

## Config deviations from stock mini-SWE

Behavioral settings are **entirely stock** — prompts, templates, submission
protocol, `step_limit: 250`, `max_consecutive_format_errors: 3`, `model_kwargs`.
Changes were operational:

| setting | stock | used | why |
|---|---|---|---|
| `--split` | `dev` | `test` | upstream's batch default is `dev`; Lite results are reported on `test` |
| `agent.cost_limit` | `3.0` | `0.10` / `0.50` | $3 x 600 = $1,800; whole parser sweep cost $0.57 |
| `agent.wall_time_limit_seconds` | `0` | `2700` | backstop against a hung instance |
| `model_kwargs.timeout` | unset | `300` | no timeout upstream; one request hung 11+ min with no retry |
| `MSWEA_GLOBAL_COST_LIMIT` | `0` | `3` / `32` | per-instance caps cannot bound a sweep |

All recorded in the manifests under `config_overrides`.

## Before these numbers are publishable

1. **`docker login`** — a free account raises the pull limit. This is the fix
   for the 382.
2. **Prune `preds.json`** of entries with no trajectory. Upstream resume skips
   anything already listed, so the 382 will be skipped unless removed.
3. **Re-run both arms**, sequentially rather than concurrently (halves the pull
   rate), then the `--convert-only` merge pass.
4. **Re-grade** to completion, producing a real `executions.jsonl`.
5. **Copy trajectories off the VM** — 218 files, needed by `run_train_traj.py`,
   currently on a VM disk only.

Known issue for the re-run: `--convert-only` overwrites the manifest with the
merge invocation's parameters, losing the original run's argv, worker count and
global limits. The manifests here describe the merge pass, not the sweeps.

## Files

| file | contents |
|---|---|
| `resolve-results.csv` | 72 graded instances: model, resolved, applied, FAIL_TO_PASS counts |
| `per-instance.csv` | all 600 records: ran/never-ran, exit status, api_calls, cost, patch size |
| `manifest-miniswe-*.json` | provenance: git commit, config snapshots, per-instance outcomes |

Not committed (too large, on the VM at
`~/hecate-mini/data/outputs/runs/sweep-2x300-mini-swe/`):
trajectories (218), `logs/` with `test_output.txt` and applied `patch.diff`
per graded instance (115MB), `minisweagent.log` per arm, `preds.json` per arm.

## One worked example

`astropy-12907` under 72B, graded during an earlier Mac smoke, shows the new
failure mode end to end. The agent made one `sed` edit whose `\` line
continuations never expanded, injecting literal backslashes into a docstring.
`git diff` produced structurally perfect hunk headers around broken content:

```
patch_applied = true
resolved      = false

E     File "/testbed/astropy/modeling/separable.py", line 268
E   SyntaxError: invalid escape sequence \
```

The old path would have scored this on whether a parser could read a
hand-written diff. This one scores it on whether the code works.
