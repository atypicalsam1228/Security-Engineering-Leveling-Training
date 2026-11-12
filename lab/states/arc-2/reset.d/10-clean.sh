#!/usr/bin/env bash
# Removes everything ARC-2 created, so lab reset starts clean.
set -euo pipefail
oc delete namespace arc-lab --ignore-not-found --wait=true
oc delete clusterpolicy arc-require-nonroot arc-disallow-latest --ignore-not-found
