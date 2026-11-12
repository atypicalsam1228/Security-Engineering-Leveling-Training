# IAC-2 live run (2026-11-10; ARC-4 ran in parallel, timings not clean)

Every step and test ran once, no reset, no fixes. `lab start iac-2` 22.1 s, INCOMPLETE notice (6 [live] items, 1 [lab-build]). Captures: `live-run/captures/IAC-2/`. Step 2c's blanks were filled with the reference values (`[""]`, `["pods"]`, `["get", "list"]`). No AWS resources created; no shared cluster settings changed. Machine time about 3.5 minutes against the module's 73 min.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 3.9 s | Matches; init also prints the "Incomplete lock file information" warning (IAC-1 bug 3) |
| 1b, 1c | 1.2, 2.9 s | `ok`, "Success! The configuration is valid." |
| 2a to 2c | 1.2 to 1.3 s | Match |
| 2d | 4.4 s | `Plan: 5 to add`, five create lines, `true` |
| 2e | 1.4 s | "your access.tf matches the reference" |
| 3a, 3b | 1.4 s each | `gate: PASS` exit 0; `FAIL empty plan input`, `gate: FAIL`, exit 1 |
| 4a | 3.6 s | Commit, push, protection JSON as shown |
| 4b | 3.6 s | "pull request 1: Add the iac-lab baseline"; four extra `remote:` hint lines (VM-4 bug) |
| 4c | 87 s | `gate: PASS`, `status posted: 201`, `iac-plan-gate success`, merge `200` |
| 4d | 6.9 s | "saved plan matches the reviewed plan", `Apply complete! Resources: 5 added`, namespace `iac-lab` Active, `BASELINE v1` |
| 5a | 1.3 s | `ok` |
| 5b | 4.1 s | **Checkpoint fails**: `drift: FOUND`, `# kubernetes_namespace_v1.lab will be updated in-place`, exit 2; module expects `drift: none`, exit 0 |
| Test 1 | 7.5 s | **Fails on the last lines**: listing, `yes`, `no` match; drift check prints FOUND, exit 2; rolebinding list shows 5 extra bindings the example omits |
| Test 2 | 34.3 s | **Passes**: local gate exit 1; cluster gate prints FAIL lines and `iac-plan-gate failure`; merge `405`, PR closes, role still `["get","list"]`; extra Tekton "task check has failed" and "failed to get logs for task check" lines |
| Test 3 | 8.7 s | **Partly fails**: the hand edit (pods 50) is caught, exit 2, naming `kubernetes_resource_quota_v1.lab`; after the revert the check still prints FOUND (namespace), exit 2, not `drift: none` and 0 |

## Bugs
1. **Perpetual namespace drift remains (blocks the CM-6 story).** IAC-1's bug in a smaller form. IAC-2's `providers.tf` has `ignore_annotations = ["openshift[.]io/.*"]` and `ignore_labels = ["pod-security...", "security[.]openshift[.]io/.*"]`, which fixed the annotations and OpenShift labels. The Tekton operator adds two more labels, `openshift-pipelines.tekton.dev/namespace-reconcile-version` and `...namespace-trusted-configmaps-version` (1.24.3); Terraform plans to strip them (`- ... = "1.24.3" -> null`) on every plan, and the plan also shows `generation 0 -> known after apply`. So 5b, Test 1 and the revert half of Test 3 never reach exit 0. Suggested fix (not made): add `"openshift-pipelines[.]tekton[.]dev/.*"` to `ignore_labels` in the start state's `providers.tf` (and the same idea for IAC-1).
2. Test 2 prints Tekton "task check has failed" and "failed to get logs" lines; expected on a failing gate, but the example should show them.
3. Test 1's example omits the five OpenShift/Tekton-added role bindings (`openshift-pipelines-edit`, `pipelines-scc-rolebinding`, `system:deployers`, `system:image-builders`, `system:image-pullers`). Cosmetic.
4. 1a init lock-file warning and 4b `remote:` hints, both known.

## Same-problem check (VM-5, AID-3, SDR-5, IAC-1)
- Tekton git-clone self-signed cert: not hit (the gate task fetches by HTTP from Gitea and runs a plain `check` step; no CA ConfigMap needed).
- `tkn pipeline start` prompting: not hit (all params passed with `-p`).
- emptyDir workspaces not shared: not hit (gate task `check`, then finally task `report`, no shared workspace).
- Task step workingDir root-owned: not hit.
- Namespace annotations and labels stripped by Terraform: partly hit (bug 1).

## Notes
- The first `tkn` run took about 87 s (most likely the `ubi9/python-312` image pull); the second, with the failed gate, about 34 s.
- Branch protection confirmed (fields `enable_push:false`, `enable_status_check`, `status_check_contexts`); `405` merge refusal confirmed.
- The module has no cleanup step; nothing cleaned up. Left in the lab: namespace `iac-lab` (5 Terraform objects plus OpenShift-added bindings, service accounts, config maps); Gitea repo `iac-baseline` with main protected, merged PR #1, closed PR for the wildcard test, branches `add-baseline` and `wildcard-role`; `/workspace/iac-2` with state and plans; PipelineRuns `iac-plan-gate-run-b9dn9` and `iac-plan-gate-run-6pp2g` in `build`.

## TODO [live] status
1 Partly: the provider block with `config_path` and the ignore regexes works and annotations and OpenShift labels are ignored, but the first plan after apply does not exit 0 (bug 1). 2 Confirmed: branch_protections fields work, merge refusal `405`, the raw endpoint with `?ref=` worked (gate task read `gate.py` from main and `plan.json` from the commit). 3 Confirmed: `tkn pipeline start ... -s pipeline --showlog` works, the finally task posts `iac-plan-gate` (`success` and `failure`), the pod pulled `registry.access.redhat.com/ubi9/python-312:1-1762230134` and reached Gitea. 4 Confirmed: `lab start` removed the old `/workspace/iac-2`, clone fresh. 5 Confirmed: Terraform 1.17.0 with the provider mirror works offline; credential helper and identity set by the module. 6 Confirmed: the learner is cluster-admin and Terraform created all five objects; the NetworkPolicy exists, OVN enforcement not tested.

## 2026-11-11 re-run

Result: PASS (clean state: iac-baseline repo and /workspace/iac-2 deleted, then `lab start iac-2`; namespace iac-lab was already absent). Captures: captures/IAC-2/rr-*.txt. The 2c blanks were filled with api_groups [""], resources ["pods"], verbs ["get","list"]. All steps 1a-5b and Tests 1-3 met their checkpoints: plan 5 to add, check `true`, gate PASS/exit 0 and `FAIL empty plan input`/exit 1, status `iac-plan-gate success`, merge 200, apply 5 added, drift none/exit 0; Test 2 gate FAIL, status failure, merge 405, PR closed, role still ["get","list"]; Test 3 drift FOUND/exit 2, then none/exit 0.

Wording-only mismatches:
- 1a: init prints an extra "Incomplete lock file information for providers" warning (module elides with "...").
- 2d: the plan shows `api_groups = [null]` for the core group "" (display only; the jq check still prints true).
- Test 3: only `# kubernetes_resource_quota_v1.lab will be updated in-place` prints; the `has changed` line is absent (module already says the first lines depend on the Terraform release). Suggest dropping the "has changed" line from the example.
- Test 1: listing has 6 role bindings as documented; ages 7-16s.
