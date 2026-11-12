#!/usr/bin/env bash
# Remove what CPS-4 created: the namespace, and the two rules keys the module adds to the Falco config map.
set -euo pipefail
oc delete namespace secure-lab --ignore-not-found --wait=true
if oc get configmap falco-custom-rules -n security-tools >/dev/null 2>&1; then
  oc patch configmap falco-custom-rules -n security-tools --type=json \
    -p '[{"op":"remove","path":"/data/secure-lab-rules.yaml"}]' 2>/dev/null || true
  oc patch configmap falco-custom-rules -n security-tools --type=json \
    -p '[{"op":"remove","path":"/data/secret-read-rule.yaml"}]' 2>/dev/null || true
fi
