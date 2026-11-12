# TODO: start state for VM-5 (Risk-Based Gate in Delivery)

+ [done] 1: OpenShift Pipelines, build namespace, gitea-clone credential, team-b-release and team-c-release, fixtures.
- [live] 1: ghcr.io/aquasecurity/trivy:0.76.1 has sh, sed, head and trivy; registry.access.redhat.com/ubi9/python-312:1 has sh and python3; pipeline pods can pull both (cluster reaches the internet).
- [live] 1: Tekton accepts a ConfigMap workspace via tkn config=; a failing step still keeps the Task result.
- [live] 3: The JSON patch applies to the two legacy pipelines; the git credential annotation matches the Gitea host.
- [live] 4: Internet from the lab shell and from pipeline pods: KEV feed, the two images, and the Trivy database.
+ [done] 2: gitea-clone git credential secret for the pipeline service account in build.
+ [done] 3: older pipelines team-b-release and team-c-release in build.
- [live] 1: Lab shell reaches the public KEV JSON feed; the ID list fits a ConfigMap (size limit); the real catalog lists none of the fictional CVE-2099 fixture IDs.
