#!/usr/bin/env bash
# One-seed leave-django-out K=0 then K=3 smoke on a short-lived L4 VM.
# Do not run on hecate-exec (CPU). Stop the GPU VM when idle.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PROVENANCE="${PROVENANCE:-unknown}"
export PYTORCH_ALLOC_CONF="${PYTORCH_ALLOC_CONF:-expandable_segments:True}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
HOLD_REPO="${HOLD_REPO:-django/django}"
OUT_K0="${OUT_K0:-data/outputs/runs/v3-smoke-k0}"
OUT_K3="${OUT_K3:-data/outputs/runs/v3-smoke-k3}"

python scripts/run_train_traj.py \
  --backend lora \
  --arm k0 \
  --split leave-repo \
  --hold-repo "$HOLD_REPO" \
  --seeds 0 \
  --hold-only \
  --provenance "$PROVENANCE" \
  --run-id v3-smoke-k0 \
  --output-dir "$OUT_K0"

python scripts/run_train_traj.py \
  --backend lora \
  --arm k3 \
  --split leave-repo \
  --hold-repo "$HOLD_REPO" \
  --seeds 0 \
  --hold-only \
  --provenance "$PROVENANCE" \
  --run-id v3-smoke-k3 \
  --output-dir "$OUT_K3"

python - <<'PY'
import json
from pathlib import Path

def django_auc(path: Path) -> float | None:
    payload = json.loads(path.read_text())
    dirs = payload.get("directions") or {}
    block = (dirs.get("lora") or dirs.get("scripted") or {}).get("hold_django") or {}
    stat = block.get("route_auc") or {}
    return stat.get("mean")

k0 = django_auc(Path("data/outputs/runs/v3-smoke-k0/results.json"))
k3 = django_auc(Path("data/outputs/runs/v3-smoke-k3/results.json"))
print(f"django Route-AUC k0={k0} k3={k3}")
if k0 is None or k3 is None:
    raise SystemExit("missing django Route-AUC; do not scale to the full protocol")
# Clearly above: not a 0.005 tick, and above the v1/v2 ~0.48 floor.
delta = k3 - k0
clear = k3 > k0 + 0.02 and k3 > 0.48
print(f"delta={delta:.4f} clearly_above={clear}")
if not clear:
    raise SystemExit("GATE: K=3 is not clearly above K=0; stop before 5-fold x 3-seed")
print("GATE PASS: proceed to 5-fold x 3-seed plus second-repo holdout")
PY
