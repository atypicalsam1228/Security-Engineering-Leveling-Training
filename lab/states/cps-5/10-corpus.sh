#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Builds the test corpus the learner measures against: ConfigMap workload-corpus in
# namespace guardrails-lab with twelve Deployments (replicas 0, so nothing runs and nothing is pulled).
#  ok-01..ok-08  ordinary workloads a developer might submit: four omit most hardening, two set a little, two are fully hardened.
#  bad-01..bad-04  unsafe workloads: privileged, hostPath volume, host network, latest tag.
# Each Deployment is named like its file (without .yaml), because the learner's score script reads it back by that name.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
IMG=registry.access.redhat.com/ubi9/ubi-minimal:9.5
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT

# mk NAME IMAGE POD_LINES CONTAINER_LINES [EXTRA_CONTAINER_LINES]
mk() {
  cat >"$dir/$1.yaml" <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $1
spec:
  replicas: 0
  selector:
    matchLabels:
      app: $1
  template:
    metadata:
      labels:
        app: $1
    spec:
$3
      containers:
        - name: app
          image: $2
          command: ["sleep", "infinity"]
$4
$5
YAML
}

LIMITS='          resources:
            requests:
              memory: 64Mi
            limits:
              memory: 128Mi'
HARD_CTR='          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]'
NONROOT='      securityContext:
        runAsNonRoot: true'
SIDECAR='        - name: sidecar
          image: registry.access.redhat.com/ubi9/ubi-minimal:9.5
          command: ["sleep", "infinity"]'

mk ok-01-plain "$IMG" "" "" ""
mk ok-02-limits "$IMG" "" "$LIMITS" ""
mk ok-03-nonroot "$IMG" "$NONROOT" "" ""
mk ok-04-hardened "$IMG" "$NONROOT" "$HARD_CTR
$LIMITS" ""
mk ok-05-two-containers "$IMG" "" "" "$SIDECAR"
mk ok-06-env "$IMG" "" "          env:
            - name: MODE
              value: lab" ""
mk ok-07-port "$IMG" "" "          ports:
            - containerPort: 8080" ""
mk ok-08-hardened-port "$IMG" "$NONROOT" "$HARD_CTR
$LIMITS
          ports:
            - containerPort: 8080" ""
mk bad-01-privileged "$IMG" "" "          securityContext:
            privileged: true" ""
mk bad-02-hostpath "$IMG" "      volumes:
        - name: host
          hostPath:
            path: /var" "" ""
mk bad-03-hostnetwork "$IMG" "      hostNetwork: true" "" ""
mk bad-04-latest "registry.access.redhat.com/ubi9/ubi-minimal:latest" "" "" ""

# Every file must be valid YAML for the API server; check them before storing.
for f in "$dir"/*.yaml; do
  oc create --dry-run=client -f "$f" -o name >/dev/null || die "generated file $f is not valid"
done
ensure_namespace guardrails-lab
oc create configmap workload-corpus -n guardrails-lab --from-file="$dir" --dry-run=client -o yaml | oc apply -f - >/dev/null
say "ConfigMap workload-corpus written in guardrails-lab (12 files)"
