# TODO: start state for CPS-5 (Guardrails Developers Inherit)

Lab needs are numbered as in the module's lab_needs list. `+ [done]` lines are covered by files in this folder;
`- [live]` lines can only be confirmed on a live cluster or account; `- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: the twelve-workload corpus (10-corpus.sh).
- [lab-build] 1: Kyverno 1.19.2 (Helm chart 3.9.2) in namespace kyverno; do not install 1.20 or later (ClusterPolicy is removed there). 20-preflight-kyverno.sh checks it.
- [live] 1: the background controller service account is named kyverno-background-controller and the aggregation label rbac.kyverno.io/aggregate-to-background-controller works on this chart version.
- [live] 1: openshift.io/requester is present on a Namespace at the moment oc new-project creates it, so the exclude in the generate policy can see it.
- [live] 1: Kyverno autogen applies the Pod mutate and validate rules to Deployments, including the add-if-absent anchors.
- [live] 1: Changing projectRequestTemplate restarts openshift-apiserver; confirm how long the project API is unavailable on a single node.
- [live] 2: registry.access.redhat.com/ubi9/ubi-minimal can be pulled (workloads run at zero replicas).
- [live] 3: OVN-Kubernetes enforces NetworkPolicy.
- [live] 4: python3 available in the lab shell.
- [lab-build] 5: an image registry at REGISTRY_HOST (lab platform script 10-registry.sh sets it to the built-in registry, image-registry.openshift-image-registry.svc:5000). The registry test creates Deployments with zero replicas (nothing is pulled), so no image has to exist there. Image signing (cosign, Kyverno verifyImages) is not used because the lab provides no signed image or key.
- [live] 5: the registry rule (pattern image: a/* | b/* with =(initContainers)) is enforced for Deployments through Kyverno autogen on 1.19.2.
- [live] 5: check-registry.py (Python wildcard match) agrees with Kyverno's own matcher for the six sample names, and the learner-written registry rule with =(initContainers) is accepted and enforced on 1.19.2. Locally the script and the reference answer were tested; nothing ran against Kyverno.
