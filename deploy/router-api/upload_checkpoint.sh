#!/usr/bin/env bash
# Locate head_logreg.pt + manifest.json and upload to GCS.
# Does not upload ModernBERT encoder weights.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT="${HECATE_GCP_PROJECT:-hecate-506120}"
BUCKET="${HECATE_GCS_BUCKET:-hecate-506120-router}"
REGION="${HECATE_GCP_REGION:-us-central1}"
ZONE="${HECATE_GCP_ZONE:-us-central1-a}"
INSTANCE="${HECATE_GCP_INSTANCE:-hecate-exec}"

SEARCHED=()
RUN_DIR="${ROUTER_RUN_DIR:-}"

file_mtime() {
  if stat -f %m "$1" >/dev/null 2>&1; then
    stat -f %m "$1"
  else
    stat -c %Y "$1"
  fi
}

fail_missing() {
  echo "ERROR: no router v1 checkpoint (head_logreg.pt + manifest.json) found." >&2
  echo "Searched:" >&2
  if [[ ${#SEARCHED[@]} -eq 0 ]]; then
    echo "  (no candidate paths)" >&2
  else
    for p in "${SEARCHED[@]}"; do
      echo "  ${p}" >&2
    done
  fi
  echo "Set ROUTER_RUN_DIR to a trained run directory, or train with:" >&2
  echo "  python scripts/run_train_text.py --backend frozen" >&2
  exit 1
}

if [[ -n "${RUN_DIR}" ]]; then
  SEARCHED+=("${RUN_DIR}")
  if [[ ! -f "${RUN_DIR}/head_logreg.pt" || ! -f "${RUN_DIR}/manifest.json" ]]; then
    fail_missing
  fi
else
  best=""
  best_m=0
  shopt -s nullglob
  for head in "${ROOT}/data/outputs/runs/"*/head_logreg.pt; do
    dir="$(dirname "${head}")"
    SEARCHED+=("${dir}")
    if [[ ! -f "${dir}/manifest.json" ]]; then
      continue
    fi
    mtime="$(file_mtime "${head}")"
    if [[ -z "${best}" || "${mtime}" -gt "${best_m}" ]]; then
      best="${dir}"
      best_m="${mtime}"
    fi
  done
  shopt -u nullglob
  RUN_DIR="${best}"
fi

if [[ -z "${RUN_DIR}" ]]; then
  SEARCHED+=("${INSTANCE}:/opt/hecate/data/outputs/runs/*/head_logreg.pt")
  if command -v gcloud >/dev/null 2>&1; then
    REMOTE_HEAD="$(gcloud compute ssh "${INSTANCE}" \
      --project "${PROJECT}" --zone "${ZONE}" --quiet \
      --command 'ls -td /opt/hecate/data/outputs/runs/*/head_logreg.pt 2>/dev/null | head -1' \
      || true)"
    if [[ -n "${REMOTE_HEAD}" ]]; then
      TMP="$(mktemp -d)"
      REMOTE_DIR="$(dirname "${REMOTE_HEAD}")"
      gcloud compute scp --project "${PROJECT}" --zone "${ZONE}" --quiet \
        "${INSTANCE}:${REMOTE_DIR}/head_logreg.pt" "${TMP}/head_logreg.pt"
      gcloud compute scp --project "${PROJECT}" --zone "${ZONE}" --quiet \
        "${INSTANCE}:${REMOTE_DIR}/manifest.json" "${TMP}/manifest.json"
      RUN_DIR="${TMP}"
    fi
  else
    echo "NOTE: gcloud not on PATH; skipped exec VM lookup." >&2
  fi
fi

if [[ -z "${RUN_DIR}" || ! -f "${RUN_DIR}/head_logreg.pt" || ! -f "${RUN_DIR}/manifest.json" ]]; then
  fail_missing
fi

RUN_ID="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1], encoding='utf-8'))['run_id'])" \
  "${RUN_DIR}/manifest.json")"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud not found. Install the Cloud SDK." >&2
  exit 1
fi

gcloud config set project "${PROJECT}" >/dev/null
gcloud services enable storage.googleapis.com --project "${PROJECT}"

if ! gcloud storage buckets describe "gs://${BUCKET}" --project "${PROJECT}" >/dev/null 2>&1; then
  echo "==> Creating bucket gs://${BUCKET} in ${REGION}"
  gcloud storage buckets create "gs://${BUCKET}" \
    --project "${PROJECT}" \
    --location "${REGION}" \
    --uniform-bucket-level-access
fi

PREFIX="gs://${BUCKET}/hecate/router-v1-text/${RUN_ID}"
echo "==> Uploading run ${RUN_ID} from ${RUN_DIR}"
gcloud storage cp "${RUN_DIR}/head_logreg.pt" "${PREFIX}/head_logreg.pt"
gcloud storage cp "${RUN_DIR}/manifest.json" "${PREFIX}/manifest.json"
echo "ROUTER_GCS_URI=${PREFIX}/head_logreg.pt"
echo "Uploaded ${PREFIX}/head_logreg.pt"
echo "Uploaded ${PREFIX}/manifest.json"
