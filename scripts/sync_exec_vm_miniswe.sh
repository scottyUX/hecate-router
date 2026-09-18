#!/usr/bin/env bash
# Copy this working tree onto the execution VM for the mini-SWE-agent sweep.
#
# Differs from sync_exec_vm.sh in one way that matters: it uploads no
# generations.jsonl. On the parser path that file is produced locally and
# shipped to the VM for grading. On the agent path run_miniswe_sweep.py
# produces it ON the VM, so there is nothing to send -- and sending a
# placeholder would overwrite whatever sits at the destination, since that
# script's scp destination filename is hardcoded.
#
# Touches only RUN_DIR; existing run directories are left alone. The VM's own
# .env is excluded from the archive and kept as-is, so its OPENROUTER_API_KEY
# is never overwritten and the local key never leaves this machine.
# Requires HECATE_GCP_PROJECT and gcloud.
set -euo pipefail

ROOT="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${HECATE_GCP_PROJECT:?Set HECATE_GCP_PROJECT to your GCP project id}"
ZONE="${HECATE_GCP_ZONE:-us-central1-a}"
INSTANCE="${HECATE_GCP_INSTANCE:-hecate-exec}"
REMOTE_DIR="${HECATE_GCP_REMOTE_DIR:-/opt/hecate}"
RUN_ID="${HECATE_RUN_ID:-sweep-2x300-mini-swe}"
RUN_DIR="${REMOTE_DIR}/data/outputs/runs/${RUN_ID}"

SSH=(gcloud compute ssh "${INSTANCE}" --project "${PROJECT}" --zone "${ZONE}" --quiet)
SCP=(gcloud compute scp --project "${PROJECT}" --zone "${ZONE}" --quiet)

echo "==> Target: ${INSTANCE} (${PROJECT}/${ZONE})"
echo "==> Run dir: ${RUN_DIR}"

echo "==> Ensuring remote directories"
"${SSH[@]}" --command "mkdir -p ${RUN_DIR}"

STAGING="$(mktemp -d)"
cleanup() { rm -rf "${STAGING}"; }
trap cleanup EXIT

echo "==> Packing source (no .venv, .env, web/node_modules, data/cache, data/outputs)"
tar -C "${ROOT}" \
  --exclude .env \
  --exclude .venv \
  --exclude .venv312 \
  --exclude venv \
  --exclude web/node_modules \
  --exclude web/.next \
  --exclude data/cache \
  --exclude data/raw \
  --exclude data/output \
  --exclude data/outputs \
  --exclude .pytest_cache \
  --exclude __pycache__ \
  --exclude .git \
  -czf "${STAGING}/hecate-src.tgz" .

echo "==> Uploading tree"
"${SCP[@]}" "${STAGING}/hecate-src.tgz" "${INSTANCE}:/tmp/hecate-src.tgz"
# Overwrites files carried in the archive; deletes nothing else. Excluded
# paths (.venv, data/outputs, data/raw) are untouched on the VM.
"${SSH[@]}" --command "tar -C ${REMOTE_DIR} -xzf /tmp/hecate-src.tgz && rm /tmp/hecate-src.tgz"

echo "==> Checking the VM's own .env (never uploaded, never overwritten)"
# Fail here rather than part-way through a 600-instance sweep. Reports
# presence only; the key itself is never printed.
if ! "${SSH[@]}" --command \
  "grep -q '^OPENROUTER_API_KEY=.\\+' ${REMOTE_DIR}/.env 2>/dev/null"; then
  echo "ERROR: ${REMOTE_DIR}/.env on ${INSTANCE} has no non-empty" >&2
  echo "       OPENROUTER_API_KEY. The agent calls OpenRouter from the VM." >&2
  echo "       Set it there directly; this script will not upload one." >&2
  exit 1
fi
echo "    OK: OPENROUTER_API_KEY present on the VM"

cat <<EOF

Sync complete. No generations.jsonl was uploaded or overwritten.
The VM's existing .env was left untouched.

On the VM:

  gcloud compute ssh ${INSTANCE} --project ${PROJECT} --zone ${ZONE}
  cd ${REMOTE_DIR} && source .venv/bin/activate
  pip install -e ".[agent]"

  # dill 0.3.8 breaks on Python 3.14 and datasets is pinned <4; expect 300
  python -c "from hecate.data.tasks import load_swebench_lite; print(len(load_swebench_lite()))"

  # smoke across repos (no --platform; the VM is x86)
  python scripts/run_miniswe_sweep.py \\
    --filter "django__django-10914|sympy__sympy-20590|astropy__astropy-12907" \\
    --model qwen/qwen-2.5-7b-instruct --workers 3 \\
    --global-cost-limit 1 --allow-incomplete \\
    --output-dir data/outputs/runs/${RUN_ID} --run-id ${RUN_ID}
EOF
