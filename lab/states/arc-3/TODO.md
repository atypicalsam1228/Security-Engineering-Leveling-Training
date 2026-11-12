# TODO: start state for ARC-3 (Choose an Admission Mode)
- platform tool: Kyverno 1.19.2 (lab_needs); required in the kyverno namespace.

+ [done] 1: namespace, kit, policies, gate.
- [live] 1: oc create --dry-run=server calls the Kyverno webhook (sideEffects NoneOnDryRun) so timings include it.
- [live] 1: policyreport resource name and the reason string PolicyViolation in 1.19; report results carry the pod in scope.name (resources[] is empty in 1.19.2); snapshot.py handles both.
- [live] 2: oc adm top pods works on the single-node cluster (monitoring stack present); metrics lag may need more than the 60 s settle time.
- [live] 1: with autogen-controllers=none and Enforce, the load Deployment is created and its ReplicaSet reports FailedCreate events.
- [live] 1: SCC admission does not add runAsNonRoot to case-root.
- [live] 3: registry.access.redhat.com/ubi9/ubi-minimal:9.5 can be pulled; the deliberate :latest case is a negative sample.
- [live] 1: blocked (Enforce) requests are recorded as events on the ClusterPolicy per Kyverno docs; confirm the message names arc-measure so snapshot.py counts it.
- note: kit/cases/latest.yaml and kit/load.yaml use :latest on purpose (negative cases); all other images are pinned to 9.5.
