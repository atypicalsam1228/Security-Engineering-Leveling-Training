#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. arc-a is plain; arc-b is labelled so new pods get a mesh sidecar.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_namespace arc-a
ensure_namespace arc-b
oc label namespace arc-b istio-injection=enabled --overwrite >/dev/null
