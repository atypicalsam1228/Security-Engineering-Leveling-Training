#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Seeds the Gitea repository vm-app (under GITEA_USER) used by the vulnerability
# management modules VM-2 to VM-5. Files are written only when they differ, so a second run changes nothing.
#   main:          old pinned packages in requirements.txt and a Dockerfile on an old base image.
#   deps-updated:  the same repository with newer package pins (the stand-in for a developer's fix).
# Package pins were chosen from memory of old releases that have published flaws. Confirm with trivy fs that main has
# findings with fixes and that deps-updated has fewer (see TODO.md).
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN

OLD_REQUIREMENTS='flask==0.12
pyyaml==5.3
requests==2.19.0
jinja2==2.10
urllib3==1.24.1'

NEW_REQUIREMENTS='flask==3.1.2
pyyaml==6.0.2
requests==2.32.5
jinja2==3.1.6
urllib3==2.5.0'

DOCKERFILE='FROM docker.io/library/nginx:1.16
COPY index.html /usr/share/nginx/html/index.html'

gitea_ensure_repo vm-app
gitea_put_file vm-app main requirements.txt "Add package pins" "$OLD_REQUIREMENTS"
gitea_put_file vm-app main Dockerfile "Add Dockerfile" "$DOCKERFILE"
gitea_put_file vm-app main index.html "Add home page" '<h1>vm-app</h1>'
gitea_ensure_branch vm-app deps-updated main
gitea_put_file vm-app deps-updated requirements.txt "Update package pins" "$NEW_REQUIREMENTS"
