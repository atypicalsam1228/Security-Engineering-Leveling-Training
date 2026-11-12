#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes what AID-5 steps 1 to 4 create.
set -euo pipefail
. "$(dirname "$0")/../../_common/lib.sh"
oc delete clusterpolicy agent-baseline agent-binding agent-network agent-guardrails agent-guardrails-roles agent-guardrails-cluster --ignore-not-found
oc delete clusterrole kyverno-agent-baseline --ignore-not-found
oc delete namespace agents agents-b agents-c --ignore-not-found
if [ -n "${GRAFANA_URL:-}" ]; then
  uid=$(grafana_get /api/v1/provisioning/alert-rules | jq -r '.[]? | select(.title == "agent-out-of-list") | .uid')
  [ -z "$uid" ] || grafana_send DELETE "/api/v1/provisioning/alert-rules/$uid" '' >/dev/null
fi
