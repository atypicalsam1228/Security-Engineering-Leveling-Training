#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Read-only: Kyverno must run and pod metrics must answer.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
crd_established clusterpolicies.kyverno.io || die "Kyverno ClusterPolicy CRD is missing; the lab build installs Kyverno 1.19.2 in the kyverno namespace"
oc adm top pods -n kyverno --no-headers >/dev/null 2>&1 || die "oc adm top pods returned nothing; ARC-3 needs the cluster metrics API"
say "Kyverno is installed and pod metrics answer"
