#!/usr/bin/env bash
# Idempotent: private Gitea repository eng-sandbox with README.md, broken.yaml and health-check.sh on main.
# health-check.sh is the one platform health script the learner reads and runs; it needs only oc and jq.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN

REPO=eng-sandbox

README=$(cat <<'EOT'
# eng-sandbox

A practice repository for the foundation module. Change it freely.

Files:
- health-check.sh: prints one line per platform tool and says UP or DOWN.
- broken.yaml: a settings file with a deliberate indent mistake to find and fix.
EOT
)

BROKEN=$(cat <<'EOT'
apiVersion: v1
kind: ConfigMap
metadata:
  name: eng-sandbox-note
  namespace: demo
 data:
  greeting: hello
EOT
)

HEALTH=$(cat <<'EOT'
#!/usr/bin/env bash
# Platform health check: prints one line per tool, exits 1 if any tool is down.
set -u
down=0

report() { # report STATE NAME NAMESPACE DETAIL
  printf '%-5s %-17s %-20s %s\n' "$1" "$2" "$3" "$4"
  [ "$1" = UP ] || down=$((down + 1))
}

check() { # check NAME NAMESPACE POD-NAME-PATTERN
  local name=$1 ns=$2 pattern=$3 counts total notready
  counts=$(oc get pods -n "$ns" -o json 2>/dev/null | jq -r --arg p "$pattern" '
    [.items[] | select(.metadata.name | test($p)) | select(.status.phase != "Succeeded")]
    | "\(length) \(map(select(.status.phase != "Running" or ((.status.containerStatuses // []) | all(.[]; .ready) | not))) | length)"')
  if [ -z "$counts" ]; then
    report DOWN "$name" "$ns" "namespace cannot be read"
    return
  fi
  read -r total notready <<< "$counts"
  if [ "$total" -eq 0 ]; then
    report DOWN "$name" "$ns" "no pods found"
  elif [ "$notready" -gt 0 ]; then
    report DOWN "$name" "$ns" "$notready of $total pods not ready"
  else
    report UP "$name" "$ns" "$total pods ready"
  fi
}

check "Loki" siem "loki"
check "Grafana" siem "grafana"
check "Mattermost" chat "."
check "Gitea" gitea "."
check "Tekton pipelines" openshift-pipelines "tekton-pipelines"
check "Kyverno" kyverno "."
check "Trivy operator" security-tools "trivy"
check "Falco" security-tools "falco"
check "Collector" openshift-logging "siem-forwarder|collector"
check "Sample app" demo "demo-app"

if [ "$down" -eq 0 ]; then
  echo "All tools up."
else
  echo "$down tool(s) down."
  exit 1
fi
EOT
)

gitea_ensure_repo "$REPO"
gitea_put_file "$REPO" main README.md "Describe the sandbox" "$README"
gitea_put_file "$REPO" main broken.yaml "Add the practice settings file" "$BROKEN"
gitea_put_file "$REPO" main health-check.sh "Add the platform health check" "$HEALTH"
