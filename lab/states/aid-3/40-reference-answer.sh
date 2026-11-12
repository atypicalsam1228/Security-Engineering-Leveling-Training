#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: stores the reference answer for the Step 2 test the learner writes in
# ConfigMap aid3-reference in project build. It is only stored, never applied; the module says to read it after trying.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_namespace build
oc create configmap aid3-reference -n build --from-file="$(dirname "$0")/answers" --dry-run=client -o yaml | oc apply -f - >/dev/null
say "created ConfigMap aid3-reference in build (test_boolean_count.txt)"
