# SIEM platform scripts (50, 60)

## 50-loki.sh (namespace siem)
- Loki 3.7.9 single binary, `auth_enabled: false` (single tenant: no X-Scope-OrgID anywhere, matching every module call), TSDB v13 schema on a 20Gi PVC (`loki-data`), compactor retention on (14 days) with the delete API enabled (`delete_request_store: filesystem`), `reject_old_samples_max_age` 7 days, 30 labels per stream, raised ingestion limits for audit volume.
- Basic auth: `loki-gateway` (UBI nginx) compares the Authorization header with `Basic base64(LOKI_USER:LOKI_PASSWORD)` built at install time and kept in Secret `loki-gateway-conf`. No password hash, so nothing depends on MD5/crypt under FIPS. Route `loki` (edge TLS, default ingress certificate) points at the gateway. Service `loki:3100` is the unauthenticated in-cluster address (used by Grafana and Alloy).
- Self-test: ready through the Route with the CA, 401 without credentials, one push (`lab_probe=platform`).
- Also installs Deployment `alloy` (+ConfigMap `alloy-config`, Service `alloy:3501`), because `lab/states/sdr-4/10-alloy.sh` copies its image from it and dies without it.
- Saves: `LOKI_URL` (https://<route host>, no path), `LOKI_USER` (keeps an existing value, else `loki`).
- Requests: Loki 100m/512Mi (limit 1 CPU/2Gi), gateway 20m/32Mi, Alloy 50m/128Mi.

## 60-grafana.sh (namespace siem)
- Grafana 13.2.4, SQLite on a 2Gi PVC, Secret `grafana-admin`, Loki data source `Loki` (uid `loki`, default) provisioned from ConfigMap `grafana-datasources`, unified alerting on, plugin preinstall off (no internet needed), Route `grafana`.
- Verifies version, admin sign-in (resets the admin password with `grafana cli admin reset-admin-password --password-from-stdin` if an old database kept another password), `GET /api/datasources/name/Loki`, and the alert-rule provisioning API.
- Saves: `GRAFANA_URL`, `GRAFANA_USER` (`admin` unless already set).
- Requests: 100m/256Mi (limit 1 CPU/1Gi).

## Not verified (no live cluster here)
- Whole scripts have not run on a cluster; manifests were checked against vendor docs only.
- UBI nginx with `-c` pointing at the mounted file and `/tmp` writable under restricted-v2.
- Grafana image running as an arbitrary UID with group 0 on the PVC (fsGroup is assigned by the SCC).
- Alloy readiness path `/-/ready`.
- ClusterRole `audit-log-reader` (non-resource URL `/loki/*`, created by `ensure_audit_log_reader_role`): the start state comments say a "lab-provided Loki endpoint enforces it". This gateway does not enforce Kubernetes RBAC; it only checks basic auth. Needs a decision if a module relies on per-user audit access.
- Collector label set (log_type, kubernetes_*) comes from the ClusterLogForwarder defaults, not from Loki settings.
