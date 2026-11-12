#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Copies the reference answer for the Step 5 writing exercise to
# /workspace/cps-3/reference. Only the reference folder is touched, never the learner's report-policy.json.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
mkdir -p /workspace/cps-3/reference
cp "$(dirname "$0")/reference/report-policy.reference.json" /workspace/cps-3/reference/report-policy.reference.json
say "reference answer is in /workspace/cps-3/reference (open it only after trying Step 5)"
