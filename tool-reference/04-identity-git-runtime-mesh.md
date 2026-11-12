# Tool reference 04: identity, git, runtime detection, mesh, network policy

Retrieved 2026-10-30. Vendor pages only. Fetch tools summarize pages, so quotes are avoided and statements are paraphrased.
Module ids are the generator file names under generators/content (arc_4 = ARC-4, and so on).

Contents
1. Keycloak 26.8.1
2. Gitea (not pinned)
3. Falco 0.45.1
4. OpenShift Service Mesh 3 (not pinned)
5. Kubernetes / OpenShift NetworkPolicy (not pinned)

---

## Keycloak (26.8.1)
- Vendor docs (all retrieved 2026-10-30):
  - [1] Configuring Keycloak for production - https://www.keycloak.org/server/configuration-production
  - [2] Configuring logging - https://www.keycloak.org/server/logging
  - [3] Configuring TLS - https://www.keycloak.org/server/enabletls
  - [4] Using a reverse proxy - https://www.keycloak.org/server/reverseproxy
  - [5] Configuring trusted certificates for mTLS - https://www.keycloak.org/server/mutual-tls
  - [6] Server Administration Guide, X.509 section (docs/latest; the page is very long and was read in chunks) - https://www.keycloak.org/docs/latest/server_admin/index.html
  - [7] Upgrading Guide (docs/latest) - https://www.keycloak.org/docs/latest/upgrading/index.html
  - [8] Login events and listeners, doc source at tag 26.8.1 - https://raw.githubusercontent.com/keycloak/keycloak/26.8.1/docs/documentation/server_admin/topics/events/login.adoc
  - [9] Brute force detection, doc source at tag 26.8.1 - https://raw.githubusercontent.com/keycloak/keycloak/26.8.1/docs/documentation/server_admin/topics/threat/brute-force.adoc
  - [10] Management interface - https://www.keycloak.org/server/management-interface
  - [11] Bootstrap admin and recovery - https://www.keycloak.org/server/bootstrap-admin-recovery
- Role in this training: identity provider for OpenShift OIDC sign-in, one-time codes and certificate sign-in; modules: cps_2, sdr_2, sdr_3, sdr_4.
- Best practices (vendor-stated):
  - Run at least two instances in production, with a supported production database; cluster traffic is TLS-encrypted by default [1].
  - Use HTTPS for all traffic; serve the admin console and API on a separate hostname or path, and block REST paths at the proxy if they must not be public [1].
  - Keep health and metrics off the main server: they are served on the management port (http-management-port, default 9000); the vendor advises against exposing them on the default server [10].
  - Do not publish /admin/, /realms/master/, /metrics or /health through a proxy; expose /realms/, /resources/ and /.well-known/ [4].
  - Passthrough is the recommended proxy mode for X.509 client certificate authentication; do not set proxy-headers with passthrough [4].
  - Default TLS protocols are TLSv1.3 and TLSv1.2; keep key passwords in a mounted secret or environment variable, not in the command line or conf file [3].
  - The initial admin is temporary: create a permanent admin and then delete the temporary one [11].
  - Brute force detection can be abused to lock real users out; the vendor suggests feeding failure logs to an intrusion prevention system [9].
  - In X.509 flows, set "CRL abort if non updated" to true so an outdated CRL fails authentication [6].
- Implementation guidance relevant to the lab:
  - Client certificates are requested with https-client-auth: none (default), request (validates a certificate only if one is presented), required (fails without one) [5].
  - Truststore: system truststore by default; for a dedicated one use https-trust-store-file and https-trust-store-password. It is shared by all realms (no per-realm truststore) [5].
  - X.509 authenticator settings: user identity source (for example SubjectDN matched by regular expression with one capture group), user mapping method (username, email or attribute), CA subject DN (required, names the trust anchor), key usage / extended key usage / policy checks (empty value disables that check) [6].
  - Revocation: CRL path may be an HTTP/LDAP URL or a file under the conf directory; OCSP can override the responder URI; OCSP fail-open accepts when no valid response exists [6].
  - Direct grant with X.509: copy the Direct grant flow, remove Username Validation and Password, add X509/Validate Username, bind the copy; vendor prefers service accounts with mTLS client authentication where possible [6].
  - Logging: log-level (default info), per-category log-level-<category>, log-console-output=json for JSON lines [2].
  - Events: enable Save events and set an Expiration in realm Events settings; the logging listener writes to category org.keycloak.events; success level defaults below info and is changed with --spi-events-listener--jboss-logging--success-level (debug, info, warn, error, fatal) [8].
  - Permanent lockout disables the account until an administrator re-enables it; re-enabling resets the counter; vendor defaults are 30 failures [9].
- Version notes:
  - 26.8.0: the CA subject DN option becomes required on X.509 user authenticators; "Revalidate Client Certificate" is deprecated; stricter behavior is planned for the next major version [7].
  - 26.8.1: key usage validation runs even when the extension is not critical (option legacy-critical-behavior restores old behavior); CRL files must resolve inside the conf directory; CRL and OCSP responses are capped at 10 MB [7].
  - 26.8.0: callers with view-only permission no longer see client secrets [7].
- Where this project differs:
  - Not used by modules: management interface, health checks, JSON log output.
- Unconfirmed:
  - Keycloak resource sizing and memory guidance: not on the production page fetched [1].
  - Stored key names for X.509 settings (module reads them from source).
  - The 26.8.1 release announcement (https://www.keycloak.org/2026/10/keycloak-2681-released) appeared in search results but was not fetched.
  - Which session idle timeout values are valid: the timeouts section was not reached in the long admin guide.

---

## Gitea (not pinned)
- Vendor docs (retrieved 2026-10-30):
  - [1] Backup and Restore - https://docs.gitea.com/administration/backup-and-restore
  - [2] API usage - https://docs.gitea.com/development/api-usage
  - [3] Webhooks - https://docs.gitea.com/usage/webhooks
  - [4] Configuration Cheat Sheet (first 100000 chars, plus a later chunk) - https://docs.gitea.com/administration/config-cheat-sheet
  - [5] HTTPS setup - https://docs.gitea.com/usage/https-setup
  - [6] Upgrade from an old Gitea - https://docs.gitea.com/installation/upgrade-from-gitea/
  - [7] Install with Docker (rootless) - https://docs.gitea.com/installation/install-with-docker-rootless
  - [8] Protected branches - https://docs.gitea.com/usage/access-control/protected-branches/
  - [9] Latest release page (go-gitea/gitea) - https://github.com/go-gitea/gitea/releases/latest
- Role in this training: in-lab git server (clone, push, API, branch protection, push webhooks); modules: eng_0, grc_3, sdr_5, vm_2, vm_3, vm_4, vm_5, aid_3, cps_2.
- Best practices (vendor-stated):
  - Stop the instance before gitea dump; a running instance can produce an inconsistent database and repository copy [1].
  - Back up before every upgrade, also for patch releases in production; minor upgrades change the database and cannot be undone without a backup [6].
  - Resolve deprecated-config warnings in Site Administration before upgrading, since a later version may refuse to start [6].
  - Tokens get very limited permissions by default; set scopes deliberately (read/write per area; write includes read; "all" is full access) [2].
  - Webhook secrets sign the raw body; receivers should verify X-Gitea-Signature (hex HMAC-SHA256) with a constant-time compare before parsing JSON [3].
  - Webhook and OAuth2 destinations are limited by [security] ALLOWED_HOST_LIST (empty default; groups loopback and private); keep webhook SKIP_TLS_VERIFY false (default) [4].
  - Leave DISABLE_GIT_HOOKS true (default), because custom hooks run arbitrary code on the host [4].
  - Registration is disabled by default (DISABLE_REGISTRATION true); consider REQUIRE_SIGNIN_VIEW and PASSWORD_CHECK_PWN [4].
  - Use built-in HTTPS (PROTOCOL, CERT_FILE, KEY_FILE) or a reverse proxy only when proxy and Gitea share a machine or private network; self-signed certificates are for testing only [5].
  - In containers, mount volumes for data and config; rootful and rootless images are not interchangeable [7].
- Implementation guidance relevant to the lab:
  - API auth header form is Authorization: token <token>; OAuth2 tokens use Bearer. Token creation via POST /users/:name/tokens needs basic auth and the token value is shown once [2].
  - Pagination uses page and limit; MAX_RESPONSE_ITEMS defaults to 50; swagger at /api/swagger and /swagger.v1.json [2][4].
  - Branch protection: required status checks take glob patterns that must match a context reporting success on the head commit (empty list not allowed); "Administrators must follow branch protection rules" blocks admin force merge; force push and push allowlists are separate settings [8].
  - Restore: unzip the dump, move app.ini, data, repos, import the SQL dump, fix ownership, restart, then run gitea admin regenerate hooks [1].
  - TLS: server certificate first in cert.pem, then intermediates; the root is optional [5].
  - Default branch for new repositories is main ([repository] DEFAULT_BRANCH) [4].
- Version notes:
  - Not pinned. Latest release page at retrieval shows v28.2.0 dated 2026-10-18; it labels nothing as breaking but lists authorization and security fixes [9].
  - API field names used by modules were checked by the module authors against Gitea main source, not a release (LAB-CONTRACT.md).
- Where this project differs:
  - grc_3 uses branch protection fields enable_status_check, status_check_contexts, block_admin_merge_override, rule_name; the docs page [8] describes the UI options, and exact API field names were not confirmed on a docs page here.
  - grc_3 needs Gitea to call a private cluster address from a webhook; [4] places the allow list in [security] ALLOWED_HOST_LIST. The lab build is not in this repository.
  - No module runs gitea dump or an upgrade; the lab has no Gitea backup exercise (grep of generators/content).
  - Lab Gitea certificate comes from a lab CA that the tools image trusts; vendor says self-signed is for testing [5]. Shortcut.
  - grc_3 does not show webhook signature verification in the fragments examined; whether the Tekton EventListener validates X-Gitea-Signature was not checked.
- Unconfirmed:
  - Token scope names needed per module (the lab build issues GITEA_TOKEN; scopes not in repo).
  - Whether [security] EGRESS_MODE exists in the pinned release (it appeared in the cheat-sheet summary; not cross-checked).
  - Upgrade steps for the rootless Docker image (that page links elsewhere).
  - Docs at docs.gitea.com/administration/https-support returned 404; /usage/https-setup was used.

---

## Falco (0.45.1)
- Vendor docs (retrieved 2026-10-30):
  - [1] Introducing Falco 0.45.0 - https://falco.org/blog/falco-0-45-0/
  - [2] Release 0.45.1 - https://github.com/falcosecurity/falco/releases/tag/0.45.1
  - [3] Rules basic elements - https://falco.org/docs/concepts/rules/basic-elements/
  - [4] Custom ruleset - https://falco.org/docs/concepts/rules/custom-ruleset/
  - [5] Overriding rules - https://falco.org/docs/concepts/rules/overriding/
  - [6] Outputs concept - https://falco.org/docs/concepts/outputs/
  - [7] Running Falco in a container - https://falco.org/docs/setup/container/
  - [8] Kubernetes (Helm) install - https://falco.org/docs/setup/kubernetes/
  - [9] Kernel drivers - https://falco.org/docs/concepts/event-sources/kernel/
  - [10] falco.yaml at tag 0.45.1 - https://raw.githubusercontent.com/falcosecurity/falco/0.45.1/falco.yaml
  - [11] Configuration options (config_files) - https://falco.org/docs/reference/daemon/config-options/
  - [12] CLI arguments (search result only, see Unconfirmed) - https://falco.org/docs/reference/daemon/cli-arguments/
- Role in this training: runtime detection in namespace security-tools, events shipped to Loki; modules: cps_3, cps_4, sdr_2, sdr_4, eng_0.
- Best practices (vendor-stated):
  - Use rules.d for custom rules and keep defaults as guidance; default rules load first, then custom files, in the order of rules_files [4].
  - Order matters: specific rules before general ones, because evaluation is first-match by default (rule_matching: first) [4][10].
  - Every rule needs an event type in its condition (for example evt.type in (execve, execveat)) so it fires once per event [3].
  - Use override blocks (append or replace) to change default rules; the append: true syntax is deprecated and goes away in 1.0.0 [5].
  - Prefer the modern eBPF driver (default); least-privilege containers drop all capabilities and add sys_admin, sys_resource, sys_ptrace [7][9].
  - Mount /sys/kernel/tracing read-only where possible as a mitigation recommended by the vendor [7].
  - Do not leave outputs_queue capacity at 0 on constrained nodes: unbounded can grow until OOM kill; a set capacity drops events when full [10].
  - Enable metrics (default off) with an interval such as 15m to 6h; output_file has no rotation [10].
  - Verify official images with cosign (signed since 0.35.0) [7].
  - Upgrade the Helm chart to the chart version matching the Falco version and read the chart breaking-changes page [8].
- Implementation guidance relevant to the lab:
  - Default rules_files: falco_rules.yaml, falco_rules.local.yaml, rules.d; only .yml and .yaml in directories are read [10].
  - Required rule fields: rule, desc, condition, output, priority; optional enabled (default true), tags, exceptions [3].
  - json_output defaults to false; stdout_output is enabled by default [10].
  - Validate a rules file with falco -V <file> (reads, validates, exits); --dry-run checks config and rules [12 via search; see Unconfirmed].
  - Priority guidance: sensitive read = WARNING, unexpected shell = NOTICE [3].
  - Container metadata (k8s.pod.name) comes from the container plugin; 0.45 removed container_engines.* keys, configure engines.cri.sockets in the plugin instead [1].
  - Helm customRules values are mounted at /etc/falco/rules.d [4].
- Version notes:
  - 0.45.0: drivers must be API 11.0.0+; older kernel modules and probes are refused; modern eBPF doubles auxiliary map memory per CPU [1].
  - 0.45.0: rules match original bytes (not UTF-8 sanitized); text and JSON output escape control characters; check parsers [1].
  - 0.45.0: container plugin engine_timeout default 10 seconds; reload_control socket off by default [1].
  - 0.45.1: bug fixes (file_output keep_alive, Prometheus metrics race, container plugin 0.7.5, reload robustness) [2].
- Where this project differs:
  - Falco install is done by the lab build, not by a module; its privileges on OpenShift nodes were not reviewed.
- Unconfirmed:
  - [12] was not fetched; the -V and --dry-run wording is from a search-result snippet of that page.
  - Default CRI socket paths for the container plugin on CRI-O (falco.yaml does not list them).
  - OpenShift-specific Falco install notes (the Kubernetes page does not mention OpenShift).
  - Metrics/resource sizing guidance for Falco pods (not found).

---

## OpenShift Service Mesh 3 (not pinned)
- Vendor docs (Red Hat docs.redhat.com was intermittently unavailable; only pages that loaded are listed; retrieved 2026-10-30):
  - [1] OSSM 3.2 Installing, Enabling mutual TLS - https://docs.redhat.com/en/documentation/red_hat_openshift_service_mesh/3.2/html/installing/ossm-enabling-mtls
  - [2] OSSM 3.2 Installing, Sidecar injection - https://docs.redhat.com/en/documentation/red_hat_openshift_service_mesh/3.2/html/installing/ossm-sidecar-injection
  - [3] OSSM 3.2 Release notes - https://docs.redhat.com/en/documentation/red_hat_openshift_service_mesh/3.2/html/release_notes/index
  - [4] Istio (upstream project) application requirements - https://istio.io/latest/docs/ops/deployment/application-requirements/
- Role in this training: sidecar mutual TLS between pods; module arc_4 (start state lab/states/arc-4 installs the operator, Istio and IstioCNI resources named default). Sidecar mode, not ambient.
- Best practices (vendor-stated):
  - In OSSM 3, set mTLS with PeerAuthentication (inbound) and DestinationRule (outbound), not the older ServiceMeshControlPlane [1].
  - PERMISSIVE is the default; STRICT accepts only mTLS. Auto mTLS encrypts sidecar-to-sidecar traffic by default (enableAutoMtls) [1].
  - Namespace STRICT: a PeerAuthentication named default in the target namespace [1].
  - Mesh-wide STRICT: put it in the control plane namespace, which must equal spec.namespace of the Istio resource [1].
  - Under STRICT, sidecar-less callers such as the Kubernetes API server need DestinationRule DISABLE entries, or they fail [1].
  - Injection happens at pod creation: restart deployments after labeling and check READY shows 2/2 [2].
  - Use the Istio CNI plugin so pods do not need NET_ADMIN and NET_RAW in an init container; otherwise the namespace needs privileged admission [4].
  - Do not run applications as UID 1337 (reserved for the sidecar) [4].
  - Prefer istiod port 15012 (TLS/mTLS) over plaintext 15010 for production [4].
- Implementation guidance relevant to the lab:
  - When the revision is named default: label the namespace istio-injection=enabled (or istio.io/rev=default); other revisions use istio.io/rev=<name> [2].
  - If the revision is not named default, create an IstioRevisionTag named default targeting the Istio resource to use istio-injection=enabled [2].
  - If both labels exist, istio-injection wins [2].
  - Opt a workload out with sidecar.istio.io/inject: 'false' under spec.template.metadata.labels, not the top-level labels [2].
  - Sidecar ports (15001, 15006, 15021, 15090, 15020) and istiod ports (15012, 15014, 15017, 443) are listed in [4]; account for these when writing NetworkPolicy.
  - Verify with Kiali lock icons or by checking 2/2 containers [1][2].
- Version notes:
  - Ambient mode is generally available in OSSM 3.2 and not supported on FIPS-enabled clusters [3].
  - Release notes mention that NetworkPolicy updates may be needed for ambient traffic [3].
  - Version-to-OpenShift support tables are linked from [3] but were not read. The lab does not pin a mesh version.
- Where this project differs:
  - arc_4 applies STRICT per namespace with a PeerAuthentication; the namespace-scoped doc text assumes auto mTLS may be off and adds a DestinationRule [1]. With auto mTLS on (default) the lab's approach matches the mesh default.
  - Mesh operator install and pinned channel come from start-state scripts (ensure_operator servicemeshoperator3); version is unpinned. Shortcut.
- Unconfirmed:
  - Red Hat prerequisites for supported OpenShift versions and the InPlace vs RevisionBased upgrade text (pages timed out or returned 503).
  - Istio resource field names beyond what the start state uses (not fetched from a Red Hat page).
  - Behavior of kubelet health probes under STRICT (the mTLS chapter does not address it).
  - Item [4] is the upstream Istio project, not Red Hat's product documentation.

---

## Kubernetes / OpenShift NetworkPolicy (not pinned)
- Vendor docs (retrieved 2026-10-30):
  - [1] Kubernetes, Network Policies - https://kubernetes.io/docs/concepts/services-networking/network-policies/
  - [2] OKD docs (matches the 4.22 line the lab pins), About network policy - https://docs.okd.io/latest/networking/network_security/network_policy/about-network-policy.html
  - [3] Red Hat OpenShift 4.20 network policy page: fetch failed (503); not used.
- Role in this training: default-deny and allow rules; modules: arc_2, arc_4, arc_5, cps_2, cps_3, cps_4, cps_5, aid_5, grc_5.
- Best practices (vendor-stated):
  - Policies are enforced by the network plugin; creating one without a supporting plugin has no effect [1].
  - Pods are open until a policy selects them; a policy lists allowed traffic, and several policies combine as a union [1][2].
  - A connection needs the source egress policy and the destination ingress policy to both allow it [1].
  - Default deny: podSelector {} with policyTypes Ingress, Egress, or both, and no rules [1].
  - A deny-all egress policy also blocks DNS, so add a separate rule to the cluster DNS service [1].
  - Match a namespace by name with the immutable label kubernetes.io/metadata.name [1].
  - OVN-Kubernetes: fewer policies with multiple rules, or matchExpressions, reduce OVS flow count [2].
  - Do not modify the NetworkPolicy objects OKD ships in its own namespaces; DNS and Ingress operator namespaces have default deny plus targeted allows, so unmanaged pods there are blocked [2].
  - For ICMP and ARP, behavior is plugin-defined; NetworkPolicy covers TCP, UDP and optionally SCTP [1].
- Implementation guidance relevant to the lab:
  - endPort (stable since Kubernetes 1.25) gives port ranges; requires a numeric port; unsupported plugins treat it as the single port [1].
  - hostNetwork pods: behavior is undefined; most plugins treat their traffic as node traffic, so use ipBlock for those [1].
  - To reach a service on an external IP from other namespaces, create a policy in openshift-ingress with a namespaceSelector for the source namespace [2].
  - OKD shows the ingress label as policy-group.network.openshift.io/ingress [2].
  - Not possible in NetworkPolicy: explicit deny, cluster-wide defaults, logging of blocked traffic, service-name targeting [1].
- Version notes:
  - NetworkPolicy API is networking.k8s.io/v1; AdminNetworkPolicy and BaselineAdminNetworkPolicy exist as v1alpha1 in the OKD API list [2].
- Where this project differs:
  - arc_4 writes default-deny plus targeted allows in the lab namespaces, as the vendor shows [1]. The DNS rule in aid_5 allows both 53 and 5353 to openshift-dns; the DNS port set is not stated on the pages fetched, so the 5353 line is not vendor-confirmed.
  - Lab modules do not show logging of denied flows; the vendor says the API has none [1], so tests rely on connection results.
  - cps_4 requires OVN-Kubernetes so the policy is enforced (consistent with [1]).
  - Modules that run in namespaces with sidecars must also allow the mesh control ports (see the mesh section).
- Unconfirmed:
  - Red Hat product-page guidance on monitoring and ingress-controller allow rules for 4.22 (the Red Hat page returned 503).
  - Whether OKD defaults for openshift-monitoring need an allow rule for scraping lab namespaces.
