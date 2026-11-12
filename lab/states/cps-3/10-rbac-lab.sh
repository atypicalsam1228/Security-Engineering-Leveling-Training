#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: namespace rbac-lab with
#  - service account report-sa and a deliberately broad role binding report-sa-edit (edit role),
#  - Deployment report-app (unhardened, runs as report-sa) that the learner hardens,
#  - Deployment backend (python http.server on 8080) with Service backend, used for the network test.
# Existing objects are left alone so a rerun never overwrites the learner's work.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
oc apply -f - >/dev/null <<'YAML'
apiVersion: v1
kind: Namespace
metadata:
  name: rbac-lab
YAML
oc get serviceaccount report-sa -n rbac-lab >/dev/null 2>&1 || oc create serviceaccount report-sa -n rbac-lab
oc get rolebinding report-sa-edit -n rbac-lab >/dev/null 2>&1 ||
  oc create rolebinding report-sa-edit --clusterrole=edit --serviceaccount=rbac-lab:report-sa -n rbac-lab --dry-run=client -o yaml | oc apply -f - >/dev/null
if ! oc get deployment report-app -n rbac-lab >/dev/null 2>&1; then
  oc apply -n rbac-lab -f - >/dev/null <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: report-app
  labels:
    app: report-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: report-app
  template:
    metadata:
      labels:
        app: report-app
    spec:
      serviceAccountName: report-sa
      containers:
        - name: report-app
          image: registry.access.redhat.com/ubi9/ubi-minimal:9.5
          command: ["sleep", "infinity"]
YAML
fi
if ! oc get deployment backend -n rbac-lab >/dev/null 2>&1; then
  oc apply -n rbac-lab -f - >/dev/null <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  labels:
    app: backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: registry.access.redhat.com/ubi9/python-311:1
          command: ["python3", "-m", "http.server", "8080", "--directory", "/tmp"]
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  selector:
    app: backend
  ports:
    - port: 8080
      targetPort: 8080
YAML
fi
oc rollout status deployment/report-app -n rbac-lab --timeout=240s
oc rollout status deployment/backend -n rbac-lab --timeout=300s
# The network test uses bash /dev/tcp and timeout inside report-app, so check they exist (no curl needed).
oc exec -n rbac-lab deploy/report-app -- bash -c 'command -v timeout >/dev/null' || die "report-app image has no timeout command"
