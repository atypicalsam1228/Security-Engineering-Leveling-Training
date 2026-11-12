# TODO: start state for IAC-2 (Deliver a Baseline as Code with Terraform)

- [live] 1: provider block in providers.tf: config_path /workspace/.lab/kubeconfig, and the ignore_annotations / ignore_labels regular expressions. Confirm that terraform plan right after the first apply exits 0 on a real OpenShift namespace (OpenShift adds its own annotations and labels).
- [live] 2: Gitea branch_protections fields, merge refusal code (405 assumed), raw endpoint with ?ref=, same open points as GRC-3.
- [live] 3: tkn pipeline start with -s pipeline --showlog; the finally task posts status iac-plan-gate; the pipeline pod can pull registry.access.redhat.com/ubi9/python-312:1-1762230134 (the cluster needs internet) and reaches Gitea at GITEA_INTERNAL_URL (plain HTTP inside the cluster, set by lab platform), so no CA is needed in the pod.
- [live] 4: 10-clean.sh removes /workspace/iac-2 only when run inside the lab shell; if lab start runs on the host, the learner folder must be removed by lab shell tooling.
- [lab-build] 5: git credential helper and identity are now set by the module itself (no lab-build need); Terraform 1.17.0 with provider mirror (verified locally only with Terraform 1.14.8).
- [live] 6: the learner is cluster-admin, so Terraform can create the namespace and its objects; OVN-Kubernetes enforces the NetworkPolicy the baseline creates.
- Not buildable offline: Terraform inside the cluster (by design the gate checks the committed plan.json).
