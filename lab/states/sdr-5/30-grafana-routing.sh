#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Creates the Mattermost contact point and the default notification route, only
# if missing, plus the siem-detect folder. The pipeline deploys the rules themselves.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GRAFANA_URL GRAFANA_USER GRAFANA_PASSWORD MM_WEBHOOK_URL
if ! grafana_get /api/v1/provisioning/contact-points | jq -e 'any(.[]?; .name == "mattermost")' >/dev/null; then
  grafana_send POST /api/v1/provisioning/contact-points \
    "$(jq -n --arg url "$(mm_pod_webhook_url)" '{name: "mattermost", type: "slack", settings: {url: $url}}')" >/dev/null
fi
# The siem-detect route re-posts a still-firing alert about every minute (the Grafana default is 5 minutes for the group
# interval and 4 hours for the repeat interval), so the Step 5 proof can be run again without a long wait.
grafana_send PUT /api/v1/provisioning/policies '{"receiver":"mattermost","group_by":["alertname"],"group_wait":"0s","routes":[{"receiver":"mattermost","object_matchers":[["grafana_folder","=","siem-detect"]],"group_wait":"0s","group_interval":"30s","repeat_interval":"1m"}]}' >/dev/null
folder_uid=$(grafana_get /api/folders | jq -r '[.[] | select(.title == "siem-detect") | .uid] | first // empty')
if [ -z "$folder_uid" ]; then
  grafana_send POST /api/folders '{"title":"siem-detect"}' >/dev/null
fi
