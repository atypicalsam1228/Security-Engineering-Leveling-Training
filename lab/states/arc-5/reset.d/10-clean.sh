#!/usr/bin/env bash
# Removes everything ARC-5 created so lab reset starts clean.
set -euo pipefail
oc delete namespace arc-ref --ignore-not-found --wait=true
oc delete clusterpolicy arc-ref-flows --ignore-not-found
