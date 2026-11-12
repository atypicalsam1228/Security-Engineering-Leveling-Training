#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: applies suspect-app (one pod with a Service) and probe (a helper pod that only
# sleeps) in the project demo, with no network policy. The containment step of SDR-4 isolates the suspect pod.
# Runs before 20-seed.sh, which reads the real pod name and seeds it into the audit and Falco records.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_namespace demo
oc apply -f "$(dirname "$0")/suspect-app.tpl" >/dev/null
for part in suspect-app probe; do
  oc rollout status "deployment/$part" -n demo --timeout=240s
done
