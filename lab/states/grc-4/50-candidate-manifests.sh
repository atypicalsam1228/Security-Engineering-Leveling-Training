#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Config map candidate-manifests in build: good.yaml (pinned tag) and
# bad.yaml (tag latest). The cluster never creates either; the pipeline only dry-runs them.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_namespace build
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/good.yaml" <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: candidate-app
spec:
  replicas: 1
  selector:
    matchLabels: {app: candidate-app}
  template:
    metadata:
      labels: {app: candidate-app}
    spec:
      containers:
        - name: app
          image: registry.access.redhat.com/ubi9/ubi-minimal:9.4
          command: ["sleep", "3600"]
YAML
sed 's#ubi-minimal:9.4#ubi-minimal:latest#' "$tmp/good.yaml" > "$tmp/bad.yaml"
oc create configmap candidate-manifests -n build --from-file="$tmp/good.yaml" --from-file="$tmp/bad.yaml" \
  --dry-run=client -o yaml | oc apply -f - >/dev/null
say "config map candidate-manifests applied"
