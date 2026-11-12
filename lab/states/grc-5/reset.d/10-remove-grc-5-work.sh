#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes what GRC-5 creates: the CronJob, its jobs, the config maps, the results
# volume (recreated by 30-monitor-access.yaml) and the test role binding.
set -euo pipefail
. "$(dirname "$0")/../../_common/lib.sh"
oc delete cronjob control-monitor -n build --ignore-not-found
oc delete job monitor-first monitor-drift -n build --ignore-not-found
oc delete configmap monitor-scripts monitor-baseline -n build --ignore-not-found
oc delete pvc monitor-pvc -n build --ignore-not-found
oc delete rolebinding extra-admin -n demo --ignore-not-found
