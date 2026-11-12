#!/usr/bin/env bash
# Destroy labs whose AutoDestroyAfter tag is before today (UTC).
#
#   sweep.sh [--apply] [--lab LAB_ID] [--force]
#
# --force (only valid together with --lab) skips the expired-date check, so the
# named lab is treated as due now. Every other safety check still applies: the
# account check and SWEEP_ACCOUNT_ID, the LabId pattern, the Terraform-managed
# tag check, and the lab's own state bucket in this account. The cost guard's
# CodeBuild project uses it: sweep.sh --apply --force --lab <LAB_ID>.
# The script never prompts and does not need a TTY.
#
# --apply also needs SWEEP_ACCOUNT_ID=<12-digit id> and refuses to run if the current
# credentials belong to a different account (so a wrong profile cannot destroy anything).
# A lab is only touched if it has a Terraform-managed resource carrying the tags, a
# well-formed LabId, and its own state bucket in this account.
#
# Default is a dry run that only lists expired labs. With --apply, for each
# expired lab it (1) asks the bastion to run `openshift-install-fips destroy
# cluster` via the artifacts bucket marker, (2) waits for status "destroyed",
# (3) runs `terraform destroy` against the lab's S3 state.
# Needs: aws, jq, terraform, run from the terraform/ directory's parent or
# anywhere (paths are resolved from this script). Requires AWS_REGION.
set -euo pipefail

APPLY=0
ONLY=""
FORCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) APPLY=1 ;;
    --lab) ONLY="${2:?--lab needs a value}"; shift ;;
    --force) FORCE=1 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ "$FORCE" = 1 ] && [ -z "$ONLY" ]; then
  echo "--force is only valid together with --lab LAB_ID" >&2
  exit 2
fi

# CodeBuild sets AWS_DEFAULT_REGION and AWS_REGION; accept either.
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-}}"
: "${AWS_REGION:?AWS_REGION must be set}"
export AWS_REGION
export TF_IN_AUTOMATION=1
export AWS_DEFAULT_REGION="$AWS_REGION"
TF_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TODAY="$(date -u +%Y-%m-%d)"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
WAIT_SECONDS="${SWEEP_WAIT_SECONDS:-3600}"
LAB_ID_PATTERN='^[a-z0-9][a-z0-9-]{0,40}$'

if [ "$APPLY" = 1 ] && [ "${SWEEP_ACCOUNT_ID:-}" != "$ACCOUNT_ID" ]; then
  echo "refusing --apply: set SWEEP_ACCOUNT_ID to the account you mean to sweep (current credentials: $ACCOUNT_ID)" >&2
  exit 2
fi

expired_labs() {
  aws resourcegroupstaggingapi get-resources --tag-filters Key=AutoDestroyAfter --output json |
    jq -r --arg today "$TODAY" --argjson force "$FORCE" '
      [.ResourceTagMappingList[]
        | (.Tags | map({(.Key): .Value}) | add) as $t
        | select(($t.ManagedBy // "") == "terraform" and ($t.LabId // "") != "" and ($t.AutoDestroyAfter // "" | test("^[0-9]{4}-[0-9]{2}-[0-9]{2}$"))
                 and ($force == 1 or $t.AutoDestroyAfter < $today))
        | $t.LabId] | unique | .[]'
}

destroy_cluster() {
  local lab="$1" bucket="$1-artifacts-$ACCOUNT_ID" status
  if ! aws s3api head-bucket --bucket "$bucket" 2>/dev/null; then
    echo "  no artifacts bucket; skipping cluster destroy"
    return 0
  fi
  echo "  asking bastion to destroy the cluster"
  printf 'destroy' | aws s3 cp - "s3://$bucket/install/destroy" --sse aws:kms >/dev/null
  local waited=0
  while [ "$waited" -lt "$WAIT_SECONDS" ]; do
    status="$(aws s3 cp "s3://$bucket/install/status" - 2>/dev/null || true)"
    [ "$status" = "destroyed" ] && return 0
    sleep 30
    waited=$((waited + 30))
  done
  echo "  cluster destroy did not finish within $WAIT_SECONDS s; not destroying the foundation" >&2
  return 1
}

destroy_foundation() {
  local lab="$1"
  (
    cd "$TF_DIR"
    state_key_arn=$(aws kms describe-key --key-id "alias/$lab-tfstate" --region "$AWS_REGION" \
      --query KeyMetadata.Arn --output text) || exit 1
    terraform init -input=false -reconfigure \
      -backend-config="bucket=$lab-tfstate-$ACCOUNT_ID" -backend-config="region=$AWS_REGION" \
      -backend-config="kms_key_id=$state_key_arn" >/dev/null
    TF_VAR_lab_id="$lab" TF_VAR_region="$AWS_REGION" TF_VAR_destroy_after="$TODAY" \
      TF_VAR_alert_email="sweeper@example.invalid" \
      terraform destroy -input=false -auto-approve
  )
}

found=0
while IFS= read -r -u 3 lab; do
  [ -n "$ONLY" ] && [ "$lab" != "$ONLY" ] && continue
  if ! printf '%s' "$lab" | grep -Eq "$LAB_ID_PATTERN"; then
    echo "skipping tag value that is not a valid lab id: $(printf '%q' "$lab")" >&2
    continue
  fi
  if ! aws s3api head-bucket --bucket "$lab-tfstate-$ACCOUNT_ID" 2>/dev/null; then
    echo "skipping $lab: no state bucket $lab-tfstate-$ACCOUNT_ID in this account (not created by this lab tooling)" >&2
    continue
  fi
  found=1
  if [ "$FORCE" = 1 ]; then echo "forced: $lab"; else echo "expired: $lab"; fi
  if [ "$APPLY" = 1 ]; then
    destroy_cluster "$lab" && destroy_foundation "$lab"
  fi
done 3< <(expired_labs)

[ "$found" = 1 ] || echo "no expired labs as of $TODAY"
[ "$APPLY" = 1 ] || echo "dry run: pass --apply to destroy"
