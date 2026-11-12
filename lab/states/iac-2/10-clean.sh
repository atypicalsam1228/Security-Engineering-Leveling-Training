#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Makes IAC-2 start from nothing whether or not IAC-1 ran: removes namespace iac-lab,
# the local Terraform working folder /workspace/iac-2 (when run inside the lab shell) and the Gitea repository
# iac-baseline (30-gitea-repo.sh recreates it), and old Tekton runs of the gate.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN
oc delete namespace iac-lab --ignore-not-found --wait=true
if [ -d /workspace ]; then
  rm -rf /workspace/iac-2
fi
gitea_call DELETE "/repos/$GITEA_USER/iac-baseline"
case "$GITEA_CODE" in 204 | 404) ;; *) die "could not remove Gitea repository iac-baseline (HTTP $GITEA_CODE)" ;; esac
if oc get namespace build >/dev/null 2>&1; then
  oc delete pipelinerun -n build -l tekton.dev/pipeline=iac-plan-gate --ignore-not-found
fi
