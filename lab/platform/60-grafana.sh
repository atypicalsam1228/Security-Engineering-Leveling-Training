#!/usr/bin/env bash
# Grafana OSS 13.2.4 in namespace siem: SQLite on a PVC, Loki data source named "Loki" provisioned from a file,
# unified alerting (on by default) with the provisioning API the SDR/AID modules call, edge-TLS Route.
#
# What the modules rely on (lab/states/_common/lib.sh grafana_get/grafana_send, sdr-3, sdr-5, aid-5):
#   - basic auth GRAFANA_USER / GRAFANA_PASSWORD against GRAFANA_URL (a Route host, trusted through the ingress CA).
#   - GET /api/datasources/name/Loki returns the data source uid.
#   - /api/v1/provisioning/{alert-rules,contact-points,policies}, /api/folders and /api/dashboards/db work as admin.
#   - alert rules use the classic_conditions expression (datasource uid -100), which Grafana 13 still supports.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

# Pin: contract (LAB-CONTRACT.md) fixes Grafana at 13.2.4. Verified to exist on Docker Hub: grafana/grafana tag 13.2.4,
# last updated 2026-10-13 (hub.docker.com/v2/repositories/grafana/grafana/tags/13.2.4); github.com/grafana/grafana
# release v13.2.4 is the 13 October 2026 release. A newer 13.3.0 exists but is deliberately not used.
GRAFANA_IMAGE="docker.io/grafana/grafana:13.2.4"
GRAFANA_PVC_SIZE="2Gi"

NS=siem
require_cluster
require_var GRAFANA_PASSWORD LOKI_CA_FILE
GRAFANA_USER="$(lab_var GRAFANA_USER)"
[ -n "$GRAFANA_USER" ] || GRAFANA_USER="admin"
lab_var_set GRAFANA_USER "$GRAFANA_USER"
ensure_namespace "$NS"

# The admin login is set from env on first start only; the check at the end repairs it if the stored password differs.
oc create secret generic grafana-admin -n "$NS" \
  --from-literal=user="$GRAFANA_USER" --from-literal=password="$GRAFANA_PASSWORD" \
  --dry-run=client -o yaml | oc apply -f - >/dev/null

# Route first so the root URL is known. Loki data source: in-cluster HTTP service, no auth needed there (Loki is single tenant).
oc apply -f - >/dev/null <<EOF
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: grafana
  namespace: ${NS}
spec:
  to:
    kind: Service
    name: grafana
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
---
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: ${NS}
spec:
  selector:
    app: grafana
  ports:
    - {name: http, port: 3000, targetPort: http}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: ${NS}
data:
  loki.yaml: |
    apiVersion: 1
    datasources:
      - name: Loki
        uid: loki
        type: loki
        access: proxy
        url: http://loki.${NS}.svc.cluster.local:3100
        isDefault: true
        editable: true
        jsonData:
          maxLines: 5000
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: grafana-data
  namespace: ${NS}
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: ${GRAFANA_PVC_SIZE}
EOF

GRAFANA_URL="https://$(route_host "$NS" grafana)"
lab_var_set GRAFANA_URL "$GRAFANA_URL"

# Env names: Grafana configuration docs (GF_<SECTION>_<KEY>). Plugin preinstall is off so the pod needs no internet.
oc apply -f - >/dev/null <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: ${NS}
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: grafana
          image: ${GRAFANA_IMAGE}
          env:
            - name: GF_SECURITY_ADMIN_USER
              valueFrom: {secretKeyRef: {name: grafana-admin, key: user}}
            - name: GF_SECURITY_ADMIN_PASSWORD
              valueFrom: {secretKeyRef: {name: grafana-admin, key: password}}
            - {name: GF_SERVER_ROOT_URL, value: "${GRAFANA_URL}"}
            - {name: GF_USERS_ALLOW_SIGN_UP, value: "false"}
            - {name: GF_ANALYTICS_REPORTING_ENABLED, value: "false"}
            - {name: GF_ANALYTICS_CHECK_FOR_UPDATES, value: "false"}
            - {name: GF_UNIFIED_ALERTING_ENABLED, value: "true"}
            - {name: GF_PLUGINS_PREINSTALL_DISABLED, value: "true"}
          ports:
            - name: http
              containerPort: 3000
          readinessProbe:
            httpGet: {path: /api/health, port: http}
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet: {path: /api/health, port: http}
            initialDelaySeconds: 60
            periodSeconds: 20
            failureThreshold: 6
          resources:
            requests: {cpu: 100m, memory: 256Mi}
            limits: {cpu: "1", memory: 1Gi}
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - {name: data, mountPath: /var/lib/grafana}
            - {name: datasources, mountPath: /etc/grafana/provisioning/datasources, readOnly: true}
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: grafana-data
        - name: datasources
          configMap:
            name: grafana-datasources
EOF
wait_rollout "$NS" deployment/grafana 600

# Calls through the Route use the ingress CA; credentials go through stdin so they are not in the process list.
grafana_route() { printf 'user = "%s:%s"\n' "$GRAFANA_USER" "$GRAFANA_PASSWORD" | curl -sS -K - --cacert "$LOKI_CA_FILE" "$@"; }
grafana_health() { curl -sS --cacert "$LOKI_CA_FILE" "$GRAFANA_URL/api/health" | jq -e '.database == "ok"'; }
wait_until "Grafana answers /api/health through the Route" 300 grafana_health
version="$(curl -sS --cacert "$LOKI_CA_FILE" "$GRAFANA_URL/api/health" | jq -r '.version')"
case "$version" in 13.2.4*) say "Grafana version $version" ;; *) die "Grafana reports version $version, expected 13.2.4" ;; esac

# Sign-in check. An old admin database keeps its old password, so reset it from the lab value when the login is refused.
auth_ok() { [ "$(grafana_route -o /dev/null -w '%{http_code}' "$GRAFANA_URL/api/org")" = 200 ]; }
if ! auth_ok; then
  say "admin login refused; resetting the admin password to the lab value"
  # Grafana CLI: grafana cli admin reset-admin-password --password-from-stdin (pkg/cmd/grafana-cli/commands/commands.go, v13.2.4)
  printf '%s' "$GRAFANA_PASSWORD" | oc exec -i -n "$NS" deployment/grafana -c grafana -- \
    grafana cli admin reset-admin-password --password-from-stdin >/dev/null || die "could not reset the Grafana admin password"
fi
wait_until "Grafana admin sign-in with GRAFANA_USER / GRAFANA_PASSWORD" 120 auth_ok

# The Loki data source must resolve by name, and the alerting provisioning API must answer.
loki_uid="$(grafana_route "$GRAFANA_URL/api/datasources/name/Loki" | jq -r '.uid // empty')"
[ -n "$loki_uid" ] || die "Grafana has no data source named Loki"
say "data source Loki has uid $loki_uid"
grafana_route "$GRAFANA_URL/api/v1/provisioning/alert-rules" | jq -e 'type == "array"' >/dev/null || die "Grafana alerting provisioning API did not answer"
say "alerting provisioning API answers"
say "Grafana: $GRAFANA_URL (user $GRAFANA_USER)"
