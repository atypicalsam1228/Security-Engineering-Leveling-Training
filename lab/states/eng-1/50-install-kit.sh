#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Copies break.yaml (two deliberate mistakes) and allow-client.yaml (the correct allow rule) to $HOME/net. The learner writes hop_check.py.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
mkdir -p "$HOME/net"
cp "$(dirname "$0")/kit/break.yaml" "$HOME/net/break.yaml"
cp "$(dirname "$0")/kit/allow-client.yaml" "$HOME/net/allow-client.yaml"
say "break.yaml and allow-client.yaml are in $HOME/net"
