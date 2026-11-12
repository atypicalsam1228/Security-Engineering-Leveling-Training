# TODO: start state for SDR-2 (Triage an Alert by Runbook)

`+ [done]` lines are covered by files in this folder; `- [live]` lines can only be confirmed on a live cluster;
`- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: Exercise records, alert messages, runbook ConfigMap.
- [live] 1: Loki accepts pushes with timestamps up to 3 hours old and the extra label lab_seed (the default age limit for old samples is 7 days).
- [live] 1: Push endpoint and basic auth: LOKI_URL + /loki/api/v1/push with LOKI_USER and LOKI_PASSWORD, as the other lab scripts use.
- [live] 4: Collector pod label app.kubernetes.io/component=collector (used by triage.py path; label set by the platform log operator).
- [lab-build] 3: Falco output reaches Loki as application logs from namespace security-tools (the seeded lines copy that shape).
- [lab-build] 3: The Keycloak event listener logs successful LOGIN events (info level) as well as LOGIN_ERROR.
- [lab-build] 4: Mattermost channel siem-alerts behind MM_WEBHOOK_URL; MM_URL and GRAFANA_URL reachable from lab shell.
- Decision: lab reset leaves old seeded records in Loki; every record has seed_run=<anchor> and triage.py reads only the current anchor. Each lab start also asks Loki to delete older copies (best effort).
- [live] Check POST /loki/api/v1/delete with a seed_run!= matcher is accepted (HTTP 204) and whether queries hide deleted lines before delete_request_cancel_period (platform default 24h) ends. Nothing depends on it.
+ [done] 2: alert messages A-101 to A-104 and ConfigMap sdr-runbook.
+ [done] 4: log collector and forwarder created if missing (10-forwarder.sh).
