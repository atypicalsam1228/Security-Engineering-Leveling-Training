#!/usr/bin/env bash
# Usage: set_mode.sh none|audit|enforce
# Puts arc-measure into one condition: removes the load pods, then removes or applies the arc-baseline policy.
set -euo pipefail
mode=${1:-}
dir="$(cd "$(dirname "$0")" && pwd)"
case "$mode" in
  none)
    oc delete deployment load -n arc-measure --ignore-not-found --wait=true
    oc delete clusterpolicy arc-baseline --ignore-not-found
    ;;
  audit | enforce)
    oc delete deployment load -n arc-measure --ignore-not-found --wait=true
    oc apply -f "$dir/policies/baseline-$mode.yaml"
    oc wait clusterpolicy/arc-baseline --for=condition=Ready --timeout=120s
    ;;
  *)
    echo "usage: set_mode.sh none|audit|enforce" >&2
    exit 2
    ;;
esac
sleep 15
echo "mode is now: $mode"
