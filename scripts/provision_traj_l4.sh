#!/usr/bin/env bash
# Short-lived L4 VM for v3 LoRA smoke. Do not use hecate-exec.
# Stop when idle: gcloud compute instances stop hecate-traj-l4 --zone us-central1-a
#
# Requires GPUS_ALL_REGIONS >= 1 on hecate-506120 (regional NVIDIA_L4_GPUS=1 is
# not enough; create fails when the global GPU quota is 0).
set -euo pipefail

PROJECT="${HECATE_GCP_PROJECT:-hecate-506120}"
ZONE="${HECATE_GCP_ZONE:-us-central1-a}"
INSTANCE="${HECATE_TRAJ_INSTANCE:-hecate-traj-l4}"

gcloud compute instances describe "${INSTANCE}" \
  --project "${PROJECT}" --zone "${ZONE}" >/dev/null 2>&1 && {
  STATUS=$(gcloud compute instances describe "${INSTANCE}" \
    --project "${PROJECT}" --zone "${ZONE}" --format='get(status)')
  echo "exists status=${STATUS}"
  if [[ "${STATUS}" == "TERMINATED" ]]; then
    gcloud compute instances start "${INSTANCE}" --project "${PROJECT}" --zone "${ZONE}"
  fi
  exit 0
}

echo "==> creating g2-standard-8 + 1x L4 (${INSTANCE})"
gcloud compute instances create "${INSTANCE}" \
  --project "${PROJECT}" \
  --zone "${ZONE}" \
  --machine-type g2-standard-8 \
  --accelerator=count=1,type=nvidia-l4 \
  --maintenance-policy TERMINATE \
  --provisioning-model STANDARD \
  --boot-disk-size 100GB \
  --boot-disk-type pd-balanced \
  --image-family pytorch-2-9-cu129-ubuntu-2404-nvidia-580 \
  --image-project deeplearning-platform-release \
  --metadata=install-nvidia-driver=True
