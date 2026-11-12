# TODO: start state for ARC-4 (Test Two Designs)
- platform tool: Red Hat OpenShift Service Mesh 3 Operator (lab_needs); installed by 10-service-mesh.sh.

+ [done] 1: mesh, namespaces, workloads, attack pods, latency script.
- [live] 1: sailoperator.io/v1 field names; the mesh deployment is named istiod in istio-system.
- [live] 2: AuthorizationPolicy and PeerAuthentication use security.istio.io/v1 on the installed mesh release.
- [live] 1: copied-label pod with a sidecar gets HTTP 403 (not a connection error) from the db sidecar; plaintext to a STRICT sidecar fails.
- [live] 1: with istiod scaled to 0, a new db pod in arc-b is refused by the sidecar injection webhook (Istio documents failurePolicy Fail), so FailedCreate events appear and no pod exists; the Sail operator may restore the istiod replica count.
- [live] 3: oc adm top pod --containers lists the istio-proxy container; ubi9/python-311:1 exists.
- [live] 4: registry.access.redhat.com/ubi9/python-311:1 can be pulled.
