# Sample application for ARC-5: web, api, db and cache, no policies. __NS__ is replaced by sed.
# The .tpl suffix keeps lab start from applying this file directly. The learner generates and applies every policy.
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
  selector: {matchLabels: {app: web}}
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
  selector: {matchLabels: {app: api}}
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
  selector: {matchLabels: {app: db}}
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
spec: {selector: {app: web}, ports: [{port: 8080, targetPort: 8080}]}
---
apiVersion: v1
kind: Service
metadata: {name: api, namespace: __NS__}
spec: {selector: {app: api}, ports: [{port: 8080, targetPort: 8080}]}
---
apiVersion: v1
kind: Service
metadata: {name: db, namespace: __NS__}
spec: {selector: {app: db}, ports: [{port: 8080, targetPort: 8080}]}
---
apiVersion: v1
kind: ServiceAccount
metadata: {name: cache, namespace: __NS__}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cache
  namespace: __NS__
  labels: {app: cache, tier: cache}
spec:
  replicas: 1
  selector: {matchLabels: {app: cache}}
  template:
    metadata: {labels: {app: cache, tier: cache}}
    spec:
      serviceAccountName: cache
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
metadata: {name: cache, namespace: __NS__}
spec: {selector: {app: cache}, ports: [{port: 8080, targetPort: 8080}]}