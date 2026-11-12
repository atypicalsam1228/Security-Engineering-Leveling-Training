#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Builds the supplied files the learner extracts with oc extract:
# ConfigMap baseline-files in harden-lab. The scan file is built from the rules that really exist on this
# cluster (a candidate that is missing is skipped), so the tailored profile never names a rule that is not there.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
CANDIDATES="ocp4-configure-network-policies-namespaces ocp4-scc-limit-privileged-containers ocp4-scc-limit-root-containers ocp4-scc-drop-container-capabilities ocp4-rbac-wildcard-use ocp4-rbac-limit-cluster-admin"
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT

cat >"$dir/namespace.yaml" <<'YAML'
apiVersion: v1
kind: Namespace
metadata:
  name: harden-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
YAML
cat >"$dir/workload-patch.yaml" <<'YAML'
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: sample-web
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 10m
              memory: 32Mi
            limits:
              memory: 128Mi
YAML
cat >"$dir/quota.yaml" <<'YAML'
apiVersion: v1
kind: ResourceQuota
metadata:
  name: harden-quota
  namespace: harden-lab
spec:
  hard:
    pods: "5"
    requests.memory: 256Mi
    limits.memory: 512Mi
YAML
cat >"$dir/default-deny.yaml" <<'YAML'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: harden-lab
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
YAML
cat >"$dir/bad-pod.yaml" <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
  namespace: harden-lab
spec:
  hostNetwork: true
  containers:
    - name: app
      image: registry.access.redhat.com/ubi9/ubi-minimal:9.5
      command: ["sleep", "infinity"]
      securityContext:
        privileged: true
YAML

enable=""
for rule in $CANDIDATES; do
  if oc get rules.compliance "$rule" -n openshift-compliance >/dev/null 2>&1; then
    enable="$enable
    - name: $rule
      rationale: Workload hardening check for this module"
  else
    say "rule $rule not found on this cluster; skipped"
  fi
done
[ "$(printf '%s\n' "$enable" | grep -c 'name:')" -ge 3 ] || die "fewer than three candidate rules exist; check oc get rules.compliance"
cat >"$dir/scan.yaml" <<YAML
apiVersion: compliance.openshift.io/v1alpha1
kind: TailoredProfile
metadata:
  name: harden-baseline
  namespace: openshift-compliance
  annotations:
    compliance.openshift.io/product-type: Platform
spec:
  title: Workload hardening checks
  description: A short list of platform checks that relate to how workloads are secured.
  enableRules:$enable
---
apiVersion: compliance.openshift.io/v1alpha1
kind: ScanSettingBinding
metadata:
  name: harden-scan
  namespace: openshift-compliance
profiles:
  - name: harden-baseline
    kind: TailoredProfile
    apiGroup: compliance.openshift.io/v1alpha1
settingsRef:
  name: default
  kind: ScanSetting
  apiGroup: compliance.openshift.io/v1alpha1
YAML
oc create configmap baseline-files -n harden-lab --from-file="$dir" --dry-run=client -o yaml | oc apply -f - >/dev/null
say "ConfigMap baseline-files written in harden-lab"
