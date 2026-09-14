#!/usr/bin/env bash
# Create the lab archive bucket (not the Cloud Run serving bucket).
# Confirm the name is free before this is the first time it runs — bucket
# names are global.
set -euo pipefail

PROJECT="${HECATE_GCP_PROJECT:-hecate-506120}"
BUCKET="${HECATE_ARTIFACTS_BUCKET:-hecate-506120-artifacts}"
REGION="${HECATE_GCP_REGION:-us-central1}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud not found. Install the Cloud SDK." >&2
  exit 1
fi

gcloud config set project "${PROJECT}" >/dev/null
gcloud services enable storage.googleapis.com --project "${PROJECT}"

if gcloud storage buckets describe "gs://${BUCKET}" --project "${PROJECT}" >/dev/null 2>&1; then
  echo "exists gs://${BUCKET}"
else
  echo "==> Creating gs://${BUCKET} in ${REGION}"
  gcloud storage buckets create "gs://${BUCKET}" \
    --project "${PROJECT}" \
    --location "${REGION}" \
    --uniform-bucket-level-access
fi

echo "==> Enabling object versioning"
gcloud storage buckets update "gs://${BUCKET}" --versioning

echo "HECATE_ARTIFACTS_URI=gs://${BUCKET}"
echo "Set that on hecate-traj-l4 before any --backend lora run."
