# GRC-3 start state: Automate Evidence Collection

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 10-demo-app.sh (namespaces demo and build, Kyverno presence check), 20-pipelines.sh (OpenShift Pipelines), 30-evidence-access.yaml (service accounts evidence-runner, gate-runner, gate-trigger, the read-only cluster role evidence-reader, trigger permissions, volume claim evidence-pvc), 40-kyverno-policy.yaml (Audit policy grc-no-latest-tag), 50-gitea-evidence-repo.sh (repository evidence-scripts, config map evidence-source, secret gitea-api, push webhook), 60-review-gate-script.yaml (config map review-gate, the gate script), 70-review-gate-pipeline.yaml (Tasks and Pipeline review-gate), 80-gate-trigger.sh (TriggerTemplate gate-template and EventListener gate-listener), 35-cronjob-reference.yaml (config map cronjob-reference: the reference answer for the Step 5 writing exercise; the learner opens it only after trying), 55-supplied-files.sh (copies kit/collect_a.py and kit/check-cronjob.py into /workspace/grc-3/evidence-work). reset.d removes the CronJob, jobs, volume claim, gate runs, branch protection and the learner's branches.
Still needed (live cluster or lab build): see TODO.md. `lab start` prints it while TODO.md exists.

Prerequisites: ENG-0 Terminal, Git and Your Lab

kit/collect_a.py is the first half of the collector (Step 2 reads it); kit/check-cronjob.py holds the learner's CronJob to the Step 5 spec. If you change the answer in 35-cronjob-reference.yaml, keep the CronJob text in generators/content/grc_3.py (CRON_HEAD) and kit/check-cronjob.py in step.

The review gate is a tested copy of the gate; if you change it, change 60-review-gate-script.yaml and nothing else. The module does not print its text.

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh (sourced by the scripts) and ../_common/demo-app.yaml.
