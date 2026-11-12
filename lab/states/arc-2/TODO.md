# TODO: start state for ARC-2 (Trace the Security Stack)
- platform tool: Kyverno 1.19.2 (lab_needs); required in the kyverno namespace.

+ [done] 1: Kyverno policies, app, network policies, script install.
- [live] 1: Kyverno 1.19.2 honours validate.failureAction at rule level and the autogen-controllers=none annotation.
- [live] 1: Audit violations appear in a policyreport resource (name may differ in 1.19; module Step 5 tells the learner to stop if none).
- [live] 3: registry.access.redhat.com/ubi9/python-311:1 exists and starts as non-root; $HOME inside lab start scripts is the learner's lab shell home.
- [live] 3: OpenShift SCC admission does not add runAsNonRoot to probe-root.
- [live] 2: OVN-Kubernetes enforces network policies on the cluster.
