#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Puts the reference answer for the role the learner writes in Step 2 at
# /workspace/iac-2/answers/access.answer.tf. It is outside the repository folder, so it is never committed and
# terraform never reads it. The module tells the learner to open it only after trying.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
REF="$(cd "$(dirname "$0")" && pwd)/ref"
mkdir -p /workspace/iac-2/answers
cp "$REF/access.answer.tf" /workspace/iac-2/answers/access.answer.tf
say "reference answer is in /workspace/iac-2/answers"
