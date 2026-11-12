#!/usr/bin/env bash
# Remove everything CPS-5 creates: policies, the extra permission, the project template and its setting, and the gr-* namespaces.
set -euo pipefail
oc patch project.config.openshift.io cluster --type=merge -p '{"spec":{"projectRequestTemplate":null}}' || true
oc delete template guardrail-project-request -n openshift-config --ignore-not-found
oc delete clusterpolicy gr-generate-deny gr-generate-quota gr-mutate-safe-defaults gr-validate-host-access gr-validate-images --ignore-not-found
oc delete clusterrole gr-kyverno-generate --ignore-not-found
for ns in $(oc get namespaces -o name | grep '^namespace/gr-' | cut -d/ -f2); do
  oc delete namespace "$ns" --ignore-not-found --wait=false
done
oc delete namespace guardrails-lab --ignore-not-found --wait=true
