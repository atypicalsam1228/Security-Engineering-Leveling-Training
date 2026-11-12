# SDR-3 live run (2026-11-09; run in parallel with others, timings not clean)

The data steps pass mechanically, but the review gate FAILS on a stacked-seed Loki, before and after one `lab reset`. Captures: `live-run/captures/SDR-3/` (`<label>.txt`; after reset `<label>-retry.txt`). `lab start sdr-3` 6.8 s; `lab reset sdr-3` 18 s; both end with the INCOMPLETE notice (no errors).

## First run
| Step | Time | Result |
| --- | --- | --- |
| 1a | 1.3 s | Four rows, not three (svc-monitor 128, lab-user7 19, lab-admin1 5, lab-user3 3). Module and CHECKPOINT say 12 and 5. **Mismatch** |
| 2a | 8.6 s | 5 audit lines. Matches |
| 2b | 4.3 s | failed_attempts 19 (module 12); secrets_read 4 matches |
| 3a | 1.3 s | Noise 4 (209 min), but 4 burst groups (peaks 9, 9, 11, 16), not two. **CHECKPOINT mismatch** |
| 4a | 2.6 s | Matches |
| 4b | 2.2 s | Matches (success, version 2, last line 6) |
| 5a | 5.9 s | **GATE FAILED**: failed_attempts 19, first_success_utc off by 400 s, real burst 1 |
| Test 1 | 2.1 s | Matches |
| Test 2 | not run | |

## After `lab reset sdr-3` (steps repeated once)
Counts grew: svc-monitor 512, lab-user7 43, lab-admin1 15, lab-user3 3; failed_attempts 43, secrets_read 8; noise 12 (176 min), burst peaks 17, 22, 24, 36. 5a GATE FAILED (failed_attempts, secrets_read, first_success off by 930 s, real burst 1). Test 2 (19.5 s): threshold 2 fails noise and burst 1; threshold 12 fails burst 1; threshold 6 prints GATE FAILED, but the module expects 6 to pass.

## Bugs
1. **Records stack up (blocker).** `20-seed.sh` re-pushes records on every `lab start` and `lab reset` and Loki keeps the old ones (TODO "Decision" line says so). Counts grow each run (12, 19, 43), first_success differs from what the gate expects, noise rises from 4 to 12, and the gate fails. A learner cannot pass Step 5 or Test 2 after any rerun, and the first start already had leftovers. Likely affects SDR-2, SDR-4 and SDR-5 too (same Loki and seed approach).
2. Step 1a lists a fourth row (lab-user3, 3 failures); CHECKPOINT says three rows.
3. Step 3a shows more than two burst groups, contradicting "two groups, peaks near 9 and 16", even on the first run.
4. `oc extract` prints file names that the expected output does not show (minor).
5. Test 2's `for` loop exits 0 even when the gate fails (by design).

## Special check: lastError
Real output: `{"name":"failed-login-burst","health":"ok","lastError":null}`. Matches the module; the null is real. The rule line prints `{"params":[6],"type":"gt"}`, keys in a different order from the module's `{"type":"gt","params":[6]}`.

## TODO [live] status
Confirmed: alert-rules GET and PUT shape; POST /api/dashboards/db with overwrite (version stays 2); Loki [5m] noise peak 4 (first run only; 12 after reset from stacking); audit and Keycloak line shapes; lab shell reaches Loki and Grafana; /api/prometheus/grafana/api/v1/rules gives health ok and lastError null.
