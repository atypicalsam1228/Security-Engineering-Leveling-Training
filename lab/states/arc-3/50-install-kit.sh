#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Copies the supplied kit to $HOME/arc. The learner writes measure.py; it is not supplied.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
mkdir -p "$HOME/arc/results"
cp -r "$(dirname "$0")/kit/." "$HOME/arc/"
rm -f "$HOME/arc/results/"*.json
oc delete clusterpolicy arc-baseline --ignore-not-found
say "kit copied to $HOME/arc; arc-measure has no policy (condition: none)"
