#!/usr/bin/env bash
# Run ON the execution VM: grade models of the three-model experiment in
# parallel, one tmux session per model, then (optionally) run the analysis
# once every grading session has exited.
#
#   bash scripts/grade_three_model.sh start opus minimax   # grade-opus, grade-minimax
#   EXPERIMENT=r2 bash scripts/grade_three_model.sh start opus gemini minimax  # grade-r2-*
#   bash scripts/grade_three_model.sh analyze-when-done     # waits, then analysis
#   bash scripts/grade_three_model.sh status
#
# Never start two graders on the same model: run_execution only appends to
# executions.jsonl after its whole harness batch returns, so two concurrent
# runs on one model would grade the same instances and collide on container
# names. `start` refuses if a grade-<model> session already exists.
set -euo pipefail

ROOT="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"
# EXPERIMENT=r2 grades the leaderboard-matched rerun (specs/018); default r1.
EXPERIMENT="${EXPERIMENT:-r1}"
case "${EXPERIMENT}" in
  r1) R=data/outputs/runs/three-model-verified
      RUN_ID=three-model-verified
      TASKS=configs/three_model_tasks.json
      SESSION=grade ;;
  r2) R=data/outputs/runs/three-model-verified-r2
      RUN_ID=three-model-verified-r2
      TASKS=configs/three_model_tasks_r2.json
      SESSION=grade-r2 ;;
  *) echo "unknown EXPERIMENT=${EXPERIMENT} (r1|r2)" >&2; exit 2 ;;
esac
WORKERS="${WORKERS:-4}"

start() {
  for m in "$@"; do
    if tmux has-session -t "${SESSION}-${m}" 2>/dev/null; then
      echo "${SESSION}-${m} already running; skipping"
      continue
    fi
    tmux new-session -d -s "${SESSION}-${m}" \
      "cd ${ROOT} && source .venv/bin/activate && \
       python scripts/run_execution.py --config ${R}/${m}/execution.yaml \
         --output-dir ${R}/${m} --run-id ${RUN_ID}-${m}-exec \
         --max-workers ${WORKERS} 2>&1 | grep -v 'HF Hub' | tee -a ${R}/grade-${m}.log"
    echo "started ${SESSION}-${m} (log: ${R}/grade-${m}.log)"
  done
}

status() {
  for m in gemini opus minimax; do
    local reports execs gens
    reports=$(ls ${R}/${m}/logs/run_evaluation/*/*/*/report.json 2>/dev/null | wc -l || true)
    execs=$( [ -f ${R}/${m}/executions.jsonl ] && wc -l < ${R}/${m}/executions.jsonl || echo 0)
    gens=$( [ -f ${R}/${m}/generations.jsonl ] && wc -l < ${R}/${m}/generations.jsonl || echo 0)
    echo "${m}: reports=${reports} executions=${execs}/${gens}"
  done
  tmux ls 2>/dev/null | grep "^${SESSION}-[a-z]*:" || echo "(no ${SESSION}-* sessions)"
}

analyze_when_done() {
  # Waits for this experiment's grading sessions to exit, then runs the analysis.
  while tmux ls 2>/dev/null | grep -q "^${SESSION}-[a-z]*:"; do sleep 30; done
  source .venv/bin/activate
  python scripts/analyze_three_model.py --run-root "${R}" --tasks-file "${TASKS}"
}

case "${1:-}" in
  start) shift; start "$@" ;;
  status) status ;;
  analyze-when-done) analyze_when_done ;;
  *) echo "usage: $0 {start <model>...|status|analyze-when-done}" >&2; exit 2 ;;
esac
