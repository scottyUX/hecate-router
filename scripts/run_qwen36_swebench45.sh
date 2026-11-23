#!/usr/bin/env bash
# TASK-012 on Spark: start the owned model server, gate, then one checkpoint of attempts.
# Phase A (no model) runs separately: run_qwen36_swebench45.py preflight --root <root>.
set -euo pipefail
TASK_ROOT="${1:?task root}"
cd "${HECATE_TASK_SOURCE:-$TASK_ROOT/source}"
export PYTHONPATH=src:scripts
export HECATE_CODE_SHA
HECATE_CODE_SHA="$(cat "$TASK_ROOT/COMMIT")"
TASK_PYTHON="$TASK_ROOT/venv/bin/python"
CONFIG="${HECATE_TASK_CONFIG:-configs/qwen36_swebench45.yaml}"
MODEL=hecate-task012-model
started=''
trim_pid=''
cleanup() {
    if [ -n "$trim_pid" ]; then kill "$trim_pid" 2>/dev/null || true; fi
    if [ -n "$started" ]; then
        docker logs "$MODEL" > "$TASK_ROOT/logs/model-$(date +%Y%m%dT%H%M%S)-$HECATE_CODE_SHA.log" 2>&1 || true
        docker stop "$MODEL" >/dev/null 2>&1 || true
        docker rm "$MODEL" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT INT TERM
"$TASK_PYTHON" - "$TASK_ROOT" <<'PY'
import os,json,subprocess,sys,time
from pathlib import Path
r=Path(sys.argv[1]); model=Path((r/'model-path.txt').read_text().strip())
if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():
    raise SystemExit('GPU occupied; other workloads will not be stopped')
for p in model.glob('*.safetensors'):
    with p.open('rb') as f:os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
memory={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemFree:','MemAvailable:'))}
if memory['MemFree']<90*1024**3 or memory['MemAvailable']<100*1024**3:raise SystemExit('Insufficient standalone memory')
(r/'memory-preflight.json').write_text(json.dumps({'memory_bytes':memory,'utc_timestamp':time.time()},indent=2)+'\n')
PY
"$TASK_PYTHON" scripts/serve_codex_qwen7b.py --root "$TASK_ROOT" --config "$CONFIG"
started=1
"$TASK_PYTHON" - "$TASK_ROOT" <<'PY' &
import os,sys,time
from pathlib import Path
r=Path((Path(sys.argv[1])/'model-path.txt').read_text().strip())
while True:
    for p in r.glob('*.safetensors'):
        with p.open('rb') as f:os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
    time.sleep(5)
PY
trim_pid=$!
"$TASK_PYTHON" - "$TASK_ROOT" "$MODEL" <<'PY'
import httpx,time,subprocess,json,sys
from pathlib import Path
for attempt in range(180):
    if subprocess.check_output(['docker','inspect','--format','{{.State.Running}}',sys.argv[2]],text=True).strip()!='true':
        raise SystemExit('Owned server exited before readiness')
    try:
        with httpx.Client(timeout=3,trust_env=False) as c:
            response=c.get('http://127.0.0.1:8136/v1/models');response.raise_for_status()
        model=next(x for x in response.json()['data'] if x['id']=='Qwen/Qwen3.6-35B-A3B')
        assert model.get('max_model_len')==262144, model
        (Path(sys.argv[1])/'endpoint-model.json').write_text(json.dumps(model,indent=2)+'\n')
        print('Exact model and native262144 context verified',flush=True);break
    except (httpx.HTTPError,AssertionError,StopIteration):time.sleep(5)
else:raise SystemExit('Native-context readiness timeout')
PY
"$TASK_PYTHON" -u scripts/run_qwen36_swebench45.py gate --root "$TASK_ROOT" --config "$CONFIG"
"$TASK_PYTHON" -u scripts/run_qwen36_swebench45.py schedule --root "$TASK_ROOT" --config "$CONFIG" "${@:2}"
