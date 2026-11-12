# Tool Reference

Vendor best practices and implementation guidance for every tool the training uses. Compiled 2026-10-30 from the vendors' own documentation (official docs, release notes and project repositories). Each section lists the pages it used, the modules that use the tool, vendor-stated practices, guidance for the tasks the modules perform, version notes, where this project differs from the vendor guidance, and what could not be confirmed.

STATUS: DRAFT. Read these limits before relying on it:
- The pages were read through a fetch tool that returns summaries, not raw pages. Re-check a paraphrase against the linked page before quoting it.
- Where the vendor has no page for the pinned version, the nearest version is used and the section says so (for example Grafana 13.3 "latest", Red Hat Pipelines 1.20 and GitOps 1.17, OKD 4.22 pages, OpenShift Logging 6.6).
- Each "Where this project differs" list is a finding to review, not a change already made.
- Nothing here is a compliance citation. Framework requirements are cited in the modules from NIST and FedRAMP only.

| File | Tools |
|---|---|
| `tool-reference/01-openshift-platform.md` | oc and kubectl, FIPS mode, audit profiles, etcd encryption, project request template, security context constraints, OpenShift Logging forwarding, `oc debug node`, Compliance Operator |
| `tool-reference/02-logging-alerting-chat.md` | Loki, Grafana 13.2.4, Alloy, Mattermost |
| `tool-reference/03-policy-supply-chain-delivery.md` | Kyverno 1.19.2, Cosign 3.1.4, Trivy 0.76.1 and Trivy Operator, OpenShift Pipelines (Tekton) and tkn, Argo CD and OpenShift GitOps |
| `tool-reference/04-identity-git-runtime-mesh.md` | Keycloak 26.8.1, Gitea, Falco 0.45.1, OpenShift Service Mesh 3, NetworkPolicy |
| `tool-reference/05-cloud-infrastructure-and-host-tools.md` | Terraform and the AWS provider, AWS S3, KMS, IAM, VPC and Budgets, AWS CLI and Session Manager plugin, the OpenShift installer on AWS, Podman and Docker, Python, PyYAML, jq and envsubst |

Pinned versions are in `LAB-CONTRACT.md` and `lab/image/versions.txt`. Loki, Alloy, Mattermost and Gitea are not pinned yet.
