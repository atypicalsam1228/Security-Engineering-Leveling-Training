#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes the seed marker, the rule and the dashboard so lab start rebuilds the
# noisy starting state. Removing the ConfigMap also removes the anchor. Old records stay in Loki, but every record has
# seed_run=<anchor> and the module's searches and the gate use the current anchor only; the next lab start also asks Loki to
# delete the old copies. (Deleting here would be unsafe: a delete range processed later could remove the next copy.)
# Replay records carry their own run label.
set -euo pipefail
. "$(dirname "$0")/../../_common/lib.sh"
require_env GRAFANA_URL GRAFANA_USER GRAFANA_PASSWORD
oc delete configmap sdr-review -n siem --ignore-not-found >/dev/null
uid=$(grafana_get /api/v1/provisioning/alert-rules | jq -r '[.[]? | select(.title == "failed-login-burst") | .uid] | first // empty')
if [ -n "$uid" ]; then
  curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" -X DELETE -H 'X-Disable-Provenance: true' "$GRAFANA_URL/api/v1/provisioning/alert-rules/$uid" >/dev/null
fi
curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" -X DELETE "$GRAFANA_URL/api/dashboards/uid/sdr-auth-overview" >/dev/null
