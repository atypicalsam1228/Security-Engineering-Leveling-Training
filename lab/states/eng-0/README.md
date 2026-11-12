# ENG-0 start state: Terminal, Git and Your Lab

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: Creates namespace demo and Deployment demo-app (1 replica, non-root), and the private Gitea repository eng-sandbox with README.md, broken.yaml (a deliberate indent mistake) and health-check.sh (one line per platform tool: Loki, Grafana, Mattermost, Gitea, Tekton pipelines, Kyverno, Trivy operator, Falco, the collector, and the sample app).
Still needed (live cluster or lab build): see TODO.md. `lab start` prints it while TODO.md exists.

Prerequisites: None. This is the foundation module of the engineering track; it runs on its own.

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh (sourced by the scripts) and ../_common/demo-app.yaml.
