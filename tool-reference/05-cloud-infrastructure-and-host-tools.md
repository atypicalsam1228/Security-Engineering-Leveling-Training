# Cloud infrastructure and host tools: vendor reference (group 05)

Retrieved 2026-10-30. Every best-practice bullet cites a fetched vendor page. Report only; no project file was edited.
Note on method: the fetch tool returns a model summary of each page, not the raw page, for most non-AWS-docs sites. Treat paraphrases as summaries and re-check a page before quoting it.

Contents
1. Terraform (1.17.0)
2. Terraform AWS provider (~> 6.0)
3. Amazon S3 (versioning, lifecycle, Object Lock, public access block)
4. AWS KMS (key policy, rotation, deletion)
5. AWS IAM and EC2 instance profiles
6. VPC, NAT, endpoints, security groups, Session Manager network needs
7. AWS Budgets
8. AWS CLI v2 (2.38.5) and Session Manager plugin (1.2.896.0)
9. OpenShift installer on AWS (OCP 4.22, single node, FIPS)
10. Podman and Docker as host container engines
11. Python 3.9, PyYAML, jq, envsubst

---

## 1. Terraform (1.17.0)
- Vendor docs (retrieved 2026-10-30):
  - [1] Manage sensitive data in your configuration - https://developer.hashicorp.com/terraform/language/state/sensitive-data
  - [2] S3 backend - https://developer.hashicorp.com/terraform/language/backend/s3
  - [3] Version constraints - https://developer.hashicorp.com/terraform/language/expressions/version-constraints
  - [4] Dependency lock file - https://developer.hashicorp.com/terraform/language/files/dependency-lock
  - [5] terraform plan command - https://developer.hashicorp.com/terraform/cli/commands/plan
  - [6] Input variables - https://developer.hashicorp.com/terraform/language/values/variables
  - [7] Terraform CHANGELOG v1.17 - https://github.com/hashicorp/terraform/blob/v1.17/CHANGELOG.md
  - [8] Install Terraform - https://developer.hashicorp.com/terraform/install
- Role in this training: infrastructure as code for the lab foundation (VPC, buckets, KMS, IAM, bastion, budget). Files terraform/*.tf.
- Best practices (vendor-stated):
  - Keep state in a remote backend with encryption at rest, restricted access and audit logging; keep local state out of Git [1].
  - S3 backend: enable bucket versioning ("highly recommended") so state survives deletion or error [2].
  - S3 backend: set encrypt = true; to use a specific KMS key set kms_key_id (needs kms:Encrypt, kms:Decrypt, kms:GenerateDataKey) [2].
  - S3 backend: use_lockfile = true locks state with an S3 lock file (default false); the DynamoDB arguments are deprecated [2].
  - Keep credentials out of backend config; values passed with -backend-config can persist in .terraform and plan files [2].
  - Root modules should use ~> to bound each provider; reusable modules set only a minimum [3].
  - Commit .terraform.lock.hcl; use init -upgrade deliberately; pre-record other platforms with providers lock -platform=... [4].
  - A saved plan (-out) holds sensitive values in cleartext; treat it as a secret and do not name it *.tf [5].
  - sensitive = true hides a value from CLI output but it is still stored in state; ephemeral variables stay out of state and plan [6].
  - Verify downloads: SHA256 checksums are published and the checksum file is GPG-signed [8].
- Implementation guidance relevant to the lab:
  - Backend bucket created before first init, partial config at init: terraform init -backend-config="bucket=..." [2].
  - plan -out=FILE then apply FILE applies exactly what was reviewed [5].
  - Variable validation blocks (condition + error_message) check inputs at the boundary [6].
- Version notes: 1.17.0 released 2026-10-21; 1.17.1 (2026-10-28) is the latest patch listed. No upgrade notes, breaking changes or deprecations listed for 1.17.0. New: variables/locals allowed in provider requirements, -minimal-refresh, Terraform Policy GA [7].
- Where this project differs:
  - versions.tf has required_version ">= 1.10"; LAB-CONTRACT.md says "Terraform 1.11 or newer". The two floors disagree (report only).
  - Shortcut: the Dockerfile pins the sha256 of the zip rather than checking the .sig that HashiCorp publishes [8] (stated in lab/image/versions.txt).
  - terraform/.terraform.lock.hcl exists (matches [4]); not checked whether it holds hashes for more than one platform (linux_amd64 and linux_arm64 both matter, since the tools image is multi-arch).
- Unconfirmed: the Terraform version that introduced use_lockfile (the S3 backend page fetched did not state it); whether 1.17 changes S3 backend behavior (CHANGELOG lists none).

## 2. Terraform AWS provider (~> 6.0)
- Vendor docs:
  - [1] Provider index (raw source of registry page) - https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/index.html.markdown
  - [2] Version 6 upgrade guide - https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/guides/version-6-upgrade.html.markdown
  - [3] aws_s3_bucket_lifecycle_configuration - https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/r/s3_bucket_lifecycle_configuration.html.markdown
  - [4] aws_s3_bucket_object_lock_configuration - https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/r/s3_bucket_object_lock_configuration.html.markdown
- Role in this training: the only Terraform provider; every resource in terraform/*.tf..
- Best practices (vendor-stated):
  - Pin with version = "~> 6.0" (the provider docs' own example) [1].
  - Avoid hard-coded static credentials in provider config; use environment variables or named profiles [1].
  - default_tags apply to all taggable resources except aws_autoscaling_group; a resource can override a key but not remove it [1].
  - ignore_tags key_prefixes hides matching tags from diffs; a resource that still sets such a tag shows a perpetual diff [1].
  - Credential lookup order: provider block, env vars, shared credentials/config files, container credentials, instance profile [1].
  - Use filter {} (empty) in lifecycle rules to cover all objects; prefix is deprecated [3].
  - Noncurrent-version rules need versioning first: add depends_on to the versioning resource [3].
  - Declare only one lifecycle configuration resource per bucket (more cause a perpetual diff) [3].
  - Object Lock on a new bucket: set versioning first, then the lock resource; rule.default_retention takes days or years, not both [4].
- Implementation guidance relevant to the lab:
  - aws_s3_bucket_lifecycle_configuration with filter {}, transition, expiration, noncurrent_version_expiration, abort_incomplete_multipart_upload [3].
  - aws_s3_bucket_object_lock_configuration with mode COMPLIANCE/GOVERNANCE [4].
  - aws_eip uses domain = "vpc" in v6 (vpc was removed) [2].
- Version notes (v6): aws_eip.vpc removed (use domain); aws_instance user_data is no longer hashed and is stored in plain text, so keep secrets out of it; cpu_core_count/threads removed (use cpu_options); most resources gain a region argument; s3_us_east_1_regional_endpoint = legacy is deprecated and removed in v7 [2]. Resource-specific notes: transition_default_minimum_object_size defaults to all_storage_classes_128K [3].
- Where this project differs:
  - Lifecycle rules use filter {} and depends_on versioning: matches [3].
  - bastion user_data is rendered by templatefile and contains region, bucket name and channel only, no secrets: consistent with [2].
  - Log bucket Glacier transition after log_archive_days: with the 128K default [3], objects under 128 KB will not transition unless a size filter or varies_by_storage_class is set. Small log objects may stay in Standard (design effect; not an error).
- Unconfirmed: exact provider 6.x minor version current on 2026-10-30; aws_budgets_budget argument details (not fetched).

## 3. Amazon S3 (versioning, lifecycle, Object Lock, public access block)
- Vendor docs:
  - [1] Locking objects with Object Lock - https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
  - [2] Blocking public access to your S3 storage - https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
  - [3] Examples of S3 Lifecycle configurations - https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-configuration-examples.html
  - [4] Security best practices for Amazon S3 - https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html
- Role in this training: log bucket (Object Lock), artifacts bucket (installer handoff), Terraform state bucket. Files: terraform/storage.tf.
- Best practices (vendor-stated):
  - Object Lock works only on versioned buckets; locks protect the specific version, new versions and delete markers can still be added [1].
  - Compliance mode: no user, including root, can overwrite or delete a protected version or shorten retention; the only early way out is deleting the AWS account [1].
  - Governance mode is for protecting against most users while allowing privileged bypass; it can be used to test retention settings first [1].
  - Turn on all four Block Public Access settings for the account and for each bucket [2].
  - Block Public Access does not change existing policies or ACLs, and identity and KMS key policies must also be checked for public grants [2].
  - Disable ACLs (bucket owner enforced, the default) and use policies [4].
  - Deny non-TLS requests with aws:SecureTransport in the bucket policy [4].
  - Enable versioning to recover from user error and application failure [4].
  - Use least privilege and IAM roles, not stored long-term credentials, for workloads [4].
  - Versioned bucket lifecycle: separate Expiration (current) from NoncurrentVersionExpiration; add AbortIncompleteMultipartUpload [3].
- Implementation guidance relevant to the lab:
  - Permanent delete of a locked version (with version ID) returns 403; a simple delete adds a delete marker [1].
  - Object Lock default retention at bucket level overrides nothing set per object: an explicit per-object retention wins [1].
  - Objects smaller than 128 KB are not transitioned by default; add a size filter or the x-amz-transition-object-size-minimum-default header to change that [3].
  - With multiple rules, permanent deletion takes precedence over transition [3].
- Version notes: from April 2026 new buckets have SSE-C blocked by default (irrelevant to SSE-KMS use here) [4].
- Where this project differs:
  - Log bucket: COMPLIANCE default retention is short on purpose (var.log_retention_days) and a lifecycle expiry larger than retention lets the bucket empty for destroy. Labeled lab shortcut: real evidence stores keep much longer retention. The precondition (expire > retention) is project logic, not vendor guidance.
  - Artifacts bucket is unversioned on purpose (so deleting install-config.yaml really removes the pull secret). [4] recommends versioning generally; this is a documented security trade-off in storage.tf.
  - Backup and artifacts buckets use force_destroy = true: lab shortcut.
  - Block Public Access, SSE-KMS with bucket key, and the aws:SecureTransport deny are applied to all three buckets: matches [2][4]. Account-level Block Public Access is not set by Terraform.
  - No access logging or CloudTrail data events configured for the buckets; [4] lists both as monitoring practices.
- Unconfirmed: whether a lifecycle Expiration rule removes a version that is still under a Compliance lock (the Object Lock page fetched does not say; the project's destroy flow depends on locked versions expiring only after retention ends).

## 4. AWS KMS (key policy, rotation, deletion)
- Vendor docs:
  - [1] Enable automatic key rotation - https://docs.aws.amazon.com/kms/latest/developerguide/rotating-keys-enable.html
  - [2] Default key policy - https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-default.html
  - [3] Delete an AWS KMS key - https://docs.aws.amazon.com/kms/latest/developerguide/deleting-keys.html
- Role in this training: customer-managed keys for EBS/S3 encryption (aws_kms_key.lab) and a separate state key. Files: terraform/kms.tf, main.tf.
- Best practices (vendor-stated):
  - Rotation is off by default for customer managed keys; enable it with EnableKeyRotation (needs kms:EnableKeyRotation) [1].
  - Default rotation period is 365 days; custom range 90 to 2560 days; kms:RotationPeriodInDays can limit values [1].
  - Rotation keeps key ID, ARN, policies and aliases unchanged, so applications need no change [1].
  - Keep the account-root statement in the key policy: a KMS key policy grants nothing automatically, and without that statement IAM policies are ineffective and the key can become unmanageable [2].
  - Key administrators and key users are separate statements; admins can still change policy and grants [2].
  - Scope service use with kms:GrantIsForAWSResource and kms:ViaService conditions [2].
  - Disabled or pending-deletion keys are not rotated [1][3].
  - Prefer disabling a key to deleting it; deletion is irreversible and ciphertext becomes unrecoverable [3].
- Implementation guidance relevant to the lab:
  - aws kms enable-key-rotation --key-id KEY [--rotation-period-in-days N]; aws kms get-key-rotation-status --key-id KEY [1].
  - Scheduled deletion needs a 7 to 30 day waiting period (default 30); actual deletion may take up to 24 hours longer; pending-deletion keys cannot be used [3].
- Version notes: automatic rotation is not available for asymmetric, HMAC, imported-material or custom-key-store keys [1].
- Where this project differs:
  - enable_key_rotation = true with default period: matches [1]. deletion_window_in_days = 7 uses the minimum; labeled lab shortcut [3].
  - Key policy statement "AllowAccountUseViaEc2AndS3" grants use to Principal "*" restricted by kms:CallerAccount and kms:ViaService (ec2, s3). The vendor default pattern names principals; the project comment says installer-created roles cannot be named in advance. Lab choice, consistent with the ViaService guidance [2].
  - CloudWatch Logs service statement uses an ArnLike condition on the log-group ARN: consistent with service-principal scoping [2].
- Unconfirmed: the CloudWatch Logs key-policy condition format (not fetched); EBS-specific key-policy requirements for the root volume (not fetched).

## 5. AWS IAM and EC2 instance profiles
- Vendor docs:
  - [1] Security best practices in IAM - https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
  - [2] Use the Instance Metadata Service - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html
  - [3] Session Manager prerequisites - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html
  - [4] OCP 4.22 Configuring an AWS account (IAM user and permissions) - https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/installing_on_aws/installing-aws-account
- Role in this training: bastion role + instance profile, installer permission policies, learner cost-guard policy, S3 bucket policies. Files: bastion.tf, iam_installer.tf, iam_learner_guard.tf.
- Best practices (vendor-stated):
  - Workloads on EC2 should use IAM role temporary credentials, not long-lived keys [1].
  - Grant only the required actions on specific resources under conditions; start from managed policies and narrow them [1].
  - Use IAM Access Analyzer to generate least-privilege policies from CloudTrail and to validate policies [1].
  - Use conditions (for example TLS-only) to restrict statements [1].
  - Use permissions boundaries to cap delegated permission management [1].
  - Remove unused roles, permissions and credentials using last-accessed information [1].
  - EC2 metadata: IMDSv2 is session-oriented; default allows v1 and v2; set tokens required to refuse v1 [2].
  - IMDS PUT response hop limit defaults to 1; raise it only for container workloads that need it [2].
  - SSM Agent 2.3.68.0 or later is required for Session Manager; AmazonSSMManagedInstanceCore provides the needed permissions [3].
- Implementation guidance relevant to the lab:
  - metadata_options { http_tokens = "required", http_put_response_hop_limit = 1 } [2].
  - Attach AmazonSSMManagedInstanceCore to the instance role for Session Manager [3].
  - Red Hat (installer): the installer IAM user needs the listed EC2/ELB/IAM/Route 53/S3 permissions; with an existing VPC the network-creation set is not needed; custom KMS adds Encrypt/Decrypt/CreateGrant (and ReEncrypt* for an encrypted AMI) [4].
- Version notes: none for the pinned items.
- Where this project differs:
  - Installer policy is Red Hat's permission list split into three managed policies, not AdministratorAccess. Red Hat's own guidance is to create an administrative IAM user and not hand-build a policy, because the cluster cannot then issue per-component credentials [4]. The project's choice is a deliberate narrowing; the page does not say it is unsupported.
  - Red Hat says temporary session tokens from MFA devices do not work because the cluster needs long-term credentials [4]. The bastion uses instance-profile (temporary) credentials. Whether the installer's default (mint) credentials mode works with instance-role credentials is not stated on the page fetched.
  - The installer policies grant S3/IAM actions on "*" (installer permission check); the project adds explicit Deny statements for the log/backup buckets and for changing its own role. Extra hardening beyond [1][4].
  - Bastion SG has all outbound open; no key pair; IMDSv2 required: matches [2][3]. Egress open is a lab shortcut.
  - Learner AWS credentials arrive via environment passthrough into the container (long-term keys possible); [1] prefers temporary credentials. Lab shortcut.
- Unconfirmed: the 6,144-character managed-policy limit cited in iam_installer.tf (not on any page fetched); that Access Analyzer would flag the "*" resource lists.

## 6. VPC, NAT, endpoints, security groups, Session Manager network needs
- Vendor docs:
  - [1] NAT gateways - https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
  - [2] Gateway endpoints for Amazon S3 - https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html
  - [3] VPC endpoints for Systems Manager - https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html
  - [4] S3 security best practices (VPC endpoint item) - https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html
- Role in this training: VPC, public/private subnets, one NAT gateway, S3 gateway endpoint, SSM interface endpoints, security groups. Files: network.tf, endpoints.tf, bastion.tf..
- Best practices (vendor-stated):
  - A public NAT gateway lives in a public subnet, needs an Elastic IP, and routes through the internet gateway; instances behind it cannot receive unsolicited inbound traffic [1].
  - S3 gateway endpoint: no extra charge, no NAT or internet gateway needed, available only in its Region, and only reachable from inside the VPC [2].
  - VPC DNS hostnames and DNS resolution must be enabled when using Amazon DNS with the gateway endpoint [2].
  - Security group rules and network ACLs of instances using the endpoint must allow traffic to S3 (prefix list for security groups) [2].
  - Use bucket policies with aws:sourceVpce / aws:sourceVpc to limit buckets to an endpoint; aws:SourceIp does not work through an endpoint [2][4].
  - Systems Manager: interface endpoints ssm, ssmmessages, ec2messages (plus s3, and optionally kms, logs) keep traffic private; ssmmessages is needed for Session Manager [3].
  - The endpoint security group must allow inbound 443 from the instance subnet [3].
  - SSM Agent opens all connections outbound; no inbound rule is needed on the instance [3].
- Implementation guidance relevant to the lab:
  - Create endpoints com.amazonaws.REGION.{ssm,ssmmessages,ec2messages}; with private DNS enabled so default hostnames resolve to the endpoint [3].
  - Gateway endpoint: associate with the route tables of subnets that need S3 [2].
- Version notes: endpoint policy defaults to full access [2].
- Where this project differs:
  - Single NAT gateway, single AZ, one private subnet: lab shortcut (cost). The pages fetched do not state a one-NAT-per-AZ recommendation; availability trade-offs not confirmed.
  - SSM interface endpoints are optional (enable_ssm_endpoints) and the NAT also gives the bastion internet; [3] says endpoints are recommended, not required. No kms or logs interface endpoint is created; with NAT present, CloudWatch Logs traffic from Session Manager works over NAT.
  - Endpoint SG allows 443 from the whole VPC CIDR rather than from the private subnet only: broader than [3]'s minimum; low risk.
  - S3 gateway endpoint uses the default full-access policy; no bucket policy restricts to aws:sourceVpce. Lab shortcut.
  - Both subnets sit in one AZ chosen by instance-type availability: matches the project note; not a vendor topic.
- Unconfirmed: NAT gateway hourly and per-GB charge figures (the pricing page was not fetched); public-vs-private subnet effects on the OpenShift installer's own subnet tagging.

## 7. AWS Budgets
- Vendor docs:
  - [1] Managing your costs with AWS Budgets - https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- Role in this training: monthly cost budget with 80 percent actual and 100 percent forecasted email alerts. File: main.tf (aws_budgets_budget.lab)..
- Best practices (vendor-stated):
  - Budgets can alert on actual (after accruing) and forecasted (before accruing) spend, by email, SNS, or both [1].
  - Budget data refreshes up to three times a day, typically 8 to 12 hours apart [1].
  - Notifications lag real usage: charges can exceed the threshold before an alert arrives, and cost can keep rising afterward [1].
  - Budget actions (for example applying a deny IAM policy at 80 percent) can respond automatically [1].
  - The page points to a separate "Best practices for AWS Budgets" topic (not fetched) [1].
- Implementation guidance relevant to the lab: cost budget, monthly period, threshold_type PERCENTAGE with ACTUAL and FORECASTED notification types [1].
- Version notes: none found.
- Where this project differs:
  - Alerts are email only; no budget action or SNS. With a 1-day auto-destroy default (DESTROY_AFTER) and 8 to 12 hour refresh [1], a budget alert may arrive after the lab is gone. Lab shortcut; the lab also relies on tags and a sweeper for cleanup.
  - alert_email is a plain variable; not sensitive. Fine.
- Unconfirmed: minimum history needed before FORECASTED alerts fire; number of free budgets per account.

## 8. AWS CLI v2 (2.38.5) and Session Manager plugin (1.2.896.0)
- Vendor docs:
  - [1] Installing or updating the latest AWS CLI - https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
  - [2] Installing past releases of the AWS CLI v2 - https://docs.aws.amazon.com/cli/latest/userguide/getting-started-version.html
  - [3] Environment variables for the AWS CLI - https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html
  - [4] Install the Session Manager plugin on Linux - https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-linux.html
  - [5] Session Manager prerequisites - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html
- Role in this training: tools in lab shell (aws, session-manager-plugin) for all AWS calls; Session Manager reaches the bastion. Modules: cps_4.
- Best practices (vendor-stated):
  - Verify the installer zip with the AWS CLI Team PGP key; fingerprint FB5D B77F D5C1 18B8 0511 ADA8 A631 0ACC 4672 475C, key expires 2027-07-01; the "not certified" GPG warning is expected [2].
  - Pin a version by appending it to the file name: awscli-exe-linux-x86_64-VERSION.zip (and .zip.sig) [2].
  - Update an existing install with ./aws/install --bin-dir ... --install-dir ... --update [2].
  - Option precedence: command-line flag over environment variable over profile [3].
  - AWS_REGION overrides AWS_DEFAULT_REGION; both are overridden by --region [3].
  - Temporary credentials need AWS_SESSION_TOKEN alongside the key pair [3].
  - AWS_PAGER set to empty disables the pager for scripts [3].
  - Session Manager from the CLI needs CLI 1.16.12 or later, the plugin on the local machine, SSM Agent 2.3.68.0 or later on the node, and outbound 443 to ssm, ssmmessages, ec2messages [5].
- Implementation guidance relevant to the lab:
  - Plugin install on RHEL 9: dnf install -y https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_64bit/session-manager-plugin.rpm (linux_arm64 for ARM) [4].
  - aws ssm start-session --target ID [--document-name NAME] [5].
- Version notes: the docs describe versioned URLs for the CLI only [2]. The plugin page shows only the /latest/ path; the project's versioned plugin URL (plugin/1.2.896.0/...) is not shown there.
- Where this project differs:
  - Project verifies CLI via GPG signature plus pinned sha256: matches [2]. The plugin has no vendor checksum file; the project pins sha256 it computed itself (documented in versions.txt).
  - Bastion user data downloads the unversioned latest CLI zip with no signature check (bastion-userdata.sh.tftpl): differs from [2]'s verify-before-install advice. Lab shortcut.
  - Bastion installs the SSM agent RPM from the regional amazon-ssm-REGION bucket if absent: the SSM page fetched covers requirements, not this URL (see Unconfirmed).
  - Lab shell passes AWS_* environment names into the container: consistent with [3] (env var precedence).
- Unconfirmed: that the pinned version 2.38.5 and plugin 1.2.896.0 still exist at the vendor URLs (not fetched); the regional SSM agent RPM URL.

## 9. OpenShift installer on AWS (OCP 4.22, single node, FIPS)
- Vendor docs (Red Hat):
  - [1] Installing on a single node, 4.22 - https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/observability/installing_on_a_single_node/index
  - [2] Installing on AWS, 4.22: Configuring an AWS account - https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/installing_on_aws/installing-aws-account
  - [3] Installing on AWS, 4.22: Installer-provisioned infrastructure - https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/installing_on_aws/installer-provisioned-infrastructure
  - [4] Installation overview, 4.22: Support for FIPS cryptography - https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/installation_overview/installing-fips
  - [5] Installation configuration parameters for AWS, 4.22 - https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/installing_on_aws/installation-config-parameters-aws
  - [6] Uninstalling a cluster on AWS, 4.22 - https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/installing_on_aws/uninstalling-cluster-aws
- Role in this training: the cluster itself; the bastion runs openshift-install-fips. terraform/templates/bastion-userdata.sh.tftpl.
- Best practices (vendor-stated):
  - Single node on AWS requires installer-provisioned infrastructure, following the AWS customizations procedure [1].
  - Set controlPlane.replicas to 1 and compute.replicas to 0 (makes the control plane schedulable) [1].
  - Cloud single-node minimum: 4 vCPU and 120 GB storage, with a warning that 4 vCPU leaves little headroom for applications and Operators [1].
  - Topology is fixed at install: single node cannot later become highly available [1].
  - FIPS: set fips: true in install-config.yaml before install; the installer must run on a RHEL host in FIPS mode; FIPS cannot be enabled after deployment [4].
  - FIPS installer binary: oc adm release extract --command=openshift-install-fips (oc 4.16 or later) or the openshift-install-rhel9-amd64.tar.gz mirror archive [4].
  - Use RSA or ECDSA SSH keys, not ed25519, for FIPS clusters [3].
  - Pull secret comes from Red Hat OpenShift Cluster Manager and authenticates image pulls from registries such as Quay [3][5].
  - The installer consumes install-config.yaml: back it up if reused; keep the installation directory and the installer, both needed to delete the cluster (metadata.json) [3][6].
  - Existing VPC: network-creation permissions are not needed; delete needs tag:UntagResources only [2].
  - Service quotas to watch: Elastic IPs, VPCs, load balancers, NAT gateways per AZ, S3 buckets (one per cluster) [2].
- Implementation guidance relevant to the lab:
  - controlPlane.platform.aws.rootVolume supports size, type, iops, throughput (gp3 125 to 2000 MiB/s) and kmsKeyARN for a customer key; with a customer-key-encrypted AMI add kms:ReEncrypt* [2][5].
  - If the install times out: openshift-install wait-for install-complete; logs in INSTALL_DIR/.openshift_install.log [3].
  - Remove with openshift-install destroy cluster from the original installation directory; then check AWS for leftovers [6].
  - AWS single-node: to pull from ECR add AmazonEC2ContainerRegistryReadOnly to the control plane role [2].
- Version notes: FIPS validation applies only to x86_64, ppc64le, s390x; FIPS cannot be turned on later [4]. The single-node page also states min 4 vCPU on generic platforms; the project's 16-vCPU m6i.4xlarge is well above it.
- Where this project differs:
  - Template: fips true, replicas 1/0, rootVolume gp3 with kmsKeyARN, extra SG: matches [1][4][5]. The instance type and root size are placeholders to confirm.
  - Bastion script: refuses to run unless /proc/sys/crypto/fips_enabled is 1; extracts the binary with oc adm release extract --command=openshift-install-fips: matches [4]. The Red Hat page does not name that /proc check (the RHEL doc is not fetched here).
  - Bastion downloads oc from the mirror by channel (not by pinned version) at boot: shortcut; not pinned to the 4.22.18 build in versions.txt.
  - The script deletes install-config.yaml from S3 after reading it; it keeps the working directory in /var/lib/lab/cluster: consistent with [3][6]. Destroy needs that directory: if the bastion is replaced first, destroy would lack metadata.json (not tested here).
  - publish: External in the template with an existing VPC: not discussed on the pages fetched.
- Unconfirmed: existing-VPC subnet tagging rules for 4.22 (page body not retrieved); whether instance-profile credentials satisfy the installer's credentials-mode needs; supported ed25519 behavior beyond the stated advice.

## 10. Podman and Docker as host container engines
- Vendor docs:
  - [1] Docker: Bind mounts - https://docs.docker.com/engine/storage/bind-mounts/
  - [2] Docker Desktop settings (resources, file sharing) - https://docs.docker.com/desktop/settings-and-maintenance/settings/
  - [3] Podman rootless tutorial - https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md
  - [4] podman-machine(1) - https://docs.podman.io/en/latest/markdown/podman-machine.1.html
  - [5] podman-machine-init(1) - https://docs.podman.io/en/latest/markdown/podman-machine-init.1.html
  - [6] podman-run(1) - https://docs.podman.io/en/latest/markdown/podman-run.1.html (first 100,000 characters read)
- Role in this training: lab CLI runs the tools image with whichever engine is found (podman or docker). Files: lab/labcli/environment.py, commands_image.py. Modules: all (every command runs in lab shell).
- Best practices (vendor-stated):
  - Docker prefers --mount over -v; -v silently creates a missing host path as a directory, --mount fails [1].
  - Bind mounts are writable by default; use ro/readonly when the container only reads [1].
  - Avoid mounting system directories [1].
  - Docker Desktop shares only /Users, /Volumes, /private, /tmp, /var/folders by default; mounts outside fail until added in Settings [2].
  - Share selectively; keep caches and databases in named volumes for speed [2].
  - macOS: VirtioFS is the default and faster file sharing; Windows: the WSL 2 backend performs better than Hyper-V [2].
  - Docker Desktop memory defaults to 50 percent of host memory (WSL 2 mode uses the WSL config instead) [2].
  - Podman on macOS and Windows runs in a VM managed by podman machine (rootless only commands); default home-directory mount is $HOME:$HOME [4][5].
  - Resources: podman machine init accepts --cpus, --memory (MiB), --disk-size (GiB) [5].
  - Rootless Podman: unique subuid/subgid ranges per user, root in the container maps to your host user, and --userns=keep-id keeps your UID inside the container [3].
  - -e NAME with no value takes the value from the host only if set [6].
- Implementation guidance relevant to the lab:
  - Bind-mount source must be an absolute path (or start with a dot) or Podman treats it as a named volume [3].
  - "Permission denied" on a bind source usually means an unmapped parent owner; --userns=keep-id does not fix it; check with podman unshare ls -ldn [3].
- Version notes: Podman default VM providers are libkrun on macOS and WSL on Windows [4].
- Where this project differs:
  - Uses -v host:container with a Windows-style path converted by Path.as_posix(), not --mount; [1] prefers --mount. Pre-existing host path is assumed, which is safe with -v creation fallback. Lab simplification.
  - Workspace mount is read-write; states directory is read-only (:ro): matches [1]. Terraform directory is mounted read-write (needed for init/apply).
  - Image runs as uid 1001 gid 0. For rootless Podman on Linux, file ownership of the bind mount depends on user-namespace mapping [3]; the CLI sets no --userns option. Not tested.
  - Secret values are passed by name only (-e NAME) so they are not placed on the command line: consistent with [6]. The --env-file is mode 0600 per LAB-CONTRACT; file precedence not checked in the part of [6] read.
  - No docs fetched for SELinux :Z relabel on Linux (see Unconfirmed); the lab CLI does not add :Z.
- Unconfirmed: podman run --volume text and --userns text (beyond first 100,000 characters / not in fetched summary); SELinux :z/:Z requirement for Linux bind mounts; Docker Desktop file-sharing behavior for Windows paths on the WSL 2 backend specifically; default VM CPU/memory for podman machine.

## 11. Python 3.9, PyYAML, jq, envsubst
- Vendor docs:
  - [1] Python status of versions - https://devguide.python.org/versions/
  - [2] PyYAML documentation - https://pyyaml.org/wiki/PyYAMLDocumentation
  - [3] jq manual - https://jqlang.org/manual/ (first 100,000 characters read)
  - [4] envsubst(1) man page (GNU manual page returned HTTP 429; man7.org mirror used) - https://man7.org/linux/man-pages/man1/envsubst.1.html
- Role in this training: shell and script helpers inside the tools image (RHEL 9 packages python3 3.9, python3-pyyaml, jq, gettext). Modules: jq in nearly all; envsubst in grc_3, grc_5, sdr_5; PyYAML in aid_4, arc_5, cps_2, vm_5.
- Best practices (vendor-stated):
  - Python: 3.9 reached end of life on 2025-10-31; supported branches listed are 3.11 to 3.15 [1].
  - PyYAML: yaml.load can run arbitrary Python from untrusted input; use safe_load (SafeLoader) [2].
  - PyYAML: safe_dump emits only standard YAML tags; default_flow_style=False forces block style [2].
  - jq: pass shell values with --arg (string) or --argjson (parsed JSON) instead of building filter text [3].
  - jq: -r removes quotes for non-JSON consumers; -e sets exit status from the last output (0 true, 1 false/null, 4 none); -n runs with null input to build JSON [3].
  - jq: @sh escapes values for POSIX shells; @base64 / @base64d per RFC 4648 [3].
  - envsubst: with a SHELL-FORMAT argument only listed variables are replaced; without one, every $VAR in the input is replaced [4].
- Implementation guidance relevant to the lab:
  - jq -n --arg k "$KEY_ARN" '{...$k...}' builds JSON safely (the lab scripts do this) [3].
  - envsubst '${LOKI_URL}' < file limits substitution to named variables [4].
- Version notes: Python 3.9 is past end of life per the vendor, but RHEL 9 ships it; whether Red Hat still patches it was not checked. Module scripts must run on 3.9 (LAB-CONTRACT).
- Where this project differs:
  - Modules using PyYAML: not inspected for load vs safe_load use beyond a grep for "yaml."; check each call [2].
- Unconfirmed: RHEL 9 python3.9 support lifecycle (Red Hat page not fetched); behavior of envsubst on undefined variables (the man page summary did not state it); remaining jq manual (characters beyond 100,000).
