#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Copies the supplied Terraform baseline to /workspace/iac-3/terraform and applies it
# for namespace iac-lab, so the module starts with a baseline that Terraform created and remembers (local state file).
# terraform init works offline: TF_CLI_CONFIG_FILE=/etc/terraform.rc selects the provider mirror in the lab image.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env KUBECONFIG
WORK=/workspace/iac-3
mkdir -p "$WORK/terraform" "$WORK/ansible"
cp "$(dirname "$0")/kit/terraform/main.tf" "$WORK/terraform/main.tf"
terraform -chdir="$WORK/terraform" init -input=false -no-color >/dev/null
terraform -chdir="$WORK/terraform" apply -auto-approve -input=false -no-color >/dev/null
rc=0
terraform -chdir="$WORK/terraform" plan -detailed-exitcode -input=false -no-color >/dev/null || rc=$?
[ "$rc" -eq 0 ] || die "the Terraform baseline does not plan clean right after apply (exit $rc); run terraform plan in $WORK/terraform and read the difference"
say "baseline applied for namespace iac-lab; work folder is $WORK"
