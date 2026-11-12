#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Read-only: Kyverno 1.19.2 (lab-provided) must run in namespace kyverno with the
# ClusterPolicy CRD, and the openshift-config namespace must exist (the project template is stored there).
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
oc get namespace kyverno >/dev/null || die "namespace kyverno is missing (the lab build installs Kyverno)"
oc get crd clusterpolicies.kyverno.io >/dev/null || die "Kyverno ClusterPolicy CRD is missing"
ready=$(oc get pods -n kyverno -o json | jq '[.items[] | select(.status.phase == "Running")] | length')
[ "$ready" -ge 1 ] || die "no Kyverno pod is Running in namespace kyverno"
oc get serviceaccount kyverno-background-controller -n kyverno >/dev/null ||
  die "service account kyverno-background-controller not found; the module needs its name for the permission check"
say "Kyverno is running ($ready pods)"
