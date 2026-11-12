#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes what GRC-3 steps 4 and 5 create: the CronJob and its jobs, the evidence
# files on the volume (by deleting the claim and letting 30-evidence-access.yaml recreate it), the branch
# protection on main, and the learner's branches. The merged collector stays in the history of main.
set -euo pipefail
. "$(dirname "$0")/../../_common/lib.sh"
oc delete cronjob evidence-collect -n build --ignore-not-found
oc delete job evidence-manual -n build --ignore-not-found
oc delete pvc evidence-pvc -n build --ignore-not-found
oc delete pipelinerun -n build -l tekton.dev/pipeline=review-gate --ignore-not-found
if [ -n "${GITEA_URL:-}" ] && [ -n "${GITEA_TOKEN:-}" ] && [ -n "${GITEA_USER:-}" ]; then
  gitea_call DELETE "/repos/$GITEA_USER/evidence-scripts/branch_protections/main"
  case "$GITEA_CODE" in 204 | 404) ;; *) die "could not remove branch protection on evidence-scripts main (HTTP $GITEA_CODE)" ;; esac
  for branch in add-collector weaken-hash; do
    gitea_call DELETE "/repos/$GITEA_USER/evidence-scripts/branches/$branch"
    case "$GITEA_CODE" in 204 | 404) ;; *) die "could not delete branch $branch (HTTP $GITEA_CODE)" ;; esac
  done
fi
