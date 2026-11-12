#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Namespaces demo and build exist, and Kyverno (lab-provided) is running.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_demo_app
ensure_namespace build
oc get crd clusterpolicies.kyverno.io >/dev/null || die "Kyverno ClusterPolicy CRD is missing (the lab build installs Kyverno)"
ready=$(oc get pods -n kyverno -o json | jq '[.items[] | select(.status.phase == "Running")] | length')
[ "$ready" -ge 1 ] || die "no Kyverno pod is Running in namespace kyverno"
say "Kyverno is running ($ready pods)"
