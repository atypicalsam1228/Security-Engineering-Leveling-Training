# VM-4 live run (2026-11-09; run in parallel with others, timings not clean)

Every step ran once and passed; no reset. `lab start vm-4` 14.5 s, INCOMPLETE notice (5 [live] items). Captures: `live-run/captures/VM-4/`.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 2.6 s | Matches (file order differs); 3 deployments and legacy-web route listed |
| 1c | 0.9 s | 37 lines |
| 1d | 7.3 s | 3 workloads; legacy-web running, exposed, critical; report-svc running only; batch-old none |
| 2a | 14.8 s | nginx 362 findings, httpd 740 |
| 2b, 2c | 1.6 s, 1.0 s | 32 and 52 lines |
| 2d | 13.6 s | KEV count 1773 equals entries; 820 CVEs, 8 in KEV, 803 with EPSS; top 5 listed |
| 3a, 3b | 2.3 s, 3.1 s | 22 and 36 lines |
| 3c | 5.2 s | 1464 rows; first rows P1 legacy-web. P1 legacy-web 166, P1 report-svc 2, P3 batch-old 6, P3 report-svc 360, P3 legacy-web 196, P4 batch-old 734 |
| 4a | 6.4 s | Suppressed CVE-2019-11477; count 1 without ignore file, 0 with it; expiry 2026-12-10 |
| 4b | 4.2 s | Issue #31 created, due 2026-12-10; second run "already recorded" |
| 5a | 8.2 s | One changed FROM line |
| 5b | 1.2 s | PR #32 open; second run prints null, null, null as the module says |
| 5c | 9.5 s | base image, `true`, `exit code: 0`, then 362 and 269 (lower) |
| Test 1 | 2.8 s | Matches |
| Test 2 | 5.0 s | Count 1 with expiry yesterday. Matches |
| Test 3 | 2.4 s | Matches |
| Test 4 | 2.0 s | Error message, exit 2, no file. Matches |

## Bugs (none blocking)
- 5a: `git push --quiet` still prints four "remote:" lines (a Gitea pull request hint); the module says push prints nothing.

## Notes
- The module's "Zero matches in KEV is a valid answer for these old images" does not hold: 8 CVEs are in KEV. CVE-2023-4863 makes report-svc P1 (2 rows); KEV rows land as P3 on batch-old (6 rows). Checkpoints and tests still pass because Test 1 picks a non-exploited CVE.
- Test 1 prints the two workload lines in the opposite order from the example.
- Left in the lab: Gitea issue #31, PR #32, branch fix/legacy-web-base-image.

## TODO [live] status
Confirmed: Trivy `--ignorefile` YAML with `expired_at`; Gitea clone, push, issue and PR with GITEA_TOKEN; public KEV feed and EPSS API (17 of 820 CVEs got null). Partly: workloads start (Route admission and a fetch through the route not checked). Not confirmed: rank.py and deadlines.py equal the VM-3 reference (not diffed).

## 2026-11-11 re-run

Result: PASS (clean state: vm-app repo and /workspace/vm-4 deleted, then `lab start vm-4`). Captures: captures/VM-4/rr-*.txt. All steps 1a-5c and Tests 1-4 met their checkpoints; no WRITE placeholders in this module. The 4b repeat printed `already recorded`, as documented.

Wording-only mismatches:
- 1a: ls prints deadlines.py, facts_lib.py, rank.py (alphabetical), the example lists rank.py first. Route/deployment lines match.
- 3c: first plan row is `P1 exception ... CVE-2023-50387 libsystemd0` (no fix published), the example shows `P1 fix` first. Tier counts also include `2 P1 vm-internal/report-svc` and `6 P3 vm-batch/batch-old`, not in the example list. Suggest the example say "rows for other tiers and workloads may also appear".
- Test 1: the two result rows print in the opposite order (report-svc first on the second pair); counts 1464 rows. Order only.
- Counts seen: 362 and 740 findings (2a), 820 CVEs / 8 KEV / 803 EPSS (2d), 362 -> 273 after re-scan (5c).
