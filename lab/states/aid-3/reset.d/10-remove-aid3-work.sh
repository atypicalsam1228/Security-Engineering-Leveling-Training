#!/usr/bin/env bash
# Removes the repository ai-tools and the local clone so the start state recreates them (clears pull requests and branches).
set -uo pipefail
. "$(dirname "$0")/../../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN
curl -sS -X DELETE -H "Authorization: token $GITEA_TOKEN" "$GITEA_URL/api/v1/repos/$GITEA_USER/ai-tools" -o /dev/null || true
rm -rf /workspace/aid-3/ai-tools
