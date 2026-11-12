# ARC-3 live run (2026-11-10; ran alongside SDR-5, timings not clean)

Module file used: `modules/ARC-3-Choose.md` (newer, 15:43 Nov 9). `modules/ARC-3-Measure.md` is an older copy of the same module and was not run (check whether it should be deleted). `lab start arc-3` 7.3 s, INCOMPLETE notice (Kyverno plus 8 [live] items). Captures: `live-run/captures/ARC-3/` (1a, 2a, 2b, 3a, 3b, 3c, 4a, test1, test2, diag1, 5a).

No interference with SDR-5: `arc-baseline` is scoped to `arc-measure`; the 13 other ClusterPolicies are scoped to `demo`, `arc-lab` or platform-labelled namespaces and were untouched. At the end `arc-baseline` is deleted, `arc-measure` is empty and `set_mode.sh none` has run.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 5.1 s | Mismatch: module expects "No resources found" but `oc get clusterpolicy` lists 13 other policies (none named `arc-baseline`); pod securityContext has no runAsNonRoot, checkpoint holds |
| 2a | 3.4 s | Matches (`measure.py`, 830 bytes) |
| 2b | 2.2 s | `review gate: PASSED` |
| 3a | 352 s | Three "snapshot saved" lines; module says about 6 min, holds |
| 3b | 3.1 s | Six FAIL lines, `review gate: FAILED`, exit 1. Matches (two of the six are both about `time.time()`) |
| 3c | 3 s | `tail -f` never ends non-interactively, used `cat loop.log; ls results`; audit.json, enforce.json, none.json present |
| 4a | 3.5 s | Enforce: root, latest and nolimits denied, 0 load pods; None and Audit: all allowed. Checkpoint holds apart from bug 1 |
| 5a | 19.8 s | Prints `enforce` only. Matches |
| Test 1 | 2.8 s | **FAIL**: prints `false`, not `true` (bug 1) |
| Test 2 | 2.9 s | `STOP: missing .../enforce.json: run all three...`, exit 2. Matches |

## Bugs
1. **Blocking for Test 1 and the Audit record count.** `snapshot.py` reports `report_fail_results` as 0 in Audit, so `jq '.report_fail_results == (.load_pods_created * 3)'` prints false. Kyverno 1.19.2 policy reports hold the pod in a top-level `scope.name`; each result's `resources[]` is empty, and `count_fail_results()` matches on `resources[].name`, so it never matches. The reports are correct: a re-run of Audit (`diag1`) gave 20 reports each with summary fail=3, 60 failed results = 20 x 3, so the module's logic holds and only the counting code is wrong. The note "false means the reports were not finished" is wrong advice; waiting longer does not help. Fix: match on `report.scope.name` and count results per report, or sum `summary.fail`. The 4a table shows `report fail results 0` for Audit, contradicting the module's text.
2. Audit shows `policy events` 270; Enforce 315 plus 10 failed-create events. The module gives no figures; both are above the 60 you might expect from 20 pods x 3 rules. Cause not checked.

## Notes
- The 4a table prints extra rows (samples used, median and p95 admit ms, kyverno memory MiB, "delay added by audit/enforce"); the module says these come from the supplied script and are not used.
- Timing is noisy: median admit ms 527 (none), 647 (audit), 740 (enforce); p95 1347, 905, 1113; partly the parallel SDR-5 run, partly the slow webhook. Kyverno memory about 354 to 374 MiB total.
- Every `oc get clusterpolicy` prints the "ClusterPolicy is deprecated, migrate to ValidatingPolicy" warning on stderr.
- The 3a background loop survives in this harness only if the container waits (`wait` appended); in a real `lab shell` it persists.

## TODO [live] status
Confirmed: `--dry-run=server` goes through the Kyverno webhook; metrics work (`oc adm top pods -n kyverno`); SCC does not add runAsNonRoot to the root case; `ubi-minimal` 9.5 and `:latest` pull and run so the deliberate `:latest` case is a valid negative sample; Enforce records FailedCreate (10 events) and policy events (315), counted for `arc-measure`.
Confirmed with a correction: the report resource is `policyreport`; in 1.19.2 `resources[]` is empty and the pod name is in `scope.name` (bug 1).
Partly: load Deployment created under Enforce (0 pods, 10 FailedCreate; ReplicaSet events not inspected); 60 s settle time was enough for reports (20 reports, 60 fails after 75 s) and metrics.
Not confirmed: the exact reason string `PolicyViolation`; the Kyverno version string.
