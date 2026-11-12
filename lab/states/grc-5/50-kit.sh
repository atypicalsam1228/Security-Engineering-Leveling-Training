#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Stores the kit files (control-monitor.yaml the scheduled job, measure.py, compare-reference.py the answer to the Step 3 exercise) in ConfigMap monitor-kit in project build,
# so the learner extracts them one at a time with --keys. Nothing is applied.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
oc create configmap monitor-kit -n build --from-file="$(dirname "$0")/kit" --dry-run=client -o yaml | oc apply -f - >/dev/null
say "created ConfigMap monitor-kit in build (control-monitor.yaml)"
