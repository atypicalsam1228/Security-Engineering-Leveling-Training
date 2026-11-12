# VM-4 start state: Prioritize by Context and Validate

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: Namespaces vm-lab (criticality=high), vm-internal, vm-batch; workloads legacy-web (Service and Route), report-svc, batch-old (0 replicas); repository vm-app; ConfigMap vm-tools (rank.py, deadlines.py, facts_lib.py).
Still needed (live cluster or lab build): see TODO.md.

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh.
