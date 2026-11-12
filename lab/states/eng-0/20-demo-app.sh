#!/usr/bin/env bash
# Idempotent: Deployment demo-app (1 replica, label app=demo-app) in namespace demo. ENG-0 scales it to 0 and back in its negative test.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_demo_app
# Short stop grace period so the ENG-0 negative test does not wait 30 seconds for the pod (patched here, not in the shared manifest).
oc patch deployment demo-app -n demo --type=merge -p '{"spec":{"template":{"spec":{"terminationGracePeriodSeconds":5}}}}' >/dev/null
oc rollout status deployment/demo-app -n demo --timeout=240s
