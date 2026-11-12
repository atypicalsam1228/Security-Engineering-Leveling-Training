#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: web, api, db and cache in arc-ref, with no policies of any kind.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
sed "s/__NS__/arc-ref/g" "$(dirname "$0")/arc-app.tpl" | oc apply -f - >/dev/null
for part in web api db cache; do
  oc rollout status "deployment/$part" -n arc-ref --timeout=240s
done
