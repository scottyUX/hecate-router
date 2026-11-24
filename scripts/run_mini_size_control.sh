#!/usr/bin/env bash
# TASK-003 owns only its own model/container and clean cache-page hints.
set -euo pipefail
TASK_ROOT="${1:?task root}"
TRAINING_DATA="${2:?training data}"
RUN_ID="${3:?run id}"
TASK_PYTHON="$TASK_ROOT/venv/bin/python"
export PYTHONPATH=src
export HECATE_CODE_SHA
HECATE_CODE_SHA="$(cat COMMIT)"
trim_pid=''
cleanup() {
    if [ -n "$trim_pid" ]; then kill "$trim_pid" 2>/dev/null || true; fi
    docker logs hecate-task003-model > "$TASK_ROOT/logs/model-final.log" 2>&1 || true
    docker stop hecate-task003-model >/dev/null 2>&1 || true
    docker rm hecate-task003-model >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
"$TASK_PYTHON" scripts/serve_codex_qwen7b.py --root "$TASK_ROOT" --config configs/mini_qwen7b_pilot.yaml --alongside-task002
# Trim only clean cached pages of this arm's exact pinned 7B snapshot, not files.
"$TASK_PYTHON" - "$TASK_ROOT" <<'PY' &
import os,pathlib,sys,time
root=pathlib.Path(sys.argv[1])/'hf/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242'
while True:
    for path in root.glob('*.safetensors'):
        with path.open('rb') as stream:
            os.posix_fadvise(stream.fileno(),0,0,os.POSIX_FADV_DONTNEED)
    time.sleep(5)
PY
trim_pid=$!
"$TASK_PYTHON" - <<'PY'
import httpx,time
for attempt in range(180):
    try:
        with httpx.Client(timeout=3,trust_env=False) as client:
            r=client.get('http://127.0.0.1:8128/v1/models');r.raise_for_status()
            assert 'Qwen/Qwen2.5-Coder-7B-Instruct' in {x['id'] for x in r.json()['data']}
        print('Mini 7B endpoint ready',flush=True)
        break
    except (httpx.HTTPError,AssertionError):
        time.sleep(5)
else:
    raise SystemExit('Mini 7B server failed to become ready')
PY
"$TASK_PYTHON" scripts/run_mini_baseline.py --root "$TASK_ROOT" --run-id "$RUN_ID" --dataset "$TRAINING_DATA"
