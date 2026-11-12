# TODO: start state for GRC-3 (Automate Evidence Collection)

Lab needs are numbered as in the module's lab_needs list. `+ [done]` lines are covered by files in this folder;
`- [live]` lines can only be confirmed on a live cluster or account; `- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: Repository evidence-scripts (public in the lab, README on main) and a push webhook to the EventListener.
- [lab-build] 1: Gitea must allow webhooks to private cluster addresses (webhook.ALLOWED_HOST_LIST in app.ini). The state script fails at the webhook call if it does not.
+ [done] 2: Task and Pipeline for the gate, config map review-gate, TriggerTemplate, EventListener, secret gitea-api, config map evidence-source.
- [live] 2: triggers.tekton.dev/v1beta1 inline binding with a value, the service el-gate-listener on port 8080, and that the push payload field body.after is the commit the gate must mark.
+ [done] 3: Service accounts, the read-only cluster role, the trigger permissions and the volume claim.
- [live] 3: The built-in cluster roles tekton-triggers-eventlistener-roles and tekton-triggers-eventlistener-clusterroles exist in OpenShift Pipelines; if the names differ the bindings in 30-evidence-access.yaml must change.
- [live] 4: Pods in build can pull registry.access.redhat.com/ubi9/python-312:1 and quay.io/openshift/origin-cli:4.22.0 (the cluster reaches the internet), that python image has curl, and pods reach Gitea at the address stored in evidence-source (the in-cluster service on port 3000 found by 50-gitea-evidence-repo.sh, or GITEA_URL when none is found).
- [lab-build] 5: Gitea certificate trusted by lab shell; GITEA_TOKEN is an administrator token. (The module sets the git credential helper and identity itself in Step 1.)
+ [done] 6: Kyverno presence check and the Audit policy grc-no-latest-tag so the policy list is not empty.
- [lab-build] 6: FIPS-mode cluster install. Confirm the newest rendered-master MachineConfig has spec.fips true.

Open items from review (live test or decision):
- Gitea fields, combined status endpoint and the 405 refusal were checked against Gitea main source on 2026-10-29. Re-check against the Gitea version the lab runs once it is pinned.
- Live check: a scheduled job fetches the raw file from a public repository without a token (unauthenticated raw URL).
