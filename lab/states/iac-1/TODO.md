# TODO: start state for IAC-1 (Run a Supplied Baseline as Code)

Lab needs are numbered as in the module's lab_needs list. `+ [done]` lines are covered by files in this folder;
`- [live]` lines can only be confirmed on a live cluster or account; `- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: namespace build and the config map iac-supplied with the supplied files.
+ [done] 4: reset removes namespace iac-lab and /workspace/iac-1.
- [lab-build] 2: image has terraform 1.17.0, provider hashicorp/kubernetes 3.4.0 in the filesystem mirror (terraform init offline), ansible-playbook with kubernetes.core 6.6.0 and the Python kubernetes package in /opt/ansible. Image has not been built.
- [lab-build] 3: kubeconfig at /workspace/.lab/kubeconfig (both the provider config_path and the playbook module_defaults use this exact path).
- [live] 1: terraform apply of the saved plan works on OpenShift (OpenShift and Tekton add annotations and labels to the namespace; the provider block ignores them so plan exits 0 after apply; re-verify live); the plan output matches the expect text in the module.
- [live] 2: the drift plan shows one update on kubernetes_resource_quota_v1.limits, the lines grep picks out ('will be', 'pods') exist, and exit code 2 appears.
- [live] 3: ansible-playbook -i localhost, baseline.yml: check mode shows changed=2 on a fresh namespace, a real run changed=2, a second run changed=0 (including the ServiceAccount, which OpenShift adds secrets to); --diff prints before and after after the hand edit to settings-record.
- [live] 4: the python interpreter line (ansible_python_interpreter: ansible_playbook_python) picks the venv Python that has the kubernetes package.
- [live] 1: negative tests: the plan with risky.tfvars on the copied folder reports 1 to destroy for kubernetes_network_policy_v1.default_deny[0] and the live policy is untouched; validate on the typo file exits 1 (this one was also checked on a workstation: the error text matches).
+ [done] 1: (verified offline, workstation, provider 3.4.0) init, validate and a create-only plan of the supplied folder; the plan lists 5 creates.
