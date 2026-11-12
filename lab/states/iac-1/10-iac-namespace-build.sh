#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Makes sure namespace build exists (it holds the config map iac-supplied, applied by 30-iac-supplied.yaml).
# Namespace iac-lab is NOT created here: the learner creates it with Terraform in Step 2.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_namespace build
say "namespace build is ready"
