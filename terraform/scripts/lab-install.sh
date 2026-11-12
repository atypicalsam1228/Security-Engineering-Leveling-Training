#!/usr/bin/env bash
# Run by `lab up` and `lab down` inside the tools container (terraform dir mounted).
#
#   lab-install.sh            render install-config.yaml, hand it to the bastion,
#                             wait for the cluster, fetch the kubeconfig
#   lab-install.sh destroy    put the install/destroy marker, wait for status
#                             "destroyed" (the caller then runs terraform destroy)
#
# Environment:
#   PULL_SECRET_FILE      path (inside the container) to the Red Hat pull secret JSON. Required.
#   BASE_DOMAIN           Route 53 base domain. Default: the single public hosted zone.
#   SSH_PUBLIC_KEY_FILE   optional public key file. Default: a fresh key pair; only the public half is used.
#   INSTALL_TIMEOUT_MIN   default 120 (estimate: an install takes roughly 45 to 70 minutes)
#   DESTROY_TIMEOUT_MIN   default 60
#   LAB_POLL_SECONDS      default 30
#   LAB_WORKSPACE_DIR     default /workspace (kubeconfig goes to $LAB_WORKSPACE_DIR/.lab/kubeconfig)
#
# Exit codes: 0 ok, 1 failure, 2 bad setup or input, 3 timeout, 4 lab is paused (no bastion).
# The pull secret is read from the file, never echoed, never put on a command line
# and never written anywhere except the temporary install-config.yaml (mode 600),
# which is deleted on exit and uploaded to the encrypted artifacts bucket.
# Nothing here has run on AWS (unverified).
set -euo pipefail
umask 077
shopt -u patsub_replacement 2>/dev/null || true

MODE="${1:-up}"
case "$MODE" in up | destroy) ;; *) echo "usage: lab-install.sh [up|destroy]" >&2; exit 2 ;; esac

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TF_DIR="$(dirname "$SCRIPT_DIR")"
TEMPLATE="$TF_DIR/templates/install-config.yaml.tpl"
WORKSPACE_DIR="${LAB_WORKSPACE_DIR:-/workspace}"
POLL="${LAB_POLL_SECONDS:-30}"
INSTALL_TIMEOUT_MIN="${INSTALL_TIMEOUT_MIN:-120}"
DESTROY_TIMEOUT_MIN="${DESTROY_TIMEOUT_MIN:-60}"
PROGRESS_EVERY=300 # seconds between progress lines

say() { printf '%s\n' "$*"; }
fail() { local code="$1"; shift; printf 'ERROR: %s\n' "$*" >&2; exit "$code"; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

for tool in aws jq terraform; do
  command -v "$tool" >/dev/null 2>&1 || fail 2 "$tool is not installed in this environment."
done

# ---- Terraform outputs ----
if ! OUT_JSON="$(terraform -chdir="$TF_DIR" output -json 2>"$TMP/tf.err")"; then
  if [ "$MODE" = destroy ]; then
    say "No readable Terraform outputs (lab infrastructure not built?). Skipping cluster destroy."
    exit 0
  fi
  fail 2 "Could not read Terraform outputs. Has 'lab up' built the infrastructure? $(tr '\n' ' ' <"$TMP/tf.err")"
fi
tfout() { printf '%s' "$OUT_JSON" | jq -r --arg k "$1" '.[$k].value // empty'; }

BUCKET="$(tfout artifacts_bucket)"
REGION="$(tfout aws_region)"
BASTION_ID="$(tfout bastion_instance_id)"
if [ -z "$BUCKET" ] || [ -z "$REGION" ]; then
  if [ "$MODE" = destroy ]; then
    say "No artifacts bucket in Terraform outputs. Skipping cluster destroy."
    exit 0
  fi
  fail 2 "Terraform outputs lack artifacts_bucket or aws_region."
fi
export AWS_DEFAULT_REGION="$REGION"
S3="s3://$BUCKET/install"

# Stops 'lab down' before Terraform when cluster resources are still in the lab VPC. Terraform knows
# nothing about them (the installer created them), so its VPC delete would fail or hang. This happens
# when the installer's metadata was lost, so 'destroy cluster' had nothing to read.
leak_check() {
  local vpc left
  vpc="$(tfout vpc_id)"
  [ -n "$vpc" ] || return 0
  left="$( {
    aws ec2 describe-instances --filters "Name=vpc-id,Values=$vpc" "Name=instance-state-name,Values=pending,running,stopping,stopped"       --query "Reservations[].Instances[?InstanceId!='${BASTION_ID:-none}'].InstanceId" --output text
    aws elbv2 describe-load-balancers --query "LoadBalancers[?VpcId=='$vpc'].LoadBalancerName" --output text
  } 2>/dev/null | tr -s '[:space:]' ' ')"
  [ -z "${left// /}" ] && return 0
  fail 5 "Cluster resources are still in the lab VPC ($vpc): $left. The installer could not destroy them (its metadata was not saved). Terraform destroy was NOT run. Remove these resources, then run 'lab down' again."
}

read_status() {
  local out
  if out="$(aws s3 cp "$S3/status" - 2>&1)"; then
    printf '%s' "$out" | tr -d '[:space:]'
    return 0
  fi
  case "$out" in
    *404* | *NoSuchKey* | *"Not Found"*) return 0 ;; # no status yet
  esac
  printf 'ERROR: could not read install/status: %s\n' "$out" >&2
  return 1
}

ssm_hint() {
  if [ -n "$BASTION_ID" ]; then
    say "Stream the bastion log (separate terminal):"
    say "  aws ssm start-session --target $BASTION_ID --region $REGION --document-name AWS-StartInteractiveCommand --parameters command=\"tail -n +1 -F /var/log/lab-install.log\""
  fi
}

elapsed_min() { echo $(( ($(date +%s) - $1) / 60 )); }

# ---------------------------------------------------------------- destroy ----
if [ "$MODE" = destroy ]; then
  STATUS="$(read_status)" || exit 1
  case "$STATUS" in
    "") say "No cluster install was ever started in this lab. Nothing to destroy before Terraform."; leak_check; exit 0 ;;
    destroyed) say "Cluster already destroyed (status: destroyed)."; leak_check; exit 0 ;;
  esac
  [ -n "$BASTION_ID" ] || fail 4 "The lab is paused (no bastion), so the cluster cannot be destroyed cleanly. Run 'lab resume', wait for it to finish, then run 'lab down' again."
  say "Cluster status is '$STATUS'. Asking the bastion to destroy the cluster (marker install/destroy)."
  # A failed earlier destroy leaves its status behind; clear it so the wait below sees only the new attempt.
  case "$STATUS" in destroy-failed*) printf 'destroying\n' | aws s3 cp - "$S3/status" --sse aws:kms >/dev/null ;; esac
  printf 'destroy\n' | aws s3 cp - "$S3/destroy" --sse aws:kms >/dev/null
  ssm_hint
  START="$(date +%s)"
  LAST="$START"
  while true; do
    STATUS="$(read_status)" || exit 1
    if [ "$STATUS" = destroyed ]; then
      say "Cluster destroyed."
      leak_check
      exit 0
    fi
    case "$STATUS" in
      destroy-failed*) fail 6 "The bastion could not destroy the cluster (status '$STATUS'). Terraform destroy was NOT run. Read the bastion log, fix the cause or remove the cluster's resources by hand, then run 'lab down' again. $(ssm_hint)" ;;
    esac
    if [ $(( $(date +%s) - START )) -ge $(( DESTROY_TIMEOUT_MIN * 60 )) ]; then
      fail 3 "Cluster destroy did not finish within $DESTROY_TIMEOUT_MIN minutes (status: '$STATUS'). The marker is still in place, so the bastion keeps working. Run 'lab down' again to keep waiting. Terraform destroy was NOT run. If an install was still running, the destroy starts only after it ends."
    fi
    if [ $(( $(date +%s) - LAST )) -ge "$PROGRESS_EVERY" ]; then
      say "  still destroying the cluster ($(elapsed_min "$START") min elapsed, status '$STATUS')"
      LAST="$(date +%s)"
    fi
    sleep "$POLL"
  done
fi

# --------------------------------------------------------------------- up ----
[ -f "$TEMPLATE" ] || fail 2 "Template not found: $TEMPLATE"
KMS_KEY_ARN="$(tfout kms_key_arn)"
PUBLIC_SUBNET_ID="$(tfout public_subnet_id)"
PRIVATE_SUBNET_ID="$(tfout private_subnet_id)"
EXTRA_SG_ID="$(tfout extra_security_group_id)"
CLUSTER_NAME="$(tfout cluster_name)"
LAB_ID="$(tfout lab_id)"
DESTROY_AFTER="$(tfout destroy_after)"
INSTANCE_TYPE="$(tfout instance_type)"
for pair in kms_key_arn:"$KMS_KEY_ARN" public_subnet_id:"$PUBLIC_SUBNET_ID" private_subnet_id:"$PRIVATE_SUBNET_ID" \
  extra_security_group_id:"$EXTRA_SG_ID" cluster_name:"$CLUSTER_NAME" lab_id:"$LAB_ID" \
  destroy_after:"$DESTROY_AFTER" instance_type:"$INSTANCE_TYPE"; do
  [ -n "${pair#*:}" ] || fail 2 "Terraform output '${pair%%:*}' is empty. Re-run 'terraform apply' (lab up) first."
done
[ -n "$BASTION_ID" ] || fail 4 "The lab is paused (no bastion). Run 'lab resume' first."

# Idempotence: look at the status before touching anything.
STATUS="$(read_status)" || exit 1
KUBECONFIG_OUT="$WORKSPACE_DIR/.lab/kubeconfig"
fetch_kubeconfig() {
  mkdir -p "$WORKSPACE_DIR/.lab"
  aws s3 cp "$S3/auth/kubeconfig" "$TMP/kubeconfig" >/dev/null || fail 1 "Could not fetch install/auth/kubeconfig from the artifacts bucket."
  install -m 600 "$TMP/kubeconfig" "$KUBECONFIG_OUT"
  chmod 600 "$KUBECONFIG_OUT" 2>/dev/null || true
  say "Kubeconfig saved to $KUBECONFIG_OUT (mode 600; on Windows the host may not enforce the mode)."
  say "The kubeadmin password stays in s3://$BUCKET/install/auth/kubeadmin-password (it is not downloaded)."
}
case "$STATUS" in
  complete)
    say "Cluster install already complete; skipping."
    [ -s "$KUBECONFIG_OUT" ] || fetch_kubeconfig
    exit 0 ;;
  failed:*)
    fail 1 "A previous install ended with status '$STATUS'. Read the bastion log, then run 'lab down' and 'lab up' to start clean. $(ssm_hint)" ;;
  installing)
    say "An install is already running on the bastion; waiting for it." ;;
  "" | destroyed) ;;
  *) fail 1 "Unexpected install status '$STATUS'." ;;
esac

if [ "$STATUS" != installing ]; then
  # --- inputs ---
  [ -n "${PULL_SECRET_FILE:-}" ] || fail 2 "PULL_SECRET_FILE is not set. Download your Red Hat pull secret, save it under your lab workspace, and set PULL_SECRET_FILE to it before 'lab up'."
  [ -f "$PULL_SECRET_FILE" ] || fail 2 "PULL_SECRET_FILE does not point to a readable file inside the tools container (set it to a file under your lab workspace)."
  PULL_SECRET="$(jq -c . "$PULL_SECRET_FILE" 2>/dev/null)" || fail 2 "The pull secret file is not valid JSON."
  printf '%s' "$PULL_SECRET" | jq -e '.auths | type == "object"' >/dev/null 2>&1 || fail 2 "The pull secret file has no 'auths' object; it does not look like a Red Hat pull secret."
  case "$PULL_SECRET" in *"'"*) fail 2 "The pull secret contains a single quote, which this script cannot embed safely." ;; esac

  if [ -n "${SSH_PUBLIC_KEY_FILE:-}" ]; then
    [ -f "$SSH_PUBLIC_KEY_FILE" ] || fail 2 "SSH_PUBLIC_KEY_FILE does not point to a readable file inside the tools container."
    SSH_KEY="$(head -n1 "$SSH_PUBLIC_KEY_FILE")"
  else
    command -v ssh-keygen >/dev/null 2>&1 || fail 2 "ssh-keygen is not installed; set SSH_PUBLIC_KEY_FILE instead."
    # ecdsa, not ed25519: the installer rejects ed25519 keys when FIPS is enabled.
    ssh-keygen -q -t ecdsa -b 256 -N '' -C "lab-$LAB_ID" -f "$TMP/node_key" >/dev/null
    SSH_KEY="$(cat "$TMP/node_key.pub")"
    # The private half is discarded on purpose: nodes are reached through 'oc debug', not ssh.
  fi
  case "$SSH_KEY" in ssh-* | ecdsa-*) ;; *) fail 2 "The SSH public key does not look like an OpenSSH public key." ;; esac

  if [ -n "${BASE_DOMAIN:-}" ]; then
    DOMAIN="$BASE_DOMAIN"
  else
    ZONES="$(aws route53 list-hosted-zones --output json | jq -r '.HostedZones[] | select(.Config.PrivateZone == false) | .Name | sub("\\.$"; "")')" || fail 2 "Could not list Route 53 hosted zones."
    COUNT="$(printf '%s\n' "$ZONES" | grep -c . || true)"
    case "$COUNT" in
      1) DOMAIN="$ZONES" ;;
      0) fail 2 "No public Route 53 hosted zone found. Create one for your base domain, or set BASE_DOMAIN." ;;
      *) fail 2 "More than one public hosted zone found ($(printf '%s' "$ZONES" | tr '\n' ' ')). Set BASE_DOMAIN to the one to use." ;;
    esac
  fi
  printf '%s' "$DOMAIN" | grep -Eq '^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$' || fail 2 "BASE_DOMAIN '$DOMAIN' is not a valid lowercase domain name."

  # --- render ---
  for value in "$DOMAIN" "$CLUSTER_NAME" "$INSTANCE_TYPE" "$KMS_KEY_ARN" "$EXTRA_SG_ID" "$REGION" "$PUBLIC_SUBNET_ID" "$PRIVATE_SUBNET_ID" "$LAB_ID" "$DESTROY_AFTER"; do
    printf '%s' "$value" | grep -Eq '^[A-Za-z0-9._:/-]+$' || fail 2 "A rendered value contains unexpected characters; refusing to build install-config.yaml."
  done
  CONFIG="$(cat "$TEMPLATE")"
  CONFIG="${CONFIG//__BASE_DOMAIN__/$DOMAIN}"
  CONFIG="${CONFIG//__CLUSTER_NAME__/$CLUSTER_NAME}"
  CONFIG="${CONFIG//__INSTANCE_TYPE__/$INSTANCE_TYPE}"
  CONFIG="${CONFIG//__KMS_KEY_ARN__/$KMS_KEY_ARN}"
  CONFIG="${CONFIG//__EXTRA_SECURITY_GROUP_ID__/$EXTRA_SG_ID}"
  CONFIG="${CONFIG//__AWS_REGION__/$REGION}"
  CONFIG="${CONFIG//__PUBLIC_SUBNET_ID__/$PUBLIC_SUBNET_ID}"
  CONFIG="${CONFIG//__PRIVATE_SUBNET_ID__/$PRIVATE_SUBNET_ID}"
  CONFIG="${CONFIG//__LAB_ID__/$LAB_ID}"
  CONFIG="${CONFIG//__DESTROY_AFTER__/$DESTROY_AFTER}"
  if printf '%s' "$CONFIG" | grep -Eq '__[A-Z_]+__'; then
    fail 2 "The template still has an unfilled placeholder; refusing to upload."
  fi
  {
    printf '%s\n' "$CONFIG"
    printf 'sshKey: %s\n' "$SSH_KEY"
    # The bastion extracts the pull secret from this exact single-line form.
    printf "pullSecret: '%s'\n" "$PULL_SECRET"
  } >"$TMP/install-config.yaml"
  chmod 600 "$TMP/install-config.yaml"

  say "Rendered install-config.yaml: cluster $CLUSTER_NAME.$DOMAIN, $INSTANCE_TYPE, region $REGION (pull secret not shown)."
  aws s3 cp "$TMP/install-config.yaml" "$S3/install-config.yaml" --sse aws:kms --sse-kms-key-id "$KMS_KEY_ARN" >/dev/null \
    || fail 1 "Upload of install-config.yaml failed. Check your AWS permissions on the artifacts bucket and the lab KMS key."
  rm -f "$TMP/install-config.yaml"
  say "Uploaded to s3://$BUCKET/install/install-config.yaml (SSE-KMS). The bastion deletes it once read."
fi

ssm_hint
say "Waiting for the cluster (timeout $INSTALL_TIMEOUT_MIN min; an install usually takes about 45 to 70 minutes, an estimate)."
START="$(date +%s)"
LAST="$START"
while true; do
  STATUS="$(read_status)" || exit 1
  case "$STATUS" in
    complete)
      say "Cluster install complete after $(elapsed_min "$START") min of waiting."
      fetch_kubeconfig
      exit 0 ;;
    failed:*)
      fail 1 "The install failed (status '$STATUS'). Read the bastion log, then run 'lab down' and try again. $(ssm_hint)" ;;
  esac
  if [ $(( $(date +%s) - START )) -ge $(( INSTALL_TIMEOUT_MIN * 60 )) ]; then
    if [ -z "$STATUS" ]; then
      fail 3 "Timed out after $INSTALL_TIMEOUT_MIN minutes and the bastion never started the install (no status). Check that the bastion is online in Systems Manager and read /var/log/lab-bootstrap.log on it. Run 'lab up' again to keep waiting."
    fi
    fail 3 "Timed out after $INSTALL_TIMEOUT_MIN minutes (status '$STATUS'). The install may still be running. Run 'lab up' again to keep waiting, or 'lab down' to stop."
  fi
  if [ $(( $(date +%s) - LAST )) -ge "$PROGRESS_EVERY" ]; then
    if [ -z "$STATUS" ]; then
      say "  waiting for the bastion to pick up the config ($(elapsed_min "$START") min; it reboots once into FIPS mode first)"
    else
      say "  install running ($(elapsed_min "$START") min elapsed, status '$STATUS')"
    fi
    LAST="$(date +%s)"
  fi
  sleep "$POLL"
done
