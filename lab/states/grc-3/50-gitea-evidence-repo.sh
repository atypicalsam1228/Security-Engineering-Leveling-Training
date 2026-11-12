#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Seeds the Gitea repository evidence-scripts (public inside the lab, so the
# scheduled job can fetch the collector without a token), the config map evidence-source (no secret), the secret
# gitea-api (the token the review gate uses to post statuses; only the gate mounts it) and a push webhook that
# calls the EventListener. GITEA_TOKEN must belong to an administrator.
# ASSUMPTION TO CONFIRM LIVE: Gitea allows webhooks to a private cluster address (webhook.ALLOWED_HOST_LIST).
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN
repo=evidence-scripts
hook_url="http://el-gate-listener.build.svc.cluster.local:8080"

gitea_call GET "/repos/$GITEA_USER/$repo"
if [ "$GITEA_CODE" != 200 ]; then
  gitea_call POST /user/repos "$(jq -n --arg n "$repo" '{name: $n, private: false, auto_init: true, default_branch: "main"}')"
  [ "$GITEA_CODE" = 201 ] || die "could not create Gitea repository $repo (HTTP $GITEA_CODE)"
fi
gitea_put_file "$repo" main README.md "Add readme" "# Evidence scripts"

# Pods call Gitea over its in-cluster address (plain HTTP, no certificate to trust) when a Gitea service on port 3000 exists;
# otherwise they use the same address as lab shell.
pod_url=$(oc get svc -n gitea -o json 2>/dev/null | jq -r '[.items[] | select(any(.spec.ports[]?; .port == 3000))] | first | select(. != null) | "http://\(.metadata.name).gitea.svc.cluster.local:3000"' || true)
pod_url=${pod_url:-$GITEA_URL}
oc create configmap evidence-source -n build --from-literal=GITEA_URL="$pod_url" \
  --from-literal=GITEA_USER="$GITEA_USER" --dry-run=client -o yaml | oc apply -f - >/dev/null
oc create secret generic gitea-api -n build --from-literal=GITEA_TOKEN="$GITEA_TOKEN" \
  --dry-run=client -o yaml | oc apply -f - >/dev/null

gitea_call GET "/repos/$GITEA_USER/$repo/hooks"
if ! printf '%s' "$GITEA_BODY" | jq -e --arg u "$hook_url" 'any(.[]; .config.url == $u)' >/dev/null; then
  gitea_call POST "/repos/$GITEA_USER/$repo/hooks" "$(jq -n --arg u "$hook_url" '{type: "gitea", active: true, events: ["push"], config: {url: $u, content_type: "json"}}')"
  [ "$GITEA_CODE" = 201 ] || die "could not create the push webhook (HTTP $GITEA_CODE)"
fi
