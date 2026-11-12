#!/usr/bin/env bash
# Remove what CPS-2 created. Deleting the namespace removes the workload, labels, quota and policy.
set -euo pipefail
oc delete scansettingbinding harden-scan -n openshift-compliance --ignore-not-found
oc delete tailoredprofile harden-baseline -n openshift-compliance --ignore-not-found
oc delete namespace harden-lab --ignore-not-found --wait=true
