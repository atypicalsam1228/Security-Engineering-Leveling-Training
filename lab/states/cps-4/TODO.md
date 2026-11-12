# TODO: start state for CPS-4 (Secure a Workload End to End)

Lab needs are numbered as in the module's lab_needs list. `+ [done]` lines are covered by files in this folder;
`- [live]` lines can only be confirmed on a live cluster or account; `- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: secure-lab, sample-api, api-client and stranger (10-secure-lab.sh).
+ [done] 2: etcd encryption on and complete (20-etcd-encryption.sh).
- [live] 2: Encrypted condition names on openshiftapiserver, kubeapiserver and authentication.operator.openshift.io; the rollout can exceed the wait_until limit on first start.
+ [done] 3: Falco and falco-custom-rules checked (30-preflight-falco.sh).
- [lab-build] 3: Falco 0.45.1 running in security-tools with json_output true and container metadata; config map falco-custom-rules mounted at /etc/falco/rules.d.
- [live] 4: AWS identity can call sts get-caller-identity, ec2 describe-volumes and kms describe-key (terraform/iam_learner_guard.tf grants the last two in policy ${lab_id}-learner-iam-simulate, output learner_cps_policy_arn).
- [live] 5: serviceAccountIssuer in authentication cluster; the module reads it to choose between no cloud access and short-lived role credentials.
- [live] 6: the lab shell can reach the internet for the AWS calls in Step 1.
