# three-model-verified — interim results

> **Interim.** Gemini 3 Flash has run all 100 tasks. Claude Opus 4.5 (70/100)
> and MiniMax M2.5 (87/100) were stopped when the OpenRouter account ran out of
> credits; their remaining 30 + 13 tasks are queued and every number below
> will be regenerated once they run. Cross-model comparisons use only the 70
> tasks graded for all three models, and **those 70 are not a random subset**
> (see [Caveats](#caveats)).

Three models through the same mini-SWE-agent scaffold on the same 100
SWE-bench Verified tasks, graded by the existing SWE-bench harness, with full
trajectories kept for routing analysis. Run 2026-10-05 on `hecate-exec`.
Infrastructure is the gpt-5-mini sanity check's
([`../verified-sanity-gpt5mini/`](../verified-sanity-gpt5mini/)), so
differences should come from the models, not the pipeline.

## Context

Hecate needs to know where models' capabilities overlap and where they
diverge, at what cost, and whether anything observable during an attempt
predicts its outcome. This run measures all three on identical tasks so their
outcomes can be compared per task, not only in aggregate.

## Method

**Models** (all via OpenRouter, provider pinned, no fallbacks outside the
listed providers, reasoning at each model's OpenRouter default):

| model | OpenRouter slug | canonical version | providers (order) | served by (observed) |
|---|---|---|---|---|
| Claude Opus 4.5 | `anthropic/claude-opus-4.5` | `claude-4.5-opus-20251124` | anthropic, amazon-bedrock, google-vertex | Anthropic (all calls) |
| Gemini 3 Flash | `google/gemini-3-flash-preview` | `gemini-3-flash-preview-20251217` | google-ai-studio, google-vertex | Google AI Studio (1 Vertex call seen in a mid-run sample) |
| MiniMax M2.5 | `minimax/minimax-m2.5` | `minimax-m2.5-20260211` | minimax | MiniMax (all calls) |

Gemini 3 Flash is a **preview** model and can change behind the same slug;
results are tied to the run date.

**Tasks**: 100 SWE-bench Verified test instances drawn uniformly at random
(seed `20261005`, sorted by `instance_id` before sampling), fixed in
[`configs/three_model_tasks.json`](../../../configs/three_model_tasks.json)
before any model was called (commit `1cf0757`). Difficulty mix (Verified's own
annotation): 40 `<15 min`, 50 `15 min – 1 hour`, 10 `1–4 hours`. 50 are django.

**Agent**: mini-swe-agent 2.4.6, [`configs/miniswe_three_model.yaml`](../../../configs/miniswe_three_model.yaml).
Prompt, templates, `step_limit: 250` and environment are byte-identical to the
sanity check (a test enforces this). Model block differs: per-model name and
provider order, Anthropic-style `cache_control` on the latest message (applied
to all three), 600 s request timeout, no pinned reasoning effort.

**Execution**: three concurrent `mini-extra swebench` processes (one per
model, 4 workers each, separate output dirs) on an e2-standard-8. All 100
images pre-pulled under an authenticated Docker Hub Pro account before any
spend (unlimited pulls; the Lite sweep lost 382/600 instances to the anonymous
limit). Graded with `swebench.harness.run_evaluation` (swebench 4.1.0) against
`SWE-bench/SWE-bench_Verified`.

**Budget**: no per-task cost cap. Per-process caps summing to $250
(Opus $185, Gemini $40, MiniMax $25) via `MSWEA_GLOBAL_COST_LIMIT`. None was
reached; the account balance ran out first.

**Infra vs. model failures**: an instance the harness ended before the model
had a real attempt (no trajectory, the litellm cost-calculation crash, or an
OpenRouter 402) is an infra failure: re-queued, never graded, never counted.
Running out of steps (`LimitsExceeded`, 250 calls) is the model's outcome and
is kept.

Scripts: `scripts/run_three_model.py`, `scripts/launch_three_model.sh`,
`scripts/grade_three_model.sh`, `scripts/extract_traj_features.py`,
`scripts/analyze_three_model.py`.

## Result (interim)

Spend so far (OpenRouter-billed cost in the trajectories): **$81.23**
(Opus $59.04, Gemini $16.55, MiniMax $5.64), plus ~$1 of attempts discarded as
infra failures.

### Resolved rate

Wilson 95% CIs in brackets.

| model | all its graded tasks | on the 70 common | `<15 min` | `15 min – 1 h` | `1–4 h` |
|---|---|---|---|---|---|
| Opus 4.5 | 57/70 — 81.4% (71–89) | **81.4%** | 21/27 | 31/37 | 5/6 |
| MiniMax M2.5 | 67/87 — 77.0% (67–85) | **74.3%** | 28/35 | 34/45 | 5/7 |
| Gemini 3 Flash | 63/100 — 63.0% (53–72) | **60.0%** | 28/40 | 32/50 | 3/10 |

Gemini's drop on the hardest bucket (3/10 on `1–4 h` vs 70% on `<15 min`) is
the largest difficulty effect in the run.

### Efficiency

| model | $/task | $/resolved | API calls (mean / median) | runtime s (median) |
|---|---|---|---|---|
| Opus 4.5 | 0.84 | 1.04 | 37 / 30 | 129 |
| Gemini 3 Flash | 0.17 | 0.26 | 57 / 35 | 83 |
| MiniMax M2.5 | 0.06 | 0.08 | 52 / 38 | 127 |

### Cross-model (70 tasks graded for all three)

- Solved by all three: **38**. Solved by none: **10**.
- Solved by exactly one: Opus **5**, Gemini **1**, MiniMax **1**.
- Solved by exactly two: Opus+MiniMax **12**, Opus+Gemini **2**, Gemini+MiniMax **1**.

| pair | agreement | Cohen's κ | discordant | exact McNemar p |
|---|---|---|---|---|
| Opus vs Gemini | 72.9% | 0.38 | Opus 17 / Gemini 2 | **0.0007** |
| Opus vs MiniMax | 87.1% | 0.63 | Opus 7 / MiniMax 2 | 0.18 |
| Gemini vs MiniMax | 77.1% | 0.49 | Gemini 3 / MiniMax 13 | **0.021** |

**Oracle router** (per task, cheapest model that resolves it; cheapest attempt
if none does): **85.7% resolved for $17.07**, vs. always-Opus 81.4% for
$59.04, always-MiniMax 74.3% for $4.60, always-Gemini 60.0% for $12.14.

### Trajectory features vs. outcome

AUROC of each process feature for resolved vs. unresolved (0.5 = no signal,
<0.5 = higher values go with *unresolved*). Strongest per group:

| group (n) | feature | AUROC | mean resolved | mean unresolved |
|---|---|---|---|---|
| pooled (257) | prompt tokens | 0.36 | 0.78M | 1.50M |
| pooled (257) | steps | 0.37 | 44 | 66 |
| MiniMax (87) | first edit step | 0.32 | 14 | 24 |
| MiniMax (87) | time to first edit (s) | 0.32 | 42 | 76 |
| Gemini (100) | peak context (tokens) | 0.30 | 16.3k | 24.0k |
| Gemini (100) | first test, fraction of run | 0.66 | 0.82 | 0.69 |
| Opus (70) | prompt tokens (strongest) | 0.39 | — | — |

Full tables: [`analysis-interim.md`](analysis-interim.md).

### Comparison with the SWE-bench leaderboard

Matched against the published mini-SWE-agent "bash only" entries for the same
three models (`20260217_mini-v2.0.0_{claude-4-5-opus,gemini-3-flash,minimax-2-5}-high`),
per task, on the tasks we graded. Their trajectories (public, the Docent
dashboards linked from each entry) were run through the same feature
extractor. Full report:
[`leaderboard-comparison-interim.md`](leaderboard-comparison-interim.md)
(`scripts/compare_three_model_leaderboard.py --trajectories`).

| model | leaderboard on our 100 | on tasks we graded: ours vs. leaderboard | agreement | κ | McNemar p |
|---|---|---|---|---|---|
| Opus 4.5 | 74% | 81.4% vs 75.7% (n=70) | 88.6% | 0.66 | 0.29 |
| Gemini 3 Flash | 73% | **63.0% vs 73.0%** (n=100) | 82.0% | 0.59 | **0.031** |
| MiniMax M2.5 | 72% | 77.0% vs 73.6% (n=87) | 82.8% | 0.54 | 0.61 |

**Opus and MiniMax reproduce the leaderboard; Gemini does not, and the
cause is visible in the trajectories.** The leaderboard ran all three at
`reasoning_effort: high`; we ran each at its OpenRouter default:

| model | reasoning tokens / task (median): ours vs. lb | steps | repo test-suite runs | first edit step | peak context | $/task |
|---|---|---|---|---|---|---|
| Opus 4.5 | 0 vs 1,661 | 30 vs 28.5 | 4 vs 4 | 11 vs 11 | 21.9k vs 22.8k | 0.84 vs 0.79 |
| Gemini 3 Flash | **0 vs 14,508** | **35 vs 52** | **0 vs 3** | **10 vs 16** | **16.9k vs 51.7k** | **0.17 vs 0.36** |
| MiniMax M2.5 | 2,663 vs 3,138 | 38 vs 50 | 5 vs 5 | 12 vs 17 | 19.8k vs 23.7k | 0.07 vs 0.09 |

Without reasoning, Gemini explores less, edits sooner, usually never runs the
repo's own tests, and submits earlier at half the cost, and resolves 10
points less. Opus behaves the same with or without its (small) high-effort
thinking budget, and MiniMax reasons by default either way. So our Gemini
number measures **Gemini 3 Flash without thinking**, not the model as
benchmarked.

**Scaffold version (2.1.0 there vs 2.4.6 here), checked by diffing the two
releases' source.** The Docker environment and cache-control code are
identical. Two changes on the run path matter:

- **Python environment.** 2.4.6's SWE-bench config sets `BASH_ENV=/root/.bashrc`
  so every agent command runs in the image's `testbed` conda env; 2.1.0 does
  not. In the leaderboard trajectories, 50–63% per model hit
  `ModuleNotFoundError` for the repo's own package (ours: 0–4 of 52 sampled),
  and the agents mostly recovered with `pip install -e .` into the base env
  (116) or `PYTHONPATH` (53). Usually ~1 wasted step, but it also means
  leaderboard agents often verified fixes in a different environment from
  the one grading uses. This favours *our* runs, consistent with our Opus
  and MiniMax being slightly (not significantly) higher, and it cannot
  explain Gemini being lower.
- **Format errors.** 2.4.6 stops a run after 3 consecutive replies without a
  valid tool call (`RepeatedFormatError`) and adds a hint when a reply was
  cut off at the token limit. No run here ended that way.

The rest is cosmetic (a renumbered step list in the prompt, progress display,
other benchmarks and model wrappers we do not use).

Other leaderboard differences (none explains a model-specific gap): direct Anthropic/Gemini APIs vs OpenRouter, MiniMax unpinned on
the leaderboard (MiniMax/Novita/Fireworks) vs pinned here, a $3 per-task cap
there vs none here, Opus with the interleaved-thinking beta header there.

**Routing on the leaderboard's own results (our 100 tasks):** the three are
statistically tied (74/73/72%, all pairwise p ≥ 0.79, κ 0.65–0.72), and the
cheapest-correct oracle reaches **82% for $13.99** vs always-Opus 74% for
$80.42. Same shape as ours: the headroom is mostly cost, and with Gemini at
full strength there is more non-dominance (only-one: Opus 4, Gemini 2,
MiniMax 3).

## Interpretation

- **Routing headroom exists and is mostly cost, not accuracy.** The oracle
  beats always-Opus by 4.3 points while spending 29% as much: most tasks Opus
  solves, a cheaper model also solves. That is the case Hecate is built for.
- **MiniMax is close to Opus at ~1/12 the cost per resolved task.** On the 70
  common tasks the gap (81.4% vs 74.3%) is not significant (p = 0.18, 9
  discordant tasks), and the two agree on 87% of tasks (κ = 0.63).
- **Gemini 3 Flash is clearly weaker here**, significantly below both others,
  and nearly all of its disagreements with Opus go Opus's way (17 vs 2). The
  leaderboard comparison shows why: this is Gemini *without reasoning*. At
  `reasoning_effort: high` it ties the other two on these tasks. The
  ranking is a property of the configuration, not only the model.
- **Non-dominance is thin but present**: 1 task Gemini alone solves, 1
  MiniMax alone, 2 Gemini+MiniMax that Opus misses. A pure "escalate to Opus"
  router loses these; they are too few to say whether they are signal or noise.
- **Length is the shared failure signal.** Across models, failed runs are
  longer and burn more context; for MiniMax, a late first edit (still
  exploring at step ~24) predicts failure. That supports mid-trajectory
  escalation (route away from a run that is still searching after N steps)
  as something worth testing. Per-model n is small and these are univariate
  AUROCs: exploratory, not a result.
- Opus's process features carry almost no signal (all AUROC ≥ 0.39): it fails
  without looking different from when it succeeds.

## Caveats

- **The 70-task common set is not random.** mini-SWE runs instances in
  dataset order, which SWE-bench groups by repo, so the credit cut-off kept
  the first 70 in that order: 50 django, 8 matplotlib, 5 astropy, 3 requests,
  3 xarray, 1 scikit-learn, and 0 sympy, sphinx, pylint or pytest
  (27 `<15 min`, 37 `15 min – 1 h`, 6 `1–4 h`). Cross-model numbers and the oracle are a
  django-heavy comparison until the remaining tasks run. Opus's per-repo row
  is missing sympy and sphinx entirely.
- **Single attempt per (model, task), temperature unpinned.** The sanity
  check matched the leaderboard on 10/13 under the same conditions; expect
  run-to-run noise of a few tasks per model.
- **CPU contention.** For ~15 minutes, grading ran alongside the MiniMax
  agent and load reached 11–17 on 8 vCPUs. Agent commands have a 60 s
  timeout. Trajectories with any command timeout: MiniMax 3, Gemini 2,
  Opus 0. Not yet checked whether MiniMax's 3 fall in the contended window
  or are ordinary slow commands.
- **Reasoning differs by model at default settings.** MiniMax reports
  reasoning tokens on all 87 runs; Opus reports none (extended thinking is
  off unless requested); Gemini reports none, either because it did not
  reason at its OpenRouter default or because they are not reported
  (unverified). "Same config" therefore does not mean "same reasoning
  budget".
- **Per-feature AUROCs are univariate and unadjusted** for the many features
  tested.

## Deviations from the proposal

| proposal | this run | why |
|---|---|---|
| 50 random + 50 difficulty-controlled tasks | 100 random | operator decision before launch |
| same model behaviour as the leaderboard | reasoning at each model's OpenRouter default (Gemini: none) | not pinned at launch; the leaderboard used `reasoning_effort: high` for all three, which accounts for the Gemini gap (see comparison) |
| (per-task budget implied) | no per-task cost cap; per-model global caps summing to $250 | operator decision |
| identical setup to the sanity check | + `cache_control`, 600 s timeout, no pinned reasoning effort | Opus re-bills full history every step without caching; hung requests seen in the Lite sweep; one reasoning setting means different things per provider |
| all models identical config | Gemini only: `cost_tracking: ignore_errors` | litellm returned $0 for some Gemini calls and mini-SWE killed the instance (4 instances, re-queued); OpenRouter's billed cost is still recorded per call |
| 300 runs | 257 so far | OpenRouter credits exhausted; 6 Opus instances killed by 402s were re-queued |

## Incidents

1. **Gemini $0 cost crash** (~20:30 UTC). 4 instances ended with `RuntimeError:
   Error calculating cost ... Cost must be > 0.0`. Fixed (`d871d61`), Gemini
   restarted, the 4 re-queued; their first attempts are kept under
   `gemini/_infra_failed/` on the VM.
2. **OpenRouter credits exhausted** (~21:20 UTC). The VM's key's account
   reached $133.94 of $135. Opus instances then failed with HTTP 402
   (`in_flight_budget_exhausted`, `requires more credits`); 6 were re-queued
   (`970a3a4`, `fe4de72`). Opus and MiniMax were stopped; Gemini had finished.
3. **Missing run manifests for Opus and MiniMax.** `run_three_model.py` writes
   its run manifest only when `mini-extra` returns; both were stopped with
   `tmux kill-session`. Provenance for those runs is in the convert manifests
   under [`manifests/`](manifests/) and in each trajectory's `info.config`.
4. **`git_commit` is null in every manifest**: the VM copy is synced without
   `.git`. Code in use: `1cf0757` at launch, `d871d61` for Gemini from its
   restart, `fe4de72` for conversion and grading.

## Next

- Add credits (~$30), then on the VM: `bash scripts/launch_three_model.sh start`
  (restarts only Opus and MiniMax; re-queued instances included).
- `--convert-only` each, `bash scripts/grade_three_model.sh start opus minimax`
  (resumes; grades only new instances), then `scripts/analyze_three_model.py`.
- Replace the `-interim` files and this README's numbers with the full-run
  ones; drop the common-set caveat if the full 100 complete.
- Copy trajectories and harness logs off the VM before stopping it.
- Check whether MiniMax's 3 timeout trajectories fall in the contended window.
- Routing: build 3-model labels from `per_task.csv`; test a step-count
  escalation rule against the oracle.
- Decide whether to re-run Gemini at `reasoning_effort: high` (~$36 for 100
  tasks at the leaderboard's cost) so the comparison is model-vs-model, or
  keep "Gemini without thinking" as a deliberately cheap tier.

## Files

| file | contents |
|---|---|
| `analysis-interim.md` | full generated report (per-repo rates, all feature tables) |
| `summary-interim.json` | every number in the report |
| `per_task-interim.csv` | one row per (model, task): status, resolved, cost, ~35 trajectory features |
| `manifests/` | per-model run/convert manifests (config snapshot, overrides, outcomes) |

Not committed (on the VM at `~/hecate-mini/data/outputs/runs/three-model-verified/`):
trajectories, `preds.json`, `generations.jsonl`, `executions.jsonl`, harness
logs and reports.
