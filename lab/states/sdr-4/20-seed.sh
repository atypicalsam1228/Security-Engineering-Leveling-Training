#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Pushes the incident records straight to Loki (they are for the timeline step, so they
# skip the learner's labeling stage), then creates ConfigMap sdr4-harness in siem: the test harness, the scenarios, the reference answer answer-secret-read.logql and
# the timeline check. The ConfigMap is created last and doubles as the "already seeded" marker. Each seeding labels its records
# seed_run=<anchor> (the anchor is in the ConfigMap); the module's searches pin to it, so records left from an earlier start are ignored.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env LOKI_URL LOKI_USER LOKI_PASSWORD LOKI_CA_FILE
here="$(cd "$(dirname "$0")" && pwd)"
ensure_namespace siem
if oc get configmap sdr4-harness -n siem >/dev/null 2>&1; then
  say "sdr4-harness already exists; incident records were seeded earlier"
  exit 0
fi
anchor=$(date +%s)
# The audit and Falco records name the real suspect pod created by 15-suspect.sh, so the containment step can find it.
# After a lab reset the old pod can still be listed as Terminating, so take the newest pod that is Running and not being deleted.
pod=""
for _ in $(seq 1 60); do
  pod=$(oc get pods -n demo -l app=suspect-app -o json 2>/dev/null     | jq -r '[.items[] | select(.status.phase == "Running" and (.metadata.deletionTimestamp == null))] | sort_by(.metadata.creationTimestamp) | last | .metadata.name // empty') || true
  [ -n "$pod" ] && break
  sleep 2
done
[ -n "$pod" ] || die "no Running pod with label app=suspect-app in namespace demo (15-suspect.sh creates it)"
(cd "$here" && python3 seed.py "$anchor" "$pod")
stage=$(mktemp -d)
cp "$here"/answer-secret-read.logql "$here"/detect_test.py "$here"/timeline_check.py "$here"/scenarios_sdr4.py "$here"/events_sdr4.py "$here"/evlib.py "$here"/lokilib.py "$here"/replay.py "$stage"/
echo "$anchor" > "$stage/anchor.txt"
oc create configmap sdr4-harness -n siem --from-file="$stage" --dry-run=client -o yaml | oc apply -f - >/dev/null
rm -rf "$stage"
say "created ConfigMap sdr4-harness"
