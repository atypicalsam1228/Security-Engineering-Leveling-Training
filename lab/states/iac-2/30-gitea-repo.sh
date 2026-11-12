#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Creates the Gitea repository iac-baseline (under GITEA_USER, private) with
# README.md, .gitignore and providers.tf on main. No branch protection and no webhook: the learner adds protection in
# Step 4 and the gate is started by hand with tkn. Also creates config map iac-source (Gitea address and owner, no
# secret) and secret iac-gitea-api (the token the gate task uses to read files and post the commit status).
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN
repo=iac-baseline

PROVIDERS='terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "3.4.0"
    }
  }
}

provider "kubernetes" {
  config_path        = "/workspace/.lab/kubeconfig"
  ignore_annotations = ["openshift[.]io/.*", "security[.]openshift[.]io/.*"]
  ignore_labels      = ["pod-security[.]kubernetes[.]io/.*", "security[.]openshift[.]io/.*", "openshift-pipelines[.]tekton[.]dev/.*"]
}'

IGNORE='.terraform/
*.tfstate
*.tfstate.*
*.tfplan
drift.txt'

gitea_ensure_repo "$repo"
gitea_put_file "$repo" main README.md "Add readme" "# iac-baseline: Terraform baseline for namespace iac-lab"
gitea_put_file "$repo" main .gitignore "Ignore Terraform working files" "$IGNORE"
gitea_put_file "$repo" main providers.tf "Add provider settings" "$PROVIDERS"

ensure_namespace build
oc create configmap iac-source -n build --from-literal=GITEA_URL="$(gitea_pod_url)" \
  --from-literal=GITEA_USER="$GITEA_USER" --dry-run=client -o yaml | oc apply -f - >/dev/null
oc create secret generic iac-gitea-api -n build --from-literal=GITEA_TOKEN="$GITEA_TOKEN" \
  --dry-run=client -o yaml | oc apply -f - >/dev/null
