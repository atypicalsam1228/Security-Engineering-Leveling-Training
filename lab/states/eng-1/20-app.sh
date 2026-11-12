#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: applies web, client and the web Service in net-lab, with no network policy.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
oc apply -f "$(dirname "$0")/net-app.tpl" >/dev/null
for part in web client; do
  oc rollout status "deployment/$part" -n net-lab --timeout=240s
done
