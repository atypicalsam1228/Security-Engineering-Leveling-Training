#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Copies latency.py and netpol.yaml (the network policies both designs share) to $HOME/arc. The learner writes mesh.yaml, cases.json, harness.py and the two design files.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
mkdir -p "$HOME/arc"
cp "$(dirname "$0")/kit/latency.py" "$HOME/arc/latency.py"
cp "$(dirname "$0")/kit/netpol.yaml" "$HOME/arc/netpol.yaml"
say "latency.py and netpol.yaml are in $HOME/arc"
