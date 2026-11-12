# VM-2 start state: Scan and Hand Off

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: Namespace vm-lab, Deployment legacy-web (nginx 1.16), Gitea repository vm-app (main and deps-updated), ConfigMap vm-tools in security-tools (handoff.sh).
Still needed (live cluster or lab build): see TODO.md.

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh.
