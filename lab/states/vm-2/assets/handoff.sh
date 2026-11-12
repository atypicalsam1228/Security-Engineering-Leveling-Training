#!/usr/bin/env bash
# Usage: bash handoff.sh scans.tsv NAME
# scans.tsv has one line per scan, tab separated: kind, target, report file, trivy exit code.
# Builds the fixed hand-off JSON (schema scan-handoff/1) and stores it as ConfigMap NAME in security-tools.
# A scan that failed is never reported as zero findings: its counts are null and the hand-off says escalate.
set -euo pipefail
list=${1:?usage: bash handoff.sh scans.tsv NAME}
name=${2:?usage: bash handoff.sh scans.tsv NAME}
namespace=security-tools
scans='[]'

while IFS=$'\t' read -r kind target file rc; do
  if [ "$rc" != 0 ] || ! jq -e . "$file" >/dev/null 2>&1; then
    status=failed
  elif jq -e '(.Results // []) | length == 0' "$file" >/dev/null; then
    status=partial
  else
    status=complete
  fi
  if [ "$status" = failed ]; then
    row=$(jq -nc --arg kind "$kind" --arg target "$target" --arg file "$file" --argjson rc "$rc" \
      '{kind: $kind, target: $target, status: "failed", exit_code: $rc, critical: null, high: null, medium: null, low: null, fixable: null, report: $file}')
  else
    row=$(jq -c --arg kind "$kind" --arg target "$target" --arg status "$status" --arg file "$file" --argjson rc "$rc" '
      def n($s): [.Results[]? | (.Vulnerabilities[]?, .Misconfigurations[]?) | select(.Severity == $s)] | length;
      {kind: $kind, target: $target, status: $status, exit_code: $rc,
       critical: n("CRITICAL"), high: n("HIGH"), medium: n("MEDIUM"), low: n("LOW"),
       fixable: ([.Results[]?.Vulnerabilities[]? | select((.FixedVersion // "") != "")] | length),
       report: $file}' "$file")
  fi
  scans=$(jq -c --argjson row "$row" '. + [$row]' <<<"$scans")
done <"$list"

now=$(date -u +%FT%TZ)
who=$(oc whoami)
mkdir -p "out/$name"
jq -n --argjson scans "$scans" --arg now "$now" --arg who "$who" '
  ([$scans[] | select(.status != "complete") | "\(.kind) scan \(.status)"]
   + [$scans[] | select((.critical // 0) > 0) | "\(.kind) has \(.critical) critical findings"]) as $reasons
  | {schema: "scan-handoff/1", scanned_at: $now, scanned_by: $who, scans: $scans,
     escalate: ($reasons | length > 0), reasons: $reasons}' >"out/$name/handoff.json"

oc create configmap "$name" -n "$namespace" --from-file="out/$name/handoff.json" --dry-run=client -o yaml | oc apply -f - >/dev/null
oc label configmap "$name" -n "$namespace" handoff=scan-handoff --overwrite >/dev/null
echo "stored configmap/$name in $namespace"
