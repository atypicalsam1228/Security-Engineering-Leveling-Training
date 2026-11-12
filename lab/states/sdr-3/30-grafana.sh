#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Creates the noisy alert rule failed-login-burst (fires above 2 in 5 minutes,
# as a Loki count compared with a classic condition) and the dashboard sdr-auth-overview with one panel and a threshold line at 2.
# Each is created only if missing. Uses the Grafana provisioning, folder, data source and dashboard APIs.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GRAFANA_URL GRAFANA_USER GRAFANA_PASSWORD
folder_uid=$(grafana_get /api/folders | jq -r '[.[] | select(.title == "siem-detect") | .uid] | first // empty')
if [ -z "$folder_uid" ]; then
  folder_uid=$(grafana_send POST /api/folders '{"title":"siem-detect"}' | jq -r .uid)
fi
loki_uid=$(grafana_get /api/datasources/name/Loki | jq -r '.uid // empty')
[ -n "$folder_uid" ] && [ -n "$loki_uid" ] || die "could not read the siem-detect folder or the Loki data source in Grafana"
expr='sum(count_over_time({log_type="application", kubernetes_namespace_name="keycloak"} |= "LOGIN_ERROR" [5m]))'

if grafana_get /api/v1/provisioning/alert-rules | jq -e 'any(.[]?; .title == "failed-login-burst")' >/dev/null; then
  say "alert rule failed-login-burst already exists"
else
  query=$(jq -n --arg ds "$loki_uid" --arg expr "$expr" '{refId:"A",datasourceUid:$ds,relativeTimeRange:{from:600,to:0},model:{refId:"A",expr:$expr,queryType:"instant",instant:true}}')
  cond=$(jq -n '{refId:"B",datasourceUid:"-100",relativeTimeRange:{from:0,to:0},model:{refId:"B",type:"classic_conditions",datasource:{type:"__expr__",uid:"-100"},conditions:[{type:"query",query:{params:["A"]},reducer:{type:"last",params:[]},evaluator:{type:"gt",params:[2]},operator:{type:"and"}}]}}')
  rule=$(jq -n --arg folder "$folder_uid" --argjson a "$query" --argjson b "$cond" \
    '{title:"failed-login-burst",ruleGroup:"detect",folderUID:$folder,noDataState:"OK",execErrState:"Error","for":"0s",condition:"B",labels:{control:"AU-6"},annotations:{summary:"failed-login-burst"},data:[$a,$b]}')
  grafana_send POST /api/v1/provisioning/alert-rules "$rule" | jq -e '.uid' >/dev/null || die "Grafana refused the failed-login-burst rule"
fi

if [ "$(grafana_get /api/dashboards/uid/sdr-auth-overview | jq -r '.dashboard.uid // empty')" = sdr-auth-overview ]; then
  say "dashboard sdr-auth-overview already exists"
else
  dash=$(jq -n --arg ds "$loki_uid" --arg expr "$expr" --arg folder "$folder_uid" '{
    dashboard: {uid: "sdr-auth-overview", title: "Sign-in failures", schemaVersion: 39, time: {from: "now-6h", to: "now"},
      panels: [{id: 1, type: "timeseries", title: "Failed sign-ins per 5 minutes", gridPos: {h: 9, w: 24, x: 0, y: 0},
        datasource: {type: "loki", uid: $ds},
        targets: [{refId: "A", datasource: {type: "loki", uid: $ds}, expr: $expr, queryType: "range"}],
        fieldConfig: {defaults: {custom: {thresholdsStyle: {mode: "line"}},
          thresholds: {mode: "absolute", steps: [{color: "green", value: null}, {color: "red", value: 2}]}}, overrides: []}}]},
    folderUid: $folder, overwrite: false}')
  grafana_send POST /api/dashboards/db "$dash" | jq -e '.uid' >/dev/null || die "Grafana refused the dashboard"
fi
