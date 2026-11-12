#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Read-only: Kyverno, the network plugin and PyYAML in the tools image.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
crd_established clusterpolicies.kyverno.io || die "Kyverno ClusterPolicy CRD is missing; the lab build installs Kyverno 1.19.2 in the kyverno namespace"
network=$(oc get network.config.openshift.io cluster -o jsonpath='{.status.networkType}')
[ "$network" = OVNKubernetes ] || die "NetworkPolicy checks need OVNKubernetes; this cluster uses $network"
python3 -c "import yaml" || die "python3 in the tools image has no yaml module (the image lists python3-pyyaml)"
say "Kyverno, the network plugin and PyYAML are ready"
