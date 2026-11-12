# TODO: start state for AID-5 (Safe Adoption Pattern for Agents)

+ [done] 1: stub eval set, forwarder, Grafana setup, reset script.
- [live] 2: Kyverno 1.19.2: generate rule fields, YAML anchors, X() anchors, JMESPath [?!contains(...)] expressions.
- [live] 2: Aggregate ClusterRole label rbac.kyverno.io/aggregate-to-background-controller is enough for generation.
- [live] 4: OVN-Kubernetes enforces the generated NetworkPolicy; DNS at openshift-dns port 5353.
- [live] 3: Audit field names for impersonation (objectRef_resource, objectRef_namespace, verb) and the line filter on the full service account name.
- [live] 3: Grafana default rule-group interval for a new group; time to detect is measured, not assumed.
- [live] 4: Image ubi9/python-311:1 tag and probe pod admitted under the guardrail policy.
+ [done] 3: forwarder, Grafana Loki data source, contact point and folder siem-detect (20-forwarder.sh, 30-*).
- [lab-build] 1: Kyverno 1.19.2 installed in project kyverno (the start state only checks that the ClusterPolicy CRD exists). Grafana with a Loki data source named Loki, the audit forwarder label log_type=audit, and MM_WEBHOOK_URL.
