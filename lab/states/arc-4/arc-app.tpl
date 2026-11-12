# Sample application for ARC-4: web, api, db plus three attack pods. __NS__ is replaced by sed.
# Services and deployments select on the tier label so that an attack pod that copies the app label is not an endpoint.
# The .tpl suffix keeps lab start from applying this file directly. Network policies and mesh policies are NOT here: the learner applies them.
apiVersion: v1
kind: ServiceAccount
metadata: {name: web, namespace: __NS__}
---
apiVersion: v1
kind: ServiceAccount
metadata: {name: api, namespace: __NS__}
---
apiVersion: v1
kind: ServiceAccount
metadata: {name: db, namespace: __NS__}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: __NS__
  labels: {app: web, tier: web}
spec:
  replicas: 1
  selector: {matchLabels: {tier: web}}
  template:
    metadata: {labels: {app: web, tier: web}}
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
  name: api
  namespace: __NS__
  labels: {app: api, tier: api}
spec:
  replicas: 1
  selector: {matchLabels: {tier: api}}
  template:
    metadata: {labels: {app: api, tier: api}}
    spec:
      serviceAccountName: api
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
  name: db
  namespace: __NS__
  labels: {app: db, tier: db}
spec:
  replicas: 1
  selector: {matchLabels: {tier: db}}
  template:
    metadata: {labels: {app: db, tier: db}}
    spec:
      serviceAccountName: db
      securityContext: {runAsNonRoot: true, seccompProfile: {type: RuntimeDefault}}
      containers:
        - name: app
          image: registry.access.redhat.com/ubi9/python-311:1
          command: ["python3", "-m", "http.server", "8080"]
          ports: [{containerPort: 8080}]
          securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: ["ALL"]}}
          resources: {requests: {cpu: 10m, memory: 48Mi}, limits: {memory: 192Mi}}
---
apiVersion: v1
kind: Service
metadata: {name: web, namespace: __NS__}
spec: {selector: {tier: web}, ports: [{port: 8080, targetPort: 8080}]}
---
apiVersion: v1
kind: Service
metadata: {name: api, namespace: __NS__}
spec: {selector: {tier: api}, ports: [{port: 8080, targetPort: 8080}]}
---
apiVersion: v1
kind: Service
metadata: {name: db, namespace: __NS__}
spec: {selector: {tier: db}, ports: [{port: 8080, targetPort: 8080}]}
---
apiVersion: v1
kind: ServiceAccount
metadata: {name: intruder, namespace: __NS__}
---
apiVersion: v1
kind: Pod
metadata:
  name: atk-stranger
  namespace: __NS__
  labels: {app: atk, sidecar.istio.io/inject: "false"}
spec:
  securityContext: {runAsNonRoot: true, seccompProfile: {type: RuntimeDefault}}
  containers:
    - name: app
      image: registry.access.redhat.com/ubi9/python-311:1
      command: ["sleep", "infinity"]
      securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: ["ALL"]}}
      resources: {requests: {cpu: 10m, memory: 32Mi}, limits: {memory: 128Mi}}
---
apiVersion: v1
kind: Pod
metadata:
  name: atk-copied-plain
  namespace: __NS__
  labels: {app: api, sidecar.istio.io/inject: "false"}
spec:
  securityContext: {runAsNonRoot: true, seccompProfile: {type: RuntimeDefault}}
  containers:
    - name: app
      image: registry.access.redhat.com/ubi9/python-311:1
      command: ["sleep", "infinity"]
      securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: ["ALL"]}}
      resources: {requests: {cpu: 10m, memory: 32Mi}, limits: {memory: 128Mi}}
---
apiVersion: v1
kind: Pod
metadata:
  name: atk-copied-mesh
  namespace: __NS__
  labels: {app: api}
spec:
  serviceAccountName: intruder
  securityContext: {runAsNonRoot: true, seccompProfile: {type: RuntimeDefault}}
  containers:
    - name: app
      image: registry.access.redhat.com/ubi9/python-311:1
      command: ["sleep", "infinity"]
      securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: ["ALL"]}}
      resources: {requests: {cpu: 10m, memory: 32Mi}, limits: {memory: 128Mi}}
