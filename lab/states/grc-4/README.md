# GRC-4 start state: Evidence in the Delivery Pipeline

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 10-demo-app.sh (namespaces, Kyverno check), 20-pipelines.sh (OpenShift Pipelines), 30-evidence-access.yaml (edit role for the pipeline service account in demo, volume claim evidence-work), 40-kyverno-policy.yaml (Enforce policy grc-enforce-no-latest-tag), 50-candidate-manifests.sh (config map candidate-manifests with good.yaml and bad.yaml), 55-policy-kit.sh (config map policy-kit with the policy-check Task and the reference answer for the learner's admit.py). reset.d removes the learner's tasks, pipeline, runs, signing secret and volume.
Still needed (live cluster or lab build): see TODO.md. `lab start` prints it while TODO.md exists.

Prerequisites: ENG-0 Terminal, Git and Your Lab

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh (sourced by the scripts) and ../_common/demo-app.yaml.
