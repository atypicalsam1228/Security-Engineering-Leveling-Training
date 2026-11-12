# Two-part sample for ENG-1: client calls web. Both run in net-lab with no network policy, so the path works at the start.
# web runs a tiny HTTP server on 8080. client only sleeps; the learner runs curl inside it with oc exec.
# The .tpl suffix keeps lab start from applying this file directly; 20-app.sh applies it.
apiVersion: v1
kind: ServiceAccount
metadata: {name: web, namespace: net-lab}
---
apiVersion: v1
kind: ServiceAccount
metadata: {name: client, namespace: net-lab}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: net-lab
  labels: {app: web}
spec:
  replicas: 1
  selector: {matchLabels: {app: web}}
  template:
    metadata: {labels: {app: web}}
    spec:
      serviceAccountName: web
      securityContext: {runAsNonRoot: true, seccompProfile: {type: RuntimeDefault}}
      containers:
        - name: app
          image: registry.access.redhat.com/ubi9/python-311:1
          command: ["python3", "-m", "http.server", "8080"]
          ports: [{containerPort: 8080}]
          securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: ["ALL"]}}
          resources: {requests: {cpu: 10m, memory: 48Mi}, limits: {memory: 192Mi}}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: client
  namespace: net-lab
  labels: {app: client}
spec:
  replicas: 1
  selector: {matchLabels: {app: client}}
  template:
    metadata: {labels: {app: client}}
    spec:
      serviceAccountName: client
      securityContext: {runAsNonRoot: true, seccompProfile: {type: RuntimeDefault}}
      containers:
        - name: app
          image: registry.access.redhat.com/ubi9/ubi-minimal:9.5
          command: ["sleep", "infinity"]
          securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: ["ALL"]}}
          resources: {requests: {cpu: 10m, memory: 32Mi}, limits: {memory: 128Mi}}
---
apiVersion: v1
kind: Service
metadata: {name: web, namespace: net-lab}
spec: {selector: {app: web}, ports: [{port: 8080, targetPort: 8080}]}
