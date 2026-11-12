#!/usr/bin/env bash
# Mattermost Team Edition in namespace chat: one server pod + one PostgreSQL pod (PVCs), edge-TLS Route.
# Creates team "lab", public channel "siem-alerts", an administrator, an incoming webhook for that channel and a personal
# access token (secret mm-api, key token, in namespace siem, as lab/states/sdr-5/40-preflight.sh expects).
# Saves MM_URL and MM_WEBHOOK_URL. Safe to repeat.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

NS=chat
# Pins (checked 2026-11-02):
#  - Mattermost 11.11.3: docker.io/mattermost/mattermost-team-edition tag 11.11.3 exists (Docker Hub tags API, pushed
#    2026-10-22) and github.com/mattermost/mattermost release v11.11.3 is not a pre-release.
#  - PostgreSQL 16 from quay.io/sclorg/postgresql-16-c9s, dated tag 20261027 (Quay tag API; the "latest" tag points at it).
#    This is the Software Collections image: it runs under an arbitrary UID, which the Docker Hub postgres image does not.
MM_IMAGE="${MM_IMAGE:-docker.io/mattermost/mattermost-team-edition:11.11.3}"
PG_IMAGE="${PG_IMAGE:-quay.io/sclorg/postgresql-16-c9s:20261027}"
MM_TEAM="lab"                 # sdr-5 mm.py reads MM_TEAM (default lab) and channel siem-alerts
MM_CHANNEL="siem-alerts"
MM_ADMIN="labadmin"
MM_ADMIN_EMAIL="labadmin@lab.invalid"
HOOK_NAME="lab-alerts"

require_var LOKI_CA_FILE
CA="$(lab_var LOKI_CA_FILE)"
ensure_namespace "$NS"
ensure_namespace siem

if ! oc get secret mattermost-db -n "$NS" >/dev/null 2>&1; then
  oc create secret generic mattermost-db -n "$NS" --from-literal=password="$(random_secret 24)" >/dev/null
  say "created secret mattermost-db"
fi
if ! oc get secret mattermost-admin -n "$NS" >/dev/null 2>&1; then
  oc create secret generic mattermost-admin -n "$NS" \
    --from-literal=username="$MM_ADMIN" --from-literal=password="$(random_secret 24)" >/dev/null
  say "created secret mattermost-admin"
fi
DB_PASS="$(oc get secret mattermost-db -n "$NS" -o jsonpath='{.data.password}' | base64 -d)"

# --- PostgreSQL ------------------------------------------------------------------------------------
# Env names POSTGRESQL_USER / POSTGRESQL_PASSWORD / POSTGRESQL_DATABASE and data dir /var/lib/pgsql/data are from the
# sclorg postgresql-container README; /usr/libexec/check-container is the readiness script that image ships.
oc apply -n "$NS" -f - >/dev/null <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mattermost-db
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 5Gi
---
apiVersion: v1
kind: Service
metadata:
  name: mattermost-db
spec:
  selector:
    app: mattermost-db
  ports:
    - name: postgres
      port: 5432
      targetPort: postgres
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mattermost-db
  labels:
    app: mattermost-db
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: mattermost-db
  template:
    metadata:
      labels:
        app: mattermost-db
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: postgres
          image: ${PG_IMAGE}
          ports:
            - name: postgres
              containerPort: 5432
          env:
            - { name: POSTGRESQL_USER, value: mattermost }
            - { name: POSTGRESQL_DATABASE, value: mattermost }
            - name: POSTGRESQL_PASSWORD
              valueFrom:
                secretKeyRef: { name: mattermost-db, key: password }
          readinessProbe:
            exec:
              command: [/usr/libexec/check-container]
            periodSeconds: 10
            failureThreshold: 6
          livenessProbe:
            tcpSocket: { port: postgres }
            initialDelaySeconds: 60
            periodSeconds: 20
          resources:
            requests: { cpu: 50m, memory: 128Mi }
            limits: { cpu: 500m, memory: 512Mi }
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - { name: data, mountPath: /var/lib/pgsql/data }
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: mattermost-db
EOF
wait_rollout "$NS" deployment/mattermost-db 600

# --- Mattermost server and route -------------------------------------------------------------------
oc apply -n "$NS" -f - >/dev/null <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mattermost-data
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 5Gi
---
apiVersion: v1
kind: Service
metadata:
  name: mattermost
spec:
  selector:
    app: mattermost
  ports:
    - name: http
      port: 8065
      targetPort: http
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: mattermost
  labels:
    app: mattermost
spec:
  to:
    kind: Service
    name: mattermost
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
EOF
route_has_host() { [ -n "$(route_host "$NS" mattermost 2>/dev/null)" ]; }
wait_until "route mattermost to get a host name" 60 route_has_host
HOST="$(route_host "$NS" mattermost)"
MM_URL_VALUE="https://${HOST}"

# Settings come from MM_* environment variables. MM_CONFIG set to a database address stores the configuration in
# PostgreSQL, so the image's read-only /mattermost/config is not written (Mattermost docs: environment variables,
# "MM_CONFIG"). The image is distroless and runs as UID 2000; under restricted-v2 the UID is random, so the data
# PVC (fsGroup-writable) is mounted at /mattermost/data and the plugin folders and /var/tmp (local-mode socket for
# mmctl --local) are emptyDir volumes. File logs are off; logs go to the console, where the collector reads them.
# No SCC beyond restricted-v2. Image build: server/build/Dockerfile at v11.11.3 (user mattermost 2000, distroless).
DSN="postgres://mattermost:${DB_PASS}@mattermost-db.${NS}.svc.cluster.local:5432/mattermost?sslmode=disable&connect_timeout=10"
oc create secret generic mattermost-env -n "$NS" --from-literal=dsn="$DSN" --dry-run=client -o yaml | oc apply -f - >/dev/null
unset DB_PASS DSN
oc apply -n "$NS" -f - >/dev/null <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mattermost
  labels:
    app: mattermost
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: mattermost
  template:
    metadata:
      labels:
        app: mattermost
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: mattermost
          image: ${MM_IMAGE}
          ports:
            - name: http
              containerPort: 8065
          env:
            - name: MM_CONFIG
              valueFrom:
                secretKeyRef: { name: mattermost-env, key: dsn }
            - name: MM_SQLSETTINGS_DATASOURCE
              valueFrom:
                secretKeyRef: { name: mattermost-env, key: dsn }
            - { name: MM_SQLSETTINGS_DRIVERNAME, value: postgres }
            - { name: MM_SERVICESETTINGS_SITEURL, value: "${MM_URL_VALUE}" }
            - { name: MM_SERVICESETTINGS_LISTENADDRESS, value: ":8065" }
            - { name: MM_SERVICESETTINGS_ENABLEINCOMINGWEBHOOKS, value: "true" }
            - { name: MM_SERVICESETTINGS_ENABLEUSERACCESSTOKENS, value: "true" }
            - { name: MM_SERVICESETTINGS_ENABLELOCALMODE, value: "true" }
            - { name: MM_TEAMSETTINGS_ENABLEOPENSERVER, value: "false" }
            - { name: MM_FILESETTINGS_DIRECTORY, value: /mattermost/data/ }
            - { name: MM_LOGSETTINGS_ENABLEFILE, value: "false" }
            - { name: MM_LOGSETTINGS_CONSOLELEVEL, value: INFO }
            - { name: MM_NOTIFICATIONLOGSETTINGS_ENABLEFILE, value: "false" }
            - { name: MM_LOGSETTINGS_ENABLEDIAGNOSTICS, value: "false" }
          readinessProbe:
            httpGet: { path: /api/v4/system/ping, port: http }
            periodSeconds: 10
            failureThreshold: 6
          startupProbe:
            httpGet: { path: /api/v4/system/ping, port: http }
            periodSeconds: 5
            failureThreshold: 72
          resources:
            requests: { cpu: 150m, memory: 512Mi }
            limits: { cpu: "1", memory: 1536Mi }
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - { name: data, mountPath: /mattermost/data }
            - { name: plugins, mountPath: /mattermost/plugins }
            - { name: client-plugins, mountPath: /mattermost/client/plugins }
            - { name: vartmp, mountPath: /var/tmp }
            - { name: tmp, mountPath: /tmp }
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: mattermost-data
        - { name: plugins, emptyDir: {} }
        - { name: client-plugins, emptyDir: {} }
        - { name: vartmp, emptyDir: {} }
        - { name: tmp, emptyDir: {} }
EOF
wait_rollout "$NS" deployment/mattermost 900

# --- team, channel, administrator, webhook and token through mmctl in local mode ------------------------
# mmctl --local talks to the server over a socket inside the pod, so it needs no login. Sub-commands and flags
# checked against server/cmd/mmctl/commands/{user,team,team_users,channel,channel_users,webhook,token}.go at v11.11.3.
mm() { oc exec -n "$NS" deploy/mattermost -c mattermost -- /mattermost/bin/mmctl --local "$@"; }
mm_ready() { mm system status >/dev/null 2>&1; }
wait_until "mmctl local mode" 300 mm_ready

if ! mm user list --all 2>/dev/null | grep -qF "$MM_ADMIN"; then
  ADMIN_PASS="$(oc get secret mattermost-admin -n "$NS" -o jsonpath='{.data.password}' | base64 -d)"
  mm user create --username "$MM_ADMIN" --email "$MM_ADMIN_EMAIL" --password "$ADMIN_PASS" \
    --system-admin --email-verified --disable-welcome-email >/dev/null
  unset ADMIN_PASS
  say "created Mattermost administrator $MM_ADMIN"
fi
if ! mm team list 2>/dev/null | grep -qx "$MM_TEAM"; then
  mm team create --name "$MM_TEAM" --display-name "Lab" >/dev/null
  say "created team $MM_TEAM"
fi
mm team users add "$MM_TEAM" "$MM_ADMIN" >/dev/null 2>&1 || true   # already a member is not an error
if ! mm channel list "$MM_TEAM" 2>/dev/null | grep -qF "$MM_CHANNEL"; then
  mm channel create --team "$MM_TEAM" --name "$MM_CHANNEL" --display-name "SIEM alerts" >/dev/null
  say "created channel $MM_CHANNEL"
fi
mm channel users add "${MM_TEAM}:${MM_CHANNEL}" "$MM_ADMIN" >/dev/null 2>&1 || true

# Incoming webhook: the list line is "Incoming:<TAB>name (id)".
HOOK_ID="$(mm webhook list "$MM_TEAM" 2>/dev/null | sed -n "s/^Incoming:[[:space:]]*${HOOK_NAME} (\([a-z0-9]*\))$/\1/p" | head -n 1)"
if [ -z "$HOOK_ID" ]; then
  HOOK_ID="$(mm webhook create-incoming --channel "${MM_TEAM}:${MM_CHANNEL}" --user "$MM_ADMIN" --display-name "$HOOK_NAME" \
    | sed -n 's/^Id: //p' | head -n 1 | tr -d '[:space:]')"
  say "created incoming webhook $HOOK_NAME"
fi
[ -n "$HOOK_ID" ] || die "could not read the incoming webhook id from mmctl"

# Personal access token for the sdr-5 pipeline (secret mm-api in namespace siem, key token). Kept while it still works.
mm_code() { curl -s -o /dev/null -w '%{http_code}' --cacert "$CA" -H "Authorization: Bearer $1" "$MM_URL_VALUE/api/v4/users/me"; }
TOKEN="$(oc get secret mm-api -n siem -o jsonpath='{.data.token}' 2>/dev/null | base64 -d 2>/dev/null || true)"
route_answers() { [ "$(curl -s -o /dev/null -w '%{http_code}' --cacert "$CA" "$MM_URL_VALUE/api/v4/system/ping")" = 200 ]; }
wait_until "Mattermost through its route" 180 route_answers
if [ -z "$TOKEN" ] || [ "$(mm_code "$TOKEN")" != 200 ]; then
  TOKEN="$(mm token generate "$MM_ADMIN" "lab-$(date +%s)" | tail -n 1 | cut -d: -f1 | tr -d '[:space:]')"
  [ "${#TOKEN}" -ge 20 ] || die "mmctl did not return an access token"
  oc create secret generic mm-api -n siem --from-literal=token="$TOKEN" --dry-run=client -o yaml | oc apply -f - >/dev/null
  say "saved access token in secret mm-api (namespace siem)"
fi
[ "$(mm_code "$TOKEN")" = 200 ] || die "the Mattermost access token is not accepted"

lab_var_set MM_URL "$MM_URL_VALUE"
lab_var_set MM_WEBHOOK_URL "${MM_URL_VALUE}/hooks/${HOOK_ID}"

# Channel check through the API.
code="$(curl -s -o /dev/null -w '%{http_code}' --cacert "$CA" -H "Authorization: Bearer $TOKEN" \
  "$MM_URL_VALUE/api/v4/teams/name/${MM_TEAM}/channels/name/${MM_CHANNEL}")"
[ "$code" = 200 ] || die "channel ${MM_TEAM}/${MM_CHANNEL} is not reachable through the API (HTTP $code)"
say "Mattermost is up at $MM_URL_VALUE (team $MM_TEAM, channel $MM_CHANNEL)"
