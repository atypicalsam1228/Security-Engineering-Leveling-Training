#!/usr/bin/env bash
# REGISTRY_HOST: the address of the cluster's built-in image registry, as pods see it.
# CPS-5 uses it as one of two allowed registries in an image policy; no image has to exist there.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
host="image-registry.openshift-image-registry.svc:5000"
oc get service image-registry -n openshift-image-registry >/dev/null 2>&1 \
  || die "the built-in image registry service was not found in openshift-image-registry"
lab_var_set REGISTRY_HOST "$host"
say "REGISTRY_HOST=$host"
