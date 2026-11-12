# VM-5 start state: Risk-Based Gate in Delivery

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: OpenShift Pipelines, namespace build, gitea-clone credential linked to pipeline, older pipelines team-b-release and team-c-release, repository vm-app, ConfigMap vm-tools (rank.py, fixtures, sample exceptions, ledger seed, the supplied gate_rules.py, gate_exceptions.py and gate_ledger.py, the Step 2 check check_matches.py and the reference answer reference-rule_match.py for the learner's own rule_match.py).
Still needed (live cluster or lab build): see TODO.md.

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh.
