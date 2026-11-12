#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes the learner's pipeline, the deployed det-* rules and the repository, so lab
# start rebuilds the starting repository.
set -euo pipefail
. "$(dirname "$0")/../../_common/lib.sh"
require_env GRAFANA_URL GRAFANA_USER GRAFANA_PASSWORD GITEA_URL GITEA_USER GITEA_TOKEN
oc delete pipeline detections -n build --ignore-not-found >/dev/null
oc delete task detections-step -n build --ignore-not-found >/dev/null
for uid in $(grafana_get /api/v1/provisioning/alert-rules | jq -r '.[]? | select(.uid | startswith("det-")) | .uid'); do
  curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" -X DELETE -H 'X-Disable-Provenance: true' "$GRAFANA_URL/api/v1/provisioning/alert-rules/$uid" >/dev/null
done
gitea_call DELETE "/repos/$GITEA_USER/detections"
oc delete rolebinding sdr5-probe -n demo --ignore-not-found >/dev/null
