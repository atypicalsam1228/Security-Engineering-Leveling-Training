#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Read-only: checks Kyverno and the network plugin before ARC-2 builds anything.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
crd_established clusterpolicies.kyverno.io || die "Kyverno ClusterPolicy CRD is missing; the lab build installs Kyverno 1.19.2 in the kyverno namespace"
oc get pods -n kyverno --no-headers | grep -q Running || die "no Running Kyverno pods in the kyverno namespace"
network=$(oc get network.config.openshift.io cluster -o jsonpath='{.status.networkType}')
[ "$network" = OVNKubernetes ] || die "NetworkPolicy checks need OVNKubernetes; this cluster uses $network"
say "Kyverno is running and the network plugin is $network"
