#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Pushes the exercise records to Loki, posts the alert messages to
# Mattermost, then creates ConfigMap sdr-runbook in siem (the learner extracts it with oc extract).
# The ConfigMap is created last and doubles as the "already seeded" marker, so a second run changes nothing.
# Each seeding labels its records seed_run=<anchor> (the anchor is in the ConfigMap); searches pin to it, so records left in Loki
# from an earlier start or reset are ignored.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env LOKI_URL LOKI_USER LOKI_PASSWORD LOKI_CA_FILE MM_WEBHOOK_URL
here="$(cd "$(dirname "$0")" && pwd)"
ensure_namespace siem
if oc get configmap sdr-runbook -n siem >/dev/null 2>&1; then
  say "sdr-runbook already exists; exercise records were seeded earlier"
  exit 0
fi
anchor=$(date +%s)
(cd "$here" && python3 seed.py "$anchor")
stage=$(mktemp -d)
cp "$here"/runbook/* "$stage"/
echo "$anchor" > "$stage/anchor.txt"
oc create configmap sdr-runbook -n siem --from-file="$stage" --dry-run=client -o yaml | oc apply -f - >/dev/null
rm -rf "$stage"
say "created ConfigMap sdr-runbook"
