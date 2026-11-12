# Notes: git-chat scripts (20, 30, 40)

All three are written to the platform brief, pass `bash -n`, and have NOT been run on a live cluster (no cluster available when written; shellcheck is not installed on the build machine). Pins are in `versions-git-chat.txt`.

## 20-gitea.sh (namespace gitea)
- Deployment `gitea` (label `app=gitea`), Service `gitea:3000`, Route `gitea` (edge TLS), PVC `gitea-data` 5Gi mounted at `/data`. Rootless image, SQLite. Requests 100m CPU / 256Mi, limit 1 CPU / 1Gi.
- Secrets: `gitea-admin` (keys `username`, `password`; the bastion save script reads these), `gitea-server` (`secret-key`).
- Repositories at `/data/git/gitea-repositories/<owner>/<repo>.git`; `curl` and `git` are in the image (Dockerfile.rootless at v28.3.0).
- Settings: registration closed, install locked, default branch `main`, `[security] ALLOWED_HOST_LIST=private,loopback` (from v28.0.0 the key is in `[security]`; `[webhook]` is deprecated), SSH off, console logging.
- Admin user `labadmin` (`admin` is reserved in Gitea). Token created with `gitea admin user generate-access-token --scopes all`, so it is an administrator token with repository, status, hook and branch-protection rights (GRC-3 and AID-3 need these).
- Saves: GITEA_URL, GITEA_INTERNAL_URL, GITEA_USER, GITEA_TOKEN.
- SCC: restricted-v2 only. All writable paths (HOME, work dir, custom dir, app.ini) are on the PVC because OpenShift assigns a random UID.

## 30-mattermost.sh (namespace chat)
- Deployments `mattermost` and `mattermost-db` (PostgreSQL 16, sclorg image, PVC 5Gi each), Service, Route. Requests: server 150m / 512Mi (limit 1 CPU / 1.5Gi), database 50m / 128Mi (limit 512Mi).
- Configuration is stored in PostgreSQL (`MM_CONFIG` = database address) so the image's config folder is not written. Plugin folders, `/tmp`, `/var/tmp` are emptyDir; data is on a PVC.
- `mmctl --local` (socket in `/var/tmp`) creates: administrator `labadmin`, team `lab`, public channel `siem-alerts`, incoming webhook `lab-alerts` for that channel, and a personal access token.
- Secrets: `mattermost-db`, `mattermost-admin`, `mattermost-env` (database address) in `chat`; `mm-api` (key `token`) in `siem`, which `lab/states/sdr-5/40-preflight.sh` checks.
- Saves: MM_URL, MM_WEBHOOK_URL (both the https Route address, because SDR-2 posts to the webhook from lab shell).

## 40-keycloak.sh (namespace keycloak)
- Deployment `keycloak` (`start-dev`, embedded H2 file database on a 2Gi PVC), Service, Route. Requests 200m / 768Mi, limit 1 CPU / 1.5Gi.
- Admin: KEYCLOAK_ADMIN_USER (default `admin` when unset) and KEYCLOAK_ADMIN_PASSWORD from lab.env, passed through secret `keycloak-admin`.
- Sign-in events: `KC_SPI_EVENTS_LISTENER__JBOSS_LOGGING__SUCCESS_LEVEL=info`, so LOGIN is logged at INFO and LOGIN_ERROR at WARN as `[org.keycloak.events] type="LOGIN", realmId="lab", ...`. Realm `lab` is created with id `lab` so `realmId="lab"` matches the module log lines.
- Saves: KEYCLOAK_URL, KEYCLOAK_ADMIN_USER.

## Unverified (needs a live run)
- Mattermost: that the Team Edition image has `/mattermost/bin/mmctl` and starts with a random UID with the mounts above; the `mmctl` list output formats used for the "already exists" checks.
- Keycloak: `-Dcom.redhat.fips=false` stops the JDK's host FIPS integration (documented for Red Hat OpenJDK; not tested with this image on a FIPS node); `start-dev` plus `KC_HOSTNAME` full URL behind the edge Route; the SPI environment variable name `KC_SPI_EVENTS_LISTENER__JBOSS_LOGGING__SUCCESS_LEVEL` (derived from the documented `--spi-<spi>--<provider>--<option>` rule; the SPI id is `eventsListener`).
- Gitea: `docker.gitea.com` pull works from the cluster; `gitea` binary on PATH inside `oc exec`.
- How the collector stores a Keycloak line (plain text or JSON) is a siem-side question.
- Grafana contact point `mattermost` uses `MM_WEBHOOK_URL` (https Route). The Grafana pod must trust the ingress CA (siem agent: mount `LOKI_CA_FILE` as the Grafana CA, or set `SSL_CERT_FILE`).
