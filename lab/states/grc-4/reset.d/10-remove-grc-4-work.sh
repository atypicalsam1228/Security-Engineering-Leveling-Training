#!/usr/bin/env bash
#  Removes what GRC-4 creates: the learner's tasks and pipeline, their runs,
# the signing secret and the evidence volume (recreated by 30-evidence-access.yaml).
set -euo pipefail
. "$(dirname "$0")/../../_common/lib.sh"
oc delete pipelinerun -n build -l tekton.dev/pipeline=evidence-bundle --ignore-not-found
oc delete taskrun -n build -l tekton.dev/task=evidence-policy --ignore-not-found
oc delete taskrun -n build -l tekton.dev/task=evidence-scan --ignore-not-found
oc delete taskrun -n build -l tekton.dev/task=evidence-bundle --ignore-not-found
oc delete pipeline evidence-bundle -n build --ignore-not-found
oc delete task evidence-scan evidence-policy evidence-bundle -n build --ignore-not-found
oc delete secret evidence-signing -n build --ignore-not-found
oc delete pvc evidence-work -n build --ignore-not-found
oc delete deployment candidate-app -n demo --ignore-not-found
oc delete configmap admit-script -n build --ignore-not-found
