# Hecate — 1-Year GCP Cost Estimate (Jul 2026 – Jun 2027)

**Purpose:** Google Cloud research credits application ($1,000 request)  
**Region:** `us-central1` (Iowa)  
**Pricing basis:** [GCP Pricing Calculator](https://cloud.google.com/products/calculator) list prices (on-demand, Jul 2026)

---

## Summary

| | |
|---|---|
| **Estimated annual total** | **$1,012 / year** |
| **Estimated monthly average** | **~$84 / month** |
| **Primary workloads** | SWE-bench Docker execution (Stage 2), DistilBERT router training (Stage 4), artifact storage |

OpenRouter API spend for patch generation (Stage 1, ~$38–$100) is **not** included — that uses OpenRouter, not GCP.

---

## Calculator line items

Enter these in [cloud.google.com/products/calculator](https://cloud.google.com/products/calculator):

### 1. Compute Engine — CPU execution (SWE-bench harness)

| Field | Value |
|-------|-------|
| Product | Compute Engine |
| Machine type | `n2-standard-8` (8 vCPU, 32 GB) |
| Region | us-central1 |
| Hours/month | **42** (≈500 hrs/year, bursty Aug–Dec) |
| Boot disk | 100 GB balanced persistent disk |
| **Monthly subtotal** | **~$16** compute + **~$10** disk ≈ **$26** |

*Assumption:* Docker-based patch execution for 300 SWE-bench Lite tasks × 4 models, plus reruns and student-repo pilots.

### 2. Compute Engine — GPU router training

| Field | Value |
|-------|-------|
| Product | Compute Engine |
| Machine type | `n1-standard-4` + **1× NVIDIA T4** |
| Region | us-central1 |
| Hours/month | **15** (≈180 hrs/year) |
| Boot disk | 50 GB balanced |
| **Monthly subtotal** | **~$8** |

*Assumption:* DistilBERT fine-tuning, hyperparameter sweeps, SDLC domain adaptation (M4/M6).

### 3. Cloud Storage — datasets & outputs

| Field | Value |
|-------|-------|
| Product | Cloud Storage |
| Class | Standard (regional) |
| Region | us-central1 |
| Storage | **400 GB** average |
| Class A ops | 50,000 / month |
| Class B ops | 200,000 / month |
| **Monthly subtotal** | **~$8** |

*Stores:* SWE-bench records, 1,200 patches, execution logs, run manifests.

### 4. Persistent Disk — Docker layer cache

| Field | Value |
|-------|-------|
| Product | Compute Engine → Persistent Disk |
| Type | Balanced PD |
| Size | **300 GB** (attached to execution VM, kept year-round) |
| **Monthly subtotal** | **~$30** |

*Speeds up repeated SWE-bench container builds and evaluation reruns.*

### 5. Artifact Registry — container images

| Field | Value |
|-------|-------|
| Product | Artifact Registry |
| Storage | **40 GB** |
| **Monthly subtotal** | **~$4** |

### 6. Cloud Logging & Monitoring

| Field | Value |
|-------|-------|
| Product | Cloud Logging |
| Log ingestion | **~15 GB / month** (after free tier) |
| **Monthly subtotal** | **~$3** |

### 7. Network egress

| Field | Value |
|-------|-------|
| Product | Cloud Storage / Compute egress |
| Egress to internet | **~25 GB / month** |
| **Monthly subtotal** | **~$3** |

---

## Annual rollup

| Service | Annual estimate |
|---------|-----------------|
| Compute Engine (CPU, n2-standard-8) | $194 |
| Compute Engine (GPU, n1-standard-4 + T4) | $97 |
| Cloud Storage (400 GB avg) | $96 |
| Persistent Disk (300 GB cache) | $360 |
| Artifact Registry | $48 |
| Logging & monitoring | $36 |
| Network egress | $36 |
| Contingency (~15%, failed runs, spot→on-demand drift) | $145 |
| **Total** | **$1,012** |

---

## Usage calendar (why these numbers)

| Period | GCP activity |
|--------|----------------|
| **Aug–Sep 2026** | Light — Stage 1 patch storage only |
| **Oct–Dec 2026** | Heavy — Stage 2 execution + label construction (M3) |
| **Jan–Mar 2027** | Medium — router training sweeps (M4) |
| **Apr–Jun 2027** | Medium — evaluation reruns + SDLC adaptation pilot (M5/M6) |

CPU execution is **bursty**, not 24/7. GPU training is **short runs** (minutes–hours), not multi-day jobs.

---

## How to generate the calculator share link

1. Open https://cloud.google.com/products/calculator  
2. Add each product above with the monthly values  
3. Confirm total ≈ **$84/month** (~$1,012/year)  
4. Click **Share estimate** (top right) → copy URL  
5. Paste that URL into the credits application

> **Note:** The share link is tied to your browser session / Google account when saved. An agent cannot generate it on your behalf — you must click Share once after entering the line items (takes ~5 minutes).

---

## What stays off GCP

| Cost | Provider | Est. |
|------|----------|------|
| Patch generation (1,200 LLM calls) | OpenRouter | ~$38–$100 |
| Local dev / pytest | Laptop | $0 |

GCP credits cover **execution, training, and storage** — the compute-heavy research path after patches are generated.
