#!/usr/bin/env bash
# seed-labels.sh — Creates the standard label taxonomy in a GitHub repo.
#
# Usage:
#   GITHUB_TOKEN=<token> OWNER=<owner> REPO=<repo> bash scripts/seed-labels.sh
#
# Required env vars:
#   GITHUB_TOKEN  — personal access token with repo scope
#   OWNER         — repo owner (user or org)
#   REPO          — repository name

set -euo pipefail

: "${GITHUB_TOKEN:?GITHUB_TOKEN is required}"
: "${OWNER:?OWNER is required}"
: "${REPO:?REPO is required}"

API="https://api.github.com/repos/${OWNER}/${REPO}/labels"

create_label() {
  local name="$1"
  local color="$2"
  local description="$3"

  # Delete if it exists (idempotent)
  curl -sf -X DELETE "${API}/$(python3 -c "import urllib.parse; print(urllib.parse.quote('${name}'))")" \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" 2>/dev/null || true

  curl -sf -X POST "${API}" \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"${name}\", \"color\": \"${color//\#/}\", \"description\": \"${description}\"}" \
    > /dev/null

  echo "  ✓ ${name}"
}

echo "Seeding labels for ${OWNER}/${REPO}..."

# Type labels
create_label "type: bug"       "d73a4a" "Something broken / unexpected behaviour"
create_label "type: feature"   "0075ca" "New capability or user-visible improvement"
create_label "type: security"  "e8843a" "Vulnerability, hardening, access control"
create_label "type: ops"       "0e8a16" "Operational / infrastructure task"
create_label "type: docs"      "cfd3d7" "Documentation gap or inaccuracy"
create_label "type: support"   "f9d0c4" "Support / investigation request"

# Priority labels
create_label "priority: very-low"  "c2e0c6" "Nice to have — no urgency"
create_label "priority: low"       "a2d96a" "Pick up when convenient"
create_label "priority: mid"       "f9a825" "Should be done this sprint"
create_label "priority: high"      "f66a0a" "Do in the next session"
create_label "priority: very-high" "b60205" "Blocking / immediate action required"

# Status labels
create_label "status: ready-for-qa" "8b5cf6" "Implementation complete; pending QA validation"

echo ""
echo "Done! ${OWNER}/${REPO} has the standard label set."
