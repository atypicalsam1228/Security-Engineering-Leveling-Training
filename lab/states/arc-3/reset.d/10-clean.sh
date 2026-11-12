#!/usr/bin/env bash
# Removes everything ARC-3 created so lab reset starts clean.
set -euo pipefail
oc delete namespace arc-measure --ignore-not-found --wait=true
oc delete clusterpolicy arc-baseline --ignore-not-found
