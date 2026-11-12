#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Makes sure etcd encryption is on (aesgcm) and complete,
# so the learner's new secret is stored encrypted. If encryption is already set, it is left alone and only waited on.
# Turning it on rolls the API servers and can take 20 minutes or longer (wait_until gives up after about 10 minutes
# per call; rerun lab start if it times out while the rollout is still going).
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
encryption_complete() {
  local res
  for res in openshiftapiserver kubeapiserver authentication.operator.openshift.io; do
    [ "$(oc get "$res" -o jsonpath='{.items[0].status.conditions[?(@.type=="Encrypted")].reason}' 2>/dev/null)" = EncryptionCompleted ] || return 1
  done
}
current=$(oc get apiserver cluster -o jsonpath='{.spec.encryption.type}')
if [ -z "$current" ] || [ "$current" = identity ]; then
  say "etcd encryption is off; turning on aesgcm"
  oc patch apiserver cluster --type=merge -p '{"spec":{"encryption":{"type":"aesgcm"}}}'
fi
wait_until "etcd encryption to complete" encryption_complete
say "etcd encryption is complete"
