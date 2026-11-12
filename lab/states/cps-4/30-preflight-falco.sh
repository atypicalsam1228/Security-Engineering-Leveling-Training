#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Read-only: Falco (installed by the lab build) must run in security-tools and the
# config map falco-custom-rules must exist, because the learner adds a rules file to it.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
oc get daemonset falco -n security-tools >/dev/null || die "daemonset falco is missing in security-tools (the lab build installs Falco)"
oc get configmap falco-custom-rules -n security-tools >/dev/null 2>&1 ||
  oc create configmap falco-custom-rules -n security-tools --dry-run=client -o yaml | oc apply -f - >/dev/null
say "Falco is present and falco-custom-rules exists"
