#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Creates the private Gitea repository detections and writes the starting files from
# the repo/ folder next to this script to branch main. A file is written only when its content differs, so a second run
# changes nothing. Uses the Gitea REST API through the helpers in ../_common/lib.sh.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN
here="$(cd "$(dirname "$0")" && pwd)"
gitea_ensure_repo detections
cd "$here/repo"
find . -type f | sort | while read -r file; do
  path="${file#./}"
  gitea_put_file detections main "$path" "seed $path" "$(cat "$file")"
done
# ci/task.yaml (plumbing the learner never changes) is kept as ci_src/task.yaml.tpl so the state loader does not read it as a manifest.
gitea_put_file detections main "ci/task.yaml" "seed ci/task.yaml" "$(cat "$here/ci_src/task.yaml.tpl")"
say "repository detections holds the starting files"
