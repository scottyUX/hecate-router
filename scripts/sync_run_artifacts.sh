#!/usr/bin/env bash
# Copy a finished run directory to HECATE_ARTIFACTS_URI/runs/<run_id>/.
# Fail-closed: missing URI, missing run dir, or a failed copy exits 1.
set -euo pipefail

ROOT="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${1:-}"
if [[ -z "${RUN_DIR}" || ! -d "${RUN_DIR}" ]]; then
  echo "Usage: scripts/sync_run_artifacts.sh <run_dir>" >&2
  exit 1
fi

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
python3 - "${RUN_DIR}" <<'PY'
import sys
from pathlib import Path

from hecate.utils.artifacts import (
    ARTIFACTS_URI_ENV,
    ArtifactError,
    artifacts_uri_from_env,
    finalize_run_artifacts,
)

run_dir = Path(sys.argv[1]).resolve()
manifest = run_dir / "manifest.json"
if not manifest.is_file():
    raise SystemExit(f"missing {manifest}")
import json
run_id = json.loads(manifest.read_text(encoding="utf-8")).get("run_id")
if not run_id:
    raise SystemExit(f"manifest missing run_id: {manifest}")
base = artifacts_uri_from_env()
if not base:
    raise SystemExit(f"{ARTIFACTS_URI_ENV} is not set")
try:
    dest = finalize_run_artifacts(run_dir, base_uri=base, run_id=str(run_id))
except ArtifactError as exc:
    raise SystemExit(str(exc)) from exc
print(f"artifacts={dest}")
PY
