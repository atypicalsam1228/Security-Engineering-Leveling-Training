# IAC-1 live run (2026-11-10; ARC-4 ran in parallel, timings not clean)

Every step ran once, no reset, no fixes. `lab start iac-1` 3.3 s, INCOMPLETE notice (2 [lab-build] and 5 [live] items). Captures: `live-run/captures/IAC-1/`. No AWS resources created; everything is on the cluster. Wall times are per labrun container call. About 2 minutes of machine time against the module's 62-minute estimate (reading dominates).

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 2.7 s | Matches: 4 files, `64 baseline/main.tf` |
| 1b, 1c | 1.3 s | Read-only; 64, 14, 14 lines |
| 1d | 4.5 s | Passes but prints a lock-file warning the module does not show (bug 3) |
| 2a | 4.4 s | Matches: `Plan: 5 to add`, `{"create":5}`, 5 create lines |
| 2b | 10.9 s | Matches: 5 added, namespace Active |
| 3a | 3.5 s | Matches (patched, 50) |
| 3b | 5.8 s | **Mismatch**: plan is `0 to add, 2 to change`, exit 2; quota line `"pods" = "50" -> "10"` correct, but the namespace is also updated in place |
| 3c | 14.0 s | **Checkpoint fails**: apply `2 changed`, pods back to 10, but the final `exit code:` is 2, not 0 |
| 4b | 4.4 s | Matches (changed=2, no service account created); reserved-name warning (bug 4) |
| 4c | 6.5 s | Matches: changed=2, then changed=0 |
| 5b | 10.7 s | Terraform line wrong (bug 1); Ansible 0 then 1 as expected; diff is JSON, not `baseline:` lines (bug 5) |
| 5c | 7.2 s | Playbook changed=1; Terraform line still exit 2, checkpoint fails |
| Test 1 | 7.2 s | **Fails**: `Plan: 0 to add, 1 to change`, terraform exit 2; Ansible changed=0 and policy `["Ingress","Egress"]` fine |
| Test 2 | 9.7 s | Partly: `^Plan:` line does not print (bug 2); destroy list, count 1 and surviving policy match |
| Test 3 | 6.0 s | Matches: same error text, `nmae` on line 3, exit 1 |

## Bugs
1. **Perpetual namespace drift (blocks the CM-6 story).** OpenShift adds 4 annotations to `iac-lab` (`openshift.io/sa.scc.*`, `security.openshift.io/MinimallySufficientPodSecurityStandard`) and the Tekton operator adds 2 labels (`openshift-pipelines.tekton.dev/namespace-*-version`). Terraform plans to strip them (`annotations ... -> null`, `labels ... -> null`) on every plan, so `-detailed-exitcode` returns 2 even with nothing changed by hand. repair.plan has 2 changes and the exit code stays 2 after the repair, so the Step 3 checkpoint ("exit 0 after repair"), Step 5 ("Terraform matches") and Test 1 all fail; the Step 3b filter shows two objects instead of one; summary.sh reports "differs" at every point. Applying also strips the Tekton labels and may fight the controllers. The start-state TODO assumed "a plain Namespace gets no project defaults"; that is false here. Suggested fix (not made): `lifecycle { ignore_changes = [metadata[0].annotations, metadata[0].labels] }` on the namespace resource or `kubernetes_annotations`; or create the namespace in the start state and have Terraform manage only the objects inside it.
2. **Test 2 `grep '^Plan:'` prints nothing**: the plan line is wrapped in colour codes because `-no-color` is missing. With bug 1 fixed, the expected line is `0 to add, 0 to change, 1 to destroy`; with the bug it is `0 to add, 1 to change, 1 to destroy`.
3. Step 1d: `init` prints an unauthenticated-provider note and a yellow "Incomplete lock file information" warning (offline mirror, linux_amd64 only); the lock file is created. Harmless, should be mentioned.
4. Ansible 2.19+ prints `Found variable using reserved name 'namespace'` (`baseline.yml:8`) to stderr on every run (4b, 5a, 5c, summary.sh); the `| grep` blocks in 4b do not hide it. Rename the variable (for example `target_ns`).
5. Step 5b: `--check --diff | grep -A3 '^--- before'` shows only `--- before / +++ after / @@ -1,6 +1,6 @@ / {` (JSON of the whole object), never `baseline: changed-by-hand` or `baseline: iac-1`. Use a larger `-A` or grep for `baseline`.
6. Step 4b shows no diff for new objects; stated in the module and correct.

## Notes
- The Tekton git-clone, `tkn` and emptyDir problems from earlier modules do not apply: IAC-1 uses no Tekton, Gitea or git.
- Everything works offline: Terraform 1.17.0 with provider 3.4.0 from the mirror; Ansible and kubernetes.core work with the `ansible_playbook_python` interpreter.
- The plan shows `api_groups = [null]` for the role (cosmetic). OpenShift added 3 extra role bindings (`system:deployers`, `system:image-builders`, `system:image-pullers`), as the module notes, plus `pipeline`, `builder`, `default`, `deployer` service accounts and CA-bundle config maps.
- The module has no cleanup step of its own, only `lab reset iac-1`, so nothing was cleaned up.
- Left in the lab: namespace `iac-lab` (5 Terraform objects plus `report-reader` and `settings-record`; settings record repaired, quota 10); `/workspace/iac-1` with state, plans and the `risky` and `broken` copies. No shared cluster settings changed.

## TODO [live] status
1 (apply works on OpenShift; plan matches expect text): partly; create plan and apply match, but the "plain Namespace gets no project defaults" assumption is disproved (bug 1). 2 (drift plan shows one update on the quota, greps work, exit 2): partly; a second update on the namespace appears. 3 (ansible check changed=2, real run 2, second run 0, diff after hand edit): confirmed including the ServiceAccount; the diff is JSON (bug 5). 4 (`ansible_python_interpreter` picks the venv Python): confirmed. Negative tests: confirmed (risky.tfvars destroys exactly `kubernetes_network_policy_v1.default_deny[0]`, policy untouched; `validate` exits 1 with the same text); only the `Plan:` grep needs `-no-color`. [lab-build] 2 and 3 (image tools, kubeconfig path): confirmed.
