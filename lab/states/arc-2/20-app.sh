#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: applies web, api and db with their network policies in arc-lab.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
sed "s/__NS__/arc-lab/g" "$(dirname "$0")/arc-app.tpl" | oc apply -f - >/dev/null
for part in web api db; do
  oc rollout status "deployment/$part" -n arc-lab --timeout=240s
done
