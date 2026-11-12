# VM-3 start state: Triage and Track Fixes

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: Gitea repository vm-app and ConfigMap vm-tools (review_gate.py, fixture-findings.json, fixture-empty.json).
Still needed (live cluster or lab build): see TODO.md.

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh.
