#!/usr/bin/env bash
# Removes everything ENG-1 created, so lab reset starts clean. The Route goes with the namespace.
set -euo pipefail
oc delete namespace net-lab --ignore-not-found --wait=true
