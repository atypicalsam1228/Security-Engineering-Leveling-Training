# Sample workload for the containment step of SDR-4: a Deployment (suspect-app) with a Service, and a helper pod (probe)
# that only sleeps, so the learner can call the others from inside the project demo with oc exec.
# The .tpl suffix keeps lab start from applying this file directly; 15-suspect.sh applies it.
apiVersion: v1
kind: ServiceAccount
metadata: {name: suspect-app, namespace: demo}
---
apiVersion: v1
kind: ServiceAccount
metadata: {name: probe, namespace: demo}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: suspect-app
  namespace: demo
  labels: {app: suspect-app}
spec:
  replicas: 1
  selector: {matchLabels: {app: suspect-app}}
  template:
    metadata: {labels: {app: suspect-app}}
    spec:
      serviceAccountName: suspect-app
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
  name: probe
  namespace: demo
  labels: {app: probe}
spec:
  replicas: 1
  selector: {matchLabels: {app: probe}}
  template:
    metadata: {labels: {app: probe}}
    spec:
      serviceAccountName: probe
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
metadata: {name: suspect-app, namespace: demo}
spec: {selector: {app: suspect-app}, ports: [{port: 8080, targetPort: 8080}]}
