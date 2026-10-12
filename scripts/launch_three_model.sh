#!/usr/bin/env bash
# Run ON the execution VM: preflight, pre-pull images, then start the three
# models concurrently in separate tmux sessions.
#
#   bash scripts/launch_three_model.sh preflight   # docker auth, disk, keys
#   bash scripts/launch_three_model.sh pull        # pre-pull all 100 images
#   bash scripts/launch_three_model.sh start       # 3 tmux sessions, one per model
#   bash scripts/launch_three_model.sh status      # progress + spend per model
#
# EXPERIMENT=r2 selects the leaderboard-matched rerun (specs/018-three-model-r2):
# its task file, run root, config and caps all come from the r2 preset in
# scripts/run_three_model.py. Default is r1.
#
# Pre-pulling first means the three agent processes never race each other for
# the same image, an image-pull failure shows up here instead of as an
# instant empty submission, and disk exhaustion is caught before any spend.
set -euo pipefail

ROOT="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"
EXPERIMENT="${EXPERIMENT:-r1}"
case "${EXPERIMENT}" in
  r1) TASKS=configs/three_model_tasks.json
      RUN_ROOT=data/outputs/runs/three-model-verified
      SESSION=3m
      MINI_VERSION=2.4.6 ;;
  r2) TASKS=configs/three_model_tasks_r2.json
      RUN_ROOT=data/outputs/runs/three-model-verified-r2
      SESSION=3m-r2
      MINI_VERSION=2.0.0 ;;
  *) echo "unknown EXPERIMENT=${EXPERIMENT} (r1|r2)" >&2; exit 2 ;;
esac
WORKERS="${WORKERS:-4}"
MODELS=(opus gemini minimax)
# ~2-4 GB per image; refuse to start the pull below this much free space.
MIN_FREE_GB="${MIN_FREE_GB:-350}"

image_names() {
  python3 - "$TASKS" <<'EOF'
import json, sys
for t in json.load(open(sys.argv[1]))["tasks"]:
    iid = t["instance_id"].replace("__", "_1776_")
    print(f"docker.io/swebench/sweb.eval.x86_64.{iid}:latest".lower())
EOF
}

preflight() {
  echo "==> Docker Hub auth"
  # Pro's unlimited pulls only apply to an authenticated daemon client.
  if ! python3 -c "import json,os,sys; a=json.load(open(os.path.expanduser('~/.docker/config.json'))).get('auths',{}); sys.exit(0 if any('docker.io' in k for k in a) else 1)" 2>/dev/null; then
    echo "ERROR: not logged in to Docker Hub. Run: docker login -u <pro-user>  (paste a PAT)" >&2
    exit 1
  fi
  echo "    OK: credentials present for Docker Hub"
  echo "==> Pull quota probe (authenticated as the logged-in account)"
  AUTH=$(python3 -c "import json,os,base64;a=json.load(open(os.path.expanduser('~/.docker/config.json')))['auths'];k=[k for k in a if 'docker.io' in k][0];print(base64.b64decode(a[k].get('auth','')).decode())" 2>/dev/null || true)
  if [[ -z "${AUTH}" ]]; then
    echo "    skipped (credentials live in a credential helper; trust docker login)"
  else
    TOKEN=$(curl -s --user "${AUTH}" \
      "https://auth.docker.io/token?service=registry.docker.io&scope=repository:ratelimitpreview/test:pull" \
      | python3 -c "import json,sys;print(json.load(sys.stdin).get('token',''))")
    curl -s --head -H "Authorization: Bearer ${TOKEN}" \
      https://registry-1.docker.io/v2/ratelimitpreview/test/manifests/latest \
      | grep -i -E "ratelimit" || echo "    no ratelimit headers: unlimited (Pro)"
  fi
  echo "==> Disk"
  df -h / | tail -1
  FREE_GB=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
  if (( FREE_GB < MIN_FREE_GB )); then
    echo "WARNING: ${FREE_GB}G free < ${MIN_FREE_GB}G. Prune: docker image prune -a -f" >&2
  fi
  echo "==> OPENROUTER_API_KEY"
  grep -q '^OPENROUTER_API_KEY=.\+' .env && echo "    OK" || { echo "ERROR: missing in .env" >&2; exit 1; }
  echo "==> tmux / python"
  command -v tmux >/dev/null || { echo "ERROR: install tmux" >&2; exit 1; }
  local have
  have=$(.venv/bin/python -c "import minisweagent; print(minisweagent.__version__)" 2>/dev/null | tail -1)
  if [[ "${have}" != "${MINI_VERSION}" ]]; then
    echo "ERROR: ${EXPERIMENT} needs mini-swe-agent ${MINI_VERSION}, installed: ${have:-none}" >&2
    exit 1
  fi
  echo "    OK: mini-swe-agent ${have}"
  if [[ "${EXPERIMENT}" == r2 ]]; then
    echo "==> Config vs leaderboard"
    .venv/bin/python scripts/check_leaderboard_config.py --experiment r2 | grep -E "FAIL|RESULT"
  fi
}

pull() {
  local log="${RUN_ROOT}/pull.log"
  mkdir -p "${RUN_ROOT}"
  : > "${log}"
  # 4 parallel pulls; failures are logged, not fatal, and re-running skips
  # images already present.
  image_names | xargs -P 4 -I{} sh -c \
    'docker image inspect {} >/dev/null 2>&1 && echo "have {}" || (docker pull -q {} >/dev/null 2>&1 && echo "pulled {}" || echo "FAILED {}")' \
    | tee -a "${log}"
  local failed
  failed=$(grep -c '^FAILED' "${log}" || true)
  echo "==> $(image_names | wc -l) images, ${failed} failed. Disk now:"
  df -h / | tail -1
  if (( failed > 0 )); then
    echo "Re-run 'pull' before 'start'." >&2
    exit 1
  fi
}

start() {
  mkdir -p "${RUN_ROOT}"
  for m in "${MODELS[@]}"; do
    if tmux has-session -t "${SESSION}-${m}" 2>/dev/null; then
      echo "tmux session ${SESSION}-${m} already running; skipping"
      continue
    fi
    tmux new-session -d -s "${SESSION}-${m}" \
      "cd ${ROOT} && source .venv/bin/activate && \
       python scripts/run_three_model.py --experiment ${EXPERIMENT} --model ${m} \
         --workers ${WORKERS} 2>&1 | tee -a ${RUN_ROOT}/${m}.log"
    echo "started ${SESSION}-${m} (log: ${RUN_ROOT}/${m}.log)"
  done
  echo "Attach: tmux attach -t ${SESSION}-opus   |   status: EXPERIMENT=${EXPERIMENT} bash $0 status"
}

status() {
  for m in "${MODELS[@]}"; do
    python3 - "${RUN_ROOT}/${m}" "$m" "${TASKS}" <<'EOF'
import json, sys, pathlib
d, m = pathlib.Path(sys.argv[1]), sys.argv[2]
n = len(json.loads(pathlib.Path(sys.argv[3]).read_text())["tasks"])
preds = json.loads((d / "preds.json").read_text()) if (d / "preds.json").exists() else {}
cost, done, notraj, exits = 0.0, 0, 0, {}
for iid in preds:
    t = d / iid / f"{iid}.traj.json"
    if not t.exists():
        notraj += 1
        continue
    info = json.loads(t.read_text()).get("info", {})
    cost += (info.get("model_stats") or {}).get("instance_cost") or 0
    done += 1
    s = info.get("exit_status") or "?"
    exits[s] = exits.get(s, 0) + 1
print(f"{m:8s} done={done:3d}/{n} no_traj={notraj:2d} cost=${cost:7.2f} exits={exits}")
EOF
  done
  tmux ls 2>/dev/null | grep "^${SESSION}-[a-z]*:" || echo "(no ${SESSION}-* tmux sessions running)"
}

case "${1:-}" in
  preflight) preflight ;;
  pull) pull ;;
  start) start ;;
  status) status ;;
  *) echo "usage: $0 {preflight|pull|start|status}" >&2; exit 2 ;;
esac
