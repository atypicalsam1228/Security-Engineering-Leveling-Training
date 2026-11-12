#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Stores the policy-check Task (evidence-policy.yaml) and the reference answer for the
# learner's admit.py (admit.reference.py) in ConfigMap policy-kit in project build. Both are only stored, never applied;
# the learner extracts the Task, writes admit.py, and opens the reference only after trying.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_namespace build
oc create configmap policy-kit -n build --from-file="$(dirname "$0")/kit" --dry-run=client -o yaml | oc apply -f - >/dev/null
say "created ConfigMap policy-kit in build (evidence-policy.yaml, admit.reference.py)"
