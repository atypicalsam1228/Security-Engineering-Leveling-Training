# CPS-5 start state: Guardrails Developers Inherit

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 30-install-kit.sh (copies kyverno-rbac.yaml and check-registry.py into /workspace/cps-5 and the finished registry rule to /workspace/cps-5/reference/validate-images-answer.yaml; it never touches the learner's own files; the learner writes the pattern of the registry rule in Step 4 and the reference is opened only afterward), 10-corpus.sh (ConfigMap workload-corpus in guardrails-lab: twelve Deployments with replicas 0, eight ordinary ok-* and four unsafe bad-*), 20-preflight-kyverno.sh (read-only check that Kyverno, its CRD and the background controller service account exist). reset.d removes the policies, the extra cluster role, the project template and its cluster setting, and every namespace named gr-*.
Still needed (live cluster or lab build): see TODO.md. `lab start` prints it while TODO.md exists.

Prerequisites: none (runs alone). The module changes cluster-wide project creation (it sets a project request template), so run `lab reset cps-5` when finished; later modules that create projects would otherwise get the quota.

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh (sourced by the scripts).

The registry rule in Step 4 uses REGISTRY_HOST (lab variable) and registry.access.redhat.com, the registry of the supplied corpus. The registry test creates two zero-replica Deployments in gr-after; reset.d removes the policy gr-validate-images and every gr-* namespace.
