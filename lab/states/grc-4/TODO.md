# TODO: start state for GRC-4 (Evidence in the Delivery Pipeline)

Lab needs are numbered as in the module's lab_needs list. `+ [done]` lines are covered by files in this folder;
`- [live]` lines can only be confirmed on a live cluster or account; `- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: Edit role for the pipeline service account in demo, volume claim evidence-work.
+ [done] 2: Config maps candidate-manifests and policy-kit (policy-check Task and reference admit.py), and the Enforce policy.
- [live] 2: Kyverno evaluates server-side dry-run requests, and generates the Deployment rule from the Pod rule (autogen default); the Ready condition on the policy.
- [live] 3: Pipeline pods can pull ghcr.io/aquasecurity/trivy:0.76.1, ubi9/python-312:1, origin-cli:4.22.0 and ghcr.io/sigstore/cosign/cosign:v3.1.4 (entrypoint /ko-app/cosign, verified 2026-11-02 from the image config), and reach the Trivy database and docker.io/library/nginx:1.16 (the cluster reaches the internet); cosign 3 accepts --use-signing-config=false and --tlog-upload=false.
- [live] 3: Trivy database reachable from pipeline pods; nginx:1.16 pullable or mirrored; cosign 3 accepts --use-signing-config=false and --tlog-upload=false; compact bundle text verifies the same as the file.
+ [done] 4: evidence-app (registry.k8s.io/pause:3.10, no OS packages) is the scanned workload; confirm trivy count is 0 on a live run.
- [live] 2: Tekton accepts a configMap volume in a Task and runs python3 /admit/admit.py from it; the ubi9/python-312 image has python3 on PATH.
