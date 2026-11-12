# GRC-2 start state: Run Evidence Collection

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 10-demo-app.sh (namespaces demo and build, Kyverno presence check), 20-pipelines.sh (OpenShift Pipelines), 30-evidence-access.yaml (service accounts evidence-runner and evidence-limited, the cluster roles evidence-reader and evidence-reader-basic, and their bindings), 35-sample-workloads.yaml (namespace grc2-workloads with payments-api, which sets runAsNonRoot, and legacy-batch, which does not: the data for the Step 5 root-pods check), 40-kyverno-policy.yaml (Audit policy grc-no-latest-tag), 50-collector-script.yaml (config map evidence-collector, generated from the COLLECTOR text in generators/content/grc_2.py), 55-reference-answer.yaml (config map evidence-reference: the reference answer to the Step 5 writing exercise, the same text as in grc_2.py), 60-collector-pipeline.yaml (Task evidence-collect and Pipeline collect-evidence; public images origin-cli:4.22.0 and ubi9/python-312:1, no tools-image parameter). reset.d removes the pipeline runs and the my-check config map the module makes.
Still needed (live cluster or lab build): see TODO.md. `lab start` prints it while TODO.md exists.

Prerequisites: ENG-0 Terminal, Git and Your Lab

If the collector text in grc_2.py changes, regenerate 50-collector-script.yaml so the two stay identical.

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh (sourced by the scripts) and ../_common/demo-app.yaml.
