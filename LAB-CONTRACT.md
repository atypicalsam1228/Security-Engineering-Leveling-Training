# Lab Contract

What every module may assume about the lab. If a module needs something not listed here, add it to the module's `lab_needs` list and the lab build will provide it.

## Where learners work

Learners run every command inside `lab shell`, a prebuilt tools container (works the same on Mac and Windows). It has: oc, kubectl, helm, jq, curl, git, openssl, terraform, aws, python3, cosign, trivy, tkn (Tekton CLI), argocd, session-manager-plugin.

## Cluster

- One real OpenShift Container Platform single-node cluster per learner on AWS (commercial region), built with FIPS mode on. The learner is cluster-admin on their own cluster.
- Namespaces: `openshift-logging` (collector), `siem` (Loki, Grafana, Alloy), `chat` (Mattermost), `keycloak` (identity), `gitea` (in-lab git server), `openshift-gitops` (Argo CD), `kyverno`, `build` (pipelines), `demo` (sample workload named `demo-app`), `security-tools` (Trivy Operator, Falco).
- Free or low-cost tools only. Included with OpenShift: OpenShift Logging, OpenShift Pipelines (Tekton), OpenShift GitOps (Argo CD), Compliance Operator. Open source: Loki, Grafana, Alloy, Mattermost, Keycloak, Gitea, Kyverno, Trivy, Cosign, Falco.
- Time comes from chrony on each node. Audit, infrastructure and application logs are the three log types.

## Pinned versions

- Kyverno 1.19.2 (Helm chart kyverno/kyverno 3.9.2, namespace `kyverno`), the current stable release on 2026-10-20. In 1.19 ClusterPolicy (kyverno.io/v1) is deprecated but fully supported; the Kyverno project plans to remove it in 1.20. CPS-5 and the ARC modules use ClusterPolicy, so the lab must not install 1.20 or later until they are rewritten for ValidatingPolicy / ImageValidatingPolicy (policies.kyverno.io/v1).
- Terraform AWS provider `~> 6.0` (terraform/versions.tf).
- Versions the module code was checked against on 2026-10-26 (pin these at lab build; Falco and Keycloak versions are not otherwise fixed by the lab): Keycloak 26.8.1, Falco 0.45.1. Gitea is not pinned yet.
- Grafana 13.2.4 (OSS), the current stable release checked on 2026-10-26 (GitHub release tagged Latest, published 13 October 2026; grafana.com/docs/grafana/latest/whatsnew/ lists 13.2 as the newest). Pin this at lab build and confirm with `GET /api/health`. Grafana documents the contact-point, notification-policy, template and mute-timing provisioning API endpoints, and the folder and data-source-by-name APIs, as deprecated (they still work); the SDR modules use them.
- Lab shell tools: Terraform 1.11 or newer and the Session Manager plugin are required; both are in the tools image (lab/image/versions.txt).

## Lab build settings the modules rely on

Found by the accuracy check (2026-10-29); the lab build must provide them, and each module's `TODO.md` lists where it is used.

- Keycloak logs successful sign-ins at debug level by default; modules that read sign-in events need them logged at a level the collector ships.
- The API server audit profile must record request bodies (`WriteRequestBodies` or higher); the role-binding scenarios in the SDR modules read the binding body.
- `lab platform` (run by `lab up`) writes a CA bundle (system CAs plus the cluster ingress CA) at `/workspace/.lab/ca-bundle.crt`; `lab shell` points SSL_CERT_FILE, CURL_CA_BUNDLE, GIT_SSL_CAINFO and REQUESTS_CA_BUNDLE at it, so git over HTTPS and the Gitea, Grafana and Mattermost APIs work from `lab shell`. Pods call Gitea at `GITEA_INTERNAL_URL` (plain HTTP inside the cluster), so they need no certificate.
- Gitea is not pinned yet; the Gitea API fields the modules use were checked against Gitea main source, not a release.
- The AID modules start a scripted stand-in model service in project `ai-lab` (no model account or key). Its code is in `lab/states/aid-2/stub/`.
- Python in the tools image is 3.9 (RHEL 9); module scripts must run on it.
- ARC-4 installs the OpenShift Service Mesh 3 Operator from its start state if it is missing; it is not pinned yet.
- ENG-0's health check looks for Tekton in `openshift-pipelines` (not only `build`) and assumes Gitea's default branch is `main`; pod-name patterns are unconfirmed.

## Learner AWS identity

`lab shell` receives the learner's own AWS credentials. Any direct AWS call in a module exercise runs as that identity, not as the bastion role. Module AWS calls are read-only. terraform/iam_learner_guard.tf provides the cost-guard policy (heartbeat, keep-alive, saves); attach it to that identity.

## Reset points

Each module has `lab start <module>` (load the starting state). `lab reset <module>` returns to the starting state. A combined run simply continues from the previous module's end state.

## Environment variables set by the lab

VARS: LAB_ID AWS_REGION CLUSTER_NAME CLUSTER_API LOKI_URL LOKI_CA_FILE LOKI_USER LOKI_PASSWORD GRAFANA_URL GRAFANA_USER GRAFANA_PASSWORD MM_URL MM_WEBHOOK_URL KEYCLOAK_URL KEYCLOAK_ADMIN_USER KEYCLOAK_ADMIN_PASSWORD GITEA_URL GITEA_INTERNAL_URL GITEA_USER GITEA_TOKEN ARGOCD_URL REGISTRY_HOST LOG_BUCKET ARTIFACTS_BUCKET BASTION_ID KMS_KEY_ARN VPC_ID GUARD_BUCKET

Passwords and tokens live only in these variables. Modules never ask the learner to type or save one.

Credentials are random per lab. `lab up` (lab/labcli/credentials.py) creates a fresh 32-character random KEYCLOAK_ADMIN_PASSWORD, GRAFANA_PASSWORD and LOKI_PASSWORD the first time and keeps them in the 0600 lab.env file (never in Terraform state or outputs, never printed, removed by `lab down`). There are no default passwords anywhere. The lab build must deploy Keycloak, Grafana and Loki with these values from lab.env. GITEA_TOKEN and MM_WEBHOOK_URL are issued by Gitea and Mattermost when the lab build deploys them; the lab build writes them to lab.env and must not use fixed values. The Gitea, Mattermost, Keycloak, Grafana and Loki deployment itself is not in this repository yet.

## Not allowed in modules

Real organization names, a fictional company or story, documents the learner must write, and numbers that are not traced to a source citation.
