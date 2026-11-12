# Platform notes: security group (70, 75, 80, 85, 90)

All scripts: idempotent, `set -euo pipefail`, one `say` line per milestone, Helm releases skipped when the pinned chart is already deployed. Pins and sources: `versions-security.txt`. `bash -n` and shellcheck (koalaman/shellcheck:stable) are clean. The Kyverno, Trivy Operator and Falco charts were rendered with `helm template` (helm 3.19.0) with the values used here to confirm resource names, CRDs and value paths. Nothing has run on a live cluster.

## 70-kyverno.sh
Helm `kyverno/kyverno` 3.9.2 into `kyverno` (release `kyverno`): deployments `kyverno-{admission,background,cleanup,reports}-controller`, one replica each. Waits for CRDs `clusterpolicies.kyverno.io`, `policies.kyverno.io`, `policyreports.wgpolicyk8s.io`, `clusterpolicyreports.wgpolicyk8s.io` and the service account `kyverno-background-controller` (CPS-5, AID-5, ARC modules). Requests total about 320m CPU and 390Mi; limits 384Mi + 256Mi + 128Mi + 256Mi memory. `runAsUser`/`runAsGroup` are nulled so the OpenShift SCC assigns the UID (Kyverno platform notes). Chart default excludes only `kube-system` from webhooks. No variables saved.

## 75-trivy-operator.sh
Helm `aquasecurity/trivy-operator` 0.38.1 into `security-tools`: Deployment `trivy-operator` (pod names start `trivy-`). Standalone mode (each scan job downloads the DB from mirror.gcr.io; two concurrent jobs, up to 1G each; the chart default of 500M got scan jobs OOMKilled. Node collector, infra assessment and CIS compliance are off (they need host access; no module reads them). Namespaces `openshift-*`, `kube-*`, `openshift` are excluded from scanning. Also labels `security-tools` privileged for Pod Security (Falco needs it). Soft-waits up to 10 minutes for the first ConfigAuditReport and VulnerabilityReport and only warns if none. Operator requests 50m/512Mi, limit 1536Mi (512Mi was OOMKilled in the live run and 1Gi left no margin at about 990Mi working set; an existing install is upgraded when the limit differs). Reports are deleted after 24h by the chart default and re-created.

## 80-falco.sh
Helm `falcosecurity/falco` 9.2.1 (Falco 0.45.1) into `security-tools`: DaemonSet `falco`, modern eBPF driver, `json_output: true`, container plugin metadata (chart default), `falcoctl` install init container on, follow sidecar off. ConfigMap `falco-custom-rules` is created empty by the script (not by Helm, so learner keys survive) and mounted at `/etc/falco/rules.d`. SCC: the chart creates SCC `falco` (privileged, hostPath, hostPID, hostNetwork) because the eBPF probe needs a privileged container and host paths on RHCOS. Requests 100m/256Mi, limit 1 CPU/1Gi. Falco stdout goes to Loki through the collector as application logs from `security-tools`.

## 85-pipelines-and-gitops.sh
Subscribes (copied `ensure_operator`, explicit channel) to OpenShift Pipelines (`openshift-pipelines-operator-rh`, `openshift-operators`), waits for TektonConfig Ready, `tekton-pipelines` pods and Task `git-clone`; then OpenShift GitOps (`openshift-gitops-operator` namespace, OperatorGroup `upgradeStrategy: Default`), waits for the `openshift-gitops` ArgoCD Available and Route `openshift-gitops-server`. Saves `ARGOCD_URL`. Extra, not in the original table: installs the OpenShift Logging operator and the `siem-forwarder` ClusterLogForwarder (same objects as `ensure_siem_forwarder`) because nothing else did and ENG-0's health check needs a collector pod before any module starts.

## 90-final-check.sh
Prints UP/DOWN with namespace and address for Loki, Grafana, Alloy, Mattermost, Gitea, Keycloak, Tekton, Argo CD, Kyverno, Trivy, Falco and the collector, checks the CRDs, `falco-custom-rules`, `siem-forwarder` and `gitea-admin`, lists the saved variable names (names only), and exits 1 if anything is down or a variable is missing.

## Unverified (needs a live cluster)
- Kyverno and Trivy pods under restricted-v2; Trivy scan jobs and DB download from mirror.gcr.io; whether `OPERATOR_EXCLUDE_NAMESPACES` accepts the glob list as the chart comment says.
- Falco modern eBPF on the RHCOS kernel, CRI-O metadata fields `k8s.ns.name` / `k8s.pod.name` without the k8smeta plugin, and that the rule file keys added by `oc set data` are loaded after `oc rollout restart`.
- Channel `latest` for Pipelines and GitOps (checked at run time), the Logging operator default channel and its OperatorGroup mode (`own`), route reachability of Argo CD (only pods and route are checked, not HTTP).
- Health URLs used by 90: Gitea `/api/healthz`, Mattermost `/api/v4/system/ping`, Keycloak `/realms/master`.
