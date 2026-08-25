#!/usr/bin/env bash
# Create (or reuse) the Stage-2 execution VM.
#
# Required:
#   export HECATE_GCP_PROJECT=your-gcp-project-id
#   gcloud auth login   # and ADC if you use it
#
# Optional:
#   HECATE_GCP_ZONE      default us-central1-a
#   HECATE_GCP_INSTANCE  default hecate-exec
#   HECATE_GCP_MACHINE   default n2-standard-8
#   HECATE_GCP_DISK_GB   default 200
#
# No service-account JSON. SSH with: gcloud compute ssh "$HECATE_GCP_INSTANCE"
set -euo pipefail

PROJECT="${HECATE_GCP_PROJECT:?Set HECATE_GCP_PROJECT to your GCP project id}"
ZONE="${HECATE_GCP_ZONE:-us-central1-a}"
INSTANCE="${HECATE_GCP_INSTANCE:-hecate-exec}"
MACHINE="${HECATE_GCP_MACHINE:-n2-standard-8}"
DISK_GB="${HECATE_GCP_DISK_GB:-200}"
IMAGE_FAMILY="${HECATE_GCP_IMAGE_FAMILY:-ubuntu-2204-lts}"
IMAGE_PROJECT="${HECATE_GCP_IMAGE_PROJECT:-ubuntu-os-cloud}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud not found. Install the Cloud SDK:" >&2
  echo "  https://cloud.google.com/sdk/docs/install" >&2
  exit 1
fi

echo "==> Project ${PROJECT} zone ${ZONE} instance ${INSTANCE}"
gcloud config set project "${PROJECT}" >/dev/null
gcloud services enable compute.googleapis.com --project "${PROJECT}"

if gcloud compute instances describe "${INSTANCE}" \
    --project "${PROJECT}" --zone "${ZONE}" >/dev/null 2>&1; then
  STATUS=$(gcloud compute instances describe "${INSTANCE}" \
    --project "${PROJECT}" --zone "${ZONE}" --format='get(status)')
  echo "Instance already exists (status=${STATUS})."
  if [[ "${STATUS}" == "TERMINATED" ]]; then
    echo "==> Starting stopped instance"
    gcloud compute instances start "${INSTANCE}" \
      --project "${PROJECT}" --zone "${ZONE}"
  fi
  exit 0
fi

STARTUP=$(cat <<'EOF'
#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git python3 python3-venv python3-pip python3-dev
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker
# Add every local login user (GCE SSH users are not always "ubuntu").
for u in ubuntu $(ls /home 2>/dev/null || true); do
  if id "$u" >/dev/null 2>&1; then
    usermod -aG docker "$u" || true
  fi
done
# Marker so the laptop can wait for bootstrap.
mkdir -p /var/lib/hecate
date -u +%Y-%m-%dT%H:%M:%SZ > /var/lib/hecate/bootstrap-complete
EOF
)

echo "==> Creating ${MACHINE} with ${DISK_GB} GB boot disk"
gcloud compute instances create "${INSTANCE}" \
  --project "${PROJECT}" \
  --zone "${ZONE}" \
  --machine-type "${MACHINE}" \
  --image-family "${IMAGE_FAMILY}" \
  --image-project "${IMAGE_PROJECT}" \
  --boot-disk-size "${DISK_GB}GB" \
  --boot-disk-type pd-balanced \
  --boot-disk-device-name "${INSTANCE}" \
  --metadata=startup-script="${STARTUP}" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --tags=hecate-exec

echo "Created. Wait for SSH, then follow docs/EXECUTION_GCP.md (sync + smoke)."
echo "  gcloud compute ssh ${INSTANCE} --project ${PROJECT} --zone ${ZONE}"
