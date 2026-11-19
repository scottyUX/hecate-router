#!/usr/bin/env bash
# TASK-006: parallel CPU preparation, resource-guarded single-GPU inference.
set -euo pipefail
TASK_ROOT="${1:?task root}"
TRAINING_DATA="${2:?training dataset}"
ATTEMPT="${3:?attempt tag}"
TASK_CONFIG=configs/codex_qwen3_30b_pilot.yaml
TASK_PYTHON="$TASK_ROOT/venv/bin/python"
export PYTHONPATH=src
export HECATE_CODE_SHA
HECATE_CODE_SHA="$(cat COMMIT)"
trim_pid=''
started_model=''
cleanup() {
    if [ -n "$trim_pid" ]; then kill "$trim_pid" 2>/dev/null || true; fi
    if [ -n "$started_model" ]; then
        docker logs hecate-task006-model > "$TASK_ROOT/logs/model-final-$ATTEMPT.log" 2>&1 || true
        docker stop hecate-task006-model >/dev/null 2>&1 || true
        docker rm hecate-task006-model >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT INT TERM
# Download and integrity checks use the existing bootstrap interpreter, not GPU.
"$HOME/venvs/vllm-qwen/bin/python" scripts/setup_codex_qwen7b.py --root "$TASK_ROOT" --config "$TASK_CONFIG"
echo "Assets ready: $(date -Is)"
"$TASK_PYTHON" - "$TASK_ROOT" <<'PY'
import pathlib,subprocess,os,sys,time,json
root=pathlib.Path(sys.argv[1]);home=pathlib.Path.home()
owned=[home/'work/hecate-task001/hf/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242',home/'work/hecate-task001/hf/models--Qwen--Qwen2.5-Coder-14B-Instruct/snapshots/aedcc2d42b622764e023cf882b6652e646b95671',root/'hf/models--Qwen--Qwen3-Coder-30B-A3B-Instruct/snapshots/b2cff646eb4bb1d68355c01b18ae02e7cf42d120']
for attempt in range(720):
    active=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    if not active:
        for directory in owned:
            for path in directory.glob('*.safetensors'):
                with path.open('rb') as stream:os.posix_fadvise(stream.fileno(),0,0,os.POSIX_FADV_DONTNEED)
        mem={line.split(':')[0]:int(line.split()[1])*1024 for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemFree:','MemAvailable:'))}
        if mem['MemFree']>=90*1024**3 and mem['MemAvailable']>=100*1024**3:
            (root/'memory-preflight.json').write_text(json.dumps({'memory_bytes':mem,'active_gpu_pids':[],'time':time.time()},indent=2)+'\n')
            print('GPU and memory guard passed',flush=True);break
    if attempt%30==0:print('Waiting for idle GPU and standalone BF16 memory headroom',flush=True)
    time.sleep(5)
else:raise SystemExit('Resource guard did not pass within one hour; no model started')
PY
"$TASK_PYTHON" scripts/serve_codex_qwen7b.py --root "$TASK_ROOT" --config "$TASK_CONFIG"
started_model=1
"$TASK_PYTHON" - "$TASK_ROOT" <<'PY' &
import pathlib,os,sys,time
root=pathlib.Path(sys.argv[1])/'hf/models--Qwen--Qwen3-Coder-30B-A3B-Instruct/snapshots/b2cff646eb4bb1d68355c01b18ae02e7cf42d120'
while True:
    for path in root.glob('*.safetensors'):
        with path.open('rb') as stream:os.posix_fadvise(stream.fileno(),0,0,os.POSIX_FADV_DONTNEED)
    time.sleep(5)
PY
trim_pid=$!
"$TASK_PYTHON" - <<'PY'
import httpx,time
for attempt in range(180):
    try:
        with httpx.Client(timeout=3,trust_env=False) as client:
            response=client.get('http://127.0.0.1:8130/v1/models');response.raise_for_status()
            assert 'Qwen/Qwen3-Coder-30B-A3B-Instruct' in {x['id'] for x in response.json()['data']}
        print('Qwen3 Codex endpoint ready',flush=True);break
    except (httpx.HTTPError,AssertionError):time.sleep(5)
else:raise SystemExit('Qwen3 server failed readiness within15min')
PY
"$TASK_PYTHON" scripts/run_codex_baseline.py fixtures --root "$TASK_ROOT" --config "$TASK_CONFIG" --run-id "task006-qwen3-fixtures-$ATTEMPT"
"$TASK_PYTHON" scripts/run_codex_baseline.py pilot --root "$TASK_ROOT" --config "$TASK_CONFIG" --run-id "task006-qwen3-codex-pilot-$ATTEMPT" --fixtures-run "$TASK_ROOT/runs/task006-qwen3-fixtures-$ATTEMPT" --dataset "$TRAINING_DATA"
