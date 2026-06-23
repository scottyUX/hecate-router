#!/usr/bin/env bash
# Create Hecate Stage 1 GitHub Project, configure Status workflow, add all issues.
# Requires: gh auth refresh -s project
set -euo pipefail

OWNER="${OWNER:-scottyUX}"
REPO="${REPO:-scottyUX/hecate}"
PROJECT_TITLE="${PROJECT_TITLE:-Hecate — Stage 1}"

echo "==> Checking project scope"
if ! gh project list --owner "$OWNER" >/dev/null 2>&1; then
  echo "ERROR: Missing GitHub Projects scope. Run:"
  echo "  gh auth refresh -h github.com -s project"
  exit 1
fi

echo "==> Creating project (skip if exists)"
PROJECT_NUM=$(gh project list --owner "$OWNER" --format json --jq ".projects[] | select(.title==\"${PROJECT_TITLE}\") | .number" | head -1)
if [[ -z "$PROJECT_NUM" ]]; then
  gh project create --owner "$OWNER" --title "$PROJECT_TITLE" \
    --readme "Patch generation for execution-grounded LLM routing (Stage 1)"
  PROJECT_NUM=$(gh project list --owner "$OWNER" --format json --jq ".projects[] | select(.title==\"${PROJECT_TITLE}\") | .number" | head -1)
fi
echo "Project number: $PROJECT_NUM"

echo "==> Linking repository"
gh project link "$PROJECT_NUM" --owner "$OWNER" --repo "$REPO" 2>/dev/null || true

echo "==> Configuring Status field options"
PROJECT_ID=$(gh project view "$PROJECT_NUM" --owner "$OWNER" --format json --jq '.id')
STATUS_FIELD=$(gh project field-list "$PROJECT_NUM" --owner "$OWNER" --format json --jq '.fields[] | select(.name=="Status")')

if [[ -n "$STATUS_FIELD" ]]; then
  FIELD_ID=$(echo "$STATUS_FIELD" | jq -r '.id')
  # Update Status options via GraphQL
  gh api graphql -f query='
    mutation($projectId: ID!, $fieldId: ID!) {
      updateProjectV2Field(input: {
        projectId: $projectId
        fieldId: $fieldId
        singleSelectOptions: [
          {name: "Backlog", color: GRAY, description: "Not yet ready"}
          {name: "Ready", color: BLUE, description: "Ready to start"}
          {name: "In progress", color: YELLOW, description: "Active work"}
          {name: "Review", color: ORANGE, description: "PR or review"}
          {name: "Done", color: GREEN, description: "Complete"}
        ]
      }) {
        projectV2Field { ... on ProjectV2SingleSelectField { name options { name } } }
      }
    }' -f projectId="$PROJECT_ID" -f fieldId="$FIELD_ID" 2>/dev/null || \
  echo "  (Status field customization may require manual edit in GitHub UI)"
fi

echo "==> Adding issues to project"
ISSUE_URLS=$(gh issue list --repo "$REPO" --limit 100 --json url --jq '.[].url')
while IFS= read -r url; do
  [[ -z "$url" ]] && continue
  gh project item-add "$PROJECT_NUM" --owner "$OWNER" --url "$url" 2>/dev/null || true
  echo "  added: $url"
done <<< "$ISSUE_URLS"

echo ""
echo "==> Project board ready"
echo "URL: https://github.com/users/${OWNER}/projects/${PROJECT_NUM}"
