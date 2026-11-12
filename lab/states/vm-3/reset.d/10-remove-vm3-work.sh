#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes the repository vm-app so the start state recreates it (clears branches and issues).
set -uo pipefail
. "$(dirname "$0")/../../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN
curl -sS -X DELETE -H "Authorization: token $GITEA_TOKEN" "$GITEA_URL/api/v1/repos/$GITEA_USER/vm-app" -o /dev/null || true
