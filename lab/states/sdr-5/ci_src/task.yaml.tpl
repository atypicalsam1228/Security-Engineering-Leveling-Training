apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: detections-step
  namespace: build
spec:
  params:
    - name: branch
      type: string
      default: main
    - name: script
      type: string
  volumes:
    - name: work
      emptyDir: {}
    - name: ca
      secret:
        secretName: detections-ci-ca
  stepTemplate:
    image: registry.access.redhat.com/ubi9/python-312:1
    workingDir: /work
    envFrom:
      - secretRef:
          name: detections-ci
    env:
      - name: HOME
        value: /tmp
      - name: LOKI_CA_FILE
        value: /etc/ca/ca.crt
      - name: SSL_CERT_FILE
        value: /etc/ca/ca.crt
      - name: BRANCH
        value: $(params.branch)
      - name: CI_SCRIPT
        value: $(params.script)
    volumeMounts:
      - name: work
        mountPath: /work
      - name: ca
        mountPath: /etc/ca
  steps:
    - name: clone
      script: |
        #!/bin/sh
        set -e
        mkdir -p /work/repo
        curl -sf --cacert /etc/ca/ca.crt -H "Authorization: token $GITEA_TOKEN" "$GITEA_URL/api/v1/repos/$GITEA_USER/detections/archive/$BRANCH.tar.gz" | tar -xz --strip-components=1 -C /work/repo
    - name: run
      script: |
        #!/bin/sh
        set -e
        cd /work/repo
        python3 "ci/$CI_SCRIPT"
