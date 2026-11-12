#!/usr/bin/env bash
# Removes what the learner created in VM-5 (the start state recreates the rest). Only VM-5's own runs are deleted: build is shared with other modules.
set -uo pipefail
oc delete pipelinerun -l tekton.dev/pipeline=risk-gated-release -n build --ignore-not-found --wait=false
oc delete pipeline risk-gated-release -n build --ignore-not-found
oc delete task risk-scan risk-gate -n build --ignore-not-found
oc delete configmap risk-gate-config -n build --ignore-not-found
oc delete pod -l tekton.dev/pipeline=risk-gated-release -n build --ignore-not-found --wait=false
oc delete pvc risk-pvc risk-source-pvc risk-ledger-pvc -n build --ignore-not-found --wait=false
