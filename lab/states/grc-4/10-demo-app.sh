#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Namespaces demo and build exist, and Kyverno (lab-provided) is running.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_demo_app
ensure_namespace build
oc get crd clusterpolicies.kyverno.io >/dev/null || die "Kyverno ClusterPolicy CRD is missing (the lab build installs Kyverno)"
ready=$(oc get pods -n kyverno -o json | jq '[.items[] | select(.status.phase == "Running")] | length')
[ "$ready" -ge 1 ] || die "no Kyverno pod is Running in namespace kyverno"
say "Kyverno is running ($ready pods)"

# The workload whose image the pipeline scans and signs. It runs registry.k8s.io/pause, a single static program with no
# operating system packages, so Trivy finds nothing to report and the good run in Step 4 can pass. The shared demo-app
# (ubi9/ubi-minimal) has dozens of HIGH and CRITICAL findings and stays as it is for the other modules.
oc apply -f - >/dev/null <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: evidence-app
  namespace: demo
  labels:
    app: evidence-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: evidence-app
  template:
    metadata:
      labels:
        app: evidence-app
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: evidence-app
          image: registry.k8s.io/pause:3.10
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              memory: 32Mi
YAML
oc rollout status deployment/evidence-app -n demo --timeout=240s
