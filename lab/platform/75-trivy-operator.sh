#!/usr/bin/env bash
# Trivy Operator in namespace security-tools: writes VulnerabilityReports, ConfigAuditReports, ExposedSecretReports and
# RbacAssessmentReports (aquasecurity.github.io CRDs) for workloads. Pods are named trivy-operator-* (ENG-0 health check
# looks for "trivy" in security-tools). Needs internet from the cluster: scan jobs pull the Trivy database and checks
# bundle from mirror.gcr.io (chart defaults).
set -euo pipefail
. "$(dirname "$0")/lib.sh"

NS=security-tools
RELEASE=trivy-operator
# Verified 2026-11-02: https://aquasecurity.github.io/helm-charts/index.yaml lists trivy-operator 0.38.1 (appVersion 0.36.1,
# newest of the chart); chart values.yaml pins scanner image aquasec/trivy:0.76.1, which equals the Trivy 0.76.1 the
# lab shell and the modules use. Images exist: mirror.gcr.io/v2/aquasec/trivy-operator/manifests/0.36.1,
# .../aquasec/trivy/manifests/0.76.1, .../aquasec/trivy-checks/manifests/1 (HTTP 200 on 2026-11-02).
CHART_REPO=https://aquasecurity.github.io/helm-charts/
CHART_VERSION=0.38.1
OPERATOR_APP_VERSION=0.36.1
SCANNER_TAG=0.76.1

installed_chart() { helm list -n "$NS" --filter "^${RELEASE}\$" -o json 2>/dev/null | jq -r '.[0] | select(.status == "deployed") | .chart // empty'; }

ensure_namespace "$NS"
# security-tools also runs Falco, which needs a privileged pod (script 80). Label the namespace so Pod Security admission
# allows it, and stop the OpenShift label syncer from resetting the labels.
oc label namespace "$NS" --overwrite \
  pod-security.kubernetes.io/enforce=privileged pod-security.kubernetes.io/audit=privileged \
  pod-security.kubernetes.io/warn=privileged security.openshift.io/scc.podSecurityLabelSync=false >/dev/null

values="$(mktemp)"
trap 'rm -f "$values"' EXIT
# No node collector: the node-collector job needs hostPID and host paths (extra SCC) and only feeds
# InfraAssessmentReports and the CIS cluster compliance reports, which no module reads. Scan jobs run in this namespace
# under restricted-v2 (chart default security context: no privilege escalation, drop ALL, read-only root).
# Platform namespaces are excluded so the single node is not flooded with scans of the OpenShift components.
# Two scan jobs at a time: each may use up to 1G (the chart default of 500M got scan jobs OOMKilled in the live run).
# Operator memory limit is 1536Mi: the live run showed OOMKilled (exit 137) restarts at 512Mi and a working set of about 990Mi against a 1Gi limit.
cat >"$values" <<'EOF'
excludeNamespaces: "openshift-*,kube-*,openshift"
operator:
  scanJobsConcurrentLimit: 2
  infraAssessmentScannerEnabled: false
  clusterComplianceEnabled: false
resources:
  requests: {cpu: 50m, memory: 512Mi}
  limits: {cpu: 500m, memory: 1536Mi}
trivy:
  resources:
    requests: {cpu: 100m, memory: 256M}
    limits: {cpu: 500m, memory: 1G}
EOF

current="$(installed_chart)"
# "helm get values" fails when the release does not exist yet (first install); with pipefail that would end the script silently.
current_limit="$(helm get values "$RELEASE" -n "$NS" -o json 2>/dev/null | jq -r '.resources.limits.memory // empty' || true)"
if [ "$current" = "trivy-operator-${CHART_VERSION}" ] && [ "$current_limit" = "1536Mi" ]; then
  say "Trivy Operator chart $CHART_VERSION already deployed"
else
  say "installing Trivy Operator $OPERATOR_APP_VERSION (chart $CHART_VERSION, scanner $SCANNER_TAG)"
  helm_apply "$RELEASE" trivy-operator "$NS" "$CHART_VERSION" --repo "$CHART_REPO" -f "$values" >/dev/null ||
    die "helm could not install the Trivy Operator chart $CHART_VERSION (needs internet access to $CHART_REPO)"
fi
wait_rollout "$NS" deployment/trivy-operator 600

crd_ok() { [ "$(oc get crd "$1" -o jsonpath='{.status.conditions[?(@.type=="Established")].status}' 2>/dev/null)" = True ]; }
for crd in vulnerabilityreports configauditreports exposedsecretreports rbacassessmentreports clusterrbacassessmentreports; do
  wait_until "CRD $crd.aquasecurity.github.io" 120 crd_ok "$crd.aquasecurity.github.io"
done

# Reports are produced asynchronously. A slow first scan is not an install failure, so only warn.
report_count() { oc get "$1" -A -o name 2>/dev/null | wc -l | tr -d ' '; }
waited=0
while [ "$waited" -lt 600 ]; do
  if [ "$(report_count configauditreports.aquasecurity.github.io)" -gt 0 ] &&
    [ "$(report_count vulnerabilityreports.aquasecurity.github.io)" -gt 0 ]; then
    break
  fi
  sleep 10
  waited=$((waited + 10))
done
say "reports so far: $(report_count configauditreports.aquasecurity.github.io) ConfigAuditReports, $(report_count vulnerabilityreports.aquasecurity.github.io) VulnerabilityReports"
if [ "$(report_count vulnerabilityreports.aquasecurity.github.io)" -eq 0 ]; then
  say "WARNING: no VulnerabilityReport yet. The first scan downloads the Trivy database; check 'oc get jobs -n $NS' and the cluster's internet access."
fi
