# Stage-2 execution on GCP

Run SWE-bench eval for Hecate patches on an x86 VM so Stage-3 labels (and
then router training) have execution-grounded outcomes. This Mac cannot pull
the prebuilt `swebench` images (they are `linux/x86_64`).

Shape matches [`GCP_COST_ESTIMATE.md`](GCP_COST_ESTIMATE.md): 8 vCPU / 32 GB
in `us-central1`, with a single **200 GB** boot disk for the first pilot
(simpler than boot + 300 GB cache disk). Prefer `n2-standard-8`; if that
machine type is sold out, `e2-standard-8` is the same shape. Stop the VM when
idle.

No service-account JSON and no API keys are stored in the repo. SSH with
`gcloud compute ssh`. Stage-1 `generations.jsonl` and other `data/outputs/`
artifacts stay **gitignored** (generated run data, not source). They are
shared on the VM at `/opt/hecate`, not in GitHub.

## Lab shared checkout

Every SSH user gets their own Linux home (`/home/jacob`, `/home/scottdavis`,
…). The checkout is **not** copied into each home. Canonical tree:

| Path | Role |
|------|------|
| `/opt/hecate` | Shared repo, `.venv`, and gitignored `data/outputs/` |
| `~/hecate` | Symlink to `/opt/hecate` (same `cd ~/hecate` for everyone) |
| `/opt/hecate/.env` | Owner-only (`0600`). Do not chmod this group-readable. |

Group `hecate` can read the tree and write `data/outputs/` (new eval runs).
`scripts/sync_exec_vm.sh` writes to `/opt/hecate` by default.

Onboard a user after their first SSH (so `/home/<user>` exists):

```bash
gcloud compute ssh hecate-exec --project hecate-506120 --zone us-central1-a
sudo bash /opt/hecate/scripts/onboard_exec_vm_user.sh jacob
```

They must disconnect and SSH again so `hecate` + `docker` groups apply. Then:

```bash
cd ~/hecate
source .venv/bin/activate
ls data/outputs/runs/exec-pilot-20/
```

Do **not** enter `/home/scottdavis`. Home dirs are private by design.

## 0. One-time laptop setup

1. Install the [Cloud SDK](https://cloud.google.com/sdk/docs/install). On this
   machine the CLI lives at `~/.local/google-cloud-sdk/bin/gcloud` (add that
   directory to `PATH`).
2. `gcloud auth login` and `gcloud auth application-default login` (browser;
   the agent cannot complete this).
3. Create or select a project with billing (or research credits).
4. Export the project id:

```bash
export PATH="$HOME/.local/google-cloud-sdk/bin:$PATH"
export HECATE_GCP_PROJECT=your-gcp-project-id
# optional overrides
# export HECATE_GCP_ZONE=us-central1-a
# export HECATE_GCP_INSTANCE=hecate-exec
```

## 1. Provision the VM

From the repo root:

```bash
bash scripts/provision_exec_vm.sh
```

Idempotent: if `hecate-exec` already exists it is left running (or started if
stopped). First boot installs Docker + Python 3 via a startup script. Wait
until SSH works and `/var/lib/hecate/bootstrap-complete` exists:

```bash
gcloud compute ssh "${HECATE_GCP_INSTANCE:-hecate-exec}" \
  --project "${HECATE_GCP_PROJECT}" \
  --zone "${HECATE_GCP_ZONE:-us-central1-a}" \
  --command 'test -f /var/lib/hecate/bootstrap-complete && docker version'
```

If `docker` fails with a permission error, disconnect and SSH again so the
`docker` group applies, or prefix commands with `sudo`.

## 2. Sync code and patches

The execution branch may not be on `origin`. Copy the working tree and the
gitignored generations file:

```bash
bash scripts/sync_exec_vm.sh
```

Remote layout: `/opt/hecate` (each user has `~/hecate` → `/opt/hecate`) with
`data/outputs/runs/sweep-2x300-qwen/generations.jsonl`. Override with
`HECATE_GCP_REMOTE_DIR` only if you are not using the shared tree.

## 3. Python env on the VM

```bash
gcloud compute ssh "${HECATE_GCP_INSTANCE:-hecate-exec}" \
  --project "${HECATE_GCP_PROJECT}" \
  --zone "${HECATE_GCP_ZONE:-us-central1-a}"
```

Then:

```bash
cd ~/hecate
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
# Optional offline check (no Docker needed for this):
python scripts/run_execution.py --dry-run --tasks 2 \
  --output-dir /tmp/exec-dry --run-id exec-dry
```

`configs/execution.yaml` defaults to `namespace: swebench` (prebuilt x86
images on Docker Hub). Do **not** pass `--namespace none` on this VM.

On this GCP VM, pull those images through an Artifact Registry **remote
repository** so Docker Hub rate limits (anonymous ~100 pulls / 6h) do not
stall the matrix. Repo: `us-central1` / `dockerhub-cache`, upstream Docker
Hub. SWE-bench namespace becomes the AR path plus `swebench`:

```bash
# one-time (laptop): API + remote repo + VM service account can pull
gcloud services enable artifactregistry.googleapis.com --project "${HECATE_GCP_PROJECT}"
gcloud artifacts repositories create dockerhub-cache \
  --project "${HECATE_GCP_PROJECT}" \
  --repository-format=docker \
  --location=us-central1 \
  --description="Pull-through cache for Docker Hub" \
  --mode=remote-repository \
  --remote-repo-config-desc="Docker Hub" \
  --remote-docker-repo=DOCKER-HUB
gcloud artifacts repositories add-iam-policy-binding dockerhub-cache \
  --project "${HECATE_GCP_PROJECT}" \
  --location=us-central1 \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"
```

On the VM (uses the instance service account; `cloud-platform` scope required):

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
export PATH="/snap/bin:$PATH"
```

Then pass:

```bash
--namespace us-central1-docker.pkg.dev/${HECATE_GCP_PROJECT}/dockerhub-cache/swebench
```

First pull of each image still goes Docker Hub → Artifact Registry, then the
cache serves later pulls. Optional: add a Docker Hub PAT in Secret Manager
(`--remote-username` / `--remote-password-secret-version`) if Google's
unauthenticated Hub quota is still tight.

## 4. Gold smoke

Proves Docker + image pull. First pull is slow.

```bash
source ~/hecate/.venv/bin/activate
cd ~/hecate
python -m swebench.harness.run_evaluation \
  --predictions_path gold \
  --instance_ids astropy__astropy-12907 \
  --max_workers 1 \
  --run_id hecate-smoke-gold
```

Logs land under `logs/run_evaluation/` relative to the current working
directory. Prefer running from `~/hecate` so they stay next to the repo (and
gitignored).

## 5. Hecate smoke (1 instance × both models)

`astropy__astropy-12907` has a parse-fail 7B patch, so it only exercises the
no-patch short-circuit for m1. Use an instance where **both** patches parsed
(95 such tasks in the sweep), e.g. `astropy__astropy-14182`:

```bash
python scripts/run_execution.py \
  --instance-ids astropy__astropy-14182 \
  --output-dir data/outputs/runs/exec-smoke \
  --run-id exec-smoke \
  --max-workers 2
```

Resume by reusing `--output-dir` and `--run-id`.

## 6. Pilot (20 tasks × 2 models)

```bash
python scripts/run_execution.py \
  --tasks 20 \
  --output-dir data/outputs/runs/exec-pilot-20 \
  --run-id exec-pilot-20 \
  --max-workers 4
```

Then labels + pre-flight:

```bash
python scripts/run_labels.py \
  --input data/outputs/runs/exec-pilot-20/executions.jsonl \
  --output-dir data/outputs/runs/exec-pilot-20
```

Inspect `preflight.json`: `m1_resolve_rate`, `m2_resolve_rate`,
`complementarity`, `routing_headroom`, `m1_positive_rate_flag`.

## 7. Copy results back to the laptop

Still gitignored under `data/outputs/`. Do not commit them.

```bash
mkdir -p data/outputs/runs/exec-pilot-20
gcloud compute scp --recurse \
  --project "${HECATE_GCP_PROJECT}" \
  --zone "${HECATE_GCP_ZONE:-us-central1-a}" \
  "${HECATE_GCP_INSTANCE:-hecate-exec}:~/hecate/data/outputs/runs/exec-pilot-20/preflight.json" \
  "${HECATE_GCP_INSTANCE:-hecate-exec}:~/hecate/data/outputs/runs/exec-pilot-20/labels.jsonl" \
  "${HECATE_GCP_INSTANCE:-hecate-exec}:~/hecate/data/outputs/runs/exec-pilot-20/labels-manifest.json" \
  "${HECATE_GCP_INSTANCE:-hecate-exec}:~/hecate/data/outputs/runs/exec-pilot-20/manifest.json" \
  data/outputs/runs/exec-pilot-20/
```

## 8. Stop the VM when idle

```bash
gcloud compute instances stop "${HECATE_GCP_INSTANCE:-hecate-exec}" \
  --project "${HECATE_GCP_PROJECT}" \
  --zone "${HECATE_GCP_ZONE:-us-central1-a}"
```

Disk charges continue while stopped; CPU does not. Delete the instance only
when you no longer need the Docker image cache.

## Full 600

Not part of this first GCP pass. Re-run `run_execution.py` without `--tasks`
only after the 20-task pre-flight shows usable headroom (or you accept a weak
floor per issue #18).
