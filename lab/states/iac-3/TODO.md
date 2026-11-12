# TODO: start state for IAC-3 (Terraform or Ansible, Choose by Evidence)
- no extra platform tools; uses terraform, ansible-playbook, ansible-lint, oc, python3 (3.9) from the lab image.

+ [done] 1: clean start, supplied Terraform baseline applied with a local state file, empty ansible folder.
+ [done] 1: (scratch cluster) provider resource names (kubernetes_namespace_v1, kubernetes_resource_quota_v1, kubernetes_network_policy_v1, kubernetes_role_v1, kubernetes_role_binding_v1) checked against provider 3.4.0 schema output.
+ [done] 1: (scratch cluster) the provider does not read KUBECONFIG (documented), so main.tf sets config_path.
+ [done] 2: (scratch cluster) ansible-playbook --check exits 0 even when the check would change objects; the PLAY RECAP changed= count is the signal (module scripts read that).
+ [done] 2: (scratch cluster) the first Ansible run on Terraform-made objects reports changed=0 only if the definitions match exactly. A Group subject made the provider add namespace default to the binding, and the provider sorts role rule resources, so the baseline uses a service account subject and sorted resource names.
- [live] 1: on OpenShift a new namespace gets extra annotations and labels; main.tf ignores openshift.io, pod-security and security.openshift.io keys with ignore_annotations and ignore_labels. Confirm terraform plan returns 0 right after apply on the real cluster.
- [live] 1: OpenShift and OpenShift Pipelines create role bindings openshift-pipelines-edit, pipelines-scc-rolebinding, system:deployers, system:image-builders and system:image-pullers in a new namespace; conformance.py allows exactly those five names. Confirm the list on the real cluster, and that no network policy exists in a new namespace.
- [live] 2: ansible-lint prints "WARNING: PATH altered ..." when started through the /usr/local/bin symlink; confirm it does not change the result in the image.
- [live] 3: python3 3.9 in the image runs measure.py and conformance.py (syntax checked on 3.9; run on 3.12 only). PyYAML comes from the image package python3-pyyaml.
- [live] 3: oc create rolebinding --serviceaccount and oc patch --type=merge work with oc 4.22.
- [live] 3: kubernetes.core.k8s finds the cluster from the exported KUBECONFIG (no kubeconfig argument in the playbook). Confirm in the image venv.
+ [done] 4: KUBECONFIG is exported by the lab shell and main.tf sets config_path to the same file.
- [live] 5: the start state applies the baseline and the plan right after apply exits 0 on the real cluster.
- [live] 4: timings are measured by the harness at run time; none are stated in the module text.
