#!/usr/bin/env bash
# Bootstrap GitHub labels, milestones, issues, and project board for Hecate Stage 1.
# Idempotent where possible — safe to re-run after partial failure.
set -euo pipefail

REPO="${REPO:-scottyUX/hecate}"

echo "==> Creating labels on ${REPO}"
# name|color|description
labels=(
  "stage-1|0E8A16|Current Stage 1 work"
  "setup|1D76DB|Repo and environment bootstrap"
  "scaffold|5319E7|Context builder and prompt template"
  "generation|FBCA04|OpenRouter client and runner"
  "infra|006B75|Data schema, cache, and plumbing"
  "pilot|D93F0B|20-task pilot gate"
  "cost|B60205|Budget guard and token accounting"
  "docs|0075CA|Reports and handoff artifacts"
  "downstream|C5DEF5|Future pipeline stages (epics)"
  "blocked|000000|Waiting on external input"
  "needs-verification|E99695|Slugs or pricing TBD"
)
for entry in "${labels[@]}"; do
  IFS='|' read -r name color desc <<< "$entry"
  gh label create "$name" --repo "$REPO" --color "$color" --description "$desc" --force 2>/dev/null || true
  echo "  label: $name"
done

echo "==> Creating milestones on ${REPO}"
milestones=(
  "M0 — Project setup"
  "M1 — Pilot (20 tasks)"
  "M2 — Full sweep (1,200 patches)"
  "M3 — Execution & labels"
  "M4 — Router training"
  "M5 — Evaluation"
  "M6 — SDLC adaptation"
)
for title in "${milestones[@]}"; do
  existing=$(gh api "repos/${REPO}/milestones" --jq ".[] | select(.title==\"${title}\") | .number" 2>/dev/null || true)
  if [[ -z "$existing" ]]; then
    gh api "repos/${REPO}/milestones" -f title="$title" -f state=open >/dev/null
    echo "  created: $title"
  else
    echo "  exists:  $title (#${existing})"
  fi
done

echo "==> Labels and milestones ready."
