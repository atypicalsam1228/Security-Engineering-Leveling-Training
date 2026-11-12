# Architecture Decisions (lab level)

STATUS: DRAFT review of the lab-level choices, written from the repository files only (README.md, LAB-CONTRACT.md, COST-CONTROLS.md, terraform/, terraform/guard/, lab/, tool-reference/). Nothing here has run on AWS or on a live cluster, so every claim about how AWS or OpenShift behaves is UNVERIFIED. Prices are estimates from memory and must be confirmed on the vendor pricing pages. "Makes sense" is the reviewer's judgment, not a test result.

Each entry: Decision, How, Why, Alternatives (pros and cons), then a verdict line.

## 1. Single-node OpenShift per learner

**Decision:** Each learner gets one single-node OpenShift Container Platform cluster on AWS, with the learner as cluster-admin.
**How:** install-config.yaml sets one control plane replica and zero compute replicas; the cluster is installed into Terraform-built subnets by `openshift-install-fips` on a bastion.
**Why:** Modules need real operators (Compliance, GitOps, Pipelines) that only a real OpenShift cluster provides, and one node is the cheapest way to get one.
**Alternatives:** (a) Three-node or multi-node OpenShift: closer to production and shows high availability, but roughly three times the compute and a longer install. (b) A local single-node developer cluster on the laptop: free and fast, but not FIPS-on-AWS, no IAM/KMS/S3 integration, and not the same operators. (c) Plain Kubernetes (kind, k3s): cheap, but loses the OpenShift-specific controls the modules teach.
**Makes sense:** Yes. The cost of single-node is that high availability, node-failure and multi-node network behavior cannot be taught.

## 2. Instance size and disk sizes

**Decision:** Cluster node `m6i.4xlarge` (default, declared a placeholder), 120 GB gp3 root disk encrypted with the lab key; bastion `m6i.large`, 60 GB gp3.
**How:** `instance_type` in variables.tf must match install-config.yaml; the README tells the learner to measure on first run and resize.
**Why:** The repository's own estimate puts the full stack at about 21 to 29 GB memory and 7 to 11 vCPU, so 64 GB and 16 vCPU gives headroom (about $0.77 per hour, estimate, us-east-1 on-demand from memory).
**Alternatives:** (a) `m6i.2xlarge` (32 GB): about half the price, but likely Pending pods in the heavy modules. (b) `r6i.2xlarge` (8 vCPU, 64 GB, about $0.50 per hour, estimate): memory-matched and cheaper, but CPU may be the limit and its availability depends on the AZ. (c) Per-module sizing with resets: cheapest, but `lab start` states are meant to chain.
**Makes sense:** Yes as a safe default, but it is unmeasured. Red Hat's single-node minimum is 8 vCPU (terraform/README.md); 120 GB is stated as the storage minimum.

## 3. FIPS-mode install and FIPS bastion

**Decision:** The cluster is installed with `fips: true`, from a bastion that is itself in FIPS mode using `openshift-install-fips`.
**How:** Bastion user data runs `fips-mode-setup --enable`, reboots, and the install service refuses to run unless `/proc/sys/crypto/fips_enabled` is 1.
**Why:** Red Hat documents that a FIPS cluster must be installed from a FIPS host with the FIPS installer, and the training teaches SC-13 on a platform where FIPS is real, not claimed.
**Alternatives:** (a) FIPS off: simpler and avoids library incompatibilities, but the checks that read the FIPS state (the GRC-2 evidence collector, ARC-4) would be meaningless. (b) FIPS on only for selected components: not possible for OpenShift; the choice is made at install and cannot be changed later.
**Makes sense:** Yes. The guard that refuses to install on a non-FIPS bastion is a good design. Unverified: that every pinned tool image (Loki, Falco, Keycloak and others) runs cleanly on a FIPS node.

## 4. NAT gateway, SSM interface endpoints and S3 gateway endpoint

**Decision:** Private subnet with a NAT gateway for outbound, three SSM interface endpoints, an S3 gateway endpoint; the bastion has no public IP, no key pair and no inbound rule, and is reached only through Session Manager.
**How:** network.tf and endpoints.tf; the interface endpoints and NAT are removed when `paused` is true; the S3 gateway endpoint is free and stays.
**Why:** It keeps the bastion free of inbound ports and keeps S3 traffic off the NAT (saving data charges). The NAT gateway and endpoints are billed hourly (cost drivers, estimate only) and are the main idle cost, which is why pause removes them.
**Alternatives:** (a) Public subnet with a security group locked to the learner IP: cheaper (no NAT, no endpoints) but needs open inbound ports and an IP that changes. (b) A NAT instance: cheaper than the managed gateway but one more host to patch. (c) Endpoints only, no NAT: not workable, the cluster must reach Red Hat registries.
**Makes sense:** Partly. It holds for the bastion. The cluster itself is installed with `publish: External`, which makes the API and ingress load balancers internet-facing; see section 17.

## 5. Object Lock compliance-mode log bucket with KMS

**Decision:** The log bucket uses S3 Object Lock in Compliance mode (default 1 day), versioning, SSE-KMS with the lab key, a Glacier transition and a 14-day expiry.
**How:** storage.tf; a precondition requires expiry to exceed retention; the artifacts bucket has no lock.
**Why:** Compliance mode is the only mode that blocks even an administrator, which protects audit logs from deletion (AU-9). The retention is deliberately short so a lab can be destroyed; the lifecycle empties the bucket afterward.
**Alternatives:** (a) Governance mode: lets an admin delete with a bypass, so it cannot prove the claim, but is easy to clean up. (b) No lock, only IAM denies: simplest, but an administrator can undo it. (c) A separate logging account: the production pattern and strongest, but needs multi-account setup.
**Makes sense:** Yes. Cost: the log bucket and key linger after `lab down` until retention ends, and `terraform destroy` can stop at that bucket (documented).

## 6. One lab per learner (own LAB_ID, no shared cluster)

**Decision:** Every learner builds an entire lab (own cluster, network, key and buckets) keyed by `LAB_ID`, and is cluster-admin.
**How:** Terraform is parameterized by `lab_id`; every resource is named and tagged with it, and the sweeper, guard and budget act on that tag only.
**Why:** The modules include destructive negative tests (break a control, disable a rule, clear logs). A shared cluster would let one learner break another, and cluster-admin is needed for the exercises.
**Alternatives:** (a) Shared multi-tenant cluster with per-learner projects: much cheaper per head, but cluster-scoped exercises (audit profile, FIPS, operators) cannot be isolated. (b) Instructor-run demo only: lowest cost, but no hands-on skill.
**Makes sense:** Yes. Trade-off is cost (about $18 per learner full run, an author's estimate) and the need for a dedicated lab account because some exercises change account defaults.

## 7. Cost guard: tiers, pause design, spend limit, dry_run default

**Decision:** Three tiers (warn, save and pause, destroy) run by a scheduled Lambda; pause stops the node and deletes NAT, bastion and endpoints; a per-lab budget triggers destroy; the guard ships with `dry_run = true`.
**How:** A pure `decide()` function reads heartbeat, keep, request and registration files in a guard bucket; CodeBuild runs `terraform apply -var paused=true`; the budget is filtered on the `LabId` cost allocation tag and publishes to SNS.
**Why:** A forgotten lab is the largest cost risk, and removing NAT and endpoints cuts the idle cost to about $0.35 a day (estimate, mostly the node disk). A pure decision function is unit-testable, and `dry_run` lets an operator watch the emails before anything is destroyed.
**Alternatives:** (a) Only `destroy_after` plus the email sweeper: simplest, but wastes learner progress and cannot save work. (b) Hard AWS-side limits (budget actions with IAM or SCP deny): stronger cap, but still billing-lagged and needs Organizations. (c) Full pause by snapshotting everything: lower idle cost, but long and fragile for OpenShift.
**Makes sense:** Mostly yes; the design is careful (grace period, error state, no action without registration). Weak points are in section 17: the spend limit is a backstop only, tag activation takes up to 24 hours, dry_run means no protection until an operator flips it, and the CodeBuild role is close to lab-wide admin. A stopped single-node cluster may need certificate approvals on resume (unverified).

## 8. Loki, Grafana and Alloy as the SIEM (not Elastic or Splunk)

**Decision:** Loki stores logs (on S3), Alloy and OpenShift Logging collect them, Grafana searches and alerts.
**How:** Namespaces `siem` and `openshift-logging`; Loki backed by the Object Lock bucket; Grafana alert rules route to Mattermost.
**Why:** All are free and open source and light enough for one node; Loki indexes labels only, so it is cheap on memory and disk, and it writes natively to S3 so AU-9 retention can be shown. Elastic needs far more memory and JVM tuning, and Splunk is commercially licensed (against the free-tools rule).
**Alternatives:** (a) Elastic stack: richer search and a detection ruleset, but heavier and the licensing is mixed. (b) Splunk: what many enterprises run, so closest to job reality, but cost and license. (c) Cloud-native (CloudWatch, OpenSearch): managed, but weaker for the on-cluster story and adds cost.
**Makes sense:** Yes for a one-node lab. It teaches the SIEM functions (collect, store, alert, respond), not a particular product, and learners should be told so. Grafana provisioning endpoints used are deprecated but working (stated in LAB-CONTRACT.md).

## 9. Kyverno (not Gatekeeper or OPA)

**Decision:** Kyverno 1.19.2 for admission policy and signed-image enforcement.
**How:** Helm chart in namespace `kyverno`; CPS-5 and the ARC modules use ClusterPolicy.
**Why:** Policies are Kubernetes YAML (no Rego to learn), and image verification with Cosign is built in. That fits learners new to the keyboard.
**Alternatives:** (a) Gatekeeper with OPA: CNCF-graduated OPA, strong, and the Rego skills transfer, but a second language to teach and image verification needs extra tooling. (b) OpenShift built-ins (security context constraints, ValidatingAdmissionPolicy): no extra component, but cannot verify signatures. (c) Kyverno CEL policies: the future direction.
**Makes sense:** Yes, but the pin is a liability: ClusterPolicy is planned for removal in Kyverno 1.20, so those modules will need rewriting (already listed as an open item).

## 10. In-lab Gitea (not external GitHub)

**Decision:** A Gitea server inside the cluster is the git source of truth for GitOps and the pipeline.
**How:** Namespace `gitea`; the tools image trusts its certificate authority; saves export repositories as git bundles.
**Why:** The lab then has no dependency on, or credentials for, an outside service, branch protection can be configured freely, and everything is destroyed with the lab.
**Alternatives:** (a) GitHub: what learners will meet at work and always available, but needs accounts, tokens and an internet path, and branch rules need a paid plan for private repos in some cases. (b) GitLab: closer to many enterprise pipelines, but far heavier. (c) A bare git server: lighter, but no protected branches or pull requests.
**Makes sense:** Yes. Risks: Gitea is not version-pinned and the API fields were checked against main source, not a release.

## 11. Mattermost as chat

**Decision:** Mattermost in namespace `chat` receives Grafana alerts and hosts the triage channel.
**How:** Grafana's `slack`-type contact point posts to a Mattermost incoming webhook over in-cluster HTTP.
**Why:** The SDR modules need a place where alerts arrive and are triaged, and Mattermost is open source and self-hostable with Slack-compatible webhooks.
**Alternatives:** (a) Slack or Teams: what many teams use, but needs outside accounts and cannot be destroyed with the lab. (b) Email only: zero extra components, but no incident-channel practice. (c) Rocket.Chat: similar, with no advantage here.
**Makes sense:** Yes, though it spends memory (about 1 to 1.5 GB with its database, estimate) for a teaching convenience. The `slack` contact point route is not confirmed as vendor-endorsed, and the lab deployment of Mattermost is not yet in the repository.

## 12. Keycloak as identity

**Decision:** Keycloak 26.8.x is the in-lab identity provider whose sign-in events the SDR modules read.
**How:** Namespace `keycloak`; random per-lab admin password in a 0600 lab.env file.
**Why:** It is open source and supports OIDC, multi-factor and brute-force detection, so it produces realistic sign-in events without a paid product.
**Alternatives:** (a) OpenShift built-in OAuth with htpasswd: lightest, but no MFA or certificate flows. (b) A cloud directory: realistic, but outside the lab and costs. (c) Red Hat build of Keycloak: supported, and the same concept, but needs an entitlement path.
**Makes sense:** Yes. Dependency to note: successful sign-ins log at debug level by default, which the log modules must account for.

## 13. Scripted stand-in model service for AID modules

**Decision:** The AID modules call a deterministic stub service in project `ai-lab`, not a real model.
**How:** `lab/states/aid-2/stub/` serves scripted answers by request id; AID-3 to AID-5 reuse the same copy.
**Why:** It needs no model account, key or spend, and produces repeatable outputs so a check can compare to expected text.
**Alternatives:** (a) A real hosted model: realistic behavior and failure modes, but cost, keys, and non-deterministic checks. (b) A small local model on the node: no key, but heavy on a node already near its memory limit. (c) Mock inside each module: duplicates code.
**Makes sense:** Yes. Limit: learners practice controls around a model, not model behavior, and should be told that.

## 14. Tools container `lab shell`

**Decision:** All learner commands run inside a prebuilt container image holding oc, kubectl, terraform, aws, cosign, trivy and others, launched by the `lab` command with the learner's AWS credentials passed by name.
**How:** `lab build-image` builds it with podman or docker; the workspace is a mounted local folder.
**Why:** It makes Mac and Windows identical and pins tool versions, which matters for command output the checks compare.
**Alternatives:** (a) Install tools on the laptop: fastest, but version drift and hard on Windows. (b) A cloud shell or the bastion: no local engine needed, but needs inbound access or per-learner cost and the credentials stay in the cloud. (c) A dev container in an editor: friendly, but ties learners to one editor.
**Makes sense:** Yes. Unverified: the image has not been built. Python 3.9 in the image (RHEL 9) constrains module scripts.

## 15. Terraform state handling

**Decision (as documented):** Terraform keeps state in an S3 bucket encrypted with a state KMS key (versions.tf s3 backend, lockfile), and the installer-built cluster is outside state.
**How:** `lab up` is documented (terraform/README.md) to create the state key and bucket, then init with backend-config.
**Why:** Remote state lets the guard's CodeBuild project run `terraform apply` for pause, resume and destroy, which a laptop-local state file could not support.
**Alternatives:** (a) Local state in the workspace: simplest for one learner, but then the guard cannot act and loss of the laptop orphans the lab. (b) Terraform Cloud: managed locking, but an outside account. (c) State in the main lab key: avoids a second key, but destroying the lab then destroys its own state.
**Makes sense:** Yes. `lab up` now runs `terraform/scripts/lab-init.sh` (state key, bucket, backend init) as described; section 17, item 1 is kept as history.

## 16. Other decisions found

- **Artifacts bucket is unversioned on purpose** (install-config holds the pull secret; versioning would keep it after delete) and a bucket policy lets only the bastion role read the install-config. Makes sense.
- **Bastion installer role plus separate learner cost-guard policy:** the learner's own credentials, not the bastion role, run any AWS calls from the lab shell, so the bastion role stays installer-only. Makes sense; the cost is that the learner identity must be named by hand.
- **One lab KMS key with a broad "account principals via EC2 and S3" statement:** needed because installer-created roles cannot be named in advance. Reasonable for a lab, looser than production (noted in terraform/README.md).
- **Single availability zone, one public and one private subnet:** cheapest, but no zone-failure teaching; an AZ precondition checks both instance types exist.
- **Budget alarm per lab plus an hourly read-only sweeper:** cheap defense in depth beside the guard. Makes sense.
- **Random per-lab credentials in lab.env, never in Terraform state:** good practice.

## 17. Questionable or worth revisiting

1. **Terraform state mismatch (high; addressed since: `lab up` runs lab-init.sh).** versions.tf declares an `s3` backend with no bucket, but `lab up` (lab/labcli/terraform.py) runs `terraform init -input=false` with no backend configuration and passes `-state=<local path>`. `lab status` also checks for a local state file. As written, init would fail or the guard would find no state at the registered bucket. Reconcile code, README and guard. Not run, so unverified.
2. **Cluster endpoints may be public (high).** The install template sets `publish: External` and includes a public subnet, so the API and ingress load balancers are likely internet-facing, contrary to the "no open inbound ports" story that only holds for the bastion. Decision: public endpoints are a documented lab choice (a comment in `terraform/templates/install-config.yaml.tpl` says so); the private-endpoint appendix below is a sketch, not built and unverified. `terraform/scripts/lab-install.sh` renders that template and drives the bastion for `lab up` and `lab down`. Unverified.
3. **Guard ships with `dry_run = true`.** Until an operator turns it off, a forgotten lab is not paused or destroyed; only emails go to the guard's operator address, not the learner. Document who owns that flip, and a test date.
4. **Spend limit is not a cap.** Billing data lags, tag activation takes up to 24 hours and covers only later spend, and until then the filtered budget sees nothing and will not fire.
5. **Guard CodeBuild role is effectively lab-wide admin** (documented). Acceptable only in a dedicated lab account; consider a permissions boundary or an SCP.
6. **Pause/resume of single-node OpenShift is untested.** Possible pending certificate signing requests after a long pause, and a rebuilt bastion must restore installer metadata to destroy the cluster; both unverified and both could strand a lab.
7. **Instance size is unmeasured and over-provisioned on paper.** The repository's own estimate says memory, not CPU, is the limit, which suggests a memory-optimized type. Measure before publishing the $18 figure.
8. **Object Lock retention of 1 day does not demonstrate a real retention period.** It is a sound lab compromise, but modules should say the lab value is not the production value, and a leftover locked bucket after `lab down` needs a learner-facing note.
9. **Kyverno ClusterPolicy removal in 1.20 and unpinned Gitea, Mattermost, Alloy and Falco.** Module commands may break on first live run; pin everything at build.
10. **Kubernetes-in-one-account blast radius.** Some exercises change account-level defaults (EBS default encryption), so a shared or production account must never be used; consider enforcing this check in `lab up`.
11. **Scope of SIEM claim.** Loki plus Grafana teaches SIEM functions but lacks correlation and a detection-rule library; the README should not imply it replaces a production SIEM.

## Appendix: how the lab would be built with private endpoints

STATUS: design sketch. Nothing here has been built or run on AWS; the OpenShift settings are from Red Hat's published install pages as remembered and must be checked against the OCP 4.22 documentation before use. The lab keeps public endpoints (decision recorded in section 17, item 2) so that `lab shell` on a laptop can reach the cluster.

Changes to the lab as built today:

- `install-config.yaml`: `publish: Internal`, and `platform.aws.vpc.subnets` lists the private subnets only. The public subnet remains for the NAT gateway.
- The API and ingress load balancers are then internal, and their DNS records are private (Route 53 private zone for the cluster domain; unverified detail).
- Operators reach the cluster by one of: VPN or Direct Connect into the VPC (production), or the existing bastion with `aws ssm start-session` using the port-forwarding document (lab-friendly, no inbound port).
- Outbound traffic: NAT gateway as today, or a proxy with an allow list (SC-7(5) outbound) for a stricter build.
- Security groups: API 6443 and ingress 443 allowed only from the VPN or bastion address range.

```text
 laptop --(VPN / Direct Connect, or SSM port forward)--> VPC
                                                           |
   private subnet:  internal API LB (6443)  internal ingress LB (443)
                          |                        |
                     single-node OpenShift  <------+
                          |
   public subnet:   NAT gateway --> allow-listed outbound (registries, AWS APIs)
```

Cost and effort: the VPN or port-forward path needs to work on Windows and Mac before any module starts; route and `*.apps` names must resolve from the laptop through the tunnel (unverified). Every `*_URL` variable in LAB-CONTRACT.md would point at an address reachable only through that path.
