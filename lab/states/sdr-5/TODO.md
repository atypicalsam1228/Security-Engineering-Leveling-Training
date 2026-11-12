# TODO: start state for SDR-5 (Detection as Code)

`+ [done]` lines are covered by files in this folder; `- [live]` lines can only be confirmed on a live cluster;
`- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: Secrets, repository files, routing, preflight.
- [live] 4: The pipeline pods can pull registry.access.redhat.com/ubi9/python-312:1 (it has python3, curl and tar) and reach GITEA_URL, GRAFANA_URL and LOKI_URL; the Gitea archive endpoint /api/v1/repos/OWNER/detections/archive/BRANCH.tar.gz answers for a branch name.
- [lab-build] 5: Mattermost team lab (override with MM_TEAM) with channel siem-alerts, and Secret mm-api in namespace siem, key token: a Mattermost personal access token for the learner account that can read and post in that channel.
- [lab-build] 2: GITEA_URL, GRAFANA_URL and LOKI_URL are reachable from pods in namespace build (otherwise 10-ci-secrets.sh needs in-cluster addresses).
- [live] 1: Gitea contents API round trip (lib.sh gitea_put_file), DELETE of a repository, git extraHeader clone over the lab CA.
- [live] 3: Grafana provisioning PUT and POST with a fixed uid; the alert message contains the rule title.
- [live] 4: Tekton: tekton.dev/v1 Task and Pipeline, a when expression on a param, task results passed between tasks, tkn pipeline start flags.
- [live] 1: Audit profile WriteRequestBodies (requestObject.roleRef in audit records).
- Decision: the evaluation interval is the Grafana default for a new rule group; the module measures it rather than setting it.
+ [done] 2: Secrets detections-ci and detections-ci-ca in build.
+ [done] 1: Reference answer for the pod-exec rule exercise copied to /workspace/sdr-5/reference (15-reference.sh); ci/check_rule.py checks a rule offline (tested locally against the reference and four wrong variants).
+ [done] 3: Grafana contact point, default route and folder siem-detect.
- [live] 3: measure.py reads the rule (folderUID, ruleGroup) and the rule group (interval in seconds) from the Grafana provisioning API.
