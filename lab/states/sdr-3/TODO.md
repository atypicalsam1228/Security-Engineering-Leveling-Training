# TODO: start state for SDR-3 (Investigate and Tune)

`+ [done]` lines are covered by files in this folder; `- [live]` lines can only be confirmed on a live cluster;
`- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: Records, ConfigMap, rule, dashboard, gate.
- [live] 2: Grafana provisioning alert-rules GET and PUT return the shape the module edits (data[1].model.conditions[0].evaluator.params).
- [live] 2: POST /api/dashboards/db accepts the dashboard JSON written by 30-grafana.sh and a jq-edited copy with overwrite true.
- [live] 1: Loki range semantics for [5m]: confirm the noise peak is 4 and not 5 (edge inclusion).
- [live] 1: Audit and Keycloak line shapes as in SDR-2 (fields user_username and objectRef_resource flatten under the json parser).
- [lab-build] 3: Grafana Loki data source named Loki; Keycloak and audit logs in Loki.
- Decision: old seeded records stay in Loki after lab reset; every record has seed_run=<anchor> and the module searches and gate pin to it (lab_seed and seed_run). Each lab start also asks Loki to delete older copies (best effort). Replay records carry their own run label.
- Decision: seeded records sit within 2 hours of the anchor, because Loki serves records older than about 3 hours only after flushing them (about 30 minutes after the push).
+ [done] 2: alert rule failed-login-burst, dashboard sdr-auth-overview, ConfigMap sdr-review.
- [live] 4: The lab shell can reach Loki and Grafana with the lab variables.
- [live] 2: GET /api/prometheus/grafana/api/v1/rules answers on the pinned Grafana with name, health and lastError for failed-login-burst, and health is ok (not nodata) when the search returns no data, because the rule maps no data to OK.
