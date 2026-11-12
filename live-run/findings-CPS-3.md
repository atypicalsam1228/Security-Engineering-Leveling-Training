# CPS-3 live run (2026-11-09; run in parallel with others, timings not clean)

Steps 1a to 4b and Tests 1 to 3 passed. Step 5b failed because the test container had no AWS credentials (harness issue, see below). `lab start cps-3` 33 s, INCOMPLETE notice (5 [live] items). Captures: `live-run/captures/CPS-3/`.

| Step | Time | Result |
| --- | --- | --- |
| 1a | 1.9 s | Matches: `yes`, report-sa in the who-can list |
| 2a | 0.9 s | `37 review_gate.py` |
| 2b | 1.2 s | FAIL line, `gate: FAIL`, `exit code: 1` |
| 3a | 2.0 s | `23 role.yaml` |
| 3b | 5.5 s | Gate PASS, server dry run, created, `yes` then `no` (delete line differs) |
| 4a | 4.8 s | `before: exit=0`, policy created and listed |
| 4b | 5.7 s | Rollout done, `gate: PASS` (dry-run line differs) |
| 5a | 0.9 s | `valid JSON`; gaps filled from the reference file |
| 5b (placeholders, correct policy, after reset) | 12.9 s, 9.8 s, about 10 s | FAIL, all from NoCredentials |
| 5c | 1.2 s | `same as the reference` |
| Test 1 | 4.6 s | Matches |
| Test 2 | 1.3 s | Both gate FAIL lines with exit 1 |
| Test 3 | 4.7 s | `after: exit=124` |

Command time about 1 minute against the module's 68. `lab reset cps-3` took 57 s.

## Bugs
1. **Step 5b needs AWS credentials in the lab shell**, and the module's NOTE only covers an AccessDenied on iam:SimulateCustomPolicy, not "Unable to locate credentials". In a learner's real shell the credentials come from `Use-LabAws` on the host, so this was a test-harness gap, not proven a module bug; but the module should say to run it first or what the error means. The "FAIL with placeholders proves the check can fail" claim cannot be checked without credentials. Re-run needed with the SSO keys passed in.
2. Step 3b delete line reads `rolebinding.rbac.authorization.k8s.io "report-sa-edit" deleted from rbac-lab namespace`; module shows `... "report-sa-edit" deleted`.
3. Step 4b dry-run line reads `deployment.apps/report-app patched`, not `patched (server dry run)`; the patch ran twice; the rollout prints two "Waiting for deployment ... old replicas pending termination" lines the module omits.
4. Step 1a output starts with `resourceaccessreviewresponse.authorization.openshift.io/<unknown>` and a blank line; the who-can list is about 70 accounts, so the short example understates it. Checkpoint holds.

## TODO [live] status
Confirmed: ubi9/python-311 http.server image runs; OVN-Kubernetes enforces default-deny (exit 0 before, 124 after); multi-document file gives a List through `oc create --dry-run=client -o json`; lab shell reaches the internet. Not tested: the learner identity may call iam:SimulateCustomPolicy (to be re-run with credentials).

## Re-run of Step 5b/5c with AWS credentials passed in (Admin SSO role)
5b: 4.8 s, `policy check: PASS`, all four decisions as wanted (allowed, then three implicitDeny). 5c: `same as the reference`. So bug 1 is a harness gap, not a lab fault. Still open: the module does not say Step 5 needs the AWS keys that `Use-LabAws` loads, and the real learner identity (not Admin) calling iam:SimulateCustomPolicy is untested.

---

# 2026-11-11 re-run

Captures: `live-run/captures/CPS-3/rr-*.txt`. `lab start cps-3` took 13.6 s. Commands run as written; for 5a I first ran the block with the WRITE placeholders (valid JSON; 5b printed FAIL as the module says), then typed GetObject and `arn:aws:s3:::report-app-data/reports/*`.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 3.3 s | yes; report-sa is in the who-can list (about 70 users); header line differs |
| 2a | 1.4 s | `37 review_gate.py` matches |
| 2b | 2.1 s | FAIL privilege escalation, gate: FAIL, exit code 1. Matches |
| 3a | 1.5 s | `23 role.yaml` matches |
| 3b | 6.1 s | gate PASS; role/binding created; get pods yes, get secrets no. Two wording differences |
| 4a | 4.7 s | before: exit=0; policy created; listed. Matches |
| 4b | 5.5 s | rollout done, gate PASS. Dry-run line differs |
| 5a | 1.8 s | valid JSON |
| 5b | 7.9 s / 8.6 s | with WRITE values: GetObject implicitDeny (want allowed), policy check FAIL; with fix: all four correct, PASS |
| 5c | 2.1 s | same as the reference |
| Test 1 | 5.7 s | PASS (yes, yes, no, no, no; report-sa not listed) |
| Test 2 | 2.9 s | PASS (both FAIL, exit 1) |
| Test 3 | 5.9 s | PASS (exit=124) |

## Mismatches
1. 1a: first output line is `resourceaccessreviewresponse.authorization.openshift.io/<unknown>` before `Namespace: rbac-lab`. Expected shows no such line. Suggested: add it to the example, or note "a header line may come first".
2. 3b: delete prints `rolebinding.rbac.authorization.k8s.io "report-sa-edit" deleted from rbac-lab namespace`, expected `... deleted`. Suggested: use the new wording.
3. 3b: the block's exit code is 1 because the last `oc auth can-i get secrets` answers `no` (the correct result). Add a note that exit 1 after "no" is normal.
4. 4b: `oc patch ... --dry-run=server` prints `deployment.apps/report-app patched` with no `(server dry run)` suffix; expected shows `patched (server dry run)`. Suggested: drop the suffix from the expected output (same as CPS-2 3a).
5. Test 3: an extra line `command terminated with exit code 124` appears before `after: exit=124`. Add to expected output.

Result: PASS with the wording mismatches above; no functional failures.
