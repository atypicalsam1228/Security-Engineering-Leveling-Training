#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Creates the secrets the detections pipeline reads in namespace build, from the lab
# variables, so no password is typed or saved by the learner. detections-ci holds environment values; detections-ci-ca
# holds the certificate authority file. The addresses are the ones lab shell uses; if the pipeline pods need different
# in-cluster addresses, see TODO.md.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN GRAFANA_URL GRAFANA_USER GRAFANA_PASSWORD LOKI_URL LOKI_USER LOKI_PASSWORD LOKI_CA_FILE
ensure_namespace build
oc create secret generic detections-ci -n build \
  --from-literal=GITEA_URL="$GITEA_URL" --from-literal=GITEA_USER="$GITEA_USER" --from-literal=GITEA_TOKEN="$GITEA_TOKEN" \
  --from-literal=GRAFANA_URL="$GRAFANA_URL" --from-literal=GRAFANA_USER="$GRAFANA_USER" --from-literal=GRAFANA_PASSWORD="$GRAFANA_PASSWORD" \
  --from-literal=LOKI_URL="$LOKI_URL" --from-literal=LOKI_USER="$LOKI_USER" --from-literal=LOKI_PASSWORD="$LOKI_PASSWORD" \
  --dry-run=client -o yaml | oc apply -f - >/dev/null
oc create secret generic detections-ci-ca -n build --from-file=ca.crt="$LOKI_CA_FILE" --dry-run=client -o yaml | oc apply -f - >/dev/null
say "secrets detections-ci and detections-ci-ca are in namespace build"
