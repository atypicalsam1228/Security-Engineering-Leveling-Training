#!/usr/bin/env bash
# Run by `lab up` inside the tools container before terraform apply.
# Creates (once, safe to repeat) the lab's state KMS key and S3 state bucket, then
# initializes the S3 backend declared in versions.tf. Names match sweep.sh and the
# cost guard: alias/<lab_id>-tfstate and <lab_id>-tfstate-<account id>.
set -euo pipefail

LAB_ID="${TF_VAR_lab_id:-${LAB_ID:-}}"
REGION="${TF_VAR_region:-${AWS_REGION:-${AWS_DEFAULT_REGION:-}}}"
if ! printf '%s' "$LAB_ID" | grep -Eq '^[a-z0-9][a-z0-9-]{0,40}$'; then
  echo "Set TF_VAR_lab_id (lowercase letters, digits, hyphens; max 41 characters) before 'lab up'." >&2
  exit 1
fi
if [ -z "$REGION" ]; then
  echo "Set TF_VAR_region (the AWS region for the lab) before 'lab up'." >&2
  exit 1
fi
export AWS_DEFAULT_REGION="$REGION"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="$LAB_ID-tfstate-$ACCOUNT_ID"
ALIAS="alias/$LAB_ID-tfstate"

KEY_ARN="$(aws kms describe-key --key-id "$ALIAS" --query KeyMetadata.Arn --output text 2>/dev/null || true)"
if [ -z "$KEY_ARN" ] || [ "$KEY_ARN" = "None" ]; then
  KEY_ARN="$(aws kms create-key --description "Terraform state for lab $LAB_ID" \
    --tags "TagKey=LabId,TagValue=$LAB_ID" --query KeyMetadata.Arn --output text)"
  aws kms create-alias --alias-name "$ALIAS" --target-key-id "$KEY_ARN"
  aws kms enable-key-rotation --key-id "$KEY_ARN"
fi

if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET" >/dev/null
  else
    aws s3api create-bucket --bucket "$BUCKET" \
      --create-bucket-configuration "LocationConstraint=$REGION" >/dev/null
  fi
fi
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket "$BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration \
  "{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"aws:kms\",\"KMSMasterKeyID\":\"$KEY_ARN\"},\"BucketKeyEnabled\":true}]}"

cd "$(dirname "$0")/.."
exec terraform init -input=false -reconfigure \
  -backend-config="bucket=$BUCKET" -backend-config="region=$REGION" \
  -backend-config="kms_key_id=$KEY_ARN"
