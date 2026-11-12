#!/usr/bin/env bash
# Shared helpers for lab start states. Source this file from a state script; do not run it.
# Every function is safe to run twice. Uses oc, aws, curl and jq only (plus basic shell tools).
# Lab variables come from LAB-CONTRACT.md; nothing secret is ever printed.
STATES_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIEM_FORWARDER_NAME="siem-forwarder"
LOGGING_NAMESPACE="openshift-logging"
MARKETPLACE_NAMESPACE="openshift-marketplace"
WAIT_TRIES=60
WAIT_STEP=10

die() { echo "ERROR: $*" >&2; exit 1; }
say() { echo "  $*"; }

require_env() {
  local name
  for name in "$@"; do
    [ -n "${!name:-}" ] || die "$name is not set. Run this inside lab shell, where lab sets it."
  done
}

wait_until() {
  local what=$1 tries=0
  shift
  until "$@" >/dev/null 2>&1; do
    tries=$((tries + 1))
    [ "$tries" -le "$WAIT_TRIES" ] || die "timed out waiting for $what"
    sleep "$WAIT_STEP"
  done
}

ensure_namespace() {
  oc get namespace "$1" >/dev/null 2>&1 || oc create namespace "$1" >/dev/null
}

# ---- demo-app (namespace demo) -------------------------------------------------------------
ensure_demo_app() {
  ensure_namespace demo
  if oc get deployment demo-app -n demo >/dev/null 2>&1; then
    say "demo-app already exists in demo; leaving it as it is"
  else
    oc apply -f "$STATES_COMMON_DIR/demo-app.yaml" >/dev/null
  fi
  oc rollout status deployment/demo-app -n demo --timeout=240s
}

# ---- OLM operators ---------------------------------------------------------------------------
subscription_for_package() {
  oc get subscription -n "$2" -o json 2>/dev/null | jq -r --arg p "$1" '[.items[] | select(.spec.name == $p) | .metadata.name] | first // empty'
}

ensure_operator_group() {
  local ns=$1 mode=$2
  [ "$mode" = global ] && return 0
  [ -z "$(oc get operatorgroup -n "$ns" -o name 2>/dev/null)" ] || return 0
  if [ "$mode" = own ]; then
    oc apply -f - >/dev/null <<EOF
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: ${ns}
  namespace: ${ns}
spec:
  targetNamespaces:
    - ${ns}
EOF
  else
    oc apply -f - >/dev/null <<EOF
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: ${ns}
  namespace: ${ns}
spec:
  upgradeStrategy: Default
EOF
  fi
}

csv_succeeded() {
  local csv
  csv=$(oc get subscription "$1" -n "$2" -o jsonpath='{.status.installedCSV}' 2>/dev/null) || return 1
  [ -n "$csv" ] || return 1
  [ "$(oc get csv "$csv" -n "$2" -o jsonpath='{.status.phase}' 2>/dev/null)" = Succeeded ]
}

# ensure_operator <package> <namespace> <own|all|global>
# Channel = the catalog's default channel, so no version is guessed here.
ensure_operator() {
  local pkg=$1 ns=$2 mode=$3 sub channel
  ensure_namespace "$ns"
  ensure_operator_group "$ns" "$mode"
  sub=$(subscription_for_package "$pkg" "$ns")
  if [ -z "$sub" ]; then
    channel=$(oc get packagemanifest "$pkg" -n "$MARKETPLACE_NAMESPACE" -o jsonpath='{.status.defaultChannel}' 2>/dev/null) || true
    [ -n "$channel" ] || die "package $pkg not found in the $MARKETPLACE_NAMESPACE catalog (is the cluster connected to the Red Hat catalog?)"
    oc apply -f - >/dev/null <<EOF
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: ${pkg}
  namespace: ${ns}
spec:
  name: ${pkg}
  channel: ${channel}
  source: redhat-operators
  sourceNamespace: ${MARKETPLACE_NAMESPACE}
  installPlanApproval: Automatic
EOF
    sub=$pkg
  fi
  wait_until "operator $pkg to finish installing" csv_succeeded "$sub" "$ns"
}

crd_established() {
  [ "$(oc get crd "$1" -o jsonpath='{.status.conditions[?(@.type=="Established")].status}' 2>/dev/null)" = True ]
}

# ---- log forwarder end state: collector identity and log forwarder ---------------------------------
role_bound_to_collector() {
  oc get clusterrolebinding -o json | jq -e --arg r "$1" --arg ns "$LOGGING_NAMESPACE" \
    '.items[] | select(.roleRef.name == $r) | select(any(.subjects[]?; .kind == "ServiceAccount" and .name == "collector" and .namespace == $ns))' >/dev/null
}

forwarder_has_delivery_mode() {
  oc get clusterlogforwarder "$SIEM_FORWARDER_NAME" -n "$LOGGING_NAMESPACE" -o json |
    jq -e '.spec.outputs[0].loki.tuning.deliveryMode == "AtLeastOnce"' >/dev/null
}

# ensure_siem_forwarder [tuned]  Creates the log forwarder end state if it is missing. An existing
# forwarder is left alone; "tuned" adds the at-least-once delivery mode.
ensure_siem_forwarder() {
  local role
  require_env LOKI_URL LOKI_USER LOKI_PASSWORD LOKI_CA_FILE
  ensure_namespace "$LOGGING_NAMESPACE"
  oc create serviceaccount collector -n "$LOGGING_NAMESPACE" --dry-run=client -o yaml | oc apply -f - >/dev/null
  for role in collect-application-logs collect-infrastructure-logs collect-audit-logs; do
    role_bound_to_collector "$role" ||
      oc create clusterrolebinding "${role}-collector" --clusterrole="$role" \
        --serviceaccount="$LOGGING_NAMESPACE:collector" --dry-run=client -o yaml | oc apply -f - >/dev/null
  done
  oc create secret generic loki-credentials -n "$LOGGING_NAMESPACE" \
    --from-literal=username="$LOKI_USER" --from-literal=password="$LOKI_PASSWORD" \
    --dry-run=client -o yaml | oc apply -f - >/dev/null
  oc create secret generic loki-ca -n "$LOGGING_NAMESPACE" --from-file=ca.crt="$LOKI_CA_FILE" \
    --dry-run=client -o yaml | oc apply -f - >/dev/null
  if oc get clusterlogforwarder "$SIEM_FORWARDER_NAME" -n "$LOGGING_NAMESPACE" >/dev/null 2>&1; then
    say "forwarder $SIEM_FORWARDER_NAME already exists"
  else
    apply_forwarder_manifest
  fi
  if [ "${1:-}" = tuned ] && ! forwarder_has_delivery_mode; then
    oc patch clusterlogforwarder "$SIEM_FORWARDER_NAME" -n "$LOGGING_NAMESPACE" --type json \
      -p '[{"op":"add","path":"/spec/outputs/0/loki/tuning","value":{"deliveryMode":"AtLeastOnce"}}]' >/dev/null
  fi
}

# Same content as the log forwarder manifest (the shell expands LOKI_URL).
apply_forwarder_manifest() {
  oc apply -f - >/dev/null <<EOF
apiVersion: observability.openshift.io/v1
kind: ClusterLogForwarder
metadata:
  name: ${SIEM_FORWARDER_NAME}
  namespace: ${LOGGING_NAMESPACE}
spec:
  serviceAccount:
    name: collector
  outputs:
    - name: siem-loki
      type: loki
      loki:
        url: "${LOKI_URL}"
        authentication:
          username:
            secretName: loki-credentials
            key: username
          password:
            secretName: loki-credentials
            key: password
      tls:
        ca:
          secretName: loki-ca
          key: ca.crt
  pipelines:
    - name: security-logs
      inputRefs:
        - audit
        - infrastructure
        - application
      outputRefs:
        - siem-loki
EOF
}

# ClusterRole audit-log-reader is lab-provided with the Loki endpoint that enforces it; created only if missing.
ensure_audit_log_reader_role() {
  if oc get clusterrole audit-log-reader >/dev/null 2>&1; then
    say "clusterrole audit-log-reader already exists"
  else
    oc create clusterrole audit-log-reader --verb=get --non-resource-url='/loki/*' --dry-run=client -o yaml | oc apply -f - >/dev/null
  fi
}

# ---- Loki and Grafana checks and calls ------------------------------------------------------
loki_get() {
  curl -s --cacert "$LOKI_CA_FILE" -u "$LOKI_USER:$LOKI_PASSWORD" "$@"
}

grafana_get() {
  curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_URL$1"
}

grafana_send() { # method path json
  curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" -X "$1" -H 'Content-Type: application/json' \
    -H 'X-Disable-Provenance: true' -d "$3" "$GRAFANA_URL$2"
}

# ---- Gitea -------------------------------------------------------------------------------------
# gitea_call <method> <path> [json]  sets GITEA_CODE and GITEA_BODY
gitea_call() {
  local out
  if [ -n "${3:-}" ]; then
    out=$(curl -s -w $'\n%{http_code}' -X "$1" -H "Authorization: token $GITEA_TOKEN" \
      -H 'Content-Type: application/json' -d "$3" "$GITEA_URL/api/v1$2") || die "cannot reach Gitea at $GITEA_URL"
  else
    out=$(curl -s -w $'\n%{http_code}' -X "$1" -H "Authorization: token $GITEA_TOKEN" \
      -H 'Content-Type: application/json' "$GITEA_URL/api/v1$2") || die "cannot reach Gitea at $GITEA_URL"
  fi
  GITEA_CODE=${out##*$'\n'}
  GITEA_BODY=${out%$'\n'*}
}

gitea_ensure_repo() { # name
  gitea_call GET "/repos/$GITEA_USER/$1"
  [ "$GITEA_CODE" = 200 ] && return 0
  gitea_call POST /user/repos "$(jq -n --arg n "$1" '{name: $n, private: true, auto_init: true, default_branch: "main"}')"
  [ "$GITEA_CODE" = 201 ] || die "could not create Gitea repository $1 (HTTP $GITEA_CODE)"
}

gitea_ensure_branch() { # repo branch from
  gitea_call GET "/repos/$GITEA_USER/$1/branches/$2"
  [ "$GITEA_CODE" = 200 ] && return 0
  gitea_call POST "/repos/$GITEA_USER/$1/branches" "$(jq -n --arg b "$2" --arg o "$3" '{new_branch_name: $b, old_branch_name: $o}')"
  [ "$GITEA_CODE" = 201 ] || die "could not create branch $2 in $1 (HTTP $GITEA_CODE)"
}

# gitea_put_file <repo> <branch> <path> <message> <content>  writes the file only when it differs
gitea_put_file() {
  local repo=$1 branch=$2 path=$3 message=$4 content=$5 sha current method body
  gitea_call GET "/repos/$GITEA_USER/$repo/contents/$path?ref=$branch"
  sha=""
  current=""
  if [ "$GITEA_CODE" = 200 ]; then
    sha=$(printf '%s' "$GITEA_BODY" | jq -r '.sha // empty')
    current=$(printf '%s' "$GITEA_BODY" | jq -r '.content // "" | gsub("\n"; "") | @base64d')
    [ "$current" = "$content" ] && return 0
  fi
  body=$(jq -n --arg b "$branch" --arg m "$message" --arg c "$content" --arg s "$sha" \
    '{branch: $b, message: $m, content: (($c + "\n") | @base64)} + (if $s != "" then {sha: $s} else {} end)')
  method=POST
  [ -z "$sha" ] || method=PUT
  gitea_call "$method" "/repos/$GITEA_USER/$repo/contents/$path" "$body"
  case "$GITEA_CODE" in 200 | 201) ;; *) die "could not write $path on $branch of $repo (HTTP $GITEA_CODE)" ;; esac
}

# gitea_pod_url: the address pods use for Gitea (plain HTTP inside the cluster; no certificate to trust).
gitea_pod_url() {
  if [ -n "${GITEA_INTERNAL_URL:-}" ]; then printf '%s' "$GITEA_INTERNAL_URL"; else printf '%s' "$GITEA_URL"; fi
}

# mm_pod_webhook_url: the incoming webhook as pods see it (plain HTTP to the chat service inside the cluster).
# Grafana runs in a pod that does not trust the cluster ingress CA, so its contact point must use this address.
mm_pod_webhook_url() {
  printf 'http://mattermost.chat.svc.cluster.local:8065/hooks/%s' "${MM_WEBHOOK_URL##*/hooks/}"
}
