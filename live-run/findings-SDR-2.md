# SDR-2 live run (2026-11-09; run in parallel with GRC-4 and VM-3, timings not clean)

No reset needed. Every step passed; output matched the module's "Example only" output and every CHECKPOINT. Captures: `live-run/captures/SDR-2/`.

`lab start sdr-2`: 13.6 s; applied 10-forwarder.sh and 20-seed.sh; INCOMPLETE notice (3 [live], 3 [lab-build], 1 Decision).

| Step | Wall | Result |
| --- | --- | --- |
| 1a runbook + alerts | 1.5 s | 4 files extracted, approved.json shown, A-101 to A-104 listed |
| 2a privilege A-101 | 1.2 s | approved = yes, admin-level = NO |
| 2b post | 1.8 s | HTTP 200 |
| 3a signin A-102 | 1.3 s | lab-user7 7 failures then success; lab-user3 3 failures, none |
| 3b post | 0.9 s | HTTP 200 |
| 4a shell A-103 | 1.4 s | Falco and audit records found; actor on approved list = yes |
| 4b post | 1.0 s | HTTP 200 |
| 5a gaps | 1.4 s | GAP audit 22:30:20Z to 22:58:20Z, 28 min |
| Test 1 path | 5.8 s | collector 1 of 1, only infrastructure LATE (24 min), SUMMARY 1 |
| Test 2 shell A-104 + gaps | 3.8 s | Audit CHECK NO, RESULT line, same 28-min GAP; triage.py exit code 2 as the module prints |
| Test 2 escalation post | 1.0 s | HTTP 200 |

Total about 8 s of runtime against 60 minutes stated.

## Bugs (minor wording)
- 2a and 3a examples show a RESULT line that the real output does not print; 4a real output has an EVENT line (the actor) between the two CHECK lines and no RESULT line.
- 2a real CHECK text reads "(actor, name, role, subject) yes"; module paraphrases it.
- 1a: `oc extract` lists the file names, then `ls` lists them again, plus anchor.txt, which the example omits.
- Test 2 example times (17:44, 17:31 to 17:59) differ from the lab's clock-relative times; marked "Example only".

## Notes
- Test 2 says to post an escalation "as in Step 3"; the agent used its own wording and got HTTP 200.
- Real Falco and Keycloak sources were not tested; only seeded lines.
- cap.sh shows exit 0 for Test 2 because the last command in the script succeeded.

## TODO [live] status
Confirmed: Loki accepts pushes up to 3 h old with lab_seed label; push endpoint and basic auth; collector pod label app.kubernetes.io/component=collector. [lab-build]: Mattermost channel and webhook, Grafana and Mattermost reachability confirmed in practice (HOP 4 "answers", all posts 200).

## 2026-11-11 re-run
Result: PASS. All steps 1a-5a, Test 1, Test 2 (plus the Test 2 escalation post) ran with checkpoints met; every post returned HTTP 200. About 25 s total. Captures: `captures/SDR-2/rr-*.txt`. Nothing failed or hung.

Mismatches (wording only):
- 2a: real CHECK answers are `yes` / `NO` (upper case NO); example shows `<yes or no>`. 2a prints no RESULT line (the example does not claim one now, so it matches).
- 1a: `ls` on a reused folder also shows `__pycache__` (left from earlier runs, not a module issue); a first-time learner sees the four files.
- 5a: real output also prints two `ok  infrastructure/application no span longer than 10 minutes` lines after the GAP line. The example says "other log types may be listed too", which covers it; suggest adding "(and an `ok` line for each log type without a gap)".
- Test 1 and Test 2 output match the example exactly (times 24 min, exit code 2, 28 minute GAP).
- Note: cap.sh reports exit=0 for Test 2 because the last command succeeds; triage.py itself exits 2 as printed.
