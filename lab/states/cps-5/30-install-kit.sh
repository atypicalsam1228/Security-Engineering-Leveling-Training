#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Copies the supplied files into the learner's module folder /workspace/cps-5:
# kyverno-rbac.yaml (Step 3, read and apply), check-registry.py (Step 4, local check of the registry rule) and
# reference/validate-images-answer.yaml (the finished registry rule, opened only after the learner has tried).
# It never touches validate-images.yaml or any other file the learner makes, so running lab start again keeps their work.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
here="$(dirname "$0")/kit"
mkdir -p /workspace/cps-5/reference
cp "$here/kyverno-rbac.yaml" "$here/check-registry.py" /workspace/cps-5/
cp "$here/validate-images-answer.tpl" /workspace/cps-5/reference/validate-images-answer.yaml
python3 /workspace/cps-5/check-registry.py /workspace/cps-5/reference/validate-images-answer.yaml >/dev/null ||
  die "the reference registry rule does not pass its own check"
say "kyverno-rbac.yaml, check-registry.py and reference/ are in /workspace/cps-5"
