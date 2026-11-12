# Lab infrastructure (Terraform)

Root module for one learner lab. Everything is built by `lab up`; the AZ selection is described below.

## Variables
Required: `lab_id`, `region`, `destroy_after` (YYYY-MM-DD), `alert_email`.
Optional: `budget_limit_usd` (default "25", placeholder; set the real limit), `cluster_name` (default first 14 chars of lab_id), `instance_type` (m6i.4xlarge, placeholder), `bastion_instance_type`, `bastion_ami_id`, `ocp_channel` (stable-4.22), `log_retention_days` (1, Object Lock Compliance), `log_archive_days`, `log_expire_days`, `enable_ssm_endpoints`.
Cost controls (all optional, see below): `paused`, `guard_bucket`, `guard_budget_topic_arn`, `spend_destroy_pct`, `state_bucket`, `state_key`, `state_kms_key_arn`.

## Outputs
Core: `kms_key_arn vpc_id public_subnet_id private_subnet_id extra_security_group_id`.
Also: `lab_id aws_region cluster_name availability_zone log_bucket artifacts_bucket bastion_instance_id installer_policy_arns state_bucket_hint`, and `destroy_after` and `instance_type` (read by `lab-install.sh`), and `lab_env` (map for LAB_ID, AWS_REGION, CLUSTER_NAME, VPC_ID, KMS_KEY_ARN plus LOG_BUCKET, ARTIFACTS_BUCKET, BASTION_ID, GUARD_BUCKET). BASTION_ID is empty while paused; GUARD_BUCKET is empty when the guard is off. Also output `guard_bucket`.
`lab up`: `terraform output -json lab_env | jq -r 'to_entries[]|"export \(.key)=\(.value)"'`.

## How `lab up` uses it
1. Create the state KMS key (alias `<lab_id>-tfstate`, rotation on) and the S3 state bucket encrypted with it (SSE-KMS), then `terraform init -backend-config=bucket=... -backend-config=region=... -backend-config=kms_key_id=<key ARN>`. The bastion and installer roles do not use the state bucket or key.
2. `terraform apply` (TF_VAR_* from env). Export `lab_env`.
3. `scripts/lab-install.sh` (run by `lab up` in the tools container, skipped with `--skip-cluster`) reads the outputs, renders `templates/install-config.yaml.tpl` (single node, `fips: true`, `publish: External`, the lab KMS key on the 120 GB root volume, the extra security group, the existing public and private subnets, `LabId` and `AutoDestroyAfter` user tags with `propagateUserTags`, `instance_type` from the Terraform output), appends `sshKey` and the pull secret, and uploads it to `s3://$ARTIFACTS_BUCKET/install/install-config.yaml` (SSE-KMS with the lab key). Inputs, all environment variables of `lab up`: `PULL_SECRET_FILE` (required; a file under the lab workspace, translated to `/workspace/...` in the container; never printed, never written outside the temporary mode-600 file), `BASE_DOMAIN` (default: the single public Route 53 hosted zone; with none or several the script stops and says so), `SSH_PUBLIC_KEY_FILE` (default: a fresh key pair whose private half is discarded). The bastion (FIPS RHEL 9, no inbound, no key pair, no public IP) reboots into FIPS mode on first boot, then `lab-install.service` picks the file up, deletes it from S3, and runs `openshift-install-fips create cluster`.
4. The script polls `install/status` (installing, complete, failed:N) with progress lines every 5 minutes and a 120 minute timeout (`INSTALL_TIMEOUT_MIN`; an install is expected to take roughly 45 to 70 minutes, an estimate), then copies `install/auth/kubeconfig` to `<workspace>/.lab/kubeconfig` (mode 600). It prints the log command: `aws ssm start-session --target $BASTION_ID --document-name AWS-StartInteractiveCommand --parameters command="tail -n +1 -F /var/log/lab-install.log"`. Re-running `lab up` is safe: status `complete` skips the install, `installing` only waits, `failed:N` stops with a message (run `lab down` first). A paused lab (no bastion) stops with a message to run `lab resume`.
5. Teardown (`lab down`): `scripts/lab-install.sh destroy` puts an object at `install/destroy` and waits up to 60 minutes (`DESTROY_TIMEOUT_MIN`) for status `destroyed`; only then does `lab down` run `terraform destroy`. If the cluster is not confirmed destroyed, Terraform is not run and the lab keeps billing until `lab down` succeeds. If no install was ever started, the cluster step is skipped. Cluster destroy runs on the bastion, so a paused lab must be resumed first.

## Design notes
- AZ: public and private subnets use the first AZ (sorted, non-opt-in) offering both `instance_type` and `bastion_instance_type`; a precondition fails with a clear message if none does.
- KMS: rotation on; key policy keeps account root, lets CloudWatch Logs use the key, and lets account principals use it only via EC2 and S3 (so installer-created cluster roles work). Add the CSI roles by name later to tighten.
- Installer IAM: Red Hat OCP 4.22 list for an existing VPC, split in three managed policies (6,144 char limit), KMS actions scoped to the lab key, attached to the bastion role. `iam:CreateServiceLinkedRole` is an addition not on Red Hat's list.
- Learner cost-guard IAM (`iam_learner_guard.tf`, only when `guard_bucket` is set): a separate managed policy for the identity the lab shell runs as (see the guard section below). It is NOT attached to the bastion role. Reason: `lab shell` runs in a local container and receives the learner's own AWS credentials (AWS_PROFILE and related variables, see lab/labcli/environment.py), so the bastion role is never the lab shell's identity. Terraform cannot know the learner identity, so name it in `learner_user_names` / `learner_role_names`, or attach the `learner_guard_policy_arn` output by hand.
- Buckets: log (Object Lock Compliance, versioning, SSE-KMS, Glacier, expiry) and artifacts. Compliance-locked versions cannot be removed early: wait `log_retention_days` before destroying the log bucket.
- Sweeper: tags `LabId` and `AutoDestroyAfter` (provider default_tags and installer userTags). `sweeper/` is a separate once-per-account module: hourly Lambda that emails expired LabIds (read-only). `scripts/sweep.sh [--apply]` does the destroying (cluster first via the bastion marker, then `terraform destroy`). Dry run by default; `--apply` also needs `SWEEP_ACCOUNT_ID` set to the account id, and only touches labs that have a state bucket in that account.

## Cost controls: paused mode, guard registration (COST-CONTROLS.md is the spec)
Nothing here has run on AWS. All figures are estimates.

- `paused` (default false). When true, Terraform removes: the NAT gateway, its Elastic IP, the private default route to the NAT (`aws_route.private_nat`), the SSM interface endpoints, and the bastion instance. It keeps: VPC, subnets, route tables, the S3 gateway endpoint, the endpoint security group, KMS key, buckets, IAM roles and the instance profile, and the cluster node (not Terraform's; the guard stops and starts it). `terraform validate` passes with `paused` true and false; `terraform plan` was not run (no credentials).
- A bastion created after a pause starts empty. `lab-install.sh` uploads `metadata.json` to `install/state/` after a successful install and restores it (with the kubeconfig) on boot, so `destroy cluster` and `export.sh` still work. Unverified.
- `guard_bucket` (default empty = everything below is off). When set, with `guard_budget_topic_arn` (required, from the guard stack): writes `labs/<lab_id>/registration.json` (`lab_id, region, state_bucket, state_key, state_kms_key_arn, destroy_after, alert_email, registered_at, tf_vars`); adds learner permissions in the learner cost-guard policy (PutObject on `heartbeat/<lab_id>`, `keep/<lab_id>`, `requests/<lab_id>.json`; GetObject on `state/<lab_id>.json` and `saves/<lab_id>/*`; ListBucket limited by prefix); sets `GUARD_BUCKET` in the `lab_env` output; installs `/opt/lab/export.sh` on the bastion; adds the budget tag filter and the destroy notification.
- Registration values: `state_bucket` defaults to `<lab_id>-tfstate-<account id>`, `state_key` to `lab/terraform.tfstate`, and `state_kms_key_arn` to a lookup of `alias/<lab_id>-tfstate`. `lab up` should pass its real values with `-var state_bucket=... -var state_kms_key_arn=...` (the same values it gives to `-backend-config`). `tf_vars` holds every input variable except `paused`; the guard re-applies with these plus `-var paused=...`. List variables (`learner_*_names`) need the guard to pass them as JSON.
- Budget: `<lab_id>-monthly` gets a cost filter on the `LabId` cost allocation tag (`user:LabId$<lab_id>`) only when `guard_bucket` is set, plus an ACTUAL notification at `spend_destroy_pct` (default 100) to the guard budget SNS topic, in addition to the two email notifications. **Activate the tag once per account**: Billing console, Cost allocation tags, user-defined tag `LabId`, Activate. Activation takes up to 24 hours and only covers spend after it; until then the filtered budget sees no spend and the limit will not fire. The SNS topic policy must allow `budgets.amazonaws.com` to publish (guard stack).
- `export.sh <LAB_ID> <GUARD_BUCKET>`: Gitea repository bundles, namespace YAML without Secrets (demo, build, siem, chat, gitea, keycloak, kyverno, security-tools), `MANIFEST.json`, `restore.sh`, uploaded to `saves/<lab_id>/<UTC timestamp>/`. The unverified commands are listed at the top of the script. Changing user data on an existing bastion changes the instance in place or replaces it; apply the guard variables before the first install.
- `scripts/sweep.sh --force --lab <id>` skips the expired-date check only; the account check, `SWEEP_ACCOUNT_ID`, id pattern, tag check and state-bucket check stay. It never prompts. The CodeBuild image needs `aws`, `jq` and `terraform`.

### Paused cost (ESTIMATE, about $0.35 a day)
- Node root disk: 120 GB gp3 at about $0.08 per GB-month = $9.60 a month, about $0.32 a day (120 GB is Red Hat's single-node storage minimum and the install-config size; check the real volume).
- Lab KMS key: $1 a month, about $0.03 a day.
- Total about $0.35 a day. Not counted: state KMS key, a few cents of S3, guard stack and snapshots. Unit prices are from memory; confirm on the AWS pricing pages.
- Removed while paused: NAT gateway and Elastic IP, three interface endpoints, the bastion and its disk. Node compute stops billing only because the guard stops the instance.

### Limits
- A paused lab still bills about $0.35 a day (estimate). Use `lab down` for zero.
- Billing data lags by hours; the spend limit is a backstop, not a hard cap.
- A stopped single-node cluster may need certificate requests approved after a long pause; unverified.
- The log bucket (Object Lock, compliance mode) cannot be deleted before its retention ends.
- Nothing here has run on AWS.

## Cost notes (ESTIMATE, not measured)
About $18 per learner is an estimate, not a quote. Main drivers: the cluster instance, NAT gateway and its hourly charge, the RHEL bastion, three interface endpoints (hourly each), EBS, load balancers. Destroy when stopping for the day. Budget alerts email at 80 percent actual and 100 percent forecast.

## Cluster size estimate (ESTIMATE from typical defaults, not measured)
Method: platform baseline plus the typical idle memory and CPU request of each tool the modules install, all present at once. Figures are rounded from vendor defaults and common practice, not read from the cluster. Replace them with the README "First run: measure the cluster size" results.

| Group | Tools | Memory (GB) | CPU request (vCPU) |
|---|---|---|---|
| Platform baseline | OpenShift single node control plane and core operators, idle | 9 to 11 | 3 to 4 |
| Logging and detection | Logging collector, Loki, Grafana, Alloy | 3 to 4 | 1 to 1.5 |
| Identity and git | Keycloak plus database, Gitea | 2 to 3 | 0.5 to 1 |
| Chat | Mattermost plus database | 1 to 1.5 | 0.3 to 0.5 |
| Delivery | Argo CD, Tekton, registry use | 2.5 to 3.5 | 1 to 1.5 |
| Policy and scanning | Kyverno, Trivy Operator, Compliance Operator | 2 to 3 | 1 to 1.5 |
| Runtime detection | Falco | 0.5 to 1 | 0.3 to 0.5 |
| Service mesh | Service Mesh | 1 to 1.5 | 0.3 to 0.5 |
| Total | | about 21 to 29 | about 7 to 11 |

Reading it:
- Red Hat's single-node minimum is 8 vCPU and 16 GB. The full stack lands well above the memory minimum, so a 32 GB node (`m6i.2xlarge`) has little headroom and could leave pods Pending during the heavy modules. A 64 GB node fits with room to spare.
- `m6i.4xlarge` (16 vCPU, 64 GB, about $0.77 per hour) fits comfortably and is the safe default. CPU is probably over-provisioned there; memory is the real limit.
- `r6i.2xlarge` (8 vCPU, 64 GB, about $0.50 per hour) matches the memory need for about a third less money, if measured CPU stays under 8 vCPU. Check availability with the AZ precondition before changing the default.
- If a learner runs one module at a time and resets between them, much less is installed at once and `m6i.2xlarge` may do.
- Hourly rates are us-east-1 on-demand from memory; confirm them in the AWS pricing page before relying on them.

## Not verified (no apply was run)
The whole install path: `scripts/lab-install.sh` and `templates/install-config.yaml.tpl` have never run (no AWS, no jq or shellcheck on the build machine), including the `platform.aws` field names for existing subnets, `rootVolume.kmsKeyARN`, `additionalSecurityGroupIDs` and `propagateUserTags` against OCP 4.22, the 120 GB / `m6i.4xlarge` values, the install and destroy durations, and whether the learner identity may use the lab KMS key for SSE-KMS uploads.
RHEL 9 AMI name filter (Red Hat owner 309956199498, `Hourly2-GP3`), SSM agent install on RHEL, oc/release.txt paths on mirror.openshift.com, `oc adm release extract --command=openshift-install-fips` on a FIPS host, IAM policy sizes, Budgets permissions for the identity running Terraform (not included here).

## export.sh assumptions

Moved out of the bastion user data (the 16 KB limit). Nothing below has run against a live cluster.

UNVERIFIED (nothing here has run against a live cluster):
 - Gitea pod label app=gitea, the `oc exec` + `curl` route to the Gitea API on
   localhost:3000 (curl must exist in the pod), and the admin credential source
   (secret gitea-admin in namespace gitea, keys username and password; assumed).
 - That git inside the pod finds repositories at /data/git/gitea-repositories/<owner>/<repo>.git
   (path assumed) and that `git bundle create - --all` writes to stdout.
 - The jq cleanup (drops status, managedFields, uid, resourceVersion and similar) is
   best effort. The output is JSON written to .yaml files (JSON is valid YAML);
   that `oc apply -f` accepts it is unverified.
 - The kubeconfig path /var/lib/lab/cluster/auth/kubeconfig and that oc is installed.
 - `aws s3 cp --sse aws:kms` with no key id uses the account default aws/s3 key; a
   guard bucket with a customer-managed key may need --sse-kms-key-id.
 - Every kind in KINDS exists on the cluster (a missing kind makes oc print an error
   and the namespace is recorded as a warning).

