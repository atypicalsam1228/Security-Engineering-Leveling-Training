# SDR-4 live run (2026-11-10; GRC-5 in parallel in `build`, timings not clean)

First pass passed every step and test. After one `lab reset sdr-4` the second pass is blocked in two places: Step 4b ends TIMELINE FAILED (Loki seed stacking), and Step 5b fails because the timeline names a pod that no longer exists. Captures: `live-run/captures/SDR-4/` (second pass `r-` prefix). `lab start sdr-4` 16.6 s, `lab reset sdr-4` 55 s; both end with the INCOMPLETE notice, no errors.

## First pass (fresh start)
| Step | Time | Result |
| --- | --- | --- |
| 1a, 1b | 2.6, 4.5 s | Match |
| 2a to 2c | 2.3 to 3.2 s | Each prints 3 lines |
| 3a starter secret-read | 28.0 s | TESTS FAILED (2): secret-single-read (peak 1), secret-controller-reads (peak 20); matches the module's hints |
| 3a own secret-read | 28.1 s | 11 PASS (harness prints `gt 0.0` and `gt 1.0` instead of `gt 0`) |
| 4a | 3.2 s | `lab-user9`, 11. Matches |
| 4b | 3.4 s | 12 rows, TIMELINE PASSED |
| 5a, 5b | 2.0, 6.8 s | Match; replacement pod ContainerCreating at 1 s, old pod isolated |
| Test 1 | 2.9 s | Matches (200 from the replacement) |
| Test 2 | 9.0 s, rerun 17.7 s | Timeline lines and 000/exit 28 match; harness did not run first time (bug 4); rerun with the tunnel open matches |

## After `lab reset sdr-4`
| Step | Time | Result |
| --- | --- | --- |
| 1a to 3a | 2 s each, 3a 27.5 s | Same as first pass |
| 4a | 2.6 s | `lab-user9` but line count **22**, not 11 |
| 4b | 3.1 s | pod `...-5fgth`, 23 rows; `FAIL expected 6 LOGIN_ERROR rows, found 12`; `FAIL out of order: audit create clusterrolebindings`; **TIMELINE FAILED** |
| 5a | 2.7 s | 12 lines |
| 5b | 10.1 s | `Error from server (NotFound): pods "...-5fgth" not found`; first call 000, exit 3; policy created but no pod relabeled |
| Test 1 | 6.2 s | Matches (never touches the timeline) |
| Test 2 | 11 to 14 s | Fails at once: harness `Connection refused`; timeline check prints four FAILs; probe exits 3 on the missing pod, not 000/28 |
| Test 2 diag (tunnel, 8 s sleep) | 20.5 s | Harness PASS, PASS, PASS |

## Does Loki stack? Yes
- Pre-state query: 15 sdr-4 lines before any step (12 in the last hour, 3 older); after one reset: 30.
- Cause: `reset.d` deletes the `sdr4-harness` ConfigMap (the seed marker) but never the Loki records, so `20-seed.sh` pushes everything again and the old rows stay inside the 6 h window that 4a uses.
- Effect: actor lines 11 to 22, LOGIN_ERROR rows 6 to 12, timeline 12 to 23 rows. Breaks the Step 4 CHECKPOINT and the timeline check with no way for a learner to recover. Step 3 detections and Test 1 are unaffected (the harness uses fresh run labels and 5-minute windows).

## Bugs
1. **Stacked seed (blocker)**; same bug as SDR-3. Any `lab reset sdr-4` or rerun within 6 h makes Step 4b fail.
2. **Stale pod name (blocker after reset).** `20-seed.sh` picks `items[0]` with `app=suspect-app` and took the previous run's Terminating replacement (`-5fgth`), not the new `-kqhnq`. Audit and Falco records name a pod that no longer exists; `pod.txt` is wrong; 5b, Test 2's last call and the CHECKPOINT fail. The timeline also names the first run's isolated pod (`-p8hks`) twice.
3. Step 3a says "about 20 seconds" per scenario (about 220 s for eleven); real total is about 28 s.
4. Test 2: `sleep 3` after `oc port-forward` was sometimes too short (`Connection refused`, traceback); with 8 s it worked. Test 2 does not reopen the Step 3a tunnel, so a closed shell gives a traceback, not the expected FAIL lines (partly a harness artifact: each test command ran in a fresh container).
5. Minor: `oc extract` prints nine file names the expected output omits; `command terminated with exit code 28` order varies; timeline rows mix `...Z` and `.000000Z`; the seed timestamps sit about an hour in the past, so a run after about 5 h of lab time drops out of the 6 h window.

## Notes
- Seeded audit records stand in for the real audit log; nothing here shows real audit records carry `requestObject.roleRef`.
- First-pass Test 2 harness output matches the example: PASS, PASS, FAIL (peak 20), TESTS FAILED (1).
- Left in the lab: `/workspace/sdr-4/` files, the quarantine policy, doubled seed (30 records), Deployment `suspect-app` with new pod `-kqhnq`, not isolated.

## TODO [live] status
Confirmed: Alloy accepts the directory and a pass-through `loki.process` stage and `alloy-detect` runs; `stage.json` plus `stage.labels` give the `audit_resource` values (eleven scenarios pass); `loki.source.api` keeps pushed labels; `oc port-forward svc/alloy-detect` works; platform Deployment `alloy` in `siem` writes to Loki; OVN enforces deny-all (curl 000, `oc exec` returns 28); `ubi9` probe pod has curl; label swap releases the pod, replacement ContainerCreating within 1 s, Service answers 200 about 3 s later.
Not confirmed: audit profile `WriteRequestBodies` on the real cluster (records are seeded); Loki `data.stats.summary.totalBytesProcessed` never exercised.

## 2026-11-11 re-run
`lab start sdr-4` ok (INCOMPLETE notice; decision note says old Loki records are now ignored via seed_run). Fresh start, single pass. Captures: `captures/SDR-4/r3-*.txt`. Steps 1a-5b and Test 2 match; the 4a/4b values are now correct (lab-user9, 11 lines; 12 rows, TIMELINE PASSED). Stacked-seed fix confirmed on a fresh start (a reset was not tried: not allowed).
Mismatches:
1. **Test 1: Service call prints 000 / exit 7 when run right after 5b.** Expected `200`. The replacement pod was still Pending at 5b (AGE 1s) and was Ready only some time later (call at ~15 s after 5b: `000`, `command terminated with exit code 7`; the same Test 1 about 1 min later: `12 / TESTS PASSED / 200`). Suggested wording: add to 5b (or Test 1) `oc wait --for=condition=ready pod -l app=suspect-app -n demo --timeout=120s` or a NOTE "the replacement pod needs up to a minute to become ready; if the call prints 000, wait and run it again". Also 5b's listing shows the new pod `0/1 Pending`, not `1/1 Running` as in the Expected block (the block is an example, but a NOTE would help).
2. 3a: the starter secret-read gives TESTS FAILED (2) (secret-single-read, secret-controller-reads) as the hints say; own version (threshold 1, verb get|list, system: excluded) gives 11 PASS, TESTS PASSED. Harness prints `gt 0.0`/`gt 1.0`, not `gt 0` (cosmetic). The 3a block's `oc extract ... > /dev/null` now hides the file names (earlier minor note resolved).
3. 5b: `networkpolicy ... created`; unlabeled new pod shows an empty QUARANTINE column (as expected).
4. Test 2: tunnel opened in the block works (no Connection refused). Output matches the Expected block except the oc line `command terminated with exit code 28` printing before `000`, and the order of the two lines can vary (module says Expected `000` then the oc line).
