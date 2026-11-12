#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: namespace harden-lab (no pod security labels) and an
# unhardened Deployment sample-web (no security context, no resource limits). An existing sample-web is left alone.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
oc apply -f - >/dev/null <<'YAML'
apiVersion: v1
kind: Namespace
metadata:
  name: harden-lab
YAML
if oc get deployment sample-web -n harden-lab >/dev/null 2>&1; then
  say "sample-web already exists in harden-lab; leaving it as it is"
else
  oc apply -n harden-lab -f - >/dev/null <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-web
  labels:
    app: sample-web
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sample-web
  template:
    metadata:
      labels:
        app: sample-web
    spec:
      containers:
        - name: sample-web
          image: registry.access.redhat.com/ubi9/ubi-minimal:9.5
          command: ["sleep", "infinity"]
YAML
fi
oc rollout status deployment/sample-web -n harden-lab --timeout=240s
