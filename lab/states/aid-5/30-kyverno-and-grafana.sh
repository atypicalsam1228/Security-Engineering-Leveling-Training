#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Checks Kyverno is installed (lab-provided; 1.19.x keeps ClusterPolicy) and creates
# what the module needs for its alert: the Grafana contact point mattermost, the default route, and the alert folder siem-detect.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GRAFANA_URL GRAFANA_USER GRAFANA_PASSWORD MM_WEBHOOK_URL
oc get crd clusterpolicies.kyverno.io >/dev/null || die "Kyverno ClusterPolicy is missing (the lab build installs Kyverno 1.19.x)"
oc get namespace kyverno >/dev/null
[ -n "$(grafana_get /api/datasources/name/Loki | jq -r '.uid // empty')" ] || die "Grafana has no data source named Loki"

if ! grafana_get /api/v1/provisioning/contact-points | jq -e 'any(.[]?; .name == "mattermost")' >/dev/null; then
  grafana_send POST /api/v1/provisioning/contact-points \
    "$(jq -n --arg url "$(mm_pod_webhook_url)" '{name: "mattermost", type: "slack", settings: {url: $url}}')" >/dev/null
fi
grafana_send PUT /api/v1/provisioning/policies '{"receiver":"mattermost","group_by":["alertname"],"group_wait":"0s"}' >/dev/null
folder_uid=$(grafana_get /api/folders | jq -r '[.[] | select(.title == "siem-detect") | .uid] | first // empty')
if [ -z "$folder_uid" ]; then
  grafana_send POST /api/folders '{"title":"siem-detect"}' >/dev/null
fi
say "Kyverno is present; Grafana has the contact point, route and folder"
