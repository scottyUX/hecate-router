# Experiments

Pre-registered lab notebook. Product/feature specs stay in `specs/001`–`015`.
These IDs are E01–E05, not a continuation of that sequence.

Each experiment is two files: `spec.md` (pre-registration) and `results.md`
(headline numbers + GCS pointers after a run). Amend `spec.md` in place;
do not create `e02-rev2/` directories. Next experiment is `e06-<short-name>/`
with questions `Q6.1`, `Q6.2`, …

| Dir | Slate | Questions |
|-----|--------|-----------|
| `e01-second-repo-replication/` | E1 | Q1.1, Q1.2 |
| `e02-specialist-django/` | E2 | Q2.1, Q2.2, Q2.3 |
| `e03-cross-pair-transfer/` | E3 | Q3.1, Q3.2 |
| `e04-lookahead-router/` | E4 | Q4.1, Q4.2 |
| `e05-repo-structure-gate/` | E5 | Q5.1, Q5.2 |

## Run IDs (BIDS-style)

Parseable key-value pairs, underscores between entities, no extra hyphens in
values (`leave-repo` → `leaverepo`):

```text
exp-02_arm-k1_split-specialist_seed-0
exp-01_arm-k0_split-leaverepo_seed-0
```

Pass that string as `--run-id`. A rerun gets `_run-2` (or a new seed), never
an overwrite. Helper: `hecate.utils.run_ids.make_run_id`.

Weights are not git. Local scratch is `data/outputs/runs/<run_id>/`; durable
copy is `gs://hecate-506120-artifacts/runs/<run_id>/`. A LoRA run without that
copy is incomplete. See `scripts/provision_artifacts_bucket.sh`.

`experiments/runs.jsonl` is appended after the first completed run.
