#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. The Tekton Triggers objects that start the review gate on a Gitea push:
# a TriggerTemplate that makes a PipelineRun and an EventListener (service el-gate-listener, port 8080).
# The gate runs in a public Python image set in 70-review-gate-pipeline.yaml. Field names follow triggers.tekton.dev/v1beta1
# and are to be confirmed live (oc explain eventlistener.spec.triggers).
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
wait_until "Tekton Triggers CRD" crd_established eventlisteners.triggers.tekton.dev
oc apply -f - >/dev/null <<'YAML'
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: gate-template
  namespace: build
spec:
  params:
    - name: sha
  resourcetemplates:
    - apiVersion: tekton.dev/v1
      kind: PipelineRun
      metadata:
        generateName: review-gate-
      spec:
        pipelineRef:
          name: review-gate
        taskRunTemplate:
          serviceAccountName: gate-runner
        params:
          - name: sha
            value: $(tt.params.sha)
        workspaces:
          - name: gate
            configMap:
              name: review-gate
---
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: gate-listener
  namespace: build
spec:
  serviceAccountName: gate-trigger
  triggers:
    - name: on-push
      bindings:
        - name: sha
          value: $(body.after)
      template:
        ref: gate-template
YAML
