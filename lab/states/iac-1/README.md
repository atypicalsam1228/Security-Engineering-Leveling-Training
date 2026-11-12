# IAC-1 start state: Run a Supplied Baseline as Code

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 10-iac-namespace-build.sh (namespace build exists), 30-iac-supplied.yaml (config map iac-supplied in build: the supplied Terraform files versions.tf, variables.tf, main.tf, risky.tfvars and broken-main.tf.txt, the playbook baseline.yml and the script summary.sh, generated from the SUPPLIED texts in generators/content/iac_1.py). reset.d/10-remove-iac-1-work.sh deletes namespace iac-lab and the folder /workspace/iac-1 (Terraform state, plans, fetched files).
Not created by the start state on purpose: namespace iac-lab, which the learner creates with Terraform in Step 2.
Still needed (live cluster or lab build): see TODO.md. `lab start` prints it while TODO.md exists.

Prerequisites: ENG-0 Terminal, Git and Your Lab (runs alone: this start state loads everything the module needs).

If a text in SUPPLIED changes in iac_1.py, regenerate 30-iac-supplied.yaml so the two stay identical.

Scripts here have not been run on a live cluster. Shared helpers: ../_common/lib.sh (sourced by the scripts).
