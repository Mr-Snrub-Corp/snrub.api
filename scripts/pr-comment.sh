#!/usr/bin/env bash
# Upsert a PR comment identified by an HTML marker in its body, so repeated CI
# runs edit the existing comment instead of stacking new ones.
#
# Usage: scripts/pr-comment.sh <pr-number> <body-file> <marker>
# Requires GH_TOKEN and GITHUB_REPOSITORY in the environment.
set -euo pipefail

pr="$1"
body_file="$2"
marker="$3"

if [[ ! -s "$body_file" ]]; then
  echo "pr-comment: $body_file missing or empty" >&2
  exit 1
fi

# --paginate applies --jq per page, so empty pages emit nothing and head -n1
# takes the first match across all pages.
existing=$(
  gh api "repos/${GITHUB_REPOSITORY}/issues/${pr}/comments" --paginate \
    --jq "map(select(.body | contains(\"${marker}\"))) | first | .id // empty" | head -n1
)

if [[ -n "$existing" ]]; then
  gh api -X PATCH "repos/${GITHUB_REPOSITORY}/issues/comments/${existing}" \
    -F body=@"$body_file" --silent
  echo "pr-comment: updated ${existing}"
else
  gh api -X POST "repos/${GITHUB_REPOSITORY}/issues/${pr}/comments" \
    -F body=@"$body_file" --silent
  echo "pr-comment: created"
fi
