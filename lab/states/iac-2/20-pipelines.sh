#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. OpenShift Pipelines (package openshift-pipelines-operator-rh), namespace build, and a
# check that the Tekton CRDs and the pipeline service account exist.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_operator openshift-pipelines-operator-rh openshift-operators global
ensure_namespace build
wait_until "Tekton Pipeline CRD" crd_established pipelines.tekton.dev
wait_until "service account pipeline in build" oc get serviceaccount pipeline -n build
