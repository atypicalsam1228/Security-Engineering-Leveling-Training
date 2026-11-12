#!/usr/bin/env bash
# Removes the sandbox repository so the start state recreates it with its original commits (a learner may have pushed more).
set -uo pipefail
. "$(dirname "$0")/../../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN
curl -sS -X DELETE -H "Authorization: token $GITEA_TOKEN" "$GITEA_URL/api/v1/repos/$GITEA_USER/eng-sandbox" -o /dev/null || true
rm -rf "${HOME:-/workspace/.lab/home}/eng-practice/eng-sandbox"
