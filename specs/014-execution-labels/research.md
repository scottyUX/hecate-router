# Research: Execution Harness and Routing Labels

**Branch**: `014-execution-labels` | **Date**: 2026-08-20

## D1 — Do not reimplement Docker apply/test

**Decision**: Call `swebench.harness.run_evaluation.main` (already pinned `swebench==4.1.0`) through a `Harness` protocol. Production adapter is `SwebenchHarness`; tests use `FakeHarness` / `ScriptedHarness`.

**Rationale**: SWE-bench already applies via `git apply` then `patch --fuzz=5`, runs repo tests in layered images, and grades FAIL_TO_PASS / PASS_TO_PASS. Reimplementing that would break comparability with published SWE-bench scores.

**Alternatives considered**: Custom `git apply` + pytest in cloned repos (rejected — misses repo-specific eval scripts and images); Modal-only (`--modal true`) as default (rejected — extra credentials; keep as unused config flag).

## D2 — One predictions file per model

**Decision**: Split Hecate’s 600-row JSONL by `model_slug` before calling the harness. Each file uses `{instance_id, model_name_or_path, model_patch}`.

**Rationale**: `get_predictions_from_file` collapses to `{instance_id: pred}`; a combined file would drop one model.

**Alternatives considered**: Sequential overwrite of a single file (rejected — harder resume); one harness process with mixed models (rejected — API cannot represent two patches per instance).

## D3 — Immutable Stage-1 artifacts; new execution run dir

**Decision**: Read `generations.jsonl`; write `data/outputs/runs/<exec-run-id>/executions.jsonl` (and predictions, logs, manifest). Never rewrite Stage-1 output.

**Rationale**: Constitution data hygiene and Stage-1 reproducibility. Resume keys off the execution JSONL, not the generation file.

**Alternatives considered**: In-place backfill (rejected — mutates the generation run); sidecar-only reports without copying records (rejected — Stage 3 needs a single joinable JSONL).

## D4 — Schema: add `resolved`, keep existing test-name lists

**Decision**: Add `GenerationRecord.resolved: bool | None`. Map `patch_applied` ← `patch_successfully_applied`; `fail_to_pass` / `pass_to_pass` ← `tests_status[FAIL_TO_PASS|PASS_TO_PASS].success`. Older JSONL without `resolved` loads as `None`.

**Rationale**: Issue #18 labels need an explicit resolved bit. Existing tests already treat the two lists as passing test names.

**Alternatives considered**: Infer resolved only at label time (rejected — operators need it on the record); store full `tests_status` on the record (deferred — reports remain under the run log dir).

## D5 — No-patch pairs skip Docker; missing reports stay pending

**Decision**: `patch_parse_ok` false or empty `extracted_patch` → do not call the harness; write `patch_applied=False`, `resolved=False`, empty lists. If a pair was submitted and `report.json` is absent, do not append an output row (apply stays unset) so resume retries.

**Rationale**: Full matrix without wasting container hours; distinguish “known fail” from “not yet run”.

**Alternatives considered**: Send empty patches to SWE-bench (it skips them, but we would still need our own record); write `patch_applied=False` on missing reports (rejected — would skip retries).

## D6 — CWD / log isolation

**Decision**: `SwebenchHarness` runs with current working directory = execution output dir. SWE-bench writes `logs/run_evaluation/<run_id>/...` relative to CWD. Also gitignore repo-root `logs/` as a safety net.

**Rationale**: FR-013; `.gitignore` currently does not ignore `logs/`.

## D7 — Namespace default vs ARM Mac

**Decision**: Config default `namespace: swebench` (pull prebuilt x86 images). CLI `--namespace none` for local ARM builds. Document GCP x86 as the intended full-matrix host.

**Rationale**: Matches package docs; this developer machine is darwin/ARM where prebuilt `linux/x86_64` images will not run.

## D8 — v1 label and pre-flight arithmetic

**Decision**: `m1_resolves = (small.resolved is True)`. Complementarity on the four boolean pairs. `oracle_routing_resolve_rate` = fraction of tasks where m1 or m2 resolved. `routing_headroom` = oracle − always-m2. Flag `m1_positive_rate < 0.15`. Shared scaffold: per-task `prompt_hash` equal across models.

**Rationale**: Issue #18 fixed choices. Parse/apply fail is already `resolved=False`.

**Alternatives considered**: Multiclass cheapest-resolver (deferred); treating apply-true with empty F2P as resolved (rejected — must match SWE-bench FULL resolution).
