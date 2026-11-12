#!/usr/bin/env bash
# Falco 0.45.1 in namespace security-tools as DaemonSet "falco" (CPS-4 restarts it with `oc rollout restart daemonset/falco`
# and reads `oc logs daemonset/falco -c falco`).
# Contract with the modules:
#  - json_output true (SDR-2/SDR-4 parse the log line as JSON: rule, output_fields["k8s.ns.name"], ["k8s.pod.name"], ["user.name"]);
#  - container metadata filled (container plugin, chart default; k8s.ns.name and k8s.pod.name come from the CRI-O pod annotations);
#  - ConfigMap falco-custom-rules (owned by this script only for its creation, never by Helm) mounted at /etc/falco/rules.d,
#    which is in Falco's rules_files list; CPS-4 adds the key secure-lab-rules.yaml with `oc set data`;
#  - the collector ships stdout of pods in security-tools to Loki as application logs (nothing to configure here).
# SCC: the chart creates SecurityContextConstraints "falco" for the falco service account (hostPath, hostPID, hostNetwork,
# privileged container). Falco cannot run on RHCOS without it: the modern eBPF probe needs a privileged container
# (leastPrivileged=false) and read access to the host /proc, /boot, /usr, /etc and the CRI-O socket. RHCOS has no kernel
# headers, so the modern eBPF driver (built into the Falco binary, CO-RE) is used instead of a kernel module.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

NS=security-tools
RELEASE=falco
# Verified 2026-11-02: https://falcosecurity.github.io/charts/index.yaml lists falco 9.2.1 with appVersion 0.45.1
# (9.2.2 ships 0.45.2; the contract pins 0.45.1). Images checked in the registries on the same date:
# docker.io/falcosecurity/falco:0.45.1, docker.io/falcosecurity/falcoctl:0.14.2 (chart default),
# ghcr.io/falcosecurity/plugins/plugin/container:0.7.5 and ghcr.io/falcosecurity/rules/falco-rules:5 (chart defaults).
CHART_REPO=https://falcosecurity.github.io/charts
CHART_VERSION=9.2.1
FALCO_VERSION=0.45.1

installed_chart() { helm list -n "$NS" --filter "^${RELEASE}\$" -o json 2>/dev/null | jq -r '.[0] | select(.status == "deployed") | .chart // empty'; }

ensure_namespace "$NS"
oc label namespace "$NS" --overwrite \
  pod-security.kubernetes.io/enforce=privileged pod-security.kubernetes.io/audit=privileged \
  pod-security.kubernetes.io/warn=privileged security.openshift.io/scc.podSecurityLabelSync=false >/dev/null

# The rules map must exist before the pod starts (a missing ConfigMap volume keeps the pod in ContainerCreating).
# Created empty and never replaced, so keys the learner adds survive a re-run of this script.
if ! oc get configmap falco-custom-rules -n "$NS" >/dev/null 2>&1; then
  oc create configmap falco-custom-rules -n "$NS" >/dev/null
  say "created empty ConfigMap falco-custom-rules"
fi

values="$(mktemp)"
trap 'rm -f "$values"' EXIT
# falcoctl "follow" sidecar off (it only checks for rule updates every 168h); the install init container stays and fetches
# the default rules (falco-rules:5) and the container plugin from ghcr.io, so the cluster needs internet access.
cat >"$values" <<'EOF'
driver:
  kind: modern_ebpf
tty: true
resources:
  requests: {cpu: 100m, memory: 256Mi}
  limits: {cpu: 1000m, memory: 1Gi}
falco:
  json_output: true
falcoctl:
  artifact:
    follow:
      enabled: false
mounts:
  volumes:
    - name: falco-custom-rules
      configMap:
        name: falco-custom-rules
  volumeMounts:
    - name: falco-custom-rules
      mountPath: /etc/falco/rules.d
EOF

current="$(installed_chart)"
if [ "$current" = "falco-${CHART_VERSION}" ]; then
  say "Falco chart $CHART_VERSION already deployed"
else
  say "installing Falco $FALCO_VERSION (chart $CHART_VERSION, modern eBPF driver)"
  helm_apply "$RELEASE" falco "$NS" "$CHART_VERSION" --repo "$CHART_REPO" -f "$values" >/dev/null ||
    die "helm could not install the Falco chart $CHART_VERSION (needs internet access to $CHART_REPO and ghcr.io). Check 'oc get pods -n $NS' and 'oc logs daemonset/falco -c falcoctl-artifact-install -n $NS'"
fi
wait_rollout "$NS" daemonset/falco 600

image="$(oc get daemonset falco -n "$NS" -o jsonpath='{.spec.template.spec.containers[?(@.name=="falco")].image}')"
case "$image" in *":$FALCO_VERSION") say "Falco image $image" ;; *) die "Falco runs $image, expected tag $FALCO_VERSION" ;; esac

json_on() { oc get configmap falco -n "$NS" -o jsonpath='{.data.falco\.yaml}' | grep -q '^json_output: true'; }
json_on || die "Falco config does not have json_output: true"
oc get configmap falco-custom-rules -n "$NS" >/dev/null || die "ConfigMap falco-custom-rules is missing"
say "Falco prints JSON; falco-custom-rules is mounted at /etc/falco/rules.d"

# Soft check: the container plugin and driver should report in the log; a missing line is a warning only.
if ! oc logs daemonset/falco -c falco -n "$NS" --tail=200 2>/dev/null | grep -qi 'modern\|Opening'; then
  say "WARNING: no driver start line in the Falco log yet; read 'oc logs daemonset/falco -c falco -n $NS'"
fi
