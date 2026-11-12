#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. The telemetry-path check in SDR-2 reads the real collector, so the
# log collector (service account, read roles) and the log forwarder to Loki must exist. Created only if missing.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_siem_forwarder
