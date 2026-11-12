# TODO: start state for ARC-5 (Verify a Reference Architecture)
- platform tool: Kyverno 1.19.2 (lab_needs); required in the kyverno namespace.

+ [done] 1: namespace, app, kit.
- [live] 1: Kyverno 1.19.2 accepts operations [CREATE, UPDATE] in match.any[].resources, rule-level failureAction, and the pattern value "api | cache | db | web".
- [live] 2: oc exec deploy/NAME -c app works for all four deployments; the socket probe takes about 3 seconds per blocked pair and the 12 probes run in parallel.
- [live] 3: Kyverno does not block deleting a NetworkPolicy or the delete of the arc-ref-flows policy itself (drift_timer relies on both deletes working).
- [live] 4: python3 in the tools image is 3.9 with PyYAML (versions.txt lists python3-pyyaml); all scripts avoid newer syntax.
