#!/usr/bin/env bash
# Run ON the execution VM: grade models of the three-model experiment in
# parallel, one tmux session per model, then (optionally) run the analysis
# once every grading session has exited.
#
#   bash scripts/grade_three_model.sh start opus minimax   # grade-opus, grade-minimax
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
R=data/outputs/runs/three-model-verified
WORKERS="${WORKERS:-4}"

start() {
  for m in "$@"; do
    if tmux has-session -t "grade-${m}" 2>/dev/null; then
      echo "grade-${m} already running; skipping"
      continue
    fi
    tmux new-session -d -s "grade-${m}" \
      "cd ${ROOT} && source .venv/bin/activate && \
       python scripts/run_execution.py --config ${R}/${m}/execution.yaml \
         --output-dir ${R}/${m} --run-id three-model-verified-${m}-exec \
         --max-workers ${WORKERS} 2>&1 | grep -v 'HF Hub' | tee -a ${R}/grade-${m}.log"
    echo "started grade-${m} (log: ${R}/grade-${m}.log)"
  done
}

status() {
  for m in gemini opus minimax; do
    local reports execs gens
    reports=$(ls ${R}/${m}/logs/run_evaluation/*/*/*/report.json 2>/dev/null | wc -l)
    execs=$( [ -f ${R}/${m}/executions.jsonl ] && wc -l < ${R}/${m}/executions.jsonl || echo 0)
    gens=$( [ -f ${R}/${m}/generations.jsonl ] && wc -l < ${R}/${m}/generations.jsonl || echo 0)
    echo "${m}: reports=${reports} executions=${execs}/${gens}"
  done
  tmux ls 2>/dev/null | grep '^grade' || echo "(no grade sessions)"
}

analyze_when_done() {
  # Waits for every grade* tmux session to exit, then runs the analysis.
  while tmux ls 2>/dev/null | grep -q '^grade'; do sleep 30; done
  source .venv/bin/activate
  python scripts/analyze_three_model.py
}

case "${1:-}" in
  start) shift; start "$@" ;;
  status) status ;;
  analyze-when-done) analyze_when_done ;;
  *) echo "usage: $0 {start <model>...|status|analyze-when-done}" >&2; exit 2 ;;
esac
