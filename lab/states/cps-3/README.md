# CPS-3 start state: Least-Privilege Roles and Baselines

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 10-rbac-lab.sh (namespace rbac-lab, service account report-sa with a deliberately broad edit binding report-sa-edit, unhardened Deployment report-app, Deployment and Service backend on port 8080). 20-reference-answer.sh (copies reference/report-policy.reference.json, the model answer for the Step 5 policy-writing exercise, to /workspace/cps-3/reference). reset.d deletes the namespace.
Still needed (live cluster or lab build): see TODO.md. `lab start` prints it while TODO.md exists.

Prerequisites: none (runs alone). The learner types the review gate, the role, the network policy and the security context patch, and writes the two gaps of the cloud policy in Step 5.

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh (sourced by the scripts).

Step 5 (scoped IAM policy, simulation) needs no cluster state, only the reference answer file above: it runs aws iam simulate-custom-policy with an inline policy. The permission iam:SimulateCustomPolicy comes from terraform/iam_learner_guard.tf, not from a start script.
