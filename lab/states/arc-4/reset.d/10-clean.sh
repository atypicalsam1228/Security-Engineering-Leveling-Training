#!/usr/bin/env bash
# Removes both ARC-4 namespaces so lab reset starts clean. The mesh itself is left alone.
set -euo pipefail
oc delete namespace arc-a arc-b --ignore-not-found --wait=true
