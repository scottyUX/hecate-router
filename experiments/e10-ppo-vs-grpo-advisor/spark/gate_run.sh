#!/usr/bin/env bash
# E10 gates G1 and G2 (amendment A4), GRPO arm only, on the DGX Spark.
#
#   gate_run.sh g1 <advisor_vllm_mem>    one training step (memory)
#   gate_run.sh g2 <advisor_vllm_mem>    three training steps (smoke)
#
# Run inside tmux, e.g.
#   tmux new -d -s e10-g1 'bash ~/e10-work/gate_run.sh g1 0.20 > ~/e10-logs/g1.log 2>&1'
#
# Starts, in order: a memory log (free -b every 10 s), the student (serve_student.sh),
# the eval server and the agent server (advisor-models, venvs ~/venvs/e10-eval and
# ~/venvs/e10-agent), then the trainer container running
# scripts/e10_train_swe_smith_grpo.sh with E10_GATE set. Everything it started is
# stopped on exit, whatever happens. Writes <run dir>/manifest.json and prints the
# peak memory. No sudo, nothing outside ~/e10-work, ~/e10-logs and the e10-hf volume.
set -euo pipefail

GATE="${1:?usage: gate_run.sh g1|g2 <advisor_vllm_mem>}"
ADVISOR_VLLM_MEM="${2:?usage: gate_run.sh g1|g2 <advisor_vllm_mem>}"
case "$GATE" in g1|g2) ;; *) echo "gate must be g1 or g2 (A4)" >&2; exit 2 ;; esac

AM="${AM:-$HOME/work/advisor-models-e10}"
AM_SHA_EXPECTED="${AM_SHA_EXPECTED:?set AM_SHA_EXPECTED to the advisor-models commit A4 runs}"
WORK="$HOME/e10-work"
LOGS="$HOME/e10-logs/$GATE"
RUNS="$WORK/runs"
AGENT_LOGS="$LOGS/agent-sessions"
SWESMITH_WORK="$WORK/swesmith-eval-$GATE"
TRAINER_IMAGE=hecate/skyrl-upstream-e10:3e8700f
ARM_IMAGE=hecate/swesmith.arm64.jd_1776_tenacity.0d40e76f:e10
STUDENT_IMAGE=vllm/vllm-openai:v0.20.0

mkdir -p "$LOGS" "$RUNS" "$AGENT_LOGS" "$SWESMITH_WORK"
PIDS=()
cleanup() {
    set +e
    docker stop e10-trainer >/dev/null 2>&1
    docker stop e10-student >/dev/null 2>&1
    docker stop e10-cachetrim >/dev/null 2>&1
    for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null; done
    echo "cleanup done: $(docker ps --format '{{.Names}}' | tr '\n' ' ')"
}
trap cleanup EXIT

# --- Preflight ---------------------------------------------------------------
echo "== preflight $(date -Is)"
df -h / | tail -1
free -h | sed -n 2p
if docker ps --format '{{.Names}}' | grep -q '^e10-'; then
    echo "an e10-* container is already running; stop it first" >&2; exit 1
fi
for img in "$TRAINER_IMAGE" "$ARM_IMAGE" "$STUDENT_IMAGE"; do
    docker image inspect "$img" >/dev/null || { echo "missing image $img" >&2; exit 1; }
done
AM_SHA="$(git -C "$AM" rev-parse HEAD)"
if [ "$AM_SHA" != "$(git -C "$AM" rev-parse "$AM_SHA_EXPECTED")" ] || [ -n "$(git -C "$AM" status --porcelain)" ]; then
    echo "advisor-models at $AM is not a clean checkout of $AM_SHA_EXPECTED" >&2; exit 1
fi
[ -f "$WORK/trim_weight_cache.py" ] || { echo "missing $WORK/trim_weight_cache.py" >&2; exit 1; }
for port in 8100 8081 8082; do
    if curl -s -m 2 "127.0.0.1:$port" >/dev/null; then echo "port $port is in use" >&2; exit 1; fi
done

# --- Weight-file cache trimming ----------------------------------------------------
# CUDA on the GB10 can use only free memory, not Linux's file cache, and the
# loaded weights otherwise sit in that cache (G1 attempt 6). Drop it for the
# e10-hf weight files now and every 10 s during the run (trim_weight_cache.py).
docker run -d --rm --name e10-cachetrim -v e10-hf:/hf:ro -v "$WORK":/w:ro --entrypoint python \
    "$TRAINER_IMAGE" /w/trim_weight_cache.py /hf --every 10 >/dev/null

# --- Memory log ----------------------------------------------------------------
( while true; do echo "$(date +%s) $(free -b | sed -n 2p)"; sleep 10; done ) > "$LOGS/memory.log" &
PIDS+=($!)

# --- Student ---------------------------------------------------------------------
bash "$WORK/serve_student.sh" > "$LOGS/student.log" 2>&1 &
PIDS+=($!)

# --- Eval and agent servers ------------------------------------------------------
export SWESMITH_IMAGE_OVERRIDE="$ARM_IMAGE"
( cd "$SWESMITH_WORK" && PYTHONPATH="$AM" exec ~/venvs/e10-eval/bin/python -m advisor_models.swe_smith.eval_server \
      --host 127.0.0.1 --port 8082 ) > "$LOGS/eval-server.log" 2>&1 &
PIDS+=($!)
( cd "$AM" && HOSTED_VLLM_API_BASE=http://localhost:8100/v1 \
      LITELLM_MODEL_REGISTRY_PATH="$AM/configs/litellm_local_student_registry.json" \
      exec ~/venvs/e10-agent/bin/python -m advisor_models.swe_smith.agent_server \
      --host 127.0.0.1 --port 8081 --log-dir "$AGENT_LOGS" ) > "$LOGS/agent-server.log" 2>&1 &
PIDS+=($!)

wait_for() {  # name url seconds
    for _ in $(seq 1 $(( $3 / 5 ))); do curl -s -m 5 "$2" >/dev/null && { echo "$1 up"; return 0; }; sleep 5; done
    echo "$1 did not come up at $2" >&2; return 1
}
wait_for student http://127.0.0.1:8100/v1/models 900
wait_for eval-server http://127.0.0.1:8082/health 120
wait_for agent-server http://127.0.0.1:8081/health 120

# --- Trainer ---------------------------------------------------------------------
RUN_ID="exp-10_arm-${GATE}smokegrpo_split-tenacitytrain_seed-0"
RUN_DIR="$RUNS/exports/$RUN_ID"
mkdir -p "$RUN_DIR"
START="$(date -Is)"
set +e
mkdir -p "$LOGS/ray"
# Ray's worker logs (vLLM engine cores, FSDP workers) are kept on the host: the
# trainer log does not always carry a worker's own error.
docker run --rm --name e10-trainer --gpus all --ipc=host --network host --shm-size=16g \
    -v "$AM":/w/advisor-models -v "$RUNS":/w/runs -v "$AGENT_LOGS":"$AGENT_LOGS" \
    -v e10-hf:/root/.cache/huggingface -v "$LOGS/ray":/tmp/ray \
    -e HF_HUB_OFFLINE=1 -e RAY_DEDUP_LOGS=0 \
    -e E10_GATE="$GATE" -e ADVISOR_VLLM_MEM="$ADVISOR_VLLM_MEM" \
    -e CKPT_ROOT=/w/runs/ckpts -e EXPORT_ROOT=/w/runs/exports \
    -e E10_AGENT_LOG_DIR="$AGENT_LOGS" \
    -e AGENT_SERVER_URL=http://127.0.0.1:8081 -e EVAL_SERVER_URL=http://127.0.0.1:8082 \
    -e AGENT_MODEL=hosted_vllm/student \
    "$TRAINER_IMAGE" bash -c "cd /w/advisor-models && bash scripts/e10_train_swe_smith_grpo.sh" \
    > "$LOGS/trainer.log" 2>&1
TRAINER_EXIT=$?
set -e
END="$(date -Is)"
# The trainer runs as root; hand its files back so they can be copied and removed without sudo.
docker run --rm -v "$RUNS":/w/runs -v "$LOGS/ray":/w/ray --entrypoint chown "$TRAINER_IMAGE" -R "$(id -u):$(id -g)" /w/runs /w/ray

# --- Manifest and peak memory ------------------------------------------------------
PEAK_USED=$(awk '{print $4}' "$LOGS/memory.log" | sort -n | tail -1)
MIN_AVAIL=$(awk '{print $8}' "$LOGS/memory.log" | sort -n | head -1)
MIN_FREE=$(awk '{print $5}' "$LOGS/memory.log" | sort -n | head -1)
cat > "$RUN_DIR/manifest.json" <<EOF
{
  "run_id": "$RUN_ID",
  "gate": "$GATE",
  "amendment": "A4",
  "advisor_models_sha": "$AM_SHA",
  "trainer_image": "$(docker image inspect -f '{{.Id}}' $TRAINER_IMAGE)",
  "student_image": "$(docker image inspect -f '{{.Id}}' $STUDENT_IMAGE)",
  "arm_image": "$(docker image inspect -f '{{.Id}}' $ARM_IMAGE)",
  "student": "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8, serve_student.sh (--gpu-memory-utilization 0.40, --max-model-len 65536, --seed 0), vLLM default sampling",
  "advisor_vllm_mem": $ADVISOR_VLLM_MEM,
  "start": "$START",
  "end": "$END",
  "trainer_exit": $TRAINER_EXIT,
  "peak_used_bytes": $PEAK_USED,
  "min_available_bytes": $MIN_AVAIL,
  "min_free_bytes": $MIN_FREE
}
EOF
cp "$LOGS/memory.log" "$LOGS/trainer.log" "$RUN_DIR/" 2>/dev/null || true
echo "== $GATE done: trainer exit $TRAINER_EXIT, peak used $((PEAK_USED / 1024**3)) GiB, min available $((MIN_AVAIL / 1024**3)) GiB, min free $((MIN_FREE / 1024**3)) GiB"
echo "== run dir $RUN_DIR"
exit "$TRAINER_EXIT"
