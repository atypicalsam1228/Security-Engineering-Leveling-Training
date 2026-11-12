#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Puts the labeling stage back to a pass-through, removes the seed marker, and removes the
# containment work: the quarantine policy, any isolated pod (kept as evidence during the module) and the sample workloads.
# Removing the ConfigMap also removes the anchor. Old records stay in Loki, but every record has seed_run=<anchor> and the
# module's searches pin to the current anchor; the next lab start also asks Loki to delete the old copies.
set -euo pipefail
oc delete configmap sdr4-harness alloy-detect-label -n siem --ignore-not-found >/dev/null
oc delete networkpolicy quarantine-deny-all -n demo --ignore-not-found >/dev/null
oc delete pod -l quarantine=true -n demo --ignore-not-found >/dev/null
oc delete deployment suspect-app probe -n demo --ignore-not-found >/dev/null
oc delete service suspect-app -n demo --ignore-not-found >/dev/null
