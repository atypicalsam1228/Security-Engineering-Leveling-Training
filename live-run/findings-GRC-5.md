# GRC-5 live run (2026-11-10; parallel with ENG-0, timings not clean)

Every step and Test ran once and passed. No reset. `lab start grc-5` 20.4 s, INCOMPLETE notice (3 [live] items). About 3 min of wall time. Captures: `live-run/captures/GRC-5/`.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 6.3 s | Matches; 11 ClusterPolicies (other modules' policies present, allowed by the checkpoint); reports present at 28 s policy age |
| 1b, 2a, 2b | 1.7 to 2.0 s | Match (nothing printed) |
| 2c | 4.6 s | Matches: CM-6 satisfied/1, CM-7 satisfied/1, CM-8 not-satisfied/1 |
| 3a | 2.1 s | Matches |
| 3b | 2.3 s | Template prints "ok" as the module says; filled with own expressions: ok |
| 3c | 2.4 s | Exact known-answer lines; with the ellipses left in: `Object of type ellipsis is not JSON serializable`, as the module claims |
| 3d | 2.9 s | Matches the reference |
| 3e | 6.4 s | Baseline created; drift false |
| 4a | 3.0 s | Matches: 5 in scope, 60, 60, oldest age 1 min |
| 5a | 18.9 s | Matches; CronJob created, job complete |
| Test 1 | 2.7 s | Matches (extra "Defaulted container" line) |
| Test 2 | 21.0 s | Matches: drift true, added rolebinding/extra-admin, binding deleted afterwards |
| Test 3 | 1.9 s | Matches |
| Test 4 | 2.7 s | Matches: `{"drift": null, "reason": "no baseline"}` |

## Bugs (none blocking)
- Test 1 and 2 logs print `Defaulted container "monitor" out of: monitor, get-oc (init)` first; not in the expected output. Add `-c monitor` or a note.
- 1a lists agent-*, arc-ref-flows and grc-enforce-no-latest-tag from other modules; harmless.
- 5a prints only `control-monitor.yaml` where the module says "a line for each file written".

## Notes
- The module uses namespace `demo`; Test 2 briefly creates and deletes rolebinding extra-admin there (about 20 s). No drift from ENG-0 appeared.
- CronJob schedule `*/15 * * * *`; monitor-pvc Bound 1Gi (gp3-csi).
- Left in the lab: build/ configmaps monitor-kit, monitor-scripts, monitor-baseline; CronJob control-monitor; jobs monitor-first and monitor-drift; PVC monitor-pvc; files in lab-workspace/grc-5/.

## TODO [live] status
Confirmed: PolicyReport group wgpolicyk8s.io and fields, reports within about 30 s; demo-app lacks the owner label so grc-require-owner-label fails (CM-8 not-satisfied); pods in build pull ubi9/python-312:1 and origin-cli:4.22.0, `/usr/bin/oc` exists and uses the service account token. Not checked: Kyverno background scan interval beyond the first appearance; the CronJob's own scheduled run.

## 2026-11-11 re-run
`lab start grc-5` ok (INCOMPLETE notice, 3 [live] items). Captures: `captures/GRC-5/r3-*.txt`. Every step and Test passed; numbers match (5 in scope, 60/60, oldest age 25 min, CM-8 not-satisfied; drift false; Test 2 drift true with rolebinding/extra-admin, binding deleted; Test 3 fresh 0 and stale CM-6/7/8; Test 4 null/no baseline). 3b template prints `ok`, 3c with ellipses fails with the ellipsis TypeError as stated, 3c with real expressions matches the known answer. The `-c monitor` fix in Test 1/2 works (no Defaulted container line).
Minor:
1. **1a:** `oc get clusterpolicy` now prints a first line `Warning: kyverno.io/v1 ClusterPolicy is deprecated and will be removed ...`. Add a note or "(a Kyverno deprecation warning may print first)".
2. **Test 2:** real output also shows `rolebinding...extra-admin created`, `job.batch/monitor-drift created`, `... condition met` and `rolebinding ... "extra-admin" deleted from demo namespace`; Expected shows only the drift line. Say "Example only. (oc prints created, condition met and deleted lines around it)".
3. 1a lists agent-* policies from other modules (harmless).
