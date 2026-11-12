#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Stores default-deny.yaml in ConfigMap secure-lab-kit in secure-lab so the learner extracts it
# (the same rule was written in the previous module). It is only stored, never applied. The allow rules, the security
# context patch and the check script are written by the learner.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
oc create configmap secure-lab-kit -n secure-lab --from-file="$(dirname "$0")/kit" --dry-run=client -o yaml | oc apply -f - >/dev/null
say "created ConfigMap secure-lab-kit in secure-lab (default-deny.yaml)"
