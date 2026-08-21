#!/usr/bin/env bash
# Copy this working tree and Stage-1 generations.jsonl onto the execution VM.
# Does not commit data. Requires HECATE_GCP_PROJECT and gcloud.
set -euo pipefail

ROOT="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${HECATE_GCP_PROJECT:?Set HECATE_GCP_PROJECT to your GCP project id}"
ZONE="${HECATE_GCP_ZONE:-us-central1-a}"
INSTANCE="${HECATE_GCP_INSTANCE:-hecate-exec}"
REMOTE_DIR="${HECATE_GCP_REMOTE_DIR:-~/hecate}"
GENERATIONS="${HECATE_GENERATIONS:-$ROOT/data/outputs/runs/sweep-2x300-qwen/generations.jsonl}"

if [[ ! -f "${GENERATIONS}" ]]; then
  echo "ERROR: generations file missing: ${GENERATIONS}" >&2
  exit 1
fi

SSH=(gcloud compute ssh "${INSTANCE}" --project "${PROJECT}" --zone "${ZONE}" --quiet)
SCP=(gcloud compute scp --project "${PROJECT}" --zone "${ZONE}" --quiet)

echo "==> Ensuring remote ${REMOTE_DIR}"
"${SSH[@]}" --command "mkdir -p ${REMOTE_DIR}/data/outputs/runs/sweep-2x300-qwen"

STAGING="$(mktemp -d)"
cleanup() { rm -rf "${STAGING}"; }
trap cleanup EXIT

echo "==> Packing source (no .venv, web/node_modules, data/cache)"
tar -C "${ROOT}" \
  --exclude .venv \
  --exclude venv \
  --exclude web/node_modules \
  --exclude web/.next \
  --exclude data/cache \
  --exclude data/raw \
  --exclude data/outputs \
  --exclude .pytest_cache \
  --exclude __pycache__ \
  -czf "${STAGING}/hecate-src.tgz" .

echo "==> Uploading tree"
"${SCP[@]}" "${STAGING}/hecate-src.tgz" "${INSTANCE}:/tmp/hecate-src.tgz"
"${SSH[@]}" --command "tar -C ${REMOTE_DIR} -xzf /tmp/hecate-src.tgz && rm /tmp/hecate-src.tgz"

echo "==> Uploading generations.jsonl"
"${SCP[@]}" "${GENERATIONS}" \
  "${INSTANCE}:${REMOTE_DIR}/data/outputs/runs/sweep-2x300-qwen/generations.jsonl"

echo "Sync complete. Next: SSH in and follow docs/EXECUTION_GCP.md (venv + smoke)."
