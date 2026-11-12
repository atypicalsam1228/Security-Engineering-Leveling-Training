#!/usr/bin/env bash
# Kyverno 1.19.2 (Helm chart kyverno/kyverno 3.9.2) in namespace kyverno.
# Modules rely on: ClusterPolicy (kyverno.io/v1) CRD, service account kyverno-background-controller, PolicyReports in
# API group wgpolicyk8s.io, rule-level validate.failureAction, autogen, `oc adm top pods -n kyverno` (ARC-3 sums memory).
# Do not move to 1.20 or later: it removes ClusterPolicy (LAB-CONTRACT.md).
set -euo pipefail
. "$(dirname "$0")/lib.sh"

NS=kyverno
RELEASE=kyverno
# Verified 2026-11-02: https://kyverno.github.io/kyverno/index.yaml lists version 3.9.2, appVersion v1.19.2.
CHART_REPO=https://kyverno.github.io/kyverno/
CHART_VERSION=3.9.2
APP_VERSION=v1.19.2

installed_chart() { helm list -n "$NS" --filter "^${RELEASE}\$" -o json 2>/dev/null | jq -r '.[0] | select(.status == "deployed") | .chart // empty'; }

values="$(mktemp)"
trap 'rm -f "$values"' EXIT
# Small footprint: one replica per controller (chart default), memory limits raised a little for the background and
# reports controllers (default 128Mi) so a busy lab does not OOM-kill them.
# runAsUser/runAsGroup are nulled: the chart hard-codes 65534, which the OpenShift restricted-v2 SCC may refuse;
# with null OpenShift assigns a UID from the namespace range. Kyverno doc "Platform Notes": set the required
# securityContext fields to null on OpenShift (https://kyverno.io/docs/installation/platform-notes/).
# The other hardening fields (runAsNonRoot, drop ALL, seccomp RuntimeDefault, read-only root) stay.
cat >"$values" <<'EOF'
crds:
  migration:
    securityContext:
      runAsUser: null
      runAsGroup: null
webhooksCleanup:
  securityContext:
    runAsUser: null
    runAsGroup: null
test:
  securityContext:
    runAsUser: null
    runAsGroup: null
admissionController:
  initContainer:
    securityContext:
      runAsUser: null
      runAsGroup: null
  container:
    securityContext:
      runAsUser: null
      runAsGroup: null
    resources:
      requests: {cpu: 100m, memory: 128Mi}
      limits: {memory: 384Mi}
backgroundController:
  securityContext:
    runAsUser: null
    runAsGroup: null
  resources:
    requests: {cpu: 50m, memory: 96Mi}
    limits: {memory: 256Mi}
cleanupController:
  securityContext:
    runAsUser: null
    runAsGroup: null
  resources:
    requests: {cpu: 20m, memory: 64Mi}
    limits: {memory: 128Mi}
reportsController:
  securityContext:
    runAsUser: null
    runAsGroup: null
  resources:
    requests: {cpu: 50m, memory: 96Mi}
    limits: {memory: 256Mi}
EOF

current="$(installed_chart)"
if [ "$current" = "kyverno-${CHART_VERSION}" ]; then
  say "Kyverno chart $CHART_VERSION already deployed"
else
  say "installing Kyverno $APP_VERSION (chart $CHART_VERSION)"
  helm_apply "$RELEASE" kyverno "$NS" "$CHART_VERSION" --repo "$CHART_REPO" -f "$values" >/dev/null ||
    die "helm could not install Kyverno chart $CHART_VERSION (needs internet access to $CHART_REPO)"
fi

for c in admission-controller background-controller cleanup-controller reports-controller; do
  wait_rollout "$NS" "deployment/kyverno-$c" 600
done

crd_ok() { [ "$(oc get crd "$1" -o jsonpath='{.status.conditions[?(@.type=="Established")].status}' 2>/dev/null)" = True ]; }
for crd in clusterpolicies.kyverno.io policies.kyverno.io policyreports.wgpolicyk8s.io clusterpolicyreports.wgpolicyk8s.io; do
  wait_until "CRD $crd" 120 crd_ok "$crd"
done
oc get serviceaccount kyverno-background-controller -n "$NS" >/dev/null ||
  die "service account kyverno-background-controller is missing; CPS-5 and AID-5 need that name"

image="$(oc get deployment kyverno-admission-controller -n "$NS" -o jsonpath='{.spec.template.spec.containers[0].image}')"
case "$image" in *":$APP_VERSION"*) say "Kyverno image $image" ;; *) die "admission controller runs $image, expected tag $APP_VERSION" ;; esac
