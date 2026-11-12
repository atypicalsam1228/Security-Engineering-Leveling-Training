# CPS-4 start state: Secure a Workload End to End

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 10-secure-lab.sh (namespace secure-lab; insecure Deployment and Service sample-api with a plain-text DB_PASSWORD value, default service account, no security context; callers api-client and stranger), 05-etcd-encryption-start.sh (turns encryption on first without waiting, with a message that a long wait is expected), 20-etcd-encryption.sh (waits for it, and turns it on if still off; aesgcm), 30-preflight-falco.sh (read-only check that Falco and the falco-custom-rules config map exist), 40-kit.sh (stores default-deny.yaml in ConfigMap secure-lab-kit, which Step 3 extracts, and the reference answer answers/secret-read-rule.txt for the learner-written Falco rule in ConfigMap secure-lab-answers, which Step 4 tells the learner to extract only after trying; kept as .txt because a rule list is not a Kubernetes manifest). reset.d deletes the namespace and both secure-lab rules keys.
Still needed (live cluster or lab build): see TODO.md. `lab start` prints it while TODO.md exists.

Prerequisites: none (runs alone). AWS calls in the module are read-only (sts, ec2 describe-volumes, kms describe-key).

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh (sourced by the scripts).
