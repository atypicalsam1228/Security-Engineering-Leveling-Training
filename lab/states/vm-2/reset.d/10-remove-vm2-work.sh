#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes the hand-off ConfigMaps the learner stored.
set -uo pipefail
oc delete configmap -l handoff=scan-handoff -A --ignore-not-found
