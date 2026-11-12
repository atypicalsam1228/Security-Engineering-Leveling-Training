#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Installs the Compliance Operator in
# openshift-compliance (package compliance-operator) and waits until the default ProfileBundles are VALID.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
bundles_valid() {
  oc get profilebundle -n openshift-compliance -o json |
    jq -e '(.items | length) > 0 and all(.items[]; .status.dataStreamStatus == "VALID")' >/dev/null
}
ensure_operator compliance-operator openshift-compliance own
wait_until "the default ProfileBundles to be VALID" bundles_valid
