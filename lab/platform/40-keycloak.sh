#!/usr/bin/env bash
# Keycloak (in-lab sign-in service) in namespace keycloak: one pod in dev mode with the embedded H2 file database on a
# PVC, edge-TLS Route. Admin user = KEYCLOAK_ADMIN_USER / KEYCLOAK_ADMIN_PASSWORD (from lab up). Creates realm "lab".
# Sign-in events are logged at INFO, as LAB-CONTRACT.md and the SDR modules require.
# Saves KEYCLOAK_URL and KEYCLOAK_ADMIN_USER. Safe to repeat.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

NS=keycloak
# Pin: Keycloak 26.8.1 (LAB-CONTRACT.md). Checked 2026-11-02: quay.io/keycloak/keycloak tag 26.8.1 exists
# (Quay tag API: multi-arch manifest list, last modified 2026-10-31; registry /v2 manifest request answers HTTP 200).
KEYCLOAK_IMAGE="${KEYCLOAK_IMAGE:-quay.io/keycloak/keycloak:26.8.1}"
REALM="lab"          # the module log lines carry realmId="lab", so the realm id is set to "lab" as well

require_var KEYCLOAK_ADMIN_PASSWORD LOKI_CA_FILE
CA="$(lab_var LOKI_CA_FILE)"
ADMIN_USER="$(lab_var KEYCLOAK_ADMIN_USER)"
ADMIN_USER="${ADMIN_USER:-admin}"

ensure_namespace "$NS"
# The password reaches the pod only through a Secret.
oc create secret generic keycloak-admin -n "$NS" --from-literal=username="$ADMIN_USER" \
  --from-literal=password="$(lab_var KEYCLOAK_ADMIN_PASSWORD)" --dry-run=client -o yaml | oc apply -f - >/dev/null

oc apply -n "$NS" -f - >/dev/null <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: keycloak-data
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 2Gi
---
apiVersion: v1
kind: Service
metadata:
  name: keycloak
  labels:
    app: keycloak
spec:
  selector:
    app: keycloak
  ports:
    - name: http
      port: 8080
      targetPort: http
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: keycloak
  labels:
    app: keycloak
spec:
  to:
    kind: Service
    name: keycloak
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
EOF
route_has_host() { [ -n "$(route_host "$NS" keycloak 2>/dev/null)" ]; }
wait_until "route keycloak to get a host name" 60 route_has_host
HOST="$(route_host "$NS" keycloak)"
KEYCLOAK_URL_VALUE="https://${HOST}"

# Settings (names from the Keycloak 26.8.1 guides: server/containers, server/reverseproxy, server/management-interface):
#  - start-dev: embedded H2 file database (dev-file) under /opt/keycloak/data, plain HTTP on 8080; TLS ends at the Route.
#  - KC_PROXY_HEADERS=xforwarded and KC_HOSTNAME (full URL) make Keycloak build links with the Route's https address.
#  - KC_HEALTH_ENABLED serves /health/ready on the management port 9000.
#  - Sign-in events: the jboss-logging event listener logs successes at "debug" by default (success-level default in
#    JBossLoggingEventListenerProviderFactory.java at 26.8.1) and failures at "warn". The SPI option
#    spi-events-listener--jboss-logging--success-level=info, set here as the environment variable
#    KC_SPI_EVENTS_LISTENER__JBOSS_LOGGING__SUCCESS_LEVEL, makes LOGIN lines appear at INFO next to LOGIN_ERROR at WARN.
#    The root log level stays INFO so those lines reach the console, where the collector reads them.
#  - FIPS: on a FIPS host the Keycloak image puts its OpenJDK in FIPS mode automatically (Keycloak guide server/fips).
#    A real FIPS-mode Keycloak needs the BouncyCastle FIPS jars in a custom image, which the lab does not build. The lab
#    Keycloak is a log source for exercises and holds no real secrets, so the JVM opts out of the host FIPS integration with
#    -Dcom.redhat.fips=false (Red Hat OpenJDK system property, documented in the OpenJDK release notes "Disabling FIPS mode").
# The image runs as UID 1000, group 0. restricted-v2 assigns a random UID with group 0; the PVC gets the pod fsGroup.
oc apply -n "$NS" -f - >/dev/null <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: keycloak
  labels:
    app: keycloak
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: keycloak
  template:
    metadata:
      labels:
        app: keycloak
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: keycloak
          image: ${KEYCLOAK_IMAGE}
          args: [start-dev]
          ports:
            - { name: http, containerPort: 8080 }
            - { name: management, containerPort: 9000 }
          env:
            - name: KC_BOOTSTRAP_ADMIN_USERNAME
              valueFrom:
                secretKeyRef: { name: keycloak-admin, key: username }
            - name: KC_BOOTSTRAP_ADMIN_PASSWORD
              valueFrom:
                secretKeyRef: { name: keycloak-admin, key: password }
            - { name: KC_HTTP_ENABLED, value: "true" }
            - { name: KC_PROXY_HEADERS, value: xforwarded }
            - { name: KC_HOSTNAME, value: "${KEYCLOAK_URL_VALUE}" }
            - { name: KC_HEALTH_ENABLED, value: "true" }
            - { name: KC_LOG, value: console }
            - { name: KC_LOG_LEVEL, value: INFO }
            - { name: KC_SPI_EVENTS_LISTENER__JBOSS_LOGGING__SUCCESS_LEVEL, value: info }
            - { name: JAVA_OPTS_APPEND, value: "-Dcom.redhat.fips=false" }
          readinessProbe:
            httpGet: { path: /health/ready, port: management }
            periodSeconds: 10
            failureThreshold: 6
          startupProbe:
            httpGet: { path: /health/ready, port: management }
            periodSeconds: 5
            failureThreshold: 90
          resources:
            requests: { cpu: 200m, memory: 768Mi }
            limits: { cpu: "1", memory: 1536Mi }
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - { name: data, mountPath: /opt/keycloak/data }
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: keycloak-data
EOF
wait_rollout "$NS" deployment/keycloak 900

# --- realm "lab" through the admin REST API over the Route --------------------------------------------------
# Token: password grant of the built-in client admin-cli in the master realm (Keycloak admin REST API docs).
kc_token() {
  jq -rn --arg u "$ADMIN_USER" --arg p "$(lab_var KEYCLOAK_ADMIN_PASSWORD)" \
    '"client_id=admin-cli&grant_type=password&username=\($u | @uri)&password=\($p | @uri)"' |
    curl -s --cacert "$CA" -X POST "$KEYCLOAK_URL_VALUE/realms/master/protocol/openid-connect/token" \
      -H 'Content-Type: application/x-www-form-urlencoded' --data @- | jq -r '.access_token // empty'
}
token_ready() { [ -n "$(kc_token)" ]; }
wait_until "Keycloak admin sign-in through its route" 300 token_ready
TOKEN="$(kc_token)"
[ -n "$TOKEN" ] || die "could not sign in to Keycloak as $ADMIN_USER"

realm_code() { curl -s -o /dev/null -w '%{http_code}' --cacert "$CA" -H "Authorization: Bearer $TOKEN" "$KEYCLOAK_URL_VALUE/admin/realms/$REALM"; }
if [ "$(realm_code)" != 200 ]; then
  code="$(jq -n --arg r "$REALM" '{id: $r, realm: $r, enabled: true, eventsEnabled: true, eventsListeners: ["jboss-logging"]}' |
    curl -s -o /dev/null -w '%{http_code}' --cacert "$CA" -X POST "$KEYCLOAK_URL_VALUE/admin/realms" \
      -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data @-)"
  [ "$code" = 201 ] || die "could not create realm $REALM (HTTP $code)"
  say "created realm $REALM"
fi
[ "$(realm_code)" = 200 ] || die "realm $REALM is not readable"
unset TOKEN

lab_var_set KEYCLOAK_URL "$KEYCLOAK_URL_VALUE"
lab_var_set KEYCLOAK_ADMIN_USER "$ADMIN_USER"
say "Keycloak is up at $KEYCLOAK_URL_VALUE (realm $REALM)"
