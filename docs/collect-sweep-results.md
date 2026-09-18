# Collecting sweep-2x300-mini-swe results onto the Mac

Run every block below **on the Mac**, not the VM. Absolute paths are used
because `~` does not reliably expand through `gcloud compute scp`.

Grading was interrupted at 57/58 of the 72B pass, so there is **no
`executions.jsonl`** — the per-instance `report.json` files under `logs/` are
the resolve data.

```bash
mkdir -p /tmp/sweep-collect
```

## 1. Structured outputs

```bash
gcloud compute scp --project hecate-506120 --zone us-central1-a \
  "hecate-exec:/home/arav/hecate-mini/data/outputs/runs/sweep-2x300-mini-swe/generations.jsonl" \
  "hecate-exec:/home/arav/hecate-mini/data/outputs/runs/sweep-2x300-mini-swe/manifest-miniswe-qwen__qwen-2.5-7b-instruct.json" \
  "hecate-exec:/home/arav/hecate-mini/data/outputs/runs/sweep-2x300-mini-swe/manifest-miniswe-qwen__qwen-2.5-72b-instruct.json" \
  /tmp/sweep-collect/
```

600 generation records plus the two run manifests (provenance: git commit,
config snapshots, per-instance exit status / cost / api_calls).

## 2. Per-instance grading reports

```bash
gcloud compute scp --project hecate-506120 --zone us-central1-a --recurse \
  "hecate-exec:/home/arav/hecate-mini/data/outputs/runs/sweep-2x300-mini-swe/logs" \
  /tmp/sweep-collect/
```

The important one. Each graded instance has `report.json` (resolved /
applied), `test_output.txt`, and the `patch.diff` that was applied. This is the
only record of the grading pass that survived the interrupt.

## 3. Predictions per arm

```bash
gcloud compute scp --project hecate-506120 --zone us-central1-a \
  "hecate-exec:/home/arav/hecate-mini/data/outputs/runs/sweep-2x300-mini-swe/qwen__qwen-2.5-7b-instruct/preds.json" \
  /tmp/sweep-collect/preds-7b.json

gcloud compute scp --project hecate-506120 --zone us-central1-a \
  "hecate-exec:/home/arav/hecate-mini/data/outputs/runs/sweep-2x300-mini-swe/qwen__qwen-2.5-72b-instruct/preds.json" \
  /tmp/sweep-collect/preds-72b.json
```

Upstream's own output: `{instance_id: {model_patch}}`. Also the resume ledger —
an instance present here is skipped on a re-run, which matters because the 382
that never executed have empty entries in these files.

## 4. Agent logs

```bash
gcloud compute scp --project hecate-506120 --zone us-central1-a \
  "hecate-exec:/home/arav/hecate-mini/data/outputs/runs/sweep-2x300-mini-swe/qwen__qwen-2.5-7b-instruct/minisweagent.log" \
  /tmp/sweep-collect/minisweagent-7b.log

gcloud compute scp --project hecate-506120 --zone us-central1-a \
  "hecate-exec:/home/arav/hecate-mini/data/outputs/runs/sweep-2x300-mini-swe/qwen__qwen-2.5-72b-instruct/minisweagent.log" \
  /tmp/sweep-collect/minisweagent-72b.log
```

Contains the `docker run ... exit status 125` burst that killed ~64% of the run,
with timestamps — the evidence for the Docker Hub pull-limit diagnosis.

## 5. Verify

```bash
find /tmp/sweep-collect -type f | wc -l
du -sh /tmp/sweep-collect
find /tmp/sweep-collect -name report.json | wc -l
```

Expect roughly 74 `report.json` files (17 from the 7B pass, ~57 from the 72B
pass before it was killed).

## Not collected

**Trajectories** (`<instance>/<instance>.traj.json`, 218 of them) are hundreds
of MB and stay on the VM. They are what `run_train_traj.py` consumes later, so
they should be copied to durable storage rather than left on a VM disk:

```bash
# on the VM
gsutil -m rsync -r \
  ~/hecate-mini/data/outputs/runs/sweep-2x300-mini-swe \
  gs://hecate-506120-artifacts/runs/sweep-2x300-mini-swe
```
