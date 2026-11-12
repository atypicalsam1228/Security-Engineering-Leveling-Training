# ARC-2 start state: Trace the Security Stack

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 05-preflight.sh (Kyverno and network plugin check), 10-namespace.yaml (arc-lab), 20-app.sh (applies arc-app.tpl: web, api, db, services, default-deny ingress plus two allow policies),
40-kyverno-policies.yaml (arc-require-nonroot Enforce, arc-disallow-latest Audit, both scoped to arc-lab), 50-install-tools.sh (copies trace_stack.py to $HOME/arc).
trace_stack.py is supplied (Python 3.9 standard library only); its map-building logic was tested offline against the manifests in this folder.

Prerequisites: ENG-0 (terminal, git, oc and lab basics). Needs the Kyverno 1.19.2 platform tool installed by the lab build. Scripts have not been run on a live cluster.
