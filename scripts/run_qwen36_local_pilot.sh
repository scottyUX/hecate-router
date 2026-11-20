#!/usr/bin/env bash
# Single approved task; independently validated controls are required first.
set -euo pipefail
TASK_ROOT="${1:?task root}"
CONTROL_RUN="${2:?validated control run}"
TASK_PYTHON="$TASK_ROOT/venv/bin/python"
TASK_CONFIG=configs/qwen36_local_evaluator.yaml
RUNTIME_SOURCE="${3:-$TASK_ROOT/source}"
cd "$RUNTIME_SOURCE"
export PYTHONPATH=src
export HECATE_CODE_SHA
HECATE_CODE_SHA="$(cat "$TASK_ROOT/runtime-commit.txt")"
model_started=''
trim_pid=''
cleanup() {
    if [ -n "$trim_pid" ]; then kill "$trim_pid" 2>/dev/null || true; fi
    if [ -n "$model_started" ]; then
        docker logs hecate-task009-model > "$TASK_ROOT/logs/model-final.log" 2>&1 || true
        docker stop hecate-task009-model >/dev/null 2>&1 || true
        docker rm hecate-task009-model >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT INT TERM
"$TASK_PYTHON" - "$CONTROL_RUN" <<'PY'
import json,sys
from pathlib import Path
from hecate.execution.codex_artifacts import checksums
p=Path(sys.argv[1])
assert checksums(p)==json.loads((p/'checksums.json').read_text()), 'Control checksum mismatch'
assert json.loads((p/'results.json').read_text()).get('controls_passed') is True
print('Independent official evaluator controls verified',flush=True)
PY
"$TASK_PYTHON" - "$TASK_ROOT" <<'PY'
import os,json,subprocess,time,sys
from pathlib import Path
root=Path(sys.argv[1])
model=root/'hf/models--Qwen--Qwen3.6-35B-A3B/snapshots/345d467b117d1fd5eda9b879a5988de9ae5f47a7'
for attempt in range(24):
    active=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    if active: raise SystemExit('GPU is occupied; no other workload will be stopped')
    for p in model.glob('*.safetensors'):
        with p.open('rb') as f: os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
    mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemFree:','MemAvailable:'))}
    if mem['MemFree']>=90*1024**3 and mem['MemAvailable']>=100*1024**3:
        (root/'memory-preflight.json').write_text(json.dumps({'memory_bytes':mem,'active_gpu_pids':[],'time':time.time()},indent=2)+'\n')
        print('Idle GPU and BF16 memory headroom verified',flush=True);break
    time.sleep(5)
else: raise SystemExit('Insufficient standalone memory; no inference started')
PY
"$TASK_PYTHON" scripts/serve_codex_qwen7b.py --root "$TASK_ROOT" --config "$TASK_CONFIG"
model_started=1
"$TASK_PYTHON" - "$TASK_ROOT" <<'PY' &
import os,sys,time
from pathlib import Path
model=Path(sys.argv[1])/'hf/models--Qwen--Qwen3.6-35B-A3B/snapshots/345d467b117d1fd5eda9b879a5988de9ae5f47a7'
while True:
    for p in model.glob('*.safetensors'):
        with p.open('rb') as f: os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
    time.sleep(5)
PY
trim_pid=$!
"$TASK_PYTHON" - <<'PY'
import time,httpx,subprocess
for attempt in range(180):
    state=subprocess.check_output(['docker','inspect','--format','{{.State.Running}}','hecate-task009-model'],text=True).strip()
    if state!='true': raise SystemExit('Owned inference container stopped before readiness; preserve logs')
    try:
        with httpx.Client(timeout=3,trust_env=False) as c:
            r=c.get('http://127.0.0.1:8132/v1/models');r.raise_for_status()
            assert 'Qwen/Qwen3.6-35B-A3B' in {m['id'] for m in r.json()['data']}
        print('Exact Qwen3.6 endpoint ready',flush=True);break
    except (httpx.HTTPError,AssertionError): time.sleep(5)
else: raise SystemExit('Endpoint readiness timeout')
PY
"$TASK_PYTHON" scripts/run_qwen36_swebench_pilot.py attempt \
    --root "$TASK_ROOT" --dataset "$TASK_ROOT/hecate-task008-verified.parquet" \
    --config "$TASK_CONFIG" --controls-run "$CONTROL_RUN" \
    --run-id task009-qwen36-codex-one-task-run-01
