#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Pushes the exercise records to Loki, then creates ConfigMap sdr-review in siem
# (review gate and helpers; the learner extracts it with oc extract). The ConfigMap is created last and doubles
# as the "already seeded" marker, so a second run changes nothing.
# Each seeding labels its records seed_run=<anchor> (the anchor is in the ConfigMap); searches pin to it, so records left in Loki
# from an earlier start or reset are ignored.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env LOKI_URL LOKI_USER LOKI_PASSWORD LOKI_CA_FILE
here="$(cd "$(dirname "$0")" && pwd)"
ensure_namespace siem
if oc get configmap sdr-review -n siem >/dev/null 2>&1; then
  say "sdr-review already exists; exercise records were seeded earlier"
  exit 0
fi
anchor=$(date +%s)
(cd "$here" && python3 seed.py "$anchor")
stage=$(mktemp -d)
cp "$here"/review_gate.py "$here"/events_sdr3.py "$here"/evlib.py "$here"/lokilib.py "$here"/replay.py "$stage"/
echo "$anchor" > "$stage/anchor.txt"
oc create configmap sdr-review -n siem --from-file="$stage" --dry-run=client -o yaml | oc apply -f - >/dev/null
rm -rf "$stage"
say "created ConfigMap sdr-review"
