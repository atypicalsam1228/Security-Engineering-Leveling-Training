#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Puts the reference answer for the pod-exec rule exercise in the learner's work area
# (/workspace/sdr-5/reference/pod-exec.json, outside the repository clone). Outside the lab shell /workspace does not exist, so
# nothing is copied. Safe to run again: the file is simply overwritten.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
here="$(cd "$(dirname "$0")" && pwd)"
if [ -d /workspace ]; then
  mkdir -p /workspace/sdr-5/reference
  cp "$here/reference/pod-exec.json" /workspace/sdr-5/reference/pod-exec.json
  say "reference answer placed in /workspace/sdr-5/reference (open it only after you have tried the exercise)"
fi
