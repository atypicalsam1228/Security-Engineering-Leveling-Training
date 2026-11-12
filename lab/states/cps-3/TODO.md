# TODO: start state for CPS-3 (Least-Privilege Roles and Baselines)

Lab needs are numbered as in the module's lab_needs list. `+ [done]` lines are covered by files in this folder;
`- [live]` lines can only be confirmed on a live cluster or account; `- [lab-build]` lines are provided by the lab build, not by start states.

+ [done] 1: rbac-lab with report-sa, the broad binding, report-app and backend (10-rbac-lab.sh).
- [live] 1: registry.access.redhat.com/ubi9/python-311 runs python3 -m http.server as the image user; the start script pins tag 1 (confirm it exists).
- [live] 2: OVN-Kubernetes enforces NetworkPolicy, so the default-deny blocks report-app to backend.
- [live] 3: oc create --dry-run=client -f FILE -o json prints a List for a multi-document file (the review gate depends on it).
- [live] 4: the lab shell can reach the internet for the AWS call in Step 5.
- [live] 5: the learner AWS identity may call iam:SimulateCustomPolicy. terraform/iam_learner_guard.tf grants it (policy ${lab_id}-learner-iam-simulate (resource learner_cps), output learner_cps_policy_arn) to the users and roles named in learner_user_names and learner_role_names; if none is named, attach the policy by hand. Step 5 passes the policy inline and creates nothing in the account. Output has not been captured from a live account.
