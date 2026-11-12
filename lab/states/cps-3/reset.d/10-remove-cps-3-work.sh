#!/usr/bin/env bash
# Remove what CPS-3 created (the whole namespace, which holds every object the module makes).
set -euo pipefail
oc delete namespace rbac-lab --ignore-not-found --wait=true
