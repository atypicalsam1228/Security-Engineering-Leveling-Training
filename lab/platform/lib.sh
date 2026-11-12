# Shared helpers for the platform install scripts. Source it: . "$(dirname "$0")/lib.sh"
# Scripts run in the tools container with the workspace at /workspace and lab.env under /workspace/.lab.

LAB_ENV_FILE="${LAB_ENV_FILE:-/workspace/.lab/lab.env}"
LAB_STATE_DIR="${LAB_STATE_DIR:-/workspace/.lab}"

say() { echo "  $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

require_cluster() {
  oc whoami >/dev/null 2>&1 || die "oc cannot sign in. Check that $KUBECONFIG exists (lab up writes it) and that the cluster is up."
}

# lab_var NAME: print the value from the process environment, else from lab.env, else nothing.
lab_var() {
  local name="$1" value
  value="${!name:-}"
  if [ -z "$value" ] && [ -f "$LAB_ENV_FILE" ]; then
    value="$(sed -n "s/^${name}=//p" "$LAB_ENV_FILE" | tail -n 1)"
  fi
  printf '%s' "$value"
}

# lab_var_set NAME VALUE: store a value in lab.env (mode 600) so the next lab shell has it. Replaces an old value.
lab_var_set() {
  local name="$1" value="$2" tmp
  case "$value" in *$'\n'*) die "lab_var_set: $name has a line break" ;; esac
  mkdir -p "$LAB_STATE_DIR"
  tmp="$(mktemp "$LAB_STATE_DIR/lab.env.XXXXXX")"
  chmod 600 "$tmp"
  { [ -f "$LAB_ENV_FILE" ] && grep -v "^${name}=" "$LAB_ENV_FILE" || true; } >"$tmp"
  printf '%s=%s\n' "$name" "$value" >>"$tmp"
  mv "$tmp" "$LAB_ENV_FILE"
  export "$name=$value"
}

# require_var NAME...: stop with a message if a lab variable is empty (reads lab.env too).
require_var() {
  local name
  for name in "$@"; do
    [ -n "$(lab_var "$name")" ] || die "$name is not set. Run 'lab up' first so the lab creates it."
    export "$name=$(lab_var "$name")"
  done
}

ensure_namespace() { oc create namespace "$1" --dry-run=client -o yaml | oc apply -f - >/dev/null; }

# wait_until "what" TIMEOUT_SECONDS command...: poll every 5 seconds until the command succeeds.
wait_until() {
  local what="$1" limit="$2" waited=0
  shift 2
  until "$@" >/dev/null 2>&1; do
    [ "$waited" -lt "$limit" ] || die "timed out after ${limit}s waiting for $what"
    sleep 5
    waited=$((waited + 5))
  done
  say "ready: $what"
}

# wait_rollout NAMESPACE KIND/NAME [SECONDS]
wait_rollout() { oc rollout status "$2" -n "$1" --timeout="${3:-600}s" >/dev/null || die "$2 in $1 did not become ready"; say "ready: $2 in $1"; }

# route_host NAMESPACE ROUTE: print the host name of a route.
route_host() { oc get route "$2" -n "$1" -o jsonpath='{.spec.host}'; }

# random_secret [BYTES]: URL-safe random text, 24 bytes by default.
random_secret() { head -c "${1:-24}" /dev/urandom | base64 | tr -d '=+/\n' | cut -c1-32; }

# install_or_upgrade_helm RELEASE CHART NAMESPACE VERSION [helm args...]
helm_apply() {
  local release="$1" chart="$2" ns="$3" version="$4"
  shift 4
  helm upgrade --install "$release" "$chart" -n "$ns" --create-namespace --version "$version" --wait --timeout 10m "$@"
}

# ingress_ca_file: write the CA that signs the default router certificate; print its path.
ingress_ca_file() {
  local out="$LAB_STATE_DIR/ingress-ca.crt"
  oc get configmap default-ingress-cert -n openshift-config-managed -o jsonpath='{.data.ca-bundle\.crt}' >"$out"
  [ -s "$out" ] || die "could not read the ingress CA from openshift-config-managed/default-ingress-cert"
  printf '%s' "$out"
}
