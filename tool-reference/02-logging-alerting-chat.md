# Tool reference 02: logging, alerting and chat

Retrieved 2026-10-30. Sources are vendor sites only (grafana.com/docs, docs.mattermost.com, github.com/grafana/alloy). The "latest" doc trees were used. Where a page says nothing on a point, that is noted and not filled from memory.

Contents
1. Loki (not pinned)
2. Grafana 13.2.4
3. Alloy (not pinned)
4. Mattermost (not pinned)

---

## Loki (not pinned; docs "latest", newest upgrade-guide entry is 3.6.0)
- Vendor docs (retrieved 2026-10-30):
  [1] Retention - https://grafana.com/docs/loki/latest/operations/storage/retention/
  [2] Log entry deletion - https://grafana.com/docs/loki/latest/operations/storage/logs-deletion/
  [3] Multi-tenancy - https://grafana.com/docs/loki/latest/operations/multi-tenancy/
  [4] Authentication - https://grafana.com/docs/loki/latest/operations/authentication/
  [5] Label best practices - https://grafana.com/docs/loki/latest/get-started/labels/bp-labels/
  [6] HTTP API - https://grafana.com/docs/loki/latest/reference/loki-http-api/
  [7] Request validation and rate limits - https://grafana.com/docs/loki/latest/operations/request-validation-rate-limits/
  [8] Storage - https://grafana.com/docs/loki/latest/operations/storage/
  [9] Ruler / alerting - https://grafana.com/docs/loki/latest/alert/
  [10] Upgrade guide - https://grafana.com/docs/loki/latest/setup/upgrade/
  [11] Query best practices - https://grafana.com/docs/loki/latest/query/bp-query/
  [12] Deployment modes - https://grafana.com/docs/loki/latest/get-started/deployment-modes/
  [13] Sizing - https://grafana.com/docs/loki/latest/setup/size/
  [14] LogQL overview - https://grafana.com/docs/loki/latest/query/
  [15] Config reference (first 100k characters only) - https://grafana.com/docs/loki/latest/configure/
  [16] Storage config page - https://grafana.com/docs/loki/latest/configure/storage/
- Role in this training: log store for audit and app logs, queried by LogQL over HTTP, with storage, retention and deletion settings; source for Grafana alert rules. Modules: sdr-2, sdr-3, sdr-4, sdr-5, aid-3, aid-4, aid-5, eng-0.
- Best practices (vendor-stated):
  - Use the TSDB index; BoltDB Shipper is deprecated and slated for removal in 4.0 [6][8].
  - Chunk storage on S3/GCS/Azure is recommended; filesystem is supported but not typically recommended for production [8].
  - Run the compactor as a single instance. Retention needs `retention_enabled: true`, `delete_request_store`, a `working_directory` and a 24h index period [1].
  - Global `retention_period` defaults to 0s (keep forever). `retention_stream` rules need at least 24h and use label matchers only. Retention changes are not retroactive [1].
  - Object-store lifecycle rules must not use an empty prefix and must never expire index, delete-request, marker or ruler objects. Set expiry longer than retention plus `retention_delete_delay` (default 2h) [1].
  - `deletion_mode: disabled` makes the delete endpoints return 403. The default is `filter-and-delete`. Endpoints exist only if retention is enabled on the compactor [2].
  - Loki has no built-in auth. Put an authenticating reverse proxy in front and have it set `X-Scope-OrgID`. Native mutual TLS authenticates the client but does not set the tenant header [4].
  - With `auth_enabled: false` the single tenant id is `fake`. With true, a missing tenant header gives 401 [3].
  - Keep labels few, bounded and long-lived. Do not use trace, order or request ids as labels; use filters or structured metadata [5].
  - Narrow the time range, use specific selectors, prefer `|=` over regex, put parsers after line filters [11].
- Implementation guidance relevant to the lab:
  - Readiness: GET /ready returns 200 [6].
  - Query: GET /loki/api/v1/query_range (start/end, limit default 100, direction default backward). Instant /query takes metric queries only; a log selector returns 400 since 3.2 [6][10].
  - Label values: GET /loki/api/v1/label/<name>/values [6].
  - Push: POST /loki/api/v1/push, protobuf or JSON, timestamps as strings [6].
  - Delete: POST /loki/api/v1/delete needs `query` and `start`, success is 204, needs TSDB index [6].
  - SSE-KMS: the S3 storage config has an `sse` block with `type: SSE-KMS` and `kms_key_id` (seen only in a search-result summary of grafana.com, not on a fetched page; see Unconfirmed).
  - S3 IAM actions: ListBucket, PutObject, GetObject, DeleteObject on the bucket and bucket/* [16].
  - Ruler (not used by the modules): Prometheus-style rule YAML, API under /loki/api/v1/rules, recording rules for expensive queries [9].
  - Ingest limits return 400 for old samples and long lines, 429 for rate limits [7].
- Version notes: 3.0 requires explicit `delete_request_store` when retention is on, moved deletion mode into `limits_config`, cut max labels per series to 15 and set max line size 256KB [10]. Structured metadata needs TSDB plus schema v13 [10]. Simple Scalable mode is removed in 4.0 [12]. 3.5.8 removed the shell from official images [10]. Single binary is documented for roughly 20GB/day or less [12]. Sizing tables cover distributed mode only [13].
- Where this project differs:
  - Start state is single-tenant (`auth_enabled: false`) with filesystem storage and retention off. The lab fronts Loki with basic auth (LOKI_USER/LOKI_PASSWORD). The vendor path is an authenticating proxy that sets the tenant header; no tenant header is set here. Labeled shortcut.
  - Filesystem storage in the start state is the documented non-production option [8]. Labeled shortcut.
  - The readiness check sends basic auth to /ready; the vendor proxy example leaves /ready open [4].
  - No module uses the Loki ruler; alerting runs in Grafana.
- Unconfirmed: exact YAML nesting of `sse`; whether `kms_key_id` accepts a full key ARN; the Loki version the lab build deploys (none pinned in versions.txt); the LogQL rule that a selector needs a non-empty matcher (not stated on pages read); the config reference beyond its first 100k characters.

---

## Grafana 13.2.4
- Vendor docs (retrieved 2026-10-30; docs "latest" is 13.3, 13.2 pages used where they exist):
  [1] What is new in 13.2 - https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v13/whats-new-in-v13-2/
  [2] Upgrade to 13.2 - https://grafana.com/docs/grafana/latest/upgrade-guide/upgrade-v13/upgrade-v13.2/
  [3] Alerting fundamentals - https://grafana.com/docs/grafana/latest/alerting/fundamentals/
  [4] Alerting best practices - https://grafana.com/docs/grafana/latest/alerting/best-practices/
  [5] Provisioning HTTP API (first 100k characters) - https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/http-api-provisioning/
  [6] Contact points - https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/
  [7] Notification policies - https://grafana.com/docs/grafana/latest/alerting/configure-notifications/create-notification-policy/
  [8] Grafana-managed alert rules - https://grafana.com/docs/grafana/latest/alerting/alerting-rules/create-grafana-managed-rule/
  [9] Alerting file provisioning - https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/
  [10] Provisioning (data sources, dashboards) - https://grafana.com/docs/grafana/latest/administration/provisioning/
  [11] Security hardening - https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-security-hardening/
  [12] Service accounts - https://grafana.com/docs/grafana/latest/administration/service-accounts/
  [13] Loki data source - https://grafana.com/docs/grafana/latest/datasources/loki/configure/ (the /configure-loki-data-source/ path returned 404 on one attempt and 200 on another; content is from the 200)
  [14] Back up Grafana - https://grafana.com/docs/grafana/latest/administration/back-up-grafana/
  [15] Dashboard best practices - https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/
  [16] Dashboard API - https://grafana.com/docs/grafana/latest/developers/http_api/dashboard/
- Role in this training: dashboards and alert rules over Loki, with contact point and policy routing to Mattermost. Modules: sdr-2, sdr-3, sdr-4, sdr-5, aid-5, eng-0.
- Best practices (vendor-stated):
  - Page on symptoms, alert only on actionable problems, link runbooks and dashboards in annotations, give each alert an owner [4].
  - Treat routing as seriously as the rule: parent policy for defaults, nested policies for specifics, group related alerts [4].
  - Reduce flapping with pending periods and `keep_firing_for` or recovery thresholds [4][8].
  - Set no-data and error handling explicitly (No Data, Alerting, Normal, Keep last state) [8].
  - Webhook URLs are protected fields; only contact point admins may change them. Test each contact point before relying on it [6].
  - Use service accounts for API automation, with short-lived, least-privilege tokens, one per application [12].
  - Hardening settings: `cookie_secure = true`, `cookie_samesite = strict`, content security policy on, `hide_version`, basic auth on metrics, `enforce_domain` [11].
  - Before an upgrade, back up grafana.ini, the plugins directory and the database (stop Grafana before copying SQLite; pg_dump or mysqldump otherwise), and test first [2][14].
  - Provisioned data sources: put secrets in `secureJsonData`, use `editable: false`, set `version`, use `${VAR}` in values [10].
  - Version-control dashboard JSON, match refresh rate to data change, use template variables [15].
- Implementation guidance relevant to the lab:
  - Create a rule: POST /api/v1/provisioning/alert-rules with folder, rule group, condition, `for`, noDataState, execErrState [5][8][9]. `X-Disable-Provenance: true` keeps API-created resources editable in the UI [5].
  - Contact point: POST/PUT /api/v1/provisioning/contact-points (v1 integrations only) [5].
  - Policy tree: PUT /api/v1/provisioning/policies replaces the whole tree; DELETE resets it to default [5][9].
  - Policy timing defaults: group wait 30s, group interval 5m, repeat interval 4h [7].
  - Loki data source: base URL only, no API path; add an `X-Scope-OrgID` custom header for multi-tenant Loki; use a CA cert for self-signed TLS; avoid skip-verify; provisioning YAML uses `type: loki`, `access: proxy`, `jsonData.maxLines` [13].
  - Dashboards: the vendor's current API is /apis/dashboard.grafana.app/v1/namespaces/:namespace/dashboards [16].
- Version notes: the 13.2 What-is-new and upgrade pages list no breaking changes [1][2]. The provisioning API page marks contact point, policy, template group and mute timing endpoints deprecated and points to the App Platform alerting APIs [5]. The dashboard API page says the new API replaces /api/dashboards/* but gives no mapping for POST /api/dashboards/db [16]. Alerting file provisioning is not available on Grafana Cloud [9].
- Where this project differs:
  - Modules call deprecated provisioning endpoints (contact-points, policies) plus /api/folders and /api/datasources/name/...; the vendor says the former still work but are deprecated [5]. LAB-CONTRACT already notes this.
  - sdr-3 pushes dashboards with POST /api/dashboards/db and overwrite; the pages read neither confirm nor deprecate this path [16].
  - Modules authenticate as the admin user with a password (basic auth); the vendor recommends service accounts with tokens [12]. Labeled shortcut.
  - Mattermost is wired as a `slack` type contact point with the webhook URL in settings. The pages read do not say whether this is the vendor-endorsed way to reach Mattermost.
  - Rules are created via the API with provenance disabled so learners can edit them; the vendor default makes API-created resources read-only in the UI [5].
  - The doc tree fetched is 13.3 "latest"; 13.2.4-specific differences beyond the 13.2 pages are not confirmed.
- Unconfirmed: Loki log queries inside alert rules (alert rule page silent); HSTS and admin-account hardening (hardening page silent); removal date of the deprecated provisioning endpoints; the second half of the provisioning API page (not read).

---

## Alloy (not pinned; latest GitHub release v1.21.3 on 2026-10-28)
- Vendor docs (retrieved 2026-10-30):
  [1] Introduction - https://grafana.com/docs/alloy/latest/introduction/
  [2] loki.source.api - https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.api/
  [3] loki.write - https://grafana.com/docs/alloy/latest/reference/components/loki/loki.write/
  [4] loki.process (first 100k characters) - https://grafana.com/docs/alloy/latest/reference/components/loki/loki.process/
  [5] alloy run - https://grafana.com/docs/alloy/latest/reference/cli/run/
  [6] Install on Kubernetes - https://grafana.com/docs/alloy/latest/set-up/install/kubernetes/
  [7] Releases - https://github.com/grafana/alloy/releases
- Role in this training: intake on the Loki push API (port 3500) with a learner-written labeling stage, writing to Loki. Modules: sdr-4 (lab/states/sdr-4/10-alloy.sh, alloy/base.alloy). The platform Deployment `alloy` in namespace siem comes from the lab build.
- Best practices (vendor-stated):
  - Keep high-cardinality values out of labels; use structured metadata or `stage.pack`; trim with `stage.label_keep` or `stage.label_drop` [4].
  - loki.source.api drops labels that start with `__`; set the tenant with the `X-Scope-OrgID` header or `loki.process` [2].
  - Use the `tls` block on loki.source.api (server cert and key; `client_ca_file` with a client auth type for mutual TLS). Default client auth is none [2].
  - In loki.write use `tls_config` with a CA. The vendor warns `insecure_skip_verify` is for isolated testing only; minimum TLS defaults to 1.2 [3].
  - Credentials can come from `password_file` or bearer token files as well as inline values [3].
  - The debug HTTP server defaults to loopback 127.0.0.1:12345 [5].
  - Reload with SIGHUP or POST /-/reload; a failed reload keeps the last good state [5].
  - Plan for drops: other 4xx responses are not retried, retries stop after `max_backoff_retries` (default 10), and drops are counted in `loki_write_dropped_entries_total` [3].
  - The loki.write WAL is experimental and off by default [3].
- Implementation guidance relevant to the lab:
  - Receive: `loki.source.api` with an `http` block (`listen_port`) and `use_incoming_timestamp = true` to keep event times. Endpoints /loki/api/v1/push, /loki/api/v1/raw, /ready [2].
  - Chain: `forward_to = [loki.process.<name>.receiver]`; stages run in file order [2][4].
  - Labeling stages: `stage.labels`, `stage.static_labels`, `stage.json`, `stage.regex`, `stage.match`, `stage.drop` [4].
  - Write: `endpoint { url, basic_auth { username, password }, tls_config { ca_file } }` [3].
  - Run: `alloy run <path>`; `--storage.path` sets the data directory (default `data-alloy/`) [5].
  - Kubernetes install is the Helm chart `grafana/alloy`; the page has no OpenShift, sizing or security-context guidance [6].
- Version notes: 1.21.3 notes list no breaking changes; 1.21.0 had some (Kafka `max_retries` default, `error_mode` default) [7]. Experimental features (WAL, queue_config) depend on the stability level; default is generally-available [3][5]. No docs for a pinned version because none is pinned.
- Where this project differs:
  - base.alloy listens on 0.0.0.0:3500 with no TLS and no client auth; the vendor offers a `tls` block [2]. Labeled shortcut for an in-cluster lab.
  - 10-alloy.sh passes `--server.http.listen-addr=0.0.0.0:12345`; the vendor default is loopback [5]. Labeled shortcut (probably for probes).
  - Credentials arrive through `sys.env(...)` from a Secret; the vendor lists `password_file` as an option [3]. The vendor page on `sys.env` and secrets was not confirmed.
  - `--storage.path=/tmp/alloy` is non-persistent; this is a lab choice [5].
  - The image is copied from the existing `alloy` Deployment; the lab chooses no version.
- Unconfirmed: the Alloy version the lab build installs; secret handling for `sys.env`; whether the Helm chart runs under the OpenShift restricted policy; resource sizing (not found on pages read).

---

## Mattermost (not pinned; newest server in upgrade notes is v12.0)
- Vendor docs (retrieved 2026-10-30):
  [1] Incoming webhooks - https://docs.mattermost.com/developers/integrate/webhooks/incoming
  [2] Personal access tokens - https://docs.mattermost.com/developers/integrate/reference/personal-access-token
  [3] Important upgrade notes (first 100k characters) - https://docs.mattermost.com/administration-guide/upgrade/important-upgrade-notes.html
  [4] Prepare your server environment - https://docs.mattermost.com/deployment-guide/server/preparations.html
  [5] Deploy on Kubernetes - https://docs.mattermost.com/deployment-guide/server/deploy-kubernetes.html
  [6] TLS setup - https://docs.mattermost.com/deployment-guide/server/setup-tls.html
  [7] Backup and disaster recovery - https://docs.mattermost.com/deployment-guide/backup-disaster-recovery.html
  [8] Secure Mattermost - https://docs.mattermost.com/security-guide/secure-mattermost
  [9] Server deployment planning - https://docs.mattermost.com/deployment-guide/server/server-deployment-planning.html
  [10] API reference landing page - https://docs.mattermost.com/api
- Role in this training: chat target for alerts (incoming webhook into channel siem-alerts), API posting with a personal access token, and a reachability check at /api/v4/system/ping. Modules: sdr-2, sdr-5, aid-2, aid-5, eng-0.
- Best practices (vendor-stated):
  - Treat the webhook URL as a secret; anyone holding it can post [1].
  - A System Admin must enable incoming webhooks; username and icon overrides need their own admin settings [1].
  - Use PostgreSQL 15 or later; MySQL support ended in v11 [3][4].
  - Put a TLS reverse proxy in front before exposing users; NGINX is recommended above 200 users; avoid self-signed certificates in production [4][6].
  - Personal access tokens do not expire. Restrict who may create them, prefer non-admin accounts, store them securely, rotate by creating new ones through the API, revoke from the profile or System Console [2].
  - Deactivating the owning account disables its tokens; reactivating restores them [2].
  - Back up the database, config/config.json (the whole config directory if SAML is used) and the data directory (files on S3 usually need no separate backup). Stop Mattermost during the backup so database and files stay in sync [7].
  - On Kubernetes the Mattermost Operator is the recommended production method, paired with a managed database and S3-compatible storage; Kubernetes deployment is not on the Professional plan [5].
  - Sizing is driven by concurrent users, not registered users [9].
  - Listed hardening controls: MFA, session length, SAML/LDAP, client certificates at the proxy, file-sharing controls, log path restrictions [8].
- Implementation guidance relevant to the lab:
  - Create a webhook: Product menu > Integrations > Incoming Webhook, choose the channel [1].
  - Post: HTTP POST of JSON with `text` (Markdown; required unless `attachments`), optional `channel` (name, not display name), `username`, `icon_url`. Posts over 16,383 characters are split [1].
  - Slack-style payloads are accepted; gaps include `<!everyone>`, `mrkdwn`, `parse`, `link_names` [1].
  - Personal access token flow: enable under System Console > Integrations > Integration Management, give the account the role to generate tokens, create under Profile > Security [2]. The Bearer header format is not shown on the pages fetched.
  - The lab uses /api/v4/system/ping; the fetched API landing page lists no endpoints [10].
- Version notes: v11 ended MySQL support; PostgreSQL 15 is the minimum; user sessions and personal access tokens can no longer set post identity props such as `from_webhook` or `override_username` (silently stripped), while webhooks, slash commands and bots are unaffected; v12.0 needs glibc 2.34 or later; the v10.11 ESR reached end of life on 2026-08-15 [3].
- Where this project differs:
  - sdr-5 posts with a personal access token (Secret mm-api). The vendor notes PAT-set identity props are now stripped and points scripts to webhooks or bot accounts [2][3]. Report only.
  - The webhook URL is held in the env var MM_WEBHOOK_URL and posted with curl; the SDR modules already call it a secret [1].
  - Modules call Mattermost over plain http in-cluster (mattermost.chat.svc.cluster.local:8065); the vendor treats a TLS proxy as a production prerequisite [4]. Labeled lab shortcut.
  - The lab Mattermost deployment is not in the repository yet (LAB-CONTRACT). The Operator path, PostgreSQL and backup are not exercised by any module.
- Unconfirmed: Bearer header usage and API rate limits (API pages showed neither); webhook rate limits (page silent); the Mattermost version the lab deploys; a server-hardening page (the URL tried returned 404); which listed hardening controls need a paid tier.
