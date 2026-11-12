# CPS-2 live run (2026-11-10; AID-5 in parallel) - PARTIAL

The lab was paused by the guard partway through Step 5a (master stopped 18:03:19Z "User initiated", bastion terminated 18:06:29Z; `lab keep` had lapsed). Steps 1a to 4c ran once and passed. 5a (partly), Test 1 and Test 2 still to run after `lab resume` / `lab start cps-2`; scripts `c2_5a.sh`, `c2_t1.sh`, `c2_t2.sh` in the scratchpad. Captures: `live-run/captures/CPS-2/`.

`lab start cps-2` 1 m 19 s, INCOMPLETE notice (3 [live] items).

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 4.2 s | Matches except pod securityContext prints `{}`, not `null` |
| 2a | 4.5 s | Matches; dry run says "configured (server dry run)"; enforce, warn, audit all `restricted` |
| 3a | 6.5 s | Rollout done; quota 128Mi/512Mi, pods 2/5. Patch dry run prints no "(server dry run)" suffix |
| 4a | 5.6 s | Matches; profile READY, binding `harden-scan`, 6 rules |
| 4b | 3.9 s | Bad pod refused (Forbidden, exit 1) |
| 4c | 29.6 s | Suite DONE, NON-COMPLIANT; module says "several minutes" |
| 5a | partial | 6 results: 1 FAIL (`harden-baseline-configure-network-policies-namespaces`), 5 MANUAL; count and texts not run |
| Test 1, 2 | not run | lab paused |

## Bugs and notes
1. **Step 5 checkpoint cannot be met.** The module says "at least one PASS"; the scan gave 0 PASS, 1 FAIL, 5 MANUAL.
2. Step 1: pod-level securityContext is `{}`, module says `null`.
3. Step 3: patch dry-run line lacks "(server dry run)"; quota shows "pods 2 of 5" while the old pod terminates.
4. Step 4: scan took 30 s, module says several minutes; "test the bad pod while it runs" framing is loose.

## TODO [live] status
Confirmed: rule names accepted; TailoredProfile without `extends` works with the `compliance.openshift.io/product-type: Platform` annotation and the suite reaches DONE; pod security admission refuses the bad pod (`restricted:latest`). Not confirmed: 5a count and three texts, Test 1, Test 2.

Left in the lab: `harden-lab` labels, patch, quota, `default-deny`; `harden-baseline` profile and `harden-scan` binding in `openshift-compliance`; files in `/workspace/cps-2`.

---

# CPS-2 finish (2026-11-10, after the lab resumed)

Captures: `live-run/captures/CPS-2/` (`5a-r2`, `test-1-r2`, `test-2-r2`). Earlier harden-lab changes, the profile, the binding and the finished scan survived the pause. `lab start cps-2` took 23.5 s. Pod-security labels on harden-lab now read warn=baseline and audit=baseline (the 2a capture showed restricted); enforce not checked.

| Step | Wall | Result |
| --- | --- | --- |
| 5a | 7.5 s | **Count 1 FAIL, 5 MANUAL, 0 PASS**; suite DONE, NON-COMPLIANT. All three texts printed. |
| Test 1 | 3.3 s | PASS: nonRoot true, allowEscalation false, dropped ["ALL"], readOnly true, memory 128Mi; pod 1/1 Running, 1 restart (example shows 0) |
| Test 2 | 5.5 s | PASS: harden-lab absent; list ai-lab, build, chat, default, demo, gitea, keycloak, kyverno, security-tools, siem |

## Bugs
1. **Step 5 checkpoint cannot be met**: module line 446 expects `<n> PASS`, line 461 says "at least one PASS"; this cluster gives 0 PASS (the FAIL is `harden-baseline-configure-network-policies-namespaces`; MANUAL: rbac-limit-cluster-admin, rbac-wildcard-use, scc-drop-container-capabilities, scc-limit-privileged-containers, scc-limit-root-containers). Either drop the PASS requirement or add a rule that can pass.
2. Test 2: `default` appears because the grep excludes only openshift* and kube-*, while the rule's own instructions exclude `default`.
3. `$FAILED` resolves to `compliancecheckresult.compliance.openshift.io/harden-baseline-configure-network-policies-namespaces`; the three texts print as the module describes.

## TODO [live] status
All confirmed: rule names exist, the TailoredProfile without `extends` reaches DONE, pod security admission refuses the bad pod. Earlier findings stand (`{}` vs `null`, dry-run suffix, 30 s scan).

---

# 2026-11-11 re-run

Captures: `live-run/captures/CPS-2/rr-*.txt`. `lab start cps-2` took 2 m 0 s. All commands run as written (extracted from the module).

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 3.9 s | Matches; `pod` prints `{}` (module example now shows `{}`); oc extract prints 6 file names, then `ls` shows 8 files |
| 2a | 4.7 s | Matches (enforce/warn/audit all restricted) |
| 3a | 8.3 s | Matches; rollout done; quota limits.memory 128Mi/512Mi, pods 2/5, requests.memory 32Mi/256Mi |
| 4a | 9.2 s | Matches; profile READY |
| 4b | 4.2 s | Matches; Forbidden names host namespaces and privileged; NotFound after |
| 4c | 41.7 s | Matches; DONE, NON-COMPLIANT |
| 5a | 19.2 s | 1 FAIL, 5 MANUAL, no PASS; texts print. Matches the new wording ("a PASS line appears only if a rule passes") |
| Test 1 | 4.0 s | PASS; pod 1/1 Running, 0 restarts |
| Test 2 | 5.9 s | PASS; harden-lab absent; list ai-lab, ai-sandbox, build, chat, demo, gitea, keycloak, kyverno, security-tools, siem, vm-batch, vm-internal, vm-lab |

## Mismatches
1. 1a: `ls` shows 8 files, not 6, when `/workspace/cps-2` has files from an earlier run (all-namespaces.txt, covered-namespaces.txt). Only an issue on a re-run; suggested wording: "ls lists at least the six yaml files".
2. 4c/5a: no mismatch. Wording "about a minute" matches (42 s).
3. Test 2 list is longer than the example (13 names); it is marked "Example only", no change needed.

Result: PASS.
