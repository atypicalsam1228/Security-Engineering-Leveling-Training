#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Waits (up to about 2 minutes) for Kyverno to write policy reports for the three grc- policies
# in demo, so Step 1 does not read an empty list on a fresh start. A timeout only prints a warning: Kyverno may need longer.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
say "Waiting for Kyverno to write the first policy reports for demo. This can take a couple of minutes on a fresh start. Read this module's Intent and Concepts while you wait."
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  count=$(oc get policyreports.wgpolicyk8s.io -n demo -o json 2>/dev/null | jq '[.items[].results[]? | select(.policy | startswith("grc-"))] | length' 2>/dev/null || echo 0)
  if [ "${count:-0}" -gt 0 ]; then say "policy reports are present ($count results)"; exit 0; fi
  sleep 10
done
say "WARNING: no policy reports yet. If Step 1 shows an empty list, wait a minute and run it again."
