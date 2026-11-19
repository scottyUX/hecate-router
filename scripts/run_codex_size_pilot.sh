#!/usr/bin/env bash
# TASK-002: sequential local paired pilot. No advisor, router or hosted API.
# Run from its source checkout inside a task-owned tmux session.
set -euo pipefail
TASK_ROOT="${1:?usage: run_codex_size_pilot.sh <task-root> <attempt-tag> <training-jsonl>}"
ATTEMPT_TAG="${2:?attempt tag required}"
TRAINING_DATA="${3:?training dataset required}"
TASK_PYTHON="$TASK_ROOT/venv/bin/python"
TASK_CONTAINER=hecate-task002-model
export PYTHONPATH=src
export HECATE_CODE_SHA
HECATE_CODE_SHA="$(cat COMMIT)"
cleanup() {
    docker logs "$TASK_CONTAINER" > "$TASK_ROOT/logs/model-final-$ATTEMPT_TAG.log" 2>&1 || true
    docker stop "$TASK_CONTAINER" >/dev/null 2>&1 || true
    docker rm "$TASK_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

for arm in 7b 14b; do
    config="configs/codex_qwen_size_pilot_$arm.yaml"
    fixture_id="task002-${arm}-fixtures-${ATTEMPT_TAG}"
    pilot_id="task002-${arm}-pilot-${ATTEMPT_TAG}"
    echo "Starting $arm: $(date -Is)"
    "$TASK_PYTHON" scripts/serve_codex_qwen7b.py --root "$TASK_ROOT" --config "$config"
    "$TASK_PYTHON" - "$config" <<'PY'
import sys,time,httpx,yaml
cfg=yaml.safe_load(open(sys.argv[1]))
for attempt in range(180):
    try:
        with httpx.Client(timeout=3,trust_env=False) as client:
            response=client.get(cfg['serving']['endpoint']+'/models')
            response.raise_for_status()
            assert cfg['model']['id'] in {x['id'] for x in response.json()['data']}
        print('Model endpoint ready',flush=True)
        break
    except (httpx.HTTPError,AssertionError):
        time.sleep(5)
else:
    raise SystemExit('Model serving did not become ready within 15 minutes')
PY
    "$TASK_PYTHON" scripts/run_codex_baseline.py fixtures --root "$TASK_ROOT" --config "$config" --run-id "$fixture_id"
    set +e
    "$TASK_PYTHON" scripts/run_codex_baseline.py pilot --root "$TASK_ROOT" --config "$config" --run-id "$pilot_id" \
        --fixtures-run "$TASK_ROOT/runs/$fixture_id" --dataset "$TRAINING_DATA"
    pilot_exit=$?
    set -e
    "$TASK_PYTHON" - "$TASK_ROOT/runs/$pilot_id/results.json" "$pilot_exit" <<'PY'
import sys,json
r=json.load(open(sys.argv[1]))
print(json.dumps({'arm_complete':r.get('tasks_considered')==20,'pilot_exit':int(sys.argv[2]),'resolved':r.get('resolved'),'evaluable':r.get('evaluable'),'records':r.get('tasks_considered')}),flush=True)
if r.get('tasks_considered')!=20:
    raise SystemExit('Arm halted before 20 records; preserve evidence and inspect before continuing')
PY
    docker logs "$TASK_CONTAINER" > "$TASK_ROOT/logs/model-${arm}-$ATTEMPT_TAG.log" 2>&1 || true
    docker stop "$TASK_CONTAINER" >/dev/null
    docker rm "$TASK_CONTAINER" >/dev/null
    echo "Finished $arm: $(date -Is)"
done
