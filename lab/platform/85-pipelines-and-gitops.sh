#!/usr/bin/env bash
# OpenShift Pipelines (Tekton) and OpenShift GitOps (Argo CD) operators.
# Pipelines goes in first so ENG-0's health check finds tekton-pipelines pods in openshift-pipelines before any module runs.
# The module start states install the Pipelines operator the same way (package openshift-pipelines-operator-rh in
# openshift-operators, all namespaces) and skip it when a Subscription for that package already exists, so the two agree.
# Saves ARGOCD_URL.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

MARKETPLACE_NAMESPACE=openshift-marketplace
CATALOG_SOURCE=redhat-operators
# Channels. Red Hat documents "latest" for both operators (Pipelines: docs.redhat.com OpenShift Pipelines 1.20 "Installing";
# GitOps: docs.redhat.com OpenShift GitOps 1.17 "Installing GitOps", Subscription channel: latest, source redhat-operators).
# The script checks that the cluster catalog really offers the channel before it subscribes.
PIPELINES_PACKAGE=openshift-pipelines-operator-rh
PIPELINES_NAMESPACE=openshift-operators
PIPELINES_CHANNEL=latest
GITOPS_PACKAGE=openshift-gitops-operator
GITOPS_NAMESPACE=openshift-gitops-operator
GITOPS_CHANNEL=latest

# --- copied from lab/states/_common/lib.sh (not sourced), with an explicit channel -----------------------------------
subscription_for_package() {
  oc get subscription -n "$2" -o json 2>/dev/null | jq -r --arg p "$1" '[.items[] | select(.spec.name == $p) | .metadata.name] | first // empty'
}

ensure_operator_group() { # namespace mode(own|all|global)
  local ns=$1 mode=$2
  [ "$mode" = global ] && return 0
  [ -z "$(oc get operatorgroup -n "$ns" -o name 2>/dev/null)" ] || return 0
  if [ "$mode" = own ]; then
    oc apply -f - >/dev/null <<EOF
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: ${ns}
  namespace: ${ns}
spec:
  targetNamespaces:
    - ${ns}
EOF
  else
    oc apply -f - >/dev/null <<EOF
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: ${ns}
  namespace: ${ns}
spec:
  upgradeStrategy: Default
EOF
  fi
}

csv_succeeded() {
  local csv
  csv=$(oc get subscription "$1" -n "$2" -o jsonpath='{.status.installedCSV}' 2>/dev/null) || return 1
  [ -n "$csv" ] || return 1
  [ "$(oc get csv "$csv" -n "$2" -o jsonpath='{.status.phase}' 2>/dev/null)" = Succeeded ]
}

# ensure_operator PACKAGE NAMESPACE MODE CHANNEL
ensure_operator() {
  local pkg=$1 ns=$2 mode=$3 channel=$4 sub
  ensure_namespace "$ns"
  ensure_operator_group "$ns" "$mode"
  sub=$(subscription_for_package "$pkg" "$ns")
  if [ -z "$sub" ]; then
    if [ "$channel" = default ]; then
      channel=$(oc get packagemanifest "$pkg" -n "$MARKETPLACE_NAMESPACE" -o jsonpath='{.status.defaultChannel}' 2>/dev/null) || true
      [ -n "$channel" ] || die "package $pkg not found in the $MARKETPLACE_NAMESPACE catalog (is the cluster connected to the Red Hat catalog?)"
    else
      oc get packagemanifest "$pkg" -n "$MARKETPLACE_NAMESPACE" -o json 2>/dev/null |
        jq -e --arg c "$channel" '.status.channels | map(.name) | index($c)' >/dev/null ||
        die "package $pkg has no channel '$channel' in the $MARKETPLACE_NAMESPACE catalog (is the cluster connected to the Red Hat catalog?)"
    fi
    oc apply -f - >/dev/null <<EOF
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: ${pkg}
  namespace: ${ns}
spec:
  name: ${pkg}
  channel: ${channel}
  source: ${CATALOG_SOURCE}
  sourceNamespace: ${MARKETPLACE_NAMESPACE}
  installPlanApproval: Automatic
EOF
    sub=$pkg
  fi
  wait_until "operator $pkg to finish installing" 900 csv_succeeded "$sub" "$ns"
}
# ---------------------------------------------------------------------------------------------------------------------

# --- OpenShift Pipelines ---------------------------------------------------------------------------------------------
ensure_operator "$PIPELINES_PACKAGE" "$PIPELINES_NAMESPACE" global "$PIPELINES_CHANNEL"

tekton_ready() { [ "$(oc get tektonconfig config -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)" = True ]; }
wait_until "TektonConfig config Ready" 900 tekton_ready
tekton_controller() {
  oc get pods -n openshift-pipelines -o json | jq -e '[.items[] | select(.metadata.name | test("tekton-pipelines")) | select(.status.phase == "Running")] | length > 0'
}
wait_until "tekton-pipelines pods Running in openshift-pipelines" 300 tekton_controller
# The start states of the delivery modules wait for this Task before they build pipelines.
wait_until "Task git-clone in openshift-pipelines" 600 oc get task git-clone -n openshift-pipelines

# --- OpenShift GitOps ------------------------------------------------------------------------------------------------
ensure_namespace "$GITOPS_NAMESPACE"
oc label namespace "$GITOPS_NAMESPACE" --overwrite openshift.io/cluster-monitoring=true >/dev/null
ensure_operator "$GITOPS_PACKAGE" "$GITOPS_NAMESPACE" all "$GITOPS_CHANNEL"

# The operator creates the default Argo CD instance "openshift-gitops" in namespace openshift-gitops.
argocd_available() { [ "$(oc get argocd openshift-gitops -n openshift-gitops -o jsonpath='{.status.phase}' 2>/dev/null)" = Available ]; }
wait_until "Argo CD instance openshift-gitops Available" 900 argocd_available
wait_until "Route openshift-gitops-server" 300 oc get route openshift-gitops-server -n openshift-gitops
wait_rollout openshift-gitops deployment/openshift-gitops-server 600

lab_var_set ARGOCD_URL "https://$(route_host openshift-gitops openshift-gitops-server)"
say "Argo CD at $(lab_var ARGOCD_URL); the admin password is in secret openshift-gitops-cluster (key admin.password)"

# --- OpenShift Logging operator and the siem-forwarder ---------------------------------------------------------------
# Nothing else installs the Logging operator, and ENG-0's health check expects a pod named siem-forwarder or collector in
# openshift-logging before any module starts, so the platform provides both. Same objects as ensure_siem_forwarder in
# lab/states/_common/lib.sh (an existing forwarder is left alone, so the start states and this script agree).
# Channel: the catalog default (the stable-6.x line differs per OpenShift release and cannot be verified offline).
LOGGING_PACKAGE=cluster-logging
LOGGING_NAMESPACE=openshift-logging
FORWARDER_NAME=siem-forwarder

oc create namespace "$LOGGING_NAMESPACE" --dry-run=client -o yaml | oc apply -f - >/dev/null
oc label namespace "$LOGGING_NAMESPACE" --overwrite openshift.io/cluster-monitoring=true >/dev/null
ensure_operator "$LOGGING_PACKAGE" "$LOGGING_NAMESPACE" own default
wait_until "CRD clusterlogforwarders.observability.openshift.io" 300 oc get crd clusterlogforwarders.observability.openshift.io

require_var LOKI_URL LOKI_USER LOKI_PASSWORD LOKI_CA_FILE
oc create serviceaccount collector -n "$LOGGING_NAMESPACE" --dry-run=client -o yaml | oc apply -f - >/dev/null
for role in collect-application-logs collect-infrastructure-logs collect-audit-logs; do
  oc create clusterrolebinding "${role}-collector" --clusterrole="$role" \
    --serviceaccount="$LOGGING_NAMESPACE:collector" --dry-run=client -o yaml | oc apply -f - >/dev/null
done
oc create secret generic loki-credentials -n "$LOGGING_NAMESPACE" \
  --from-literal=username="$LOKI_USER" --from-literal=password="$LOKI_PASSWORD" --dry-run=client -o yaml | oc apply -f - >/dev/null
oc create secret generic loki-ca -n "$LOGGING_NAMESPACE" --from-file=ca.crt="$LOKI_CA_FILE" --dry-run=client -o yaml | oc apply -f - >/dev/null
if oc get clusterlogforwarder "$FORWARDER_NAME" -n "$LOGGING_NAMESPACE" >/dev/null 2>&1; then
  say "forwarder $FORWARDER_NAME already exists"
else
  oc apply -f - >/dev/null <<YAML
apiVersion: observability.openshift.io/v1
kind: ClusterLogForwarder
metadata:
  name: ${FORWARDER_NAME}
  namespace: ${LOGGING_NAMESPACE}
spec:
  serviceAccount:
    name: collector
  outputs:
    - name: siem-loki
      type: loki
      loki:
        url: "${LOKI_URL}"
        authentication:
          username:
            secretName: loki-credentials
            key: username
          password:
            secretName: loki-credentials
            key: password
      tls:
        ca:
          secretName: loki-ca
          key: ca.crt
  pipelines:
    - name: security-logs
      inputRefs:
        - audit
        - infrastructure
        - application
      outputRefs:
        - siem-loki
YAML
fi
collector_running() {
  oc get pods -n "$LOGGING_NAMESPACE" -o json | jq -e '[.items[] | select(.metadata.name | test("siem-forwarder|collector")) | select(.status.phase == "Running")] | length > 0'
}
wait_until "collector pod Running in $LOGGING_NAMESPACE" 600 collector_running
