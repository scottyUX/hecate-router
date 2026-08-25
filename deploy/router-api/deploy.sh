#!/usr/bin/env bash
# Deploy the experimental text-only router to Cloud Run (IAM-only, scale to zero).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT="${HECATE_GCP_PROJECT:-hecate-506120}"
REGION="${HECATE_GCP_REGION:-us-central1}"
SERVICE="${ROUTER_CLOUD_RUN_SERVICE:-hecate-router-v1-experimental}"
BUCKET="${HECATE_GCS_BUCKET:-hecate-506120-router}"
THRESHOLD="${ROUTER_THRESHOLD:-0.5}"

if [[ -z "${ROUTER_GCS_URI:-}" ]]; then
  echo "ERROR: set ROUTER_GCS_URI to gs://<bucket>/hecate/router-v1-text/<run_id>/head_logreg.pt" >&2
  echo "Run: bash deploy/router-api/upload_checkpoint.sh" >&2
  exit 1
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud not found. Install the Cloud SDK." >&2
  exit 1
fi

STAGE="$(mktemp -d)"
cleanup() { rm -rf "${STAGE}"; }
trap cleanup EXIT

mkdir -p "${STAGE}/src/hecate/router"
cp "${ROOT}/src/hecate/__init__.py" "${STAGE}/src/hecate/"
cp "${ROOT}/src/hecate/router/backends.py" "${STAGE}/src/hecate/router/"
cp "${ROOT}/src/hecate/router/infer.py" "${STAGE}/src/hecate/router/"
: > "${STAGE}/src/hecate/router/__init__.py"
cp "${ROOT}/deploy/router-api/Dockerfile" "${STAGE}/"
cp "${ROOT}/deploy/router-api/requirements.txt" "${STAGE}/"
cp "${ROOT}/deploy/router-api/app.py" "${STAGE}/"
cp "${ROOT}/deploy/router-api/score.py" "${STAGE}/"

echo "==> Project ${PROJECT} region ${REGION} service ${SERVICE}"
gcloud config set project "${PROJECT}" >/dev/null
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  compute.googleapis.com \
  --project "${PROJECT}" \
  --quiet

RUNTIME_SA="${ROUTER_RUNTIME_SA:-hecate-router@${PROJECT}.iam.gserviceaccount.com}"
BUILD_SA="${ROUTER_BUILD_SA:-hecate-router-build@${PROJECT}.iam.gserviceaccount.com}"

gcloud iam service-accounts create hecate-router \
  --display-name="Hecate router v1 runtime" \
  --project "${PROJECT}" 2>/dev/null || true
gcloud iam service-accounts create hecate-router-build \
  --display-name="Hecate router v1 Cloud Build" \
  --project "${PROJECT}" 2>/dev/null || true
gcloud iam service-accounts describe "${RUNTIME_SA}" --project "${PROJECT}" >/dev/null
gcloud iam service-accounts describe "${BUILD_SA}" --project "${PROJECT}" >/dev/null

for ROLE in \
  roles/logging.logWriter \
  roles/artifactregistry.writer \
  roles/storage.objectAdmin \
  roles/cloudbuild.builds.builder
do
  gcloud projects add-iam-policy-binding "${PROJECT}" \
    --member="serviceAccount:${BUILD_SA}" \
    --role="${ROLE}" \
    --quiet >/dev/null
done

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/storage.objectViewer" \
  --project "${PROJECT}" \
  --quiet >/dev/null

ACCOUNT="$(gcloud config get-value account)"
if [[ "${ACCOUNT}" == *.gserviceaccount.com ]]; then
  MEMBER="serviceAccount:${ACCOUNT}"
else
  MEMBER="user:${ACCOUNT}"
fi
gcloud iam service-accounts add-iam-policy-binding "${RUNTIME_SA}" \
  --project "${PROJECT}" \
  --member="${MEMBER}" \
  --role="roles/iam.serviceAccountUser" \
  --quiet >/dev/null
gcloud iam service-accounts add-iam-policy-binding "${BUILD_SA}" \
  --project "${PROJECT}" \
  --member="${MEMBER}" \
  --role="roles/iam.serviceAccountUser" \
  --quiet >/dev/null

echo "==> Building and deploying (CPU, min-instances=0, IAM-only)"
gcloud run deploy "${SERVICE}" \
  --source "${STAGE}" \
  --region "${REGION}" \
  --project "${PROJECT}" \
  --quiet \
  --cpu 2 \
  --memory 2Gi \
  --min-instances 0 \
  --max-instances 2 \
  --timeout 120 \
  --no-allow-unauthenticated \
  --cpu-boost \
  --service-account "${RUNTIME_SA}" \
  --build-service-account "projects/${PROJECT}/serviceAccounts/${BUILD_SA}" \
  --set-env-vars "ROUTER_GCS_URI=${ROUTER_GCS_URI},ROUTER_THRESHOLD=${THRESHOLD},HF_HOME=/tmp/hf,TRANSFORMERS_CACHE=/tmp/hf,ROUTER_DEVICE=cpu,ROUTER_CACHE_DIR=/tmp/hecate-router"

ACCOUNT="$(gcloud config get-value account)"
if [[ "${ACCOUNT}" == *.gserviceaccount.com ]]; then
  MEMBER="serviceAccount:${ACCOUNT}"
else
  MEMBER="user:${ACCOUNT}"
fi
gcloud run services add-iam-policy-binding "${SERVICE}" \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --member="${MEMBER}" \
  --role="roles/run.invoker" \
  --quiet >/dev/null

URL="$(gcloud run services describe "${SERVICE}" \
  --project "${PROJECT}" --region "${REGION}" --format='value(status.url)')"
echo "Service URL: ${URL}"
echo "Call with:"
echo "  curl -sS -X POST \"${URL}/v1-experimental/route\" \\"
echo "    -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"problem_statement\": \"example issue text\"}'"
