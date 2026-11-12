#!/usr/bin/env bash
# Gitea (in-lab git server) in namespace gitea: one rootless pod, SQLite on a PVC, edge-TLS Route.
# Saves GITEA_URL, GITEA_INTERNAL_URL, GITEA_USER, GITEA_TOKEN. Creates secret gitea-admin (keys username, password).
# Safe to repeat: existing secrets, the admin user and a still-valid token are kept.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

NS=gitea
# Pin: Gitea 28.3.0 (GitHub release v28.3.0, latest stable, published 2026-11-01; not a pre-release).
# Image checked 2026-11-02: docker.io/gitea/gitea tag 28.3.0-rootless exists, and the registry docker.gitea.com
# (named in the Gitea install docs) answers HTTP 200 for /v2/gitea/manifests/28.3.0-rootless.
GITEA_IMAGE="${GITEA_IMAGE:-docker.gitea.com/gitea:28.3.0-rootless}"
GITEA_ADMIN_NAME="labadmin"   # "admin" is a reserved Gitea user name, so it is not used.
GITEA_ADMIN_EMAIL="labadmin@lab.invalid"
DATA_SIZE="5Gi"

require_var LOKI_CA_FILE
CA="$(lab_var LOKI_CA_FILE)"

ensure_namespace "$NS"

# --- secrets (created once, never regenerated) -------------------------------------------------
if ! oc get secret gitea-admin -n "$NS" >/dev/null 2>&1; then
  oc create secret generic gitea-admin -n "$NS" \
    --from-literal=username="$GITEA_ADMIN_NAME" --from-literal=password="$(random_secret 24)" >/dev/null
  say "created secret gitea-admin"
fi
if ! oc get secret gitea-server -n "$NS" >/dev/null 2>&1; then
  oc create secret generic gitea-server -n "$NS" --from-literal=secret-key="$(random_secret 32)" >/dev/null
  say "created secret gitea-server"
fi

# --- storage, service, route ---------------------------------------------------------------------
oc apply -n "$NS" -f - >/dev/null <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: gitea-data
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: ${DATA_SIZE}
---
apiVersion: v1
kind: Service
metadata:
  name: gitea
  labels:
    app: gitea
spec:
  selector:
    app: gitea
  ports:
    - name: http
      port: 3000
      targetPort: http
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: gitea
  labels:
    app: gitea
spec:
  to:
    kind: Service
    name: gitea
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
EOF
route_has_host() { [ -n "$(route_host "$NS" gitea 2>/dev/null)" ]; }
wait_until "route gitea to get a host name" 60 route_has_host
HOST="$(route_host "$NS" gitea)"
GITEA_URL_VALUE="https://${HOST}"
GITEA_INTERNAL="http://gitea.${NS}.svc.cluster.local:3000"

# --- deployment ------------------------------------------------------------------------------------
# Settings use the rootless image's GITEA__SECTION__KEY convention (docker-setup.sh runs environment-to-ini; source:
# github.com/go-gitea/gitea docker/rootless/usr/local/bin/docker-setup.sh at v28.3.0).
# The image runs as UID 1000 but OpenShift restricted-v2 assigns a random UID, so every path Gitea writes is moved to the
# PVC mounted at /data (HOME, work dir, custom dir, app.ini). No SCC beyond restricted-v2 is needed.
# Repositories sit at /data/git/gitea-repositories/<owner>/<repo>.git, as terraform/templates/bastion-userdata.sh.tftpl expects.
# [security] ALLOWED_HOST_LIST=private,loopback lets webhooks reach cluster addresses (GRC-3 sends push hooks to
# el-gate-listener.build.svc). From v28.0.0 the key lives in [security]; [webhook] ALLOWED_HOST_LIST is deprecated
# (modules/setting/webhook.go at v28.3.0; custom/conf/app.example.ini lists the built-ins "loopback" and "private").
oc apply -n "$NS" -f - >/dev/null <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gitea
  labels:
    app: gitea
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: gitea
  template:
    metadata:
      labels:
        app: gitea
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gitea
          image: ${GITEA_IMAGE}
          # Gitea refuses to start unless RUN_USER equals the OS user, and OpenShift runs the pod as a random UID with no
          # passwd entry (user.Current() returns the number). docker-setup.sh writes RUN_USER from \$USER (default "git"), so
          # set \$USER to the UID before the stock entrypoint, and force RUN_USER in an app.ini that already exists on the PVC.
          command:
            - /bin/sh
            - -c
            - 'export USER="\$(id -u)" GITEA____RUN_USER="\$(id -u)"; exec /usr/bin/dumb-init -- /usr/local/bin/docker-entrypoint.sh'
          ports:
            - name: http
              containerPort: 3000
          env:
            - { name: HOME, value: /data/gitea/home }
            - { name: GITEA_WORK_DIR, value: /data/gitea }
            - { name: GITEA_CUSTOM, value: /data/gitea/custom }
            - { name: GITEA_APP_INI, value: /data/gitea/app.ini }
            - { name: ROOT_URL, value: "${GITEA_URL_VALUE}/" }
            - { name: SSH_DOMAIN, value: "${HOST}" }
            - { name: DISABLE_SSH, value: "true" }
            - { name: DB_TYPE, value: sqlite3 }
            - { name: INSTALL_LOCK, value: "true" }
            - { name: DISABLE_REGISTRATION, value: "true" }
            - { name: REQUIRE_SIGNIN_VIEW, value: "false" }
            - name: SECRET_KEY
              valueFrom:
                secretKeyRef: { name: gitea-server, key: secret-key }
            - { name: GITEA__server__DOMAIN, value: "${HOST}" }
            - { name: GITEA__server__START_SSH_SERVER, value: "false" }
            - { name: GITEA__repository__ROOT, value: /data/git/gitea-repositories }
            - { name: GITEA__repository__DEFAULT_BRANCH, value: main }
            - { name: GITEA__security__ALLOWED_HOST_LIST, value: "private,loopback" }
            - { name: GITEA__log__MODE, value: console }
            - { name: GITEA__log__LEVEL, value: Info }
          readinessProbe:
            httpGet: { path: /api/healthz, port: http }
            periodSeconds: 10
            failureThreshold: 6
          startupProbe:
            httpGet: { path: /api/healthz, port: http }
            periodSeconds: 5
            failureThreshold: 60
          resources:
            requests: { cpu: 100m, memory: 256Mi }
            limits: { cpu: "1", memory: 1Gi }
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - { name: data, mountPath: /data }
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: gitea-data
EOF
wait_rollout "$NS" deployment/gitea 600

# --- admin user and token, through the Gitea CLI and API inside the pod (curl and git are in the image) ----
gx() { oc exec -n "$NS" deploy/gitea -c gitea -- "$@"; }
gitea_cli() { gx gitea -c /data/gitea/app.ini "$@"; }
api_code() { # path [token]
  if [ -n "${2:-}" ]; then
    gx curl -s -o /dev/null -w '%{http_code}' -H "Authorization: token $2" "http://localhost:3000/api/v1$1"
  else
    gx curl -s -o /dev/null -w '%{http_code}' "http://localhost:3000/api/v1$1"
  fi
}

ADMIN_PASS="$(oc get secret gitea-admin -n "$NS" -o jsonpath='{.data.password}' | base64 -d)"
if [ "$(api_code "/users/$GITEA_ADMIN_NAME")" != 200 ]; then
  # Flags checked against cmd/admin_user_create.go at v28.3.0.
  gitea_cli admin user create --admin --username "$GITEA_ADMIN_NAME" --password "$ADMIN_PASS" \
    --email "$GITEA_ADMIN_EMAIL" --must-change-password=false >/dev/null
  say "created Gitea administrator $GITEA_ADMIN_NAME"
fi
unset ADMIN_PASS

TOKEN="$(lab_var GITEA_TOKEN)"
if [ -z "$TOKEN" ] || [ "$(api_code /user "$TOKEN")" != 200 ]; then
  # Scope "all" covers repositories, statuses, hooks and admin calls (GRC-3 needs an administrator token).
  # Flags checked against cmd/admin_user_generate_access_token.go at v28.3.0.
  TOKEN="$(gitea_cli admin user generate-access-token --username "$GITEA_ADMIN_NAME" \
    --token-name "lab-$(date +%s)" --scopes all --raw | tail -n 1 | tr -d '[:space:]')"
  [ "${#TOKEN}" -ge 20 ] || die "Gitea did not return an access token"
  say "created Gitea access token"
fi

lab_var_set GITEA_URL "$GITEA_URL_VALUE"
lab_var_set GITEA_INTERNAL_URL "$GITEA_INTERNAL"
lab_var_set GITEA_USER "$GITEA_ADMIN_NAME"
lab_var_set GITEA_TOKEN "$TOKEN"

# --- check through the Route with the ingress CA ------------------------------------------------------
gitea_via_route() { curl -s -o /dev/null -w '%{http_code}' --cacert "$CA" -H "Authorization: token $TOKEN" "$GITEA_URL_VALUE/api/v1/user"; }
route_answers() { [ "$(gitea_via_route)" = 200 ]; }
wait_until "Gitea API through its route" 180 route_answers
curl -s --cacert "$CA" -H "Authorization: token $TOKEN" "$GITEA_URL_VALUE/api/v1/user" | jq -e '.is_admin == true' >/dev/null \
  || die "the Gitea token does not belong to an administrator"
say "Gitea is up at $GITEA_URL_VALUE (user $GITEA_ADMIN_NAME)"
