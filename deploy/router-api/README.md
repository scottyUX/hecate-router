# Experimental text-only router API (v1)

**This is not a validated routing decision.** Internal/testing access to a
trained head so people can inspect scores. Do **not** point Hecate’s
patch-generation pipeline at this endpoint.

## What the experiment is

Text-only router v1: frozen `answerdotai/ModernBERT-base` + a logistic
regression head (`Linear(768→1)`). Input is a SWE-bench **issue
`problem_statement`**. Output is `P(small model resolves)` for
Qwen3-Coder-480B vs Claude 4 Opus (mini-SWE-agent, Verified).

- Headline split is **grouped by repo**. AUROC is **~0.53 (near chance)**.
- Leave-django-out has **not** run. Treat scores as a demo of the serving
  path, not evidence the router works.
- Unrelated to serving Qwen3-Coder itself (vLLM / large-model GCS).

Related notes:

- Lab journal: **Text-only router v1** (2026-08-25) — AUROC, logreg vs mlp,
  grouped-by-repo split. Filename used in that writeup:
  `lab-journal-2026-08-25-text-only-router-v1.md`. Search `/journal` in the
  lab app; that file is not in this git tree.
- Dataset / headroom / complementarity:
  [`data/external/README.md`](../../data/external/README.md)
- Trainer (not this API): [`scripts/run_train_text.py`](../../scripts/run_train_text.py),
  [`configs/router_text.yaml`](../../configs/router_text.yaml)
- Do **not** mix with Spec 015 / Lite `run_train.py` (different labels).

The only HTTP route is `POST /v1-experimental/route` (there is no `/route`).
Every JSON 200 includes:

```json
"warning": "experimental — near-chance AUROC, see lab journal"
```

## How to call the API

Live URL (IAM-only Cloud Run, project `hecate-506120`):

https://hecate-router-v1-experimental-io7ijkkkaq-uc.a.run.app

GCS access on this project is **not** enough. You need `gcloud` plus
`roles/run.invoker` on this service. Anyone already logged into gcloud can
mint their own token; nobody hands out a secret.

**1. One-time**

```bash
gcloud auth login
gcloud config set project hecate-506120
```

If a call returns **403**, you are missing invoker. Ask a project admin:

```bash
gcloud run services add-iam-policy-binding hecate-router-v1-experimental \
  --project hecate-506120 \
  --region us-central1 \
  --member="user:YOU@ucsc.edu" \
  --role="roles/run.invoker"
```

**2. Ping**

```bash
TOKEN="$(gcloud auth print-identity-token)"
curl -sS -X POST \
  "https://hecate-router-v1-experimental-io7ijkkkaq-uc.a.run.app/v1-experimental/route" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"problem_statement": "Django admin raises AttributeError on save."}'
```

Optional `"threshold": 0.6` in the JSON (default `0.5`). Empty
`problem_statement` → 422. No token → 403. First request after idle can be
slow (scale-to-zero; encoder downloads from Hugging Face).

**3. Response**

```json
{
  "p_small_resolves": 0.58,
  "routing_decision": "small",
  "model_version": "router-v1-text",
  "warning": "experimental — near-chance AUROC, see lab journal"
}
```

`routing_decision` is `"small"` if `p_small_resolves >= threshold`, else
`"large"`. With near-chance AUROC that cut is not a settled policy.

## What is served (operators)

Checkpoint in GCS (head only; encoder from Hugging Face at startup):

`gs://hecate-506120-router/hecate/router-v1-text/<run_id>/head_logreg.pt`

### Upload checkpoint

```bash
export HECATE_GCP_PROJECT=hecate-506120
# optional: ROUTER_RUN_DIR=/path/to/run  HECATE_GCS_BUCKET=hecate-506120-router
bash deploy/router-api/upload_checkpoint.sh
```

Looks for `head_logreg.pt` + `manifest.json` in this order: `ROUTER_RUN_DIR`,
newest local `data/outputs/runs/*/`, then the exec VM
`/opt/hecate/data/outputs/runs/`. Exits 1 with searched paths if nothing is
found (train first: `python scripts/run_train_text.py --backend frozen`).

### Deploy

```bash
export HECATE_GCP_PROJECT=hecate-506120
export ROUTER_GCS_URI=gs://hecate-506120-router/hecate/router-v1-text/<run_id>/head_logreg.pt
bash deploy/router-api/deploy.sh
```

Cloud Run: CPU only, 2 vCPU / 2Gi, min instances 0, IAM-only. Runtime SA
`hecate-router`, build SA `hecate-router-build`.
