# Agent pipeline (mini-SWE-agent)

Replaces Stage-1 single-shot generation + unified-diff parsing with an agent that
edits files in a container. Stages 2-4 (execution, labels, router) are unchanged.

Verified end to end on 2026-09-14 — see [Traced run](#traced-run).

## Old pipeline (parser path)

```
                   configs/option_a.yaml
                            |
  SwebenchTask ---> render_prompt() -------> one API call
  (issue text)      + ORACLE context         (temperature 0)
                    = gold-patch files             |
                                                   v
                                            raw_response
                                          (prose + a diff)
                                                   |
                                                   v
                                    extract_patch()  <-- unidiff
                                    src/hecate/generation/patch.py
                                                   |
                              +--------------------+--------------------+
                              | patch_parse_ok=True             =False  |
                              v                                         v
                       extracted_patch                          DISCARDED
                              |                            (269 / 600 records)
                              v
                       generations.jsonl
                              |
                              v
                     run_execution.py  --> executions.jsonl --> labels --> router
```

**Failure mode:** the model hand-writes `@@ -a,b +c,d @@` headers. One miscount
and unidiff rejects an otherwise-correct fix. 269 of 600 records were lost this
way; 33 of 43 audited cases were arithmetic errors, not bad fixes.

## New pipeline (agent path)

```
                  configs/option_a.yaml + configs/miniswe.yaml
                            |
  SwebenchTask ---> mini-extra swebench (batch, upstream)
  (issue text        |
   only, NO          |  docker run swebench/sweb.eval.x86_64.<instance>
   oracle files)     |  agent loop, <= 250 steps:
                     |      THOUGHT -> bash tool call -> observation
                     |      (edits files directly: sed, heredoc, python)
                     |  then: git diff -- <paths> > patch.txt
                     |        echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt
                     v
        <out>/<model>/preds.json          {instance_id: {model_patch}}
        <out>/<model>/<inst>/<inst>.traj.json   full message history
                     |
                     v
        src/hecate/agent/convert.py
          model_patch  -> extracted_patch
          submitted?   -> patch_parse_ok
          exit_status  -> decoding_params
          repo/commit  -> load_swebench_lite()
                     |
                     v
              generations.jsonl        (SAME SCHEMA AS BEFORE)
                     |
                     v
            run_execution.py --> executions.jsonl --> labels --> router
                  (UNCHANGED)                                 (traj.json feeds
                                                               run_train_traj.py
                                                               directly)
```

**No parser.** `git diff` computes the hunk headers, so the arithmetic failure
class cannot occur.

## Changes made

- **New** `src/hecate/agent/batch.py` — wraps `mini-extra swebench` (batch). Upstream
  owns the worker pool, resume (`--redo-existing`), and slicing.
- **New** `src/hecate/agent/convert.py` — mini-SWE output -> `GenerationRecord`.
- **New** `scripts/run_miniswe_sweep.py` — per-model runs + merge. Mirrors `run_sweep.py`.
- **New** `tests/test_miniswe_batch.py` — 14 offline tests, no Docker/API.
- **One output dir per model.** `preds.json` is keyed by `instance_id` only, with no
  model dimension — a shared dir would silently overwrite across models.
- **Empty submissions become records**, not omissions. `run_execution` asserts a
  complete instance x model matrix; a failed agent yields `patch_parse_ok: false`
  and grades as `no_patch`.
- **`--split test` forced.** Upstream's `swebench` batch defaults to `dev`.
- **`_resolve_mini_extra` prefers the console script beside `sys.executable`.** PATH
  can point at another venv's `mini-extra`, running the agent under a different Python.
- **Default `--cost-limit` 0.10, not upstream's 3.00.** The entire 600-sample parser
  sweep cost $0.567; a $3/instance cap bounds nothing. Needs raising per tier — see
  [Known issues](#known-issues).
- **Added `--request-timeout` (300s) and `--wall-time-limit` (2700s).** mini-SWE passes
  no timeout to litellm, so a stalled provider request blocks its worker forever
  (observed: one request open 11+ min, zero retry warnings, since tenacity only fires
  on an exception).
- **Added `--filter`** — `--tasks N` slices `0:N`, and SWE-bench Lite is ordered by
  repo, so small smokes draw from one repo only.
- **Prompts and `step_limit` left at upstream defaults.** Editing them forfeits the
  comparability that motivated the switch.

## What each part does

| Component | Purpose |
|---|---|
| `configs/option_a.yaml` | Model slugs, tiers, budget. Shared with the parser path. |
| `configs/miniswe.yaml` | Scaffold pins: subset, split, environment class, cost limit. |
| `scripts/run_miniswe_sweep.py` | Entry point. Runs each model into its own dir, then merges. |
| `src/hecate/agent/batch.py` | Builds/executes the `mini-extra swebench` argv. No orchestration of its own. |
| `mini-extra swebench` (upstream) | Boots a container per instance, runs the agent loop, writes `preds.json` + trajectories. |
| `src/hecate/agent/convert.py` | Maps agent output onto `GenerationRecord`. The only translation layer. |
| `scripts/run_execution.py` | **Unchanged.** Applies each patch in a clean container, runs `FAIL_TO_PASS` + `PASS_TO_PASS`. |
| `scripts/run_labels.py` | **Unchanged.** `executions.jsonl` -> routing labels. |
| `scripts/run_train_traj.py` | **Unchanged.** Reads `messages` — mini-SWE's native trajectory format. |

Keeping `run_execution.py` as the grader is what makes the new 600 comparable to the
parser-path 600: same harness, same containers, same test lists.

## Traced run

`astropy__astropy-12907`, Qwen2.5-72B, on an arm64 Mac (x86 images under Rosetta).

### 1. Command

```bash
python scripts/run_miniswe_sweep.py \
  --tasks 2 --model qwen/qwen-2.5-72b-instruct \
  --platform linux/amd64 \
  --output-dir data/outputs/runs/miniswe-mac-smoke72 --run-id miniswe-mac-smoke72
```

Resolved argv:

```
mini-extra swebench --subset lite --split test
  --model openrouter/qwen/qwen-2.5-72b-instruct
  --output data/outputs/runs/miniswe-mac-smoke72/qwen__qwen-2.5-72b-instruct
  --workers 1 --slice 0:2 --environment-class docker
  -c swebench.yaml -c agent.cost_limit=0.1
  -c environment.run_args=["--rm", "--platform", "linux/amd64"]
```

### 2. Agent loop -> trajectory

6 API calls, 70.6s wall clock, $0.0155. The one edit it made:

```bash
sed -i '269i\    elif isinstance(transform, CompoundModel) and isinstance(transform.left, CompoundModel):\        sepleft = _separable(transform.left.left)\        ...' astropy/modeling/separable.py
```

Then the stock submission protocol:

```bash
git diff -- astropy/modeling/separable.py > patch.txt
echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt
```

Trajectory `info` block:

```json
{"exit_status": "Submitted", "submission": "diff --git a/astropy/...",
 "model_stats": {"instance_cost": 0.0155368, "api_calls": 6},
 "mini_version": "2.4.6"}
```

### 3. preds.json

```json
{
  "astropy__astropy-12907": {
    "model_name_or_path": "openrouter/qwen/qwen-2.5-72b-instruct",
    "instance_id": "astropy__astropy-12907",
    "model_patch": "diff --git a/astropy/modeling/separable.py ..."
  },
  "astropy__astropy-14182": { ..., "model_patch": "" }
}
```

Note `model_patch: ""` on the second instance — it hit the cost limit. No model key
anywhere in this file; that is why each model needs its own output dir.

### 4. convert.py -> generations.jsonl

```json
{
  "instance_id": "astropy__astropy-12907",
  "repo": "astropy/astropy",
  "base_commit": "d16bfe05a744909de4b27f5875fe0d4ed41ce607",
  "model_slug": "qwen/qwen-2.5-72b-instruct",
  "tier": "large",
  "prompt": null,                    // no single prompt on this path
  "context_files": [],               // no oracle context
  "raw_response": null,              // no prose to parse
  "extracted_patch": "diff --git a/astropy/modeling/separable.py\n...",
  "patch_parse_ok": true,            // = agent submitted something non-empty
  "cost_usd": 0.0155368,
  "decoding_params": {
    "scaffold": "mini-swe-agent", "scaffold_version": ">=2,<3",
    "exit_status": "Submitted", "api_calls": 6,
    "traj_path": "data/outputs/runs/.../astropy__astropy-12907.traj.json"
  },
  "run_id": "miniswe-mac-smoke72",
  "patch_applied": null, "resolved": null    // Stage-2 placeholders
}
```

The patch itself, as `git diff` produced it:

```diff
@@ -266,6 +266,7 @@ def _cdot(left, right):
     def _n_inputs_outputs(input, position):
         """
+    elif isinstance(transform, CompoundModel) and ...:\        sepleft = ...
         Return ``n_inputs``, ``n_outputs`` fo
```

Hunk header arithmetic is correct — git computed it. The *content* is wrong: the
`sed` used `\` continuations that never expanded, injecting one line of literal
backslashes into a docstring.

### 5. run_execution.py -> executions.jsonl

```bash
python scripts/run_execution.py \
  --input  data/outputs/runs/miniswe-mac-smoke72/generations.jsonl \
  --output-dir data/outputs/runs/miniswe-mac-smoke72 \
  --run-id miniswe-smoke72-exec \
  --model qwen/qwen-2.5-72b-instruct --instance-ids astropy__astropy-12907
```

```
Found 1 existing instance images. Will reuse them.
Evaluation: 100%|##########| 1/1 [02:35<00:00, 155.54s/it, OK=0, FAIL=1, error=0]
Instances resolved: 0
Instances unresolved: 1
run_id=miniswe-smoke72-exec attempted=1 no_patch=0 evaluated=1 resolved=0
```

Test output inside the eval container:

```
E     File "/testbed/astropy/modeling/separable.py", line 268
E       """
E       ^
E   SyntaxError: invalid escape sequence \
ERROR astropy/modeling/tests/test_separable.py
!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!
```

Final record:

```json
{"instance_id": "astropy__astropy-12907",
 "model_slug": "qwen/qwen-2.5-72b-instruct",
 "patch_applied": true,      // valid diff, applied cleanly
 "resolved": false}          // then failed on the injected backslashes
```

**`applied=true, resolved=false` is the result the new pipeline exists to produce.**
The old path would have scored this task by whether a parser could read a
hand-written diff. This one scores it by whether the code works.

### Artifacts

```
data/outputs/runs/miniswe-mac-smoke72/
├── qwen__qwen-2.5-72b-instruct/
│   ├── preds.json                                    # step 3
│   ├── minisweagent.log
│   └── astropy__astropy-12907/*.traj.json            # step 2, feeds run_train_traj.py
├── generations.jsonl                                 # step 4
├── predictions-qwen__qwen-2.5-72b-instruct.jsonl     # step 5 input to harness
├── executions.jsonl                                  # step 5
├── manifest.json                                     # git_commit, swebench_version 4.1.0
└── logs/run_evaluation/.../{report.json,test_output.txt,patch.diff}
```

## Known issues

- **Cost caps need per-tier calibration.** $0.10 truncated a working 72B run at 41
  edits. 72B measured ~$0.044/instance vs 7B ~$0.003. Use ~$1.00 for the large tier.
- **Killed instances lose their cost record.** `instance_cost` is written only at
  instance end. Budget from OpenRouter's usage API, not from trajectories.
- **32k-context models cannot run stock config.** History is resent every step with no
  trimming, so `step_limit: 250` is unreachable — observed `BadRequestError` at call 85.
  Long-context models avoid a documented deviation.
- **`run_execution.py` fails closed on an incomplete matrix.** Single-model runs need
  `--model` explicitly.
- **Grading is slow under Rosetta** (155s/instance with the image cached). The agent
  phase is 97% API wait so it is machine-insensitive; grading is not.
- **Interrupted runs leave orphaned containers.** Clean up with `docker rm -f`.
