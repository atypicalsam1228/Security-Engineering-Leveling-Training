#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes everything IAC-2 creates: namespace iac-lab (made by the learner's Terraform),
# the Gitea repository iac-baseline (branches, pull requests and branch protection go with it), the Tekton runs, tasks and
# pipeline, the config map and secret, and the local Terraform folder /workspace/iac-2 (state, plans, clone).
# The start state recreates what the module needs.
set -uo pipefail
. "$(dirname "$0")/../../_common/lib.sh"
oc delete namespace iac-lab --ignore-not-found --wait=true
if [ -d /workspace ]; then
  rm -rf /workspace/iac-2
fi
if [ -n "${GITEA_URL:-}" ] && [ -n "${GITEA_USER:-}" ] && [ -n "${GITEA_TOKEN:-}" ]; then
  curl -sS -X DELETE -H "Authorization: token $GITEA_TOKEN" "$GITEA_URL/api/v1/repos/$GITEA_USER/iac-baseline" -o /dev/null || true
fi
if oc get namespace build >/dev/null 2>&1; then
  oc delete pipelinerun -n build -l tekton.dev/pipeline=iac-plan-gate --ignore-not-found
  oc delete pipeline iac-plan-gate -n build --ignore-not-found
  oc delete task iac-plan-check iac-plan-report -n build --ignore-not-found
  oc delete configmap iac-source -n build --ignore-not-found
  oc delete secret iac-gitea-api -n build --ignore-not-found
fi
