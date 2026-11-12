#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: web, api, db and three attack pods in each namespace. No policies: the learner applies them.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
for ns in arc-a arc-b; do
  sed "s/__NS__/$ns/g" "$(dirname "$0")/arc-app.tpl" | oc apply -f - >/dev/null
  for part in web api db; do
    oc rollout status "deployment/$part" -n "$ns" --timeout=240s
  done
  oc wait --for=condition=Ready pod/atk-stranger pod/atk-copied-plain pod/atk-copied-mesh -n "$ns" --timeout=240s
done
