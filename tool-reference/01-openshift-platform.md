# OpenShift Platform Features and Compliance Operator - Vendor Reference

Retrieved 2026-10-30. Sources are vendor pages only (Red Hat docs, OKD docs, the vendor GitHub repos). Where docs.redhat.com had no fetchable body, the OKD 4.22 page (the community build of the same docs) is cited and labeled.

Contents
1. OpenShift CLI (oc, kubectl) 4.22.18
2. FIPS mode
3. API server audit profiles
4. etcd encryption
5. Project request template
6. Security context constraints (SCC)
7. OpenShift Logging collector and log forwarding
8. oc debug node
9. Compliance Operator

---

## 1. OpenShift CLI: oc and kubectl (4.22.18)
- Vendor docs:
  - [1] OpenShift CLI (oc), OCP 4.22, https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/cli_tools/openshift-cli-oc (retrieved 2026-10-30)
  - [2] Getting started with the OpenShift CLI, OKD 4.22, https://docs.okd.io/4.22/cli_reference/openshift_cli/getting-started-cli.html (2026-10-30)
  - [3] Understanding authentication, OCP 4.22, https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/authentication_and_authorization/understanding-authentication (2026-10-30)
- Role in this training: the lab shell's main client; every cluster module uses it. kubectl ships in the same tarball (versions.txt).
- Best practices (vendor-stated):
  - Use an `oc` version that matches the cluster; an older `oc` cannot run all commands of a newer release. [2]
  - Behind a proxy, set HTTP_PROXY, HTTPS_PROXY, NO_PROXY; `oc` honors them, and auth headers go only over HTTPS. [1][2]
  - Prefer `oc login <url> --web` to avoid putting a token on the command line; the vendor warns the local callback server uses HTTP, not HTTPS, so avoid it on multi-user workstations. [2]
  - API requests authenticate with OAuth bearer tokens or X.509 client certificates; requests with neither become system:anonymous. [3]
- Implementation guidance:
  - Download from the Red Hat mirror (https://mirror.openshift.com/pub/openshift-v4/clients/oc/latest/), unpack, put `oc` on PATH. [2]
  - `oc login -u <user>` interactive, or the console's "Copy login command" for a token login. [2]
- Version notes: the project pins 4.22.18 from the versioned mirror path (versions.txt); [2] shows the `latest` path, which is not version-pinned.
- Where this project differs: none found; the pinned versioned URL plus sha256 is stricter than [2].
- Unconfirmed: oc-to-cluster version-skew policy (not found in the pages fetched).

## 2. FIPS mode (4.22)
- Vendor docs:
  - [1] Support for FIPS cryptography, OCP 4.22, https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/installation_overview/installing-fips (2026-10-30)
  - [2] Enabling etcd encryption, OCP 4.22, https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/etcd/enabling-etcd-encryption (2026-10-30; via search extract)
- Role in this training: cluster built with `fips: true`; the check reads the kernel flag on the node. Modules: ARC-4, GRC-2, GRC-3 (grep, case-insensitive "fips").
- Best practices (vendor-stated):
  - FIPS must be chosen at install time; it cannot be turned on after deployment. Set `fips: true` in install-config.yaml. [1]
  - Run the installer from a RHEL 9 host that is itself in FIPS mode, and use `openshift-install-fips` instead of `openshift-install`. [1]
  - Get the FIPS installer with `oc adm release extract --registry-config <pull secret> --command=openshift-install-fips --to <dir> <release image>` (needs oc 4.16 or newer), or from the public mirror tarball. [1]
  - FIPS is supported on x86_64, ppc64le and s390x only. [1]
  - Use CRI-O so containers can detect a FIPS host; use RHEL disk encryption for data at rest. [1]
  - For etcd, boot nodes in FIPS mode and, after install, apply AES-CBC etcd encryption per the etcd procedure. [1]
- Implementation guidance: verification command is not in the fetched FIPS page. The module reads `/proc/sys/crypto/fips_enabled` through `oc debug node/<n> -- chroot /host`; this is lab practice, not from [1] (see Unconfirmed).
- Version notes: [1] lists limits: TLS FIPS support is incomplete; Azure File storage blocks FIPS mode; no single-step hash/signature function.
- Where this project differs: the lab turns on etcd encryption with `aesgcm`; [1] names AES-CBC for the FIPS case (see section 4). 4.22 release notes mention TLS profile and cipher fixes for FIPS clusters (search extract only, not read in full).
- Unconfirmed: a vendor-stated verification command for FIPS mode on a running node.

## 3. API server audit profiles (4.22)
- Vendor docs:
  - [1] Configuring the audit log policy, OCP 4.22, https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/security_and_compliance/audit-log-policy-config (2026-10-30)
  - [2] Set up log forwarding (audit collection), Logging 6.6, https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.6/html/configure/set-up-log-forwarding (2026-10-30)
- Role in this training: GRC-2 reads the profile; SDR-2 and SDR-4 depend on request bodies being logged; forwards audit logs.
- Best practices (vendor-stated):
  - Profiles: Default (metadata for reads and writes; bodies only for OAuth token requests), WriteRequestBodies (adds bodies for create, update, patch, delete, deletecollection), AllRequestBodies (adds bodies for reads), None (logs nothing). [1]
  - Secret, Route and OAuthClient resources and OAuth server events are logged at metadata level only, whatever the profile. [1]
  - Body-logging profiles cost more CPU, memory and I/O than Default. [1]
  - Red Hat does not recommend None unless the troubleshooting risk is understood. [1]
  - customRules can set a profile per group; they override the top-level profile, first match wins; they are ignored if the top-level profile is None. [1]
  - Audit logs are voluminous and sensitive; consider `prune` filters before forwarding. [2]
- Implementation guidance:
  - `oc edit apiserver cluster`, set `spec.audit.profile`; confirm the rollout with `oc get kubeapiserver` until NodeInstallerProgressing shows AllNodesAtLatestRevision (takes minutes). [1]
- Version notes: unset profile means Default. [1]
- Where this project differs: SDR-2 notes that the Default profile logs metadata only and WriteRequestBodies is needed for role-binding bodies; SDR-4 text says "the audit profile records request bodies". Check that the start state sets WriteRequestBodies or higher (not verified here). Module GRC-2 treats an unset profile as Default, which matches [1].
- Unconfirmed: exact per-verb list differences between docs versions (older pages list fewer verbs).

## 4. etcd encryption (4.22)
- Vendor docs:
  - [1] Enabling etcd encryption, OCP 4.22, https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/etcd/enabling-etcd-encryption (2026-10-30)
  - [2] Enabling etcd encryption, OKD 4.22, https://docs.okd.io/4.22/etcd/etcd-encrypt.html (2026-10-30)
  - [3] Backing up and restoring etcd data, OCP 4.22, https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/etcd/backing-up-and-restoring-etcd-data (2026-10-30)
- Role in this training: CPS-4 start state turns it on; patches it with the TLS profile.
- Best practices (vendor-stated):
  - Supported types: AES-CBC (PKCS#7, 32-byte key) and AES-GCM (random nonce, 32-byte key). Keys rotate every 7 days; up to 10 old keys are kept. [1]
  - Encrypted: secrets, config maps, routes, OAuth access and authorize tokens. Only values are encrypted; resource types, namespaces and names stay readable. [2]
  - Do not back up etcd until initial encryption finishes; an early backup may be partly encrypted. [2]
  - Encryption keys are needed to restore a backup; with encryption on, the static_kuberesources tarball holds them, so store it apart from the snapshot. [2][3]
  - Expect higher memory use for a few resources and a transient backup-performance effect. [2]
  - Back up from one control plane host only, off-peak, after the first certificate rotation (24 hours after install), and keep backups outside the cluster. [3]
- Implementation guidance:
  - `oc edit apiserver`; set `spec.encryption.type` to `aesgcm` or `aescbc`. Takes 20 minutes or longer. [1]
  - Verify the Encrypted condition is EncryptionCompleted on three resources: `oc get openshiftapiserver`, `oc get kubeapiserver`, `oc get authentication.operator.openshift.io`, each with `-o=jsonpath='{range .items[0].status.conditions[?(@.type=="Encrypted")]}{.reason}{"\n"}{.message}{"\n"}'`. [1]
  - Switching type migrates data automatically. [1]
  - Backup: `oc debug --as-root node/<n>`, `chroot /host`, `/usr/local/bin/cluster-backup.sh /home/core/assets/backup`. [3]
- Version notes: [3] says a restore needs a snapshot from the same z-stream release. 4.22 docs also list Kubernetes KMS v2 (section titles only; not read).
- Where this project differs: the lab chooses `aesgcm` (stated as a lab choice in CPS-4); FIPS page names AES-CBC (section 2). The start-state script checks the same three resources as [1]. No module takes the etcd snapshot described in [3] (grep found no use).
- Unconfirmed: KMS v2 procedure; whether AES-GCM vs AES-CBC has a vendor performance statement.

## 5. Project request template (4.22)
- Vendor docs:
  - [1] Projects (Configuring project creation), OCP 4.22, https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/building_applications/projects (2026-10-30)
- Role in this training: CPS-5 adds a ResourceQuota to the template.
- Best practices (vendor-stated):
  - The API server builds each new project from the template named in `projectRequestTemplate`; if unset, a default template makes the requester admin. [1]
  - Template parameters: PROJECT_NAME (required), PROJECT_DISPLAYNAME, PROJECT_DESCRIPTION, PROJECT_ADMIN_USER, PROJECT_REQUESTING_USER. [1]
  - Self-provisioning is granted by the `self-provisioner` cluster role through the `self-provisioners` binding; inspect it with `oc describe clusterrolebinding.rbac self-provisioners`. [1]
- Implementation guidance:
  - `oc adm create-bootstrap-project-template -o yaml > template.yaml`, edit, `oc create -f template.yaml -n openshift-config`. [1]
  - `oc edit project.config.openshift.io/cluster`, set `spec.projectRequestTemplate.name`; the default name is `project-request`; create a project to verify. [1]
  - `projectRequestMessage` customizes the text for users who cannot self-provision (named in search extract; section body not read).
- Version notes: none found.
- Where this project differs: the lab emits JSON and uses `oc apply` and `oc patch --type=merge` instead of `oc edit`; equivalent in effect. The `sleep 30` plus `oc wait clusteroperator/openshift-apiserver --for=condition=Progressing=False` step is a lab shortcut; [1] only says to create a project to verify.
- Unconfirmed: whether the API server needs a rollout after the config change (not stated in the text read).

## 6. Security context constraints (4.22)
- Vendor docs:
  - [1] Managing security context constraints, OCP 4.22, https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/authentication_and_authorization/managing-pod-security-policies (2026-10-30)
- Role in this training: relies on restricted SCC admission when testing a root pod.
- Best practices (vendor-stated):
  - Do not modify default SCCs; changes can break platform pods and are reset during some upgrades. Create custom SCCs instead. [1]
  - restricted-v3 is the strictest default and applies to authenticated users; it forces a user namespace (hostUsers: false). restricted-v2 drops all capabilities, sets seccomp runtime/default and blocks privilege escalation. [1]
  - `privileged` is for cluster administration only. A pod's `privileged: true` does not by itself pick that SCC; admission picks by permission and priority. [1]
  - Never set priority above 0 on default SCCs. [1]
  - Grant SCC access through RBAC: `oc create role <r> --verb=use --resource=scc --resource-name=<scc> -n <ns>`, then bind it. [1]
  - Do not run workloads in default, kube-*, openshift-* system projects; SCC admission does not work there. [1]
  - New SCCs should allow at least configMap, downwardAPI, emptyDir, persistentVolumeClaim, secret, projected volumes. [1]
- Implementation guidance:
  - Which SCC admitted a pod: `oc get pod <p> -o jsonpath='{.metadata.annotations.openshift\.io\/scc}{"\n"}'`. [1]
  - `oc get scc`, `oc describe scc <name>`. Require one SCC with `openshift.io/required-scc` on the pod template, not a live pod. [1]
- Version notes: restricted-v3 is described in 4.22; the lab text names "restricted SCCs".
- Unconfirmed: `oc adm policy add-scc-to-user` text (not in the section read).

## 7. OpenShift Logging collector and log forwarding (Logging 6.6 docs; version not pinned)
- Vendor docs:
  - [1] Set up log forwarding, Logging 6.6, https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.6/html/configure/set-up-log-forwarding (2026-10-30)
  - [2] Configuring log forwarding, Logging 6.6, https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.6/html/configure/configuring-log-forwarding (2026-10-30)
  - [3] Configure outputs, Logging 6.6, https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.6/html/configure/configure-outputs (2026-10-30)
  - [4] Fine-tune log forwarding, Logging 6.6, https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.6/html/optimize/fine-tune-log-forwarding (2026-10-30)
- Role in this training: (ClusterLogForwarder `siem-forwarder`), helpers in lab/states/_common/lib.sh, SDR modules downstream.
- Best practices (vendor-stated):
  - Create a service account in openshift-logging and bind one ClusterRole per log type: collect-application-logs, collect-infrastructure-logs, collect-audit-logs. [2]
  - Bind the role BEFORE adding the log type to inputRefs. If a type is added without its binding, the Operator removes the whole collector DaemonSet and all collection stops. [1]
  - Audit logs are much larger and more sensitive than other types; consider `prune` filters before forwarding. Logging is not a SIEM and gives no secure audit storage. [1][2]
  - With a LokiStack output, include the `tls.ca` block; without it the forwarder shows Ready but no logs arrive. [1]
  - Delivery: unset means an in-memory buffer (fast, not durable). `AtLeastOnce` re-sends after a crash and may duplicate; `AtMostOnce` favors throughput. Other tuning: compression, maxWrite, minRetryDuration, maxRetryDuration. [4]
  - `loki` output type is for external Loki and supports custom label keys and tenant keys; `lokiStack` is for the Red Hat LokiStack. [3]
- Implementation guidance:
  - `oc adm policy add-cluster-role-to-user collect-audit-logs system:serviceaccount:openshift-logging:collector`; check with `oc get clusterrolebinding -o wide | grep collect`. [1]
  - ClusterLogForwarder apiVersion `observability.openshift.io/v1`, with `spec.serviceAccount`, `spec.outputs[]`, `spec.pipelines[].inputRefs/outputRefs`. [1][2]
  - Add audit later with `oc edit clusterlogforwarder <name> -n <ns>` after the binding exists. [2]
- Version notes: Logging 6 moved the API to observability.openshift.io and merged ClusterLogging into ClusterLogForwarder; Fluentd was removed in favor of Vector (search extract of the 6.6 upgrade page). Search results gave conflicting minimum OCP versions for 6.6 (4.19 vs 4.20); the Operator life-cycle page was seen only as a search snippet.
- Where this project differs:
  - The lab binds all three roles first (matches [1]) and uses the external `loki` type with username and password secrets and a CA secret; the docs pages read show the lokiStack example only, so the exact `loki` field names are not checked here.
  - The doc example says the ClusterLogForwarder `metadata.name` must be `instance`; the lab names it `siem-forwarder`. The statement is in the lokiStack example; whether it applies to custom names is not verified here.
  - The module YAML sets no `prune` filter for the audit input and the delivery mode is added later via a patch; both fit [4] but audit volume advice in [1] is not applied.
  - Static basic-auth password for Loki is a lab shortcut.
- Unconfirmed: which Logging version the lab installs (default channel is chosen at run time by ensure_operator); `loki` output field names; collector resource sizing (not read).

## 8. oc debug node (4.22)
- Vendor docs:
  - [1] Host security (Day 2), OKD 4.22, https://docs.okd.io/4.22/post_installation_configuration/day_2_core_cnf_clusters/security/security-host-sec.html (2026-10-30)
  - [2] Bare-metal node maintenance (Day 2), OKD 4.22, https://docs.okd.io/4.22/post_installation_configuration/day_2_core_cnf_clusters/troubleshooting/troubleshooting-bmn-maintenance.html (2026-10-30)
  - [3] Before you update the cluster (etcd backup), OKD 4.22, https://docs.okd.io/4.22/post_installation_configuration/day_2_core_cnf_clusters/updating/update-before-the-update.html (2026-10-30)
- Role in this training: GRC-2 (FIPS flag).
- Best practices (vendor-stated):
  - Red Hat recommends a debug pod as the way to reach a node; avoid direct SSH, and never use the root user (use `core`). Do not configure direct root access. [1]
  - Use SSH only if `oc debug` fails. [2]
  - Configuring the node host from the OS is not recommended or supported; use it for inspection. [2]
- Implementation guidance:
  - `oc debug node/<node>` then `chroot /host` to run host binaries. [1][2]
  - Root session: `oc debug --as-root node/<node>`. [3]
  - Node logs: `oc adm node-logs <node> -u crio`. [2]
- Version notes: none found.
- Where this project differs: the modules use the one-line form `oc debug node/$NODE -- chroot /host <cmd>`, which fits [1] and [2]. The pages read do not show that exact form.
- Unconfirmed: the debug pod's privilege requirements for a non-admin (learner is cluster-admin here).

## 9. Compliance Operator (docs list 1.10.0 as newest; version not pinned)
- Vendor docs:
  - [1] Compliance Operator chapter, OCP 4.22, https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/security_and_compliance/compliance-operator (2026-10-30)
  - [2] Installing the Compliance Operator, OKD 4.22, https://docs.okd.io/4.22/security/compliance_operator/co-management/compliance-operator-installation.html (2026-10-30)
  - [3] Managing Compliance Operator remediation, OKD 4.22, https://docs.okd.io/4.22/security/compliance_operator/co-scans/compliance-operator-remediation.html (2026-10-30)
  - [4] Compliance Operator usage, upstream repo, https://github.com/openshift/compliance-operator/blob/master/doc/usage.md (2026-10-30)
- Role in this training: CPS-2 (start states 20-compliance-operator.sh); mentions it.
- Best practices (vendor-stated):
  - The Operator is not an auditor; an authorized assessor must certify compliance. [1]
  - Define persistent storage before install (raw results); all nodes must run the same release; supported on RHCOS only. [2][1]
  - Namespace needs `pod-security.kubernetes.io/enforce: privileged` in 4.22. [2]
  - Do not add the system:authenticated group or requiredDropCapabilities to the `restricted` SCC; it can break scanner pods. [2]
  - Manage scans with ScanSetting + ScanSettingBinding (creating a ComplianceSuite or ComplianceScan by hand is discouraged). [1][4]
  - Default ScanSetting: daily at 01:00, 1Gi volume, keeps 3 results, no automatic remediation. `default-auto-apply` applies and updates remediations automatically; use only with care. [1][3]
  - Platform checks use ocp4-* profiles; node checks use ocp4-*-node or rhcos4-* profiles; the `roles` field must match MachineConfigPool names. [1][4]
  - Applying a MachineConfig remediation reboots every node in the pool; pause the pool (`.spec.paused: true`) when applying several. Re-scan after applying. [3]
- Implementation guidance:
  - Install (CLI): Namespace, OperatorGroup (targetNamespaces = itself), Subscription (channel stable, source redhat-operators). [2]
  - `oc get profile.compliance -n openshift-compliance`; check bundles via `status.dataStreamStatus` = VALID. [1]
  - ScanSettingBinding `profiles` + `settingsRef: default`; watch `oc get compliancesuites -w`; results are ComplianceCheckResult objects labeled with check-status and severity. [1][4]
  - Apply a fix: `oc -n openshift-compliance patch complianceremediations/<name> --patch '{"spec":{"apply":true}}' --type=merge`. [3]
  - Raw ARF results: per-scan PVC; extract with a pod mount and `oc cp`, or `oc compliance fetch-raw`. [4][1]
  - Re-run a binding: `oc compliance rerun-now scansettingbindings <name>` (search extract, oc-compliance plugin). [1]
- Version notes: 1.10.0 (stable channel) updates the ocp4-cis profiles to CIS benchmark v2.0.0 and refreshes the ocp4-stig and rhcos4-stig profile content; CIS 1.7 profiles removed; NetworkPolicy objects are created for operand pods. [1]
- Where this project differs:
  - The lab creates the namespace plain (ensure_namespace) and subscribes to the catalog default channel; [2] requires the privileged pod-security label and names channel stable. Whether the OLM install adds the label is not verified here.
  - Module binds ocp4-stig and ocp4-stig-node with the default setting (report-only), which matches [1]; the module states that profile names are looked up first.
  - One-node cluster: the default roles worker and master both map to the same node; node scan time is not a concern.
- Unconfirmed: exact resource sizing for the scanner pods on single-node; storage class availability on the lab cluster.
