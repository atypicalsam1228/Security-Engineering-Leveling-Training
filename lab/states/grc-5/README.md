# GRC-5 start state: Continuous Control Monitoring Design

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 10-demo-app.sh (namespaces, Kyverno check), 20-pipelines.sh (OpenShift Pipelines), 30-monitor-access.yaml (service account monitor-reader, read-only Role and binding in demo, volume claim monitor-pvc), 40-kyverno-policies.yaml (Audit policies grc-no-latest-tag, grc-no-privileged, grc-require-owner-label), 45-wait-reports.sh (waits up to about 2 minutes for the first policy reports and prints a message that a wait is expected), 50-kit.sh (stores control-monitor.yaml, measure.py and compare-reference.py in ConfigMap monitor-kit in build; Steps 3, 4 and 5 extract them with --keys; compare-reference.py is the answer to the Step 3 exercise and is opened only after the learner tries). reset.d removes the CronJob, jobs, config maps, volume and the test role binding.
Still needed (live cluster or lab build): see TODO.md. `lab start` prints it while TODO.md exists.

Prerequisites: ENG-0 Terminal, Git and Your Lab

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh (sourced by the scripts) and ../_common/demo-app.yaml.
