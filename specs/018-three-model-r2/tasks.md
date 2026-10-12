# Tasks: Three-Model Verified Rerun (r2)

**Input**: [spec.md](./spec.md), [plan.md](./plan.md)

**Tests**: Required (constitution III). Write tests first where noted.

## Phase 0: Already done (commit `b58bd82`)

- [x] T000 Pin `mini-swe-agent==2.0.0`; per-model `reasoning` manifest field.
      (b58bd82's Gemini `reasoning.effort=high` override in r1's table is
      moved to the r2 preset in T006.)

## Phase 1: Reference data and task set

- [x] T001 `scripts/fetch_leaderboard_reference.py`: fetch one trajectory per
      entry and write `info.config` + `mini_version` (templates in full) to
      `configs/leaderboard_reference/<entry>.json`; fetch 20 MiniMax
      trajectories and write per-call provider counts to
      `minimax_provider_mix.json`. Run once and commit the outputs.
- [x] T002 Test first: subset draw is deterministic, size 50, ⊂ source,
      sorted, counts correct.
- [x] T003 `scripts/draw_three_model_subset.py`; generate and commit
      `configs/three_model_tasks_r2.json` (seed `20261012`). **Before any
      model call.**

## Phase 2: Config and runner

- [x] T004 `configs/miniswe_leaderboard.yaml` (2.0.0 built-in verbatim,
      `temperature: null`, `pull_timeout: 300`; model class is passed per
      model with `--model-class`). Test: agent and
      environment blocks and templates equal the installed built-in.
- [x] T005 `src/hecate/agent/openrouter_headers.py`: `OpenRouterModel`
      subclass that sends `extra_headers` as HTTP headers. Test with a
      mocked `requests.post`.
- [x] T006 Test first: `--experiment r1` reproduces r1's config, table
      (no reasoning keys), tasks, run root and caps; `--experiment r2
      --dry-run` gives 50 ids, r2 paths and the per-model kwargs in plan.md.
- [x] T007 `run_three_model.py`: `--experiment` presets, r2 model table,
      `-c` overrides, version guard, r2 manifest fields.
- [x] T008 Test first + implement `scripts/check_leaderboard_config.py`:
      passes for r2, fails for r1 (it has `BASH_ENV`, a different template,
      `cost_limit 0`).
- [x] T009 `launch_three_model.sh` and `grade_three_model.sh`: `EXPERIMENT`
      env var, sessions `3m-r2-<model>` / `grade-r2-<model>`, `/N` status;
      preflight checks the experiment's mini-swe-agent version and, for r2,
      runs the config check.
- [x] T010 `compare_three_model_leaderboard.py`: `/N` labels,
      `--baseline-per-task`. Reasoning tokens come through the existing
      `--trajectories` medians.
- [x] T010b Realized provider mix per model from r2 trajectories (per-call
      `extra.response.provider`); needed for T020.
- [x] T011 Full test suite green.

## Phase 3: VM run

- [x] T012 `hecate-exec`: `git pull`; `pip install -e ".[agent]"`; confirm
      2.0.0.
- [x] T013 Top up OpenRouter to ≥ $130 available. (Ran on a separate key with
      $100; spend was $66.63.)
- [x] T014 `EXPERIMENT=r2`: preflight, config check, pull.
- [x] T015 Smoke: `--tasks 2` per model into a smoke-only run root. Check:
      Gemini served only by Google AI Studio and Opus only by Anthropic;
      MiniMax only by the three allowed providers; reasoning tokens/call
      within roughly 2x of the leaderboard's on the same tasks; Opus shows
      reasoning between tool calls (beta header effective); no 60 s
      timeout retries; `usage.cost` > 0 on every call. **Stop if any check
      fails.**
- [x] T016 `start`; watch `status`.
- [x] T017 `--prune-infra-failures` and rerun until no infra failures remain.

## Phase 4: Grade and report

- [x] T018 Grade all three (r2 env vars).
- [x] T019 `extract_traj_features.py` and `analyze_three_model.py` with r2
      paths.
- [x] T020 Compare against the leaderboard (primary) and r1 (secondary).
- [x] T021 `docs/runs/three-model-verified-r2/README.md`: method and full
      config table vs the leaderboard, results, the pre-registered analysis,
      realized provider mix, residual differences and caveats.
