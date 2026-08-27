#!/usr/bin/env bash
# Full protocol after the leave-django-out smoke gate passes.
# HOLD_REPO2 is computed from the CSV histogram if unset.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PROVENANCE="${PROVENANCE:-unknown}"
HOLD_REPO="${HOLD_REPO:-django/django}"

if [[ -z "${HOLD_REPO2:-}" ]]; then
  HOLD_REPO2="$(python - <<'PY'
from pathlib import Path
from hecate.data.external_miniswe import read_joined_csv, read_joined_text_csv, JoinError, JoinedLabel
from hecate.router.dataset import RouterExample
from hecate.router.traj import second_holdout_repo

csv = Path("data/external/qwen3coder_vs_claude4opus_miniswe_external.csv")
try:
    rows = read_joined_csv(csv)
except JoinError:
    rows = [
        JoinedLabel(r.instance_id, r.repo, r.small_model_resolved, r.large_model_resolved)
        for r in read_joined_text_csv(Path("data/external/qwen3coder_vs_claude4opus_with_text.csv"))
    ]
examples = [
    RouterExample(r.instance_id, r.repo, "", False, r.small_model_resolved, r.large_model_resolved)
    for r in rows
]
print(second_holdout_repo(examples, "django/django"))
PY
)"
fi

echo "second holdout repo: $HOLD_REPO2"

for ARM in k0 k3; do
  python scripts/run_train_traj.py \
    --backend lora \
    --arm "$ARM" \
    --split grouped \
    --provenance "$PROVENANCE" \
    --run-id "v3-grouped-${ARM}" \
    --output-dir "data/outputs/runs/v3-grouped-${ARM}"

  python scripts/run_train_traj.py \
    --backend lora \
    --arm "$ARM" \
    --split leave-repo \
    --hold-repo "$HOLD_REPO" \
    --provenance "$PROVENANCE" \
    --run-id "v3-django-${ARM}" \
    --output-dir "data/outputs/runs/v3-django-${ARM}"

  python scripts/run_train_traj.py \
    --backend lora \
    --arm "$ARM" \
    --split leave-repo \
    --hold-repo "$HOLD_REPO2" \
    --provenance "$PROVENANCE" \
    --run-id "v3-second-${ARM}" \
    --output-dir "data/outputs/runs/v3-second-${ARM}"
done
