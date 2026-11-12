#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Installs the Service Mesh 3 operator, then an Istio resource named default and an IstioCNI resource named default (needed by this module alone; nothing earlier has to have run).
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
say "Installing the Service Mesh operator. Expect 5 to 10 minutes the first time and only seconds after that. Read this module's Intent and Concepts while you wait."
ensure_operator servicemeshoperator3 openshift-operators global
wait_until "the Istio CRD" crd_established istios.sailoperator.io
wait_until "the IstioCNI CRD" crd_established istiocnis.sailoperator.io
ensure_namespace istio-system
ensure_namespace istio-cni
oc apply -f - >/dev/null <<YAML
apiVersion: sailoperator.io/v1
kind: Istio
metadata:
  name: default
spec:
  namespace: istio-system
  updateStrategy:
    type: InPlace
---
apiVersion: sailoperator.io/v1
kind: IstioCNI
metadata:
  name: default
spec:
  namespace: istio-cni
YAML
oc wait --for=condition=Ready istio/default --timeout=300s
oc wait --for=condition=Ready istiocni/default --timeout=300s
network=$(oc get network.config.openshift.io cluster -o jsonpath='{.status.networkType}')
[ "$network" = OVNKubernetes ] || die "the network policy tests need OVNKubernetes; this cluster uses $network"
say "mesh is Ready; network plugin is $network"
