# TODO: start state for GRC-5 (Continuous Control Monitoring Design)

Lab needs are numbered as in the module's lab_needs list. `+ [done]` lines are covered by files in this folder;
`- [live]` lines can only be confirmed on a live cluster or account; `- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: Three Audit policies for demo.
- [live] 1: PolicyReport API group wgpolicyk8s.io and result fields (policy, result, timestamp.seconds) and the scope field on each report on Kyverno 1.19.2; background scan interval, so reports may take time to appear.
+ [done] 2: demo-app is deployed by 10-demo-app.sh.
- [live] 2: demo-app carries no owner label, so grc-require-owner-label reports a failure (confirm in the demo-app manifest).
+ [done] 3: Service account, read Role and binding, volume claim.
- [live] 4: Pods in build can pull registry.access.redhat.com/ubi9/python-312:1 and quay.io/openshift/origin-cli:4.22.0 (the cluster reaches the internet), /usr/bin/oc exists in the second image (verified 2026-11-02 by reading the image layers), and oc in the Python pod uses the service account token without a kubeconfig.
