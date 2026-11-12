#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Read-only checks for things the lab build provides.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
oc get crd pipelines.tekton.dev >/dev/null || die "OpenShift Pipelines (Tekton) is not installed"
oc get secret mm-api -n siem -o jsonpath='{.data.token}' >/dev/null 2>&1 || die "Secret mm-api (key token) is missing in namespace siem: the lab build provides a Mattermost access token"
oc get deployment gitea -n gitea >/dev/null 2>&1 || say "note: Deployment gitea not found in namespace gitea (name differs?); GITEA_URL is what counts"
say "Tekton, the Mattermost token secret and Gitea were found"
