#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Puts the supplied files in the GRC-3 working folder: collect_a.py (the three checks the
# learner reads and runs in Step 2) and check-cronjob.py (the check the learner runs on their own CronJob in Step 5).
# Running it again replaces both files with the supplied versions and leaves everything else in the folder alone.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
work=/workspace/grc-3/evidence-work
mkdir -p "$work/evidence"
cp "$(dirname "$0")/kit/collect_a.py" "$work/collect_a.py"
cp "$(dirname "$0")/kit/check-cronjob.py" "$work/check-cronjob.py"
say "collect_a.py and check-cronjob.py are in $work"
