#!/usr/bin/env bash
# Loki (single binary, filesystem on a PVC) in namespace siem, with an nginx basic-auth gateway and an edge-TLS Route.
# Also installs the platform Alloy Deployment `alloy` that lab/states/sdr-4/10-alloy.sh copies its image from.
#
# What the modules rely on (grepped from lab/states/_common/lib.sh, sdr-*, aid-3/ailog.py, ensure_siem_forwarder):
#   - LOKI_URL is an https Route host with no path; clients add /loki/api/v1/push, /query, /query_range, /ready.
#   - basic auth with LOKI_USER / LOKI_PASSWORD on every path; trust through LOKI_CA_FILE (ingress CA).
#   - single tenant: no X-Scope-OrgID header anywhere, so auth_enabled is false.
#   - the OpenShift collector (Vector) sends labels log_type, kubernetes_namespace_name, kubernetes_pod_name,
#     kubernetes_container_name, ...; the seeds add extra labels (lab_seed, lab_measure, run). Label limit raised.
#   - seeds push samples up to 3 hours old (sdr-2 TODO); reject_old_samples_max_age is 7 days here.
#   - old seeded records go away only by retention or the delete API, so compactor retention and deletes are on.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

# Pins (see versions-siem.txt). Sources:
#  Loki 3.7.9: github.com/grafana/loki/releases (latest, 2026-10-20) and Docker Hub grafana/loki tag 3.7.9.
#  Alloy v1.21.3: github.com/grafana/alloy/releases (2026-10-28) and Docker Hub grafana/alloy tag v1.21.3.
#  nginx: registry.access.redhat.com/v2/ubi9/nginx-126/manifests/1-1777855212 answers 200 (Red Hat image, arbitrary UID, port 8080).
LOKI_IMAGE="docker.io/grafana/loki:3.7.9"
ALLOY_IMAGE="docker.io/grafana/alloy:v1.21.3"
GATEWAY_IMAGE="registry.access.redhat.com/ubi9/nginx-126:1-1777855212"
LOKI_PVC_SIZE="20Gi"
LOKI_RETENTION="336h" # 14 days, enough for a lab (limits_config.retention_period)

NS=siem
require_cluster
require_var LOKI_PASSWORD LOKI_CA_FILE
LOKI_USER="$(lab_var LOKI_USER)"
[ -n "$LOKI_USER" ] || LOKI_USER="loki"
lab_var_set LOKI_USER "$LOKI_USER"
ensure_namespace "$NS"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

# ---- Loki configuration. Key names: Loki docs operations/storage/retention.md and cmd/loki/loki-local-config.yaml at v3.7.9.
cat >"$tmp_dir/loki.yaml" <<EOF
auth_enabled: false
server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: info
common:
  instance_addr: 127.0.0.1
  path_prefix: /data
  storage:
    filesystem:
      chunks_directory: /data/chunks
      rules_directory: /data/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory
schema_config:
  configs:
    - from: "2020-10-24"
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 50
limits_config:
  retention_period: ${LOKI_RETENTION}
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  max_label_names_per_series: 30
  ingestion_rate_mb: 32
  ingestion_burst_size_mb: 64
  per_stream_rate_limit: 16MB
  per_stream_rate_limit_burst: 64MB
  volume_enabled: true
compactor:
  working_directory: /data/retention
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  delete_request_store: filesystem
analytics:
  reporting_enabled: false
EOF
loki_hash="$(openssl dgst -sha256 -r "$tmp_dir/loki.yaml" | cut -d' ' -f1)"
oc create configmap loki-config -n "$NS" --from-file=loki.yaml="$tmp_dir/loki.yaml" --dry-run=client -o yaml | oc apply -f - >/dev/null

# ---- Gateway: nginx compares the Authorization header with the expected value built now from LOKI_USER:LOKI_PASSWORD.
# A direct string compare needs no password hash, so nothing depends on MD5/crypt under FIPS. The file lives in a Secret.
expected="$(printf '%s:%s' "$LOKI_USER" "$LOKI_PASSWORD" | base64 | tr -d '\n')"
cat >"$tmp_dir/nginx.conf" <<EOF
pid /tmp/nginx.pid;
error_log /dev/stderr warn;
events { worker_connections 512; }
http {
  access_log off;
  client_body_temp_path /tmp/cb;
  proxy_temp_path /tmp/pt;
  fastcgi_temp_path /tmp/fc;
  uwsgi_temp_path /tmp/uw;
  scgi_temp_path /tmp/sc;
  client_max_body_size 64m;
  # The map key "Basic <base64 user:password>" is longer than nginx's default bucket (64), which aborts startup.
  map_hash_bucket_size 256;
  map \$http_authorization \$lab_auth_ok {
    default 0;
    "Basic ${expected}" 1;
  }
  server {
    listen 8080;
    location = /gateway-health { return 200 "ok"; }
    location / {
      if (\$lab_auth_ok = 0) {
        add_header WWW-Authenticate 'Basic realm="loki"' always;
        return 401;
      }
      proxy_pass http://loki.${NS}.svc.cluster.local:3100;
      proxy_set_header Authorization "";
      proxy_http_version 1.1;
      proxy_read_timeout 300s;
      proxy_send_timeout 300s;
    }
  }
}
EOF
conf_hash="$(openssl dgst -sha256 -r "$tmp_dir/nginx.conf" | cut -d' ' -f1)"
oc create secret generic loki-gateway-conf -n "$NS" --from-file=nginx.conf="$tmp_dir/nginx.conf" --dry-run=client -o yaml | oc apply -f - >/dev/null

# ---- Loki workload. restricted-v2 SCC: no runAsUser (the namespace range is assigned) and the PVC gets the fsGroup.
oc apply -f - >/dev/null <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: loki-data
  namespace: ${NS}
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: ${LOKI_PVC_SIZE}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: loki
  namespace: ${NS}
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: loki
  template:
    metadata:
      labels:
        app: loki
      annotations:
        lab/config-hash: "${loki_hash}"
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: loki
          image: ${LOKI_IMAGE}
          args: ["-config.file=/etc/loki/loki.yaml"]
          ports:
            - name: http
              containerPort: 3100
          readinessProbe:
            httpGet: {path: /ready, port: http}
            initialDelaySeconds: 15
            periodSeconds: 10
          livenessProbe:
            httpGet: {path: /ready, port: http}
            initialDelaySeconds: 60
            periodSeconds: 20
            failureThreshold: 6
          resources:
            requests: {cpu: 100m, memory: 512Mi}
            limits: {cpu: "1", memory: 2Gi}
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - {name: config, mountPath: /etc/loki}
            - {name: data, mountPath: /data}
      volumes:
        - name: config
          configMap:
            name: loki-config
        - name: data
          persistentVolumeClaim:
            claimName: loki-data
---
apiVersion: v1
kind: Service
metadata:
  name: loki
  namespace: ${NS}
spec:
  selector:
    app: loki
  ports:
    - {name: http, port: 3100, targetPort: http}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: loki-gateway
  namespace: ${NS}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: loki-gateway
  template:
    metadata:
      labels:
        app: loki-gateway
      annotations:
        lab/conf-hash: "${conf_hash}"
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: nginx
          image: ${GATEWAY_IMAGE}
          command: ["nginx", "-g", "daemon off;", "-c", "/etc/nginx/gateway/nginx.conf"]
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet: {path: /gateway-health, port: http}
            periodSeconds: 10
          resources:
            requests: {cpu: 20m, memory: 32Mi}
            limits: {cpu: 500m, memory: 128Mi}
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - {name: conf, mountPath: /etc/nginx/gateway, readOnly: true}
            - {name: tmp, mountPath: /tmp}
      volumes:
        - name: conf
          secret:
            secretName: loki-gateway-conf
        - name: tmp
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: loki-gateway
  namespace: ${NS}
spec:
  selector:
    app: loki-gateway
  ports:
    - {name: http, port: 8080, targetPort: http}
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: loki
  namespace: ${NS}
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: loki-gateway
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
EOF

wait_rollout "$NS" deployment/loki 600
wait_rollout "$NS" deployment/loki-gateway 300

LOKI_URL="https://$(route_host "$NS" loki)"
lab_var_set LOKI_URL "$LOKI_URL"

# Calls through the Route use the ingress CA; credentials go through stdin so they are not in the process list.
loki_route() { printf 'user = "%s:%s"\n' "$LOKI_USER" "$LOKI_PASSWORD" | curl -sS -K - --cacert "$LOKI_CA_FILE" "$@"; }
loki_ready() { [ "$(loki_route -o /dev/null -w '%{http_code}' "$LOKI_URL/ready")" = 200 ]; }
wait_until "Loki ready through the Route with basic auth" 300 loki_ready
anon_code="$(curl -s --cacert "$LOKI_CA_FILE" -o /dev/null -w '%{http_code}' "$LOKI_URL/ready")"
[ "$anon_code" = 401 ] || die "Loki gateway answered HTTP $anon_code without credentials (expected 401)"
say "Loki gateway refuses requests without credentials"

# Push one line with the call the modules use (POST /loki/api/v1/push, no tenant header).
probe_ns="$(date +%s)000000000"
body="{\"streams\":[{\"stream\":{\"lab_probe\":\"platform\"},\"values\":[[\"${probe_ns}\",\"platform install probe\"]]}]}"
code="$(loki_route -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d "$body" "$LOKI_URL/loki/api/v1/push")"
[ "$code" = 204 ] || die "Loki push through the Route returned HTTP $code"
say "Loki accepts pushes at $LOKI_URL/loki/api/v1/push"

# ---- Platform Alloy: sdr-4 reads this Deployment's image. It takes Loki pushes on 3501 and forwards them in-cluster.
oc apply -f - >/dev/null <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: alloy-config
  namespace: ${NS}
data:
  config.alloy: |
    loki.source.api "platform" {
      http {
        listen_address = "0.0.0.0"
        listen_port    = 3501
      }
      forward_to = [loki.write.local.receiver]
    }
    loki.write "local" {
      endpoint {
        url = "http://loki.${NS}.svc.cluster.local:3100/loki/api/v1/push"
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alloy
  namespace: ${NS}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alloy
  template:
    metadata:
      labels:
        app: alloy
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: alloy
          image: ${ALLOY_IMAGE}
          args: ["run", "/etc/alloy", "--storage.path=/tmp/alloy", "--server.http.listen-addr=0.0.0.0:12345"]
          ports:
            - {name: http, containerPort: 12345}
            - {name: intake, containerPort: 3501}
          readinessProbe:
            httpGet: {path: /-/ready, port: http}
            periodSeconds: 10
          resources:
            requests: {cpu: 50m, memory: 128Mi}
            limits: {cpu: 500m, memory: 512Mi}
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - {name: config, mountPath: /etc/alloy}
            - {name: tmp, mountPath: /tmp}
      volumes:
        - name: config
          configMap:
            name: alloy-config
        - name: tmp
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: alloy
  namespace: ${NS}
spec:
  selector:
    app: alloy
  ports:
    - {name: intake, port: 3501, targetPort: intake}
EOF
wait_rollout "$NS" deployment/alloy 300
say "Loki: $LOKI_URL (user $LOKI_USER); in-cluster http://loki.${NS}.svc.cluster.local:3100"
