#!/usr/bin/env bash
# Installs the in-lab services, one numbered script at a time. Safe to repeat: finished services are skipped.
# Runs inside the tools container (lab platform). Usage: install.sh [--only NN]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/lib.sh"

ONLY=""
if [ "${1:-}" = "--only" ]; then ONLY="${2:-}"; [ -n "$ONLY" ] || die "--only needs a number, for example --only 20"; fi

require_cluster
ran=0
for script in "$HERE"/[0-9][0-9]-*.sh; do
  [ -e "$script" ] || die "no install scripts found in $HERE"
  name="$(basename "$script")"
  case "$name" in "$ONLY"*) ;; *) [ -z "$ONLY" ] || continue ;; esac
  echo "== $name"
  bash "$script"
  ran=$((ran + 1))
done
[ "$ran" -gt 0 ] || die "no install script starts with '$ONLY'"
echo "== done: $ran script(s)"
