#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes everything IAC-1 creates: the namespace iac-lab (Terraform builds it; deleting it also
# removes the quota, network policy, role, role binding, service account and config map) and the folder /workspace/iac-1
# (Terraform state files, saved plans and the fetched supplied files). The config map iac-supplied is part of the start state and is kept.
set -euo pipefail
oc delete namespace iac-lab --ignore-not-found --wait=true --timeout=180s
if [ -d /workspace/iac-1 ]; then
  rm -rf /workspace/iac-1
fi
