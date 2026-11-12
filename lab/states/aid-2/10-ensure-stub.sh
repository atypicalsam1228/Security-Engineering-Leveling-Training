#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: deploys the deterministic stub model service in namespace ai-lab.
# Other AID start states call this file, so the stub code lives in one place (stub/stub.py).
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
STUB_DIR="$(cd "$(dirname "$0")" && pwd)/stub"

ensure_namespace ai-lab
oc create configmap stub-model-code -n ai-lab --from-file=stub.py="$STUB_DIR/stub.py" --dry-run=client -o yaml | oc apply -f - >/dev/null
oc apply -f "$STUB_DIR/stub-deployment.yaml" >/dev/null
# A changed ConfigMap does not restart the pod by itself, so restart when the code differs from what runs.
want=$(sha256sum "$STUB_DIR/stub.py" | cut -d' ' -f1)
have=$(oc get deployment stub-model -n ai-lab -o jsonpath='{.spec.template.metadata.annotations.stub-sha256}' 2>/dev/null || true)
if [ "$want" != "$have" ]; then
  oc patch deployment stub-model -n ai-lab --type merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"stub-sha256\":\"$want\"}}}}}" >/dev/null
fi
oc rollout status deployment/stub-model -n ai-lab --timeout=180s
# Check from inside the cluster that the scripted answers work (no secret involved).
reply=$(oc exec -n ai-lab deployment/stub-model -- python3 -c 'import json,urllib.request as u;r=u.Request("http://127.0.0.1:8080/v1/answer",json.dumps({"request_id":"summary-ok"}).encode());print(json.load(u.urlopen(r))["model"])') || die "the stub model service did not answer"
say "stub model service answers (model $reply)"
