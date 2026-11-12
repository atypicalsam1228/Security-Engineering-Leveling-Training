#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Publishes the supplied files in assets/ as ConfigMap vm-tools in security-tools.
# Learners fetch them with: oc extract configmap/vm-tools -n security-tools --to=. --confirm
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_namespace security-tools
oc create configmap vm-tools -n security-tools --from-file="$(dirname "$0")/assets" --dry-run=client -o yaml | oc apply -f - >/dev/null
