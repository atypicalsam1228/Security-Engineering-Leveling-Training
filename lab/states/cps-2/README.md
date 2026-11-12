# CPS-2 start state: Apply a Hardening Baseline

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 10-sample-web.sh (namespace harden-lab without pod security labels, and an unhardened Deployment sample-web), 20-compliance-operator.sh (installs the Compliance Operator, waits for VALID ProfileBundles), 30-baseline-files.sh (ConfigMap baseline-files: namespace.yaml, workload-patch.yaml, quota.yaml, default-deny.yaml, bad-pod.yaml, and scan.yaml built from the candidate rules that exist on the cluster). reset.d removes the scan, the tailored profile and the namespace.
Still needed (live cluster or lab build): see TODO.md. `lab start` prints it while TODO.md exists.

Prerequisites: none (runs alone). The learner extracts the supplied files with `oc extract configmap/baseline-files -n harden-lab --to=.`.

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh (sourced by the scripts).
