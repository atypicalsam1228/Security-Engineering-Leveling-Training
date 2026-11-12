#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: OpenShift Pipelines, namespace build, the Gitea clone secret and the
# review gate (ConfigMap ai-review-gate holds review_gate.py, so the gate lives outside the repository it checks).
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN
ensure_operator openshift-pipelines-operator-rh openshift-operators global
ensure_namespace build
wait_until "service account pipeline in build" oc get serviceaccount pipeline -n build
wait_until "task git-clone in openshift-pipelines" oc get task git-clone -n openshift-pipelines

oc create secret generic gitea-clone -n build --type=kubernetes.io/basic-auth \
  --from-literal=username="$GITEA_USER" --from-literal=password="$GITEA_TOKEN" --dry-run=client -o yaml | oc apply -f - >/dev/null
oc annotate secret gitea-clone -n build tekton.dev/git-0="$GITEA_URL" --overwrite >/dev/null
oc secrets link pipeline gitea-clone -n build
# The lab's own certificate authority, so git-clone verifies the Gitea certificate instead of skipping the check.
# The key must be named ca-bundle.crt, the file name git-clone looks for in its ssl-ca-directory workspace.
ca_bundle=/workspace/.lab/ca-bundle.crt
[ -s "$ca_bundle" ] || die "lab CA bundle not found at $ca_bundle"
oc create configmap lab-ca -n build --from-file=ca-bundle.crt="$ca_bundle" --dry-run=client -o yaml | oc apply -f - >/dev/null
# A volume claim for the clone: the clone task and the gate task run in separate pods, so an emptyDir would not be shared.
oc apply -f - >/dev/null <<'YAML'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ai-review-pvc
  namespace: build
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
YAML
oc create configmap ai-review-gate -n build --from-file=review_gate.py="$(dirname "$0")/review_gate.py" --dry-run=client -o yaml | oc apply -f - >/dev/null

# Tekton parameter reference, passed through to the Pipeline unexpanded.
TEKTON_GATE_IMAGE='$(params.gate-image)'
oc apply -f - >/dev/null <<YAML
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: ai-script-review
  namespace: build
spec:
  params:
    - name: git-url
    - name: git-revision
      default: main
    - name: gate-image
      default: registry.access.redhat.com/ubi9/python-312:1
  workspaces:
    - name: source
    - name: ssl-ca
      optional: true
  tasks:
    - name: clone
      taskRef:
        resolver: cluster
        params:
          - name: kind
            value: task
          - name: name
            value: git-clone
          - name: namespace
            value: openshift-pipelines
      params:
        - name: URL
          value: \$(params.git-url)
        - name: REVISION
          value: \$(params.git-revision)
      workspaces:
        - name: output
          workspace: source
        - name: ssl-ca-directory
          workspace: ssl-ca
    - name: review-gate
      runAfter: ["clone"]
      workspaces:
        - name: source
          workspace: source
      taskSpec:
        workspaces:
          - name: source
        volumes:
          - name: gate
            configMap:
              name: ai-review-gate
        steps:
          - name: run-gate
            image: $TEKTON_GATE_IMAGE
            workingDir: \$(workspaces.source.path)
            volumeMounts:
              - name: gate
                mountPath: /gate
            script: |
              #!/bin/sh
              python3 /gate/review_gate.py .
YAML
say "pipeline ai-script-review and gate ConfigMap are in place"
