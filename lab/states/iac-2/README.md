# IAC-2 start state: Deliver a Baseline as Code with Terraform

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 10-clean.sh (removes namespace iac-lab, /workspace/iac-2 and the Gitea repository iac-baseline, so the module runs alone whether or not IAC-1 ran), 20-pipelines.sh (OpenShift Pipelines, namespace build), 30-gitea-repo.sh (repository iac-baseline with README.md, .gitignore and providers.tf on main; config map iac-source; secret iac-gitea-api), 40-plan-gate-pipeline.yaml (Tasks iac-plan-check and iac-plan-report, Pipeline iac-plan-gate). 35-reference.sh (the reference answer for the role the learner writes in Step 2, copied from ref/access.answer.tf to /workspace/iac-2/answers/, outside the repository folder). reset.d removes all of it plus the pipeline runs.
Still needed (live cluster or lab build): see TODO.md.

Prerequisites: ENG-0 and IAC-1 (teaching only; nothing is loaded from them).
Scripts here have not been run on a live cluster. Shared helpers: ../_common/lib.sh.
