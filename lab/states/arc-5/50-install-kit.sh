#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Copies check_flows.py, drift_timer.py and flows-bad.txt to $HOME/arc.
# The learner writes flows.yaml, the two generators, the conformance test and its helper files.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
mkdir -p "$HOME/arc/generated"
cp -r "$(dirname "$0")/kit/." "$HOME/arc/"
say "kit copied to $HOME/arc"
