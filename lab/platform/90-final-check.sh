#!/usr/bin/env bash
# Final check of the in-lab services. One line per service: UP or DOWN, namespace, address. Exits 1 if anything is down
# or a lab variable the contract promises is missing. Prints variable names only, never values.
# Pod patterns match ENG-0's health check (lab/states/eng-0/30-sandbox-repo.sh), plus an HTTP probe through the Route
# (checked against the ingress CA, no -k) where the service has a health URL.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

CA="$(lab_var LOKI_CA_FILE)"
DOWN=0

row() { # STATE NAME NAMESPACE DETAIL
  printf '%-5s %-16s %-22s %s\n' "$1" "$2" "$3" "$4"
  [ "$1" = UP ] || DOWN=$((DOWN + 1))
}

# pods_state NAMESPACE PATTERN: prints "ok N" or a reason. A Succeeded (finished job) pod is ignored.
pods_state() {
  local counts total notready
  counts="$(oc get pods -n "$1" -o json 2>/dev/null | jq -r --arg p "$2" '
    [.items[] | select(.metadata.name | test($p)) | select(.status.phase != "Succeeded")]
    | "\(length) \(map(select(.status.phase != "Running" or ((.status.containerStatuses // []) | all(.[]; .ready) | not))) | length)"')" || true
  [ -n "$counts" ] || { echo "namespace cannot be read"; return 1; }
  read -r total notready <<<"$counts"
  [ "$total" -gt 0 ] || { echo "no pods found"; return 1; }
  [ "$notready" -eq 0 ] || { echo "$notready of $total pods not ready"; return 1; }
  echo "$total pods ready"
}

# http_code URL [curl args...]
http_code() { local url=$1; shift; curl -sS -m 20 --cacert "$CA" -o /dev/null -w '%{http_code}' "$@" "$url" 2>/dev/null || true; }

# check NAME NAMESPACE POD-PATTERN [ADDRESS HTTP_PATH EXPECTED_CODES [curl args...]]
check() {
  local name=$1 ns=$2 pattern=$3 address=${4:-} path=${5:-} expect=${6:-} detail code
  shift 3
  [ $# -lt 3 ] || shift 3
  if ! detail="$(pods_state "$ns" "$pattern")"; then
    row DOWN "$name" "$ns" "$detail"
    return
  fi
  if [ -n "$address" ] && [ -n "$path" ]; then
    code="$(http_code "${address}${path}" "$@")"
    case " $expect " in
      *" $code "*) ;;
      *) row DOWN "$name" "$ns" "$address answers HTTP ${code:-none} on $path"; return ;;
    esac
  fi
  row UP "$name" "$ns" "${address:-$detail}"
}

LOKI_URL="$(lab_var LOKI_URL)"
GRAFANA_URL="$(lab_var GRAFANA_URL)"
GITEA_URL="$(lab_var GITEA_URL)"
MM_URL="$(lab_var MM_URL)"
KEYCLOAK_URL="$(lab_var KEYCLOAK_URL)"
ARGOCD_URL="$(lab_var ARGOCD_URL)"

check "Loki" siem '^loki' "$LOKI_URL" /ready "200" -u "$(lab_var LOKI_USER):$(lab_var LOKI_PASSWORD)"
check "Grafana" siem '^grafana' "$GRAFANA_URL" /api/health "200"
check "Alloy" siem '^alloy' ""
check "Mattermost" chat '.' "$MM_URL" /api/v4/system/ping "200"
check "Gitea" gitea '.' "$GITEA_URL" /api/healthz "200"
check "Keycloak" keycloak '.' "$KEYCLOAK_URL" /realms/master "200"
check "Tekton pipelines" openshift-pipelines 'tekton-pipelines' ""
check "Argo CD" openshift-gitops 'openshift-gitops-server' "$ARGOCD_URL" "" ""
check "Kyverno" kyverno '^kyverno-(admission|background|cleanup|reports)-controller' ""
check "Trivy operator" security-tools '^trivy-operator' ""
check "Falco" security-tools '^falco' ""
check "Collector" openshift-logging 'siem-forwarder|collector' ""

# Objects the modules read, beyond pod readiness.
oc get crd clusterpolicies.kyverno.io policyreports.wgpolicyk8s.io >/dev/null 2>&1 ||
  row DOWN "Kyverno CRDs" kyverno "ClusterPolicy or PolicyReport CRD missing"
oc get crd vulnerabilityreports.aquasecurity.github.io configauditreports.aquasecurity.github.io >/dev/null 2>&1 ||
  row DOWN "Trivy CRDs" security-tools "VulnerabilityReport or ConfigAuditReport CRD missing"
oc get configmap falco-custom-rules -n security-tools >/dev/null 2>&1 ||
  row DOWN "Falco rules map" security-tools "ConfigMap falco-custom-rules missing"
oc get clusterlogforwarder siem-forwarder -n openshift-logging >/dev/null 2>&1 ||
  row DOWN "Log forwarder" openshift-logging "ClusterLogForwarder siem-forwarder missing"
oc get secret gitea-admin -n gitea >/dev/null 2>&1 ||
  row DOWN "Gitea secret" gitea "secret gitea-admin missing"

# Variables the platform must have saved (names only).
VARS="LOKI_URL LOKI_CA_FILE LOKI_USER LOKI_PASSWORD GRAFANA_URL GRAFANA_USER GRAFANA_PASSWORD MM_URL MM_WEBHOOK_URL KEYCLOAK_URL KEYCLOAK_ADMIN_USER KEYCLOAK_ADMIN_PASSWORD GITEA_URL GITEA_INTERNAL_URL GITEA_USER GITEA_TOKEN ARGOCD_URL"
missing=""
echo "Saved variables (names only):"
for v in $VARS; do
  if [ -n "$(lab_var "$v")" ]; then
    printf '  %s\n' "$v"
  else
    missing="$missing $v"
  fi
done
[ -z "$missing" ] || { echo "Missing variables:$missing" >&2; DOWN=$((DOWN + 1)); }

if [ "$DOWN" -eq 0 ]; then
  echo "All platform services are up."
else
  die "$DOWN platform check(s) failed. Run 'lab platform --only NN' for the failing service after reading its message above."
fi
