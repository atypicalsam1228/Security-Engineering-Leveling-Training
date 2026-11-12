#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes the seed marker so lab start seeds a fresh set of records.
# Removing the ConfigMap also removes the anchor, so triage.py can no longer find the old copy. Old records stay in Loki, but every
# record has seed_run=<anchor> and triage.py reads only the current anchor; the next lab start also asks Loki to delete the old copies.
# (Deleting here would be unsafe: a delete range processed later could remove the next copy.)
set -euo pipefail
oc delete configmap sdr-runbook -n siem --ignore-not-found >/dev/null
