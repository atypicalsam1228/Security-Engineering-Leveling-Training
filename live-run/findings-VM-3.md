# VM-3 live run (2026-11-09; run in parallel with GRC-4 and SDR-2, timings not clean)

All steps ran as written; every CHECKPOINT met; no reset. Commands were extracted verbatim from the markdown. Captures: `live-run/captures/VM-3/`. `lab start vm-3`: 8.4 s, INCOMPLETE notice listing 4 [live] items.

| Step | Time | Result |
| --- | --- | --- |
| 1a | 2.7 s | 3 fixture and gate files (order differs from module); first finding CVE-2018-1000656 flask, HIGH |
| 2a | 0.8 s | `31 rank.py` |
| 2b | 0.7 s | `15 deadlines.py` |
| 2c | 0.9 s | CRITICAL, CRITICAL, HIGH, HIGH |
| 3a | 1.0 s | `23 gitea_api.py` |
| 3b | 2.0 s | `25 gitea_items.py` |
| 4a | 1.2 s | `47 triage.py` |
| 4b | 18.8 s | Gate 8 PASS plus RESULT: PASS (twice); dry run 5 lines; real run `created 29, already tracked 0` |
| 5a | 13.4 s | 5 pins print; `closed 23, still open 6` |
| T1 | 1.3 s | dry run planned 29, Gitea holds 29, titles unique, CRITICAL due 2026-11-24 |
| T2 | 2.6 s | `created 1, already tracked 6`, then `created 0, already tracked 7` |
| T3 | 1.9 s | ranking check FAIL, RESULT FAIL (1 checks failed), exit code 1; "got [...]" text matches |
| T4 | 3.3 s | open count 7 before and after; message and exit code 3 match |

## Bugs (none blocking)
- Test 2 example says "already tracked 5"; live gave 6 then 7. Test 4 example says open count 5; live gave 7. Both labelled "Example only".
- `oc extract` prints nothing to the learner, though the module says it prints one line per file.

## Notes
- First Test 2 run created 1 item: a new MEDIUM CVE-2026-25645 in requests on deps-updated that main did not have. Module says "may create", so fine.
- Step 5 leaves 6 items open (5 HIGH urllib3 findings and 1 MEDIUM requests on deps-updated), matching "any items still open are findings the fix did not remove".
- 29 items stay under the 50-issue page limit; paging not stressed.
- Machine time is far below the module's 68 minutes (48 hands-on).

## TODO [live] status
All 4 confirmed: Gitea API fields (due_date, PATCH state, python3 trusts the Gitea certificate; the 50-item limit was not stressed); deps-updated has fewer findings than main (29 to 23 closed, 6 open); review gate passes the reference solution against a real scan; the lab shell can fetch the Trivy database.

## 2026-11-11 re-run

Result: PASS (clean state: vm-app repo and /workspace/vm-3 deleted, then `lab start vm-3`). Captures: captures/VM-3/rr-*.txt.

- Steps 1a-5a all met their checkpoints. 4b: Gate 8 PASS, RESULT: PASS (printed twice), `created 29, already tracked 0`. 5a: `closed 23, still open 6`.
- Test 1: 29 items listed (example 9, marked Example only). Wording only.
- Test 2: first run `created 1, already tracked 6`, second `created 0, already tracked 7`. Example says `created 0, already tracked 5` twice. Functional difference in count only: the fixed.json contains one finding not yet tracked, so the first run creates one. Suggest example read `created 1, already tracked 6` then `created 0, already tracked 7`, or say counts will differ.
- Test 3: gate FAIL on ranking, RESULT: FAIL (1 checks failed), exit code 1. Matches the example.
- Test 4: open count 7 before and after (example 5); `cannot use fixture-empty.json ...`, exit code 3. Matches except the count.
- 1a: ls order differs from the module (fixture-findings.json, review_gate.py, fixture-empty.json). Wording only.
- Lab note: `lab start` does not reset Gitea issues or the local folder; a repeat run showed `created 0, already tracked 29` until the repo was deleted.
