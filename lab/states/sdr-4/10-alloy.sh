#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Creates a second Alloy instance, alloy-detect, in namespace siem. It receives test
# events on port 3500, runs the labeling stage in ConfigMap alloy-detect-label (a pass-through at the start) and writes
# to Loki. The image is copied from the existing Deployment alloy in siem, so no version is chosen here.
# Alloy reads every .alloy file in /etc/alloy, so the learner replaces only label.alloy.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env LOKI_URL LOKI_USER LOKI_PASSWORD LOKI_CA_FILE
here="$(cd "$(dirname "$0")" && pwd)"
ensure_namespace siem
image=$(oc get deployment alloy -n siem -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null) || true
[ -n "$image" ] || die "Deployment alloy was not found in namespace siem (the lab build provides Alloy); cannot copy its image"
oc create configmap alloy-detect-base -n siem --from-file=base.alloy="$here/alloy/base.alloy" --dry-run=client -o yaml | oc apply -f - >/dev/null
if ! oc get configmap alloy-detect-label -n siem >/dev/null 2>&1; then
  oc create configmap alloy-detect-label -n siem --from-file=label.alloy="$here/alloy/label.alloy" --dry-run=client -o yaml | oc apply -f - >/dev/null
fi
oc create secret generic alloy-detect-loki -n siem --from-literal=username="$LOKI_USER" --from-literal=password="$LOKI_PASSWORD" \
  --from-file=ca.crt="$LOKI_CA_FILE" --dry-run=client -o yaml | oc apply -f - >/dev/null
oc apply -f - >/dev/null <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alloy-detect
  namespace: siem
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alloy-detect
  template:
    metadata:
      labels:
        app: alloy-detect
    spec:
      containers:
        - name: alloy
          image: ${image}
          args:
            - run
            - /etc/alloy
            - --storage.path=/tmp/alloy
            - --server.http.listen-addr=0.0.0.0:12345
          env:
            - name: LOKI_URL
              value: "${LOKI_URL}"
            - name: LOKI_USER
              valueFrom:
                secretKeyRef:
                  name: alloy-detect-loki
                  key: username
            - name: LOKI_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: alloy-detect-loki
                  key: password
          ports:
            - containerPort: 3500
          volumeMounts:
            - name: config
              mountPath: /etc/alloy
            - name: loki-ca
              mountPath: /etc/loki-ca
      volumes:
        - name: config
          projected:
            sources:
              - configMap:
                  name: alloy-detect-base
              - configMap:
                  name: alloy-detect-label
        - name: loki-ca
          secret:
            secretName: alloy-detect-loki
---
apiVersion: v1
kind: Service
metadata:
  name: alloy-detect
  namespace: siem
spec:
  selector:
    app: alloy-detect
  ports:
    - port: 3500
      targetPort: 3500
EOF
oc rollout status deployment/alloy-detect -n siem --timeout=240s
