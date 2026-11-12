#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes everything IAC-3 creates: the namespace iac-lab (with every object in it)
# and the learner's working folder /workspace/iac-3 (the Terraform state file, the playbook and the scripts).
set -euo pipefail
oc delete namespace iac-lab --ignore-not-found --wait=true
rm -rf /workspace/iac-3
