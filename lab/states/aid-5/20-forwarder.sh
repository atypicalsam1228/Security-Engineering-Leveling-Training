#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Ensures the cluster audit log forwarder is running, so audit records reach Loki with log_type=audit.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_siem_forwarder tuned
