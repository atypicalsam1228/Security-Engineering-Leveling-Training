#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: namespace secure-lab with an insecure starting workload.
#  - Deployment and Service sample-api (python http.server on 8080) that uses the default service account,
#    keeps a plain-text DB_PASSWORD value in its pod spec, has no security context and no network policy.
#  - Deployments api-client (label role=api-client) and stranger (label role=stranger): two callers for the network test.
# Existing objects are left alone so a rerun never overwrites the learner's work. The Deployments are made with oc create, not
# oc apply, on purpose: apply stores the whole first spec (with the plain-text password) in a last-applied-configuration
# annotation that Test 1 in the module would find after the password is removed.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
oc apply -f - >/dev/null <<'YAML'
apiVersion: v1
kind: Namespace
metadata:
  name: secure-lab
YAML
if ! oc get deployment sample-api -n secure-lab >/dev/null 2>&1; then
  oc create -n secure-lab -f - >/dev/null <<'YAML' || { echo 'oc create failed for sample-api' >&2; exit 1; }
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-api
  labels:
    app: sample-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sample-api
  template:
    metadata:
      labels:
        app: sample-api
    spec:
      containers:
        - name: sample-api
          image: registry.access.redhat.com/ubi9/python-311:1
          command: ["python3", "-m", "http.server", "8080", "--directory", "/tmp"]
          ports:
            - containerPort: 8080
          env:
            - name: DB_PASSWORD
              value: lab-only-plain-text-value
---
apiVersion: v1
kind: Service
metadata:
  name: sample-api
spec:
  selector:
    app: sample-api
  ports:
    - port: 8080
      targetPort: 8080
YAML
fi
for who in api-client stranger; do
  if ! oc get deployment "$who" -n secure-lab >/dev/null 2>&1; then
    oc create -n secure-lab -f - >/dev/null <<YAML || { echo "oc create failed for $who" >&2; exit 1; }
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $who
  labels:
    app: $who
spec:
  replicas: 1
  selector:
    matchLabels:
      app: $who
  template:
    metadata:
      labels:
        app: $who
        role: $who
    spec:
      containers:
        - name: $who
          image: registry.access.redhat.com/ubi9/ubi-minimal:9.5
          command: ["sleep", "infinity"]
YAML
  fi
done
for d in sample-api api-client stranger; do
  oc rollout status deployment/$d -n secure-lab --timeout=300s
done
