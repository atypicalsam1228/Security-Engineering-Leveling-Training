#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Starts etcd encryption first and does not wait, so the rollout (20 minutes or longer the
# first time) overlaps the sample workload build in 10-secure-lab.sh. 20-etcd-encryption.sh then waits for it to finish.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
current=$(oc get apiserver cluster -o jsonpath='{.spec.encryption.type}')
if [ -z "$current" ] || [ "$current" = identity ]; then
  say "Turning on etcd encryption. The first time this can take 20 minutes or longer; lab start waits for it before it finishes. Read this module's Intent and Concepts while you wait. If lab start times out, run it again: the rollout keeps going."
  oc patch apiserver cluster --type=merge -p '{"spec":{"encryption":{"type":"aesgcm"}}}'
fi
