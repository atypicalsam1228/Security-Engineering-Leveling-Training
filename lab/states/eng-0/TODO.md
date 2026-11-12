# Open items: start state for ENG-0 (Terminal, Git and Your Lab)

Lab needs are numbered as in the module's lab_needs list. `+ [done]` lines are covered by files in this folder;
`- [live]` lines can only be confirmed on a live cluster or account; `- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: Gitea reachable at GITEA_URL, with the lab token able to create a repository and push (HTTPS certificate trusted by the tools image). Checked 2026-11-03: Gitea up and eng-sandbox created; the push itself is exercised by ENG-0 Step 2b.
+ [done] 2: Gitea repository eng-sandbox with README.md, broken.yaml and health-check.sh (30-sandbox-repo.sh).
+ [done] 3: Deployment demo-app (1 replica, label app=demo-app) in namespace demo (20-demo-app.sh).
+ [done] 4: Pod names behind the health check patterns: loki and grafana in siem; tekton-pipelines in openshift-pipelines; trivy and falco in security-tools; siem-forwarder in openshift-logging. Checked on a live cluster 2026-11-03: every pattern in 30-sandbox-repo.sh matches a Running pod, no change needed.
