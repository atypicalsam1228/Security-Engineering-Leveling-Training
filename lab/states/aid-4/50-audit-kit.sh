#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Stores the audit writer (audit.py) and the Loki helper it imports (ailog.py, the one copy kept in
# ../aid-3/) in ConfigMap aid4-kit in project ai-lab, so the learner extracts them instead of retyping the Loki push code from AID-3.
# Also stores the reference answers to the Step 2 writing exercise in ConfigMap aid4-ref, kept apart from aid4-kit (which the learner extracts into the agent folder).
# The learner still writes policy.py, agent.py and loop.py.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
ensure_namespace ai-lab
here="$(dirname "$0")"
oc create configmap aid4-kit -n ai-lab --from-file=audit.py="$here/kit/audit.py" --from-file=ailog.py="$here/../aid-3/ailog.py" --dry-run=client -o yaml | oc apply -f - >/dev/null
oc create configmap aid4-ref -n ai-lab --from-file=my_cases.py="$here/reference/my_cases.py" --from-file=kinds.py="$here/reference/kinds.py" --dry-run=client -o yaml | oc apply -f - >/dev/null
say "created ConfigMaps aid4-kit (audit.py and ailog.py) and aid4-ref (reference answers for the Step 2 exercise) in ai-lab"
