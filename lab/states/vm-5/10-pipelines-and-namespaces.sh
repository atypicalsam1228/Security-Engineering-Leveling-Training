#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Namespace build, OpenShift Pipelines, a Gitea clone credential linked to the
# pipeline service account, and two older pipelines (team-b-release, team-c-release) that only clone.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN
ensure_operator openshift-pipelines-operator-rh openshift-operators global
ensure_namespace build
wait_until "service account pipeline in build" oc get serviceaccount pipeline -n build
wait_until "task git-clone in openshift-pipelines" oc get task git-clone -n openshift-pipelines
host="${GITEA_URL#*://}"
oc create secret generic gitea-clone -n build --type=kubernetes.io/basic-auth \
  --from-literal=username="$GITEA_USER" --from-literal=password="$GITEA_TOKEN" --dry-run=client -o yaml | oc apply -f - >/dev/null
oc annotate secret gitea-clone -n build "tekton.dev/git-0=${GITEA_URL%%://*}://${host%%/*}" --overwrite >/dev/null
oc secrets link pipeline gitea-clone -n build
# The lab's own certificate authority, so git-clone verifies the Gitea certificate instead of skipping the check.
# The key must be named ca-bundle.crt, the file name git-clone looks for in its ssl-ca-directory workspace.
ca_bundle=/workspace/.lab/ca-bundle.crt
[ -s "$ca_bundle" ] || die "lab CA bundle not found at $ca_bundle"
oc create configmap lab-ca -n build --from-file=ca-bundle.crt="$ca_bundle" --dry-run=client -o yaml | oc apply -f - >/dev/null
for team in team-b-release team-c-release; do
  cat <<EOF | oc apply -f - >/dev/null
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: $team
  namespace: build
spec:
  params:
    - name: git-url
    - name: git-revision
      default: main
  workspaces:
    - name: source
    - name: ssl-ca
      optional: true
  tasks:
    - name: clone
      taskRef:
        resolver: cluster
        params:
          - {name: kind, value: task}
          - {name: name, value: git-clone}
          - {name: namespace, value: openshift-pipelines}
      params:
        - {name: URL, value: \$(params.git-url)}
        - {name: REVISION, value: \$(params.git-revision)}
      workspaces:
        - {name: output, workspace: source}
        - {name: ssl-ca-directory, workspace: ssl-ca}
EOF
done
