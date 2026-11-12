# IAC-3 live run (2026-11-10; ARC-4 and others in parallel, timings not clean)

`lab start iac-3` 14.4 s, INCOMPLETE notice with 8 [live] items. Every step and test ran. **Without two edits to the agent's own copies of the files in /workspace/iac-3, Steps 1a, 2b, 3b, 4c and 5b fail**; after them every step and test passes. No reset. AWS not touched, nothing to clean up. Captures: `live-run/captures/IAC-3/` (including `unblock`, `unblock2`; the folder holds the files from the failing runs).

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 3.2 s | **Mismatch**: terraform plan exit 2, "1 to change", not 0; two Tekton labels (`openshift-pipelines.tekton.dev/namespace-reconcile-version` and `...namespace-trusted-configmaps-version`, both "1.24.3") that main.tf does not ignore; five resource lines and `ls` match |
| 1b | 1.2 s | Matches |
| 1c | 4.7 s | Matches; ansible-lint 0 failures; "PATH altered" warning and "new release available" notice appear |
| 2a | 9.3 s | Matches (changed=0, ok=1 twice, five `ok:` item lines) |
| 2b | 11.8 s | Playbook part matches (delete says "deleted from iac-lab namespace", then changed=1, then changed=0); Terraform part exit 2 from the same Tekton label diff, not 0; quota itself fine |
| 3a | 1.2 s | Matches |
| 3b | 7.4 s failed, 28.9 s passed | Before unblock: "The baseline is not clean", exit 1 (the module's advice would not fix it); after: 8-row table and three summary lines match; Terraform 1.6 to 1.9 s per check (example 0.3 s), Ansible 3.6 to 4.0 s (example 2.4 s); exit codes 0/2/0 Terraform, 0 on every Ansible row |
| 4a, 4b | 1.7, 1.3 s | Match (five state entries, no extra-binding) |
| 4c | 2.5 s | **Mismatch**: conformance FAILED, exit 1; two live role bindings that Tekton creates are not in the PLATFORM allowlist: `openshift-pipelines-edit` (ClusterRole edit) and `pipelines-scc-rolebinding` (ClusterRole pipelines-scc-clusterrole); after unblock `conformance ok (all)`, exit 0 |
| 5a | 1.3 s | Matches |
| 5b | 8.3 s failed, 8.4 s passed | Before: DRIFT live conformance naming the same two bindings, exit 1; after: four PASS lines, exit 0 |
| Test 1 | 9.1 s | Passes after unblock; listing shows the two Tekton bindings plus the three `system:` ones |
| Test 2 | 20.8 s | Matches (terraform exit 0, changed=0, DRIFT live conformance naming extra-binding, gate exit 1, after cleanup exit 0) |
| Test 3 | 4.3 s | Matches (line 40 `verbs: ["*"]`, code check fails, apply skipped, gate exit 1, live role stays `["get","list","watch"]`) |

## Bugs
1. **Terraform strips Tekton namespace labels (same family as IAC-1 and IAC-2).** The start-state `terraform/main.tf` has `ignore_labels` only for `pod-security...` and `security.openshift.io/...`; it needs `"openshift-pipelines[.]tekton[.]dev/.*"` too. Breaks 1a, 2b and 3b, and a learner following the module is stuck at Step 3. The Tekton labels appear within seconds of namespace creation.
2. **PLATFORM allowlist is incomplete.** OpenShift Pipelines adds `openshift-pipelines-edit` and `pipelines-scc-rolebinding` to every new namespace; conformance.py (module text in Step 4b) allows only the three `system:` bindings. Breaks 4c, 5b and Test 1 on a lab with Pipelines. The module text, the Section 6 note and the "exactly three role bindings" statements (Section 2.3 and the design decision) need to list five. No network policy exists in a new namespace, as the TODO assumed.
3. Step 3 example seconds are low (Terraform 0.3 s, Ansible 2.3 s; real about 1.6 to 1.9 s and 3.6 to 4.0 s).
4. Minor: delete message reads "deleted from iac-lab namespace"; Ansible prints two "[WARNING]: No inventory was parsed" lines before each playbook run that the module's grep does not filter; the Step 1c example mentions only the PATH warning.

## Unblocks (agent's copy only)
- `/workspace/iac-3/terraform/main.tf`: `ignore_labels` also lists `"openshift-pipelines[.]tekton[.]dev/.*"`; plan then returns exit 0.
- `/workspace/iac-3/conformance.py`: `PLATFORM` also lists `"openshift-pipelines-edit"` and `"pipelines-scc-rolebinding"`.
- Real fix belongs in `lab/states/iac-3/kit` (main.tf) and the module text (PLATFORM set and counts).

## Same problems as earlier modules?
Terraform stripping labels: yes (bug 1; IAC-1 and IAC-2 hit the same family). Argo CD sync: not involved. git-clone TLS, `tkn pipeline start` prompts, emptyDir workspaces, root-owned workingDir: not applicable (no pipeline or git here).

## TODO [live] status
Confirmed: python3 3.9 runs measure.py and conformance.py with PyYAML present; `oc create rolebinding --serviceaccount` and `oc patch --type=merge` work; `kubernetes.core.k8s` finds the cluster from the exported KUBECONFIG; the ansible-lint PATH warning does not change the result; the harness measures timings at run time.
Not met as written: "OpenShift creates the three system: bindings and no network policy" (two Tekton bindings are also created, bug 2); "terraform plan returns 0 right after apply on the real cluster" (exit 2 until the Tekton label ignore is added, bug 1; covers the [live] 1 namespace-annotations and [live] 5 plan-after-apply items).

State left: `/workspace/iac-3` with the two edits; `iac-lab` namespace with baseline objects intact (quota, default-deny, role, binding); no extra-binding and no wild.yml.

## 2026-11-11 re-run

Result: PASS (`lab start iac-3` rebuilt /workspace/iac-3 and the baseline itself). Captures: captures/IAC-3/rr-*.txt. All steps 1a-5b and Tests 1-3 met their checkpoints: Terraform exit 0, lint 0 failures, changed=1 then changed=0 after the quota delete, harness table (a and b caught by both tools, c by neither), `conformance ok (all)`, four PASS lines, Test 2 `DRIFT live conformance` / gate exit 1 / cleanup exit 0, Test 3 wildcard refused and live verbs still get, list, watch.

Wording-only mismatches:
- Delete messages end `deleted from iac-lab namespace` (2b quota, Test 2 binding); the examples show `deleted`.
- 1c and Test 3: ansible-lint also prints a "A new release of ansible-lint is available" line, and Test 3 prints `<unknown>:1: SyntaxWarning: invalid decimal literal` before the lint result. Suggest adding the SyntaxWarning to the Test 3 note next to the PATH warning.
- 4a: ls shows `-rw-r--r--` (no trailing dot) and no `.` SELinux marker.
- 2a/2b: Ansible also prints two `[WARNING]: No inventory was parsed` lines each run; the module only mentions the PATH warning.
