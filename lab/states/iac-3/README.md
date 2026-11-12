# IAC-3 start state: Terraform or Ansible, Choose by Evidence

Implemented: the items below.
- reset.d/10-remove-iac-3-work.sh deletes namespace iac-lab and /workspace/iac-3. 10-clean.sh runs the same removal at every start, so the module works whether or not IAC-1 or IAC-2 ran (their iac-lab objects are removed).
- 20-baseline.sh copies kit/terraform/main.tf to /workspace/iac-3/terraform, runs terraform init (offline, provider mirror) and apply, and confirms plan -detailed-exitcode returns 0. It also creates the empty folder /workspace/iac-3/ansible.
- kit/terraform/main.tf: namespace iac-lab, resource quota iac-quota, network policy default-deny, role iac-reader, role binding iac-reader-binding (subject: service account iac-viewer). Provider hashicorp/kubernetes 3.4.0, config_path from var.kubeconfig (default /workspace/.lab/kubeconfig).

The learner writes: ansible/baseline.yml, measure.py, conformance.py, drift_check.sh (all under /workspace/iac-3).

Checked offline on a scratch single-node Kubernetes (not OpenShift) with terraform 1.17.0, provider 3.4.0, ansible-core 2.20.11, kubernetes.core 6.6.0, ansible-lint 26.10.1: the whole module flow and all three verify tests behave as written. Scripts have not been run on a live OpenShift cluster.
