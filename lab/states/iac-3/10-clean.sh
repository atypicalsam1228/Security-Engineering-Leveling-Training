#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Starts from nothing, so the module works whether or not IAC-1 or IAC-2 ran:
# the same removal that lab reset runs, applied at every start.
set -euo pipefail
exec bash "$(dirname "$0")/reset.d/10-remove-iac-3-work.sh"
