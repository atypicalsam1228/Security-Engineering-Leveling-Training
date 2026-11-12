# AID-2 live run (2026-11-10; SDR-5 in parallel, timings not clean)

Every step and test ran once and passed. No reset, no fixes. `lab start aid-2` 10 s, INCOMPLETE notice (3 [live] items and 1 [lab-build] item). Captures: `live-run/captures/AID-2/`. No overlap with SDR-5: AID-2 touches only `ai-lab` (stub-model), `ai-sandbox`, `/workspace/aid-2/` and a Mattermost webhook post.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 6.9 s | Matches; both Forwarding lines, `{"status": "ok"}`, script sizes a 264, b 411, c 352 bytes |
| 1b | 3.0 s | `syntax ok` for all three |
| 2a | 3.3 s | Matches with one order difference (bug 1) |
| 3a | 3.0 s | Matches; `shim/oc` prints the two-line stand-in |
| 3b | 3.4 s | Matches; "tidy complete" before the deletes; install download and report call lines, token printed in plain text |
| 4a | 3.9 s | Matches; `checked project: ai-sandbox` |
| 5a | 4.1 s | Matches; message lists b:8, b:9, b:12, c:5, c:6 with no token; last line `ok`; only script-a.sh left |
| Test 1 | 3.3 s | Matches |
| Test 2 | 3.1 s | Matches (count 3, two delete lines, config map survives) |
| Test 3 | 5.1 s | Matches (`checked project: no-such-project`, exit 0, then NotFound; the wrapper's exit=1 is from the final `oc get project`) |

## Bugs (none blocking)
1. Step 2a: the example order is trap, delete, delete; real order is by line number: delete (b:8), delete (b:9), trap (b:12).
2. Step 1a: the health reply has no trailing newline, so `{"status": "ok"}` runs into the next "Handling connection" line. Cosmetic.

## Notes
- Step 3b: the `rpt_live_...` token appears in the harness output (stub value; the Step 5 SECURITY note covers it). Redact in any screenshot.
- Step 5a posts to the real lab chat channel; only the `ok` reply was seen, arrival in Mattermost not checked.
- The stub pod showed 1 restart at age 80 min; `lastState` is empty now, cause unknown.
- Left in the lab: `/workspace/aid-2/review/` (rejected/, shim/, harness-b.txt, script-a.sh) and one Mattermost message.

## TODO [live] status
Confirmed: `ubi9/python-311:1` runs the stub with `readOnlyRootFilesystem: true`, dropped capabilities, no privilege escalation, answers `/healthz` and `/v1/answer`; the lab runner applied `10-ensure-stub.sh` and `20-sandbox.yaml` and the `stub/` subfolder caused no error; `oc port-forward -n ai-lab svc/stub-model 8089:8080` works with `svc/NAME`. Partly: `MM_WEBHOOK_URL` is set and the webhook returned `ok` ([lab-build] item); channel arrival not checked. TODO.md and the start-state notice still list these as unconfirmed.
