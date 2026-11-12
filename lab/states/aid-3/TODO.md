# TODO: start state for AID-3 (AI-Assisted Automation Under Review)

+ [done] 1: stub model service (shared with aid-2).
+ [done] 3: review_gate.py, pipeline definition, Gitea repo and branch setup scripts.
- [live] 4: Loki push endpoint, tenant and gateway path used by ailog.py (LOKI_URL, LOKI_CA_FILE, LOKI_USER, LOKI_PASSWORD).
- [live] 2: Gitea branch protection API fields, and whether the administrator account can override the required status.
- [live] 3: tkn flags: --exit-with-pipelinerun-error ; git-clone cluster resolver available.
- [live] 1: oc port-forward svc/stub-model works from the lab shell.
- [lab-build] 4: Env vars GITEA_URL, GITEA_USER, GITEA_TOKEN exported to the lab shell.
+ [done] 2: Gitea repository ai-tools with protected main and branch bad-summarizer (setup scripts).
- [live] 2: image registry.access.redhat.com/ubi9/python-312:1 (python3 with unittest) is pulled by the cluster from the internet; tag exists.
- [lab-build] 2: Loki credentials and LOKI_CA_FILE exported to the lab shell.
- [live] 4: Loki instant query endpoint GET /loki/api/v1/query with basic authentication, the LogQL of the three drafts (sum by (user) over count_over_time with | json | event=...), and the lab shell clock agreeing with Loki to within a few seconds (Step 5 counts eight events in the last hour).
- [live] 2: on an existing lab where main is already protected, gitea_put_file may be refused when it updates ailog.py or seed_fixture.py (unconfirmed); then delete the ai-tools repository and run lab start aid-3 again.
