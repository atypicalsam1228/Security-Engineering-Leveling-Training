# CPS-4 live run (2026-11-10; run in parallel with GRC-4, timings not clean)

Every step and every test ran once and passed. No reset, nothing changed. Captures: `live-run/captures/CPS-4/`. `00-state-after-start.txt` is from a failed first attempt (cluster down, 237 s).

`lab start cps-4` took 8 min 54 s (much of it the encryption rollout), INCOMPLETE notice with 5 TODO items. About 4 min of command time for the steps against the module's 76 min.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 15.2 s | Matches; node volumes show 9 x True (example shows 2) |
| 2a | 2.8 s | Matches, 16 lines |
| 2b | 8.6 s | Matches except dry-run line |
| 3a, 3b, 3c | 3.7, 2.9, 4.8 s | Match |
| 4a, 4b, 4c | 3.0, 2.6, 2.7 s | Match |
| 4d | 2.8 s | Matches; count 0 |
| 4e | 9.0 s | Matches |
| 4f | 3.4 s | Reference rule identical to the learner's two lines |
| 5a, 5b | 2.4, 4.0 s | 24 lines; 7 PASS, exit 0 |
| Test 1 to 4 | 5.8, 5.0, 4.6, 7.6 s | Match (Test 4 adds an exit-124 line) |
| Test 5, 6 | 20.4, 20.2 s | Falco event found |
| Test 7 | 20.7 s | `new events: 0` |
| Test 8 | 9.2 s | First run 6 PASS and one FAIL (plain-text secret in env), after removal 7 PASS |

## Mismatches against "Example only" text (none blocking)
- 2b: server dry-run prints `deployment.apps/sample-api patched`, not `patched (server dry run)`. The first `oc set env ... DB_PASSWORD-` prints `updated`, a line the example omits.
- 2b, 4e, Test 8: rollout prints two "Waiting for deployment ... old replicas are pending termination" lines the example omits.
- 4f: `oc extract` prints `answers/secret-read-rule.txt`.
- Test 4: extra "command terminated with exit code 124" line before `stranger: exit=124`.
- Test 5 and 6: `oc logs` returns the Falco event as a long raw JSON line, not the short "Warning Shell started" text; learners see a wall of JSON.
- Test 6: the command shows `cat --coreutils-prog-shebang=cat /usr/bin/cat /etc/sample-api/password`, not `cat /etc/sample-api/password`.
- Test 1: group 1000830000 and a current date; Falco user 1000830000 (examples differ, "Example only").
- Test 5 and 6: `oc rollout status daemonset/falco` returns at once.

## Notes
- Test 7 waits on a 10-minute log window, so BEFORE may contain Test 6's event; it still reported 0 new events.
- Left in the lab: secure-lab changes (service account, secret, three NetworkPolicies, hardened deployment), config map falco-custom-rules in security-tools, files in `/workspace/cps-4/`.

## TODO [live] status
- Encrypted conditions: confirmed in part (openshiftapiserver EncryptionCompleted; kubeapiserver and authentication not checked; Test 2 shows `k8s:enc:aesgcm:v1:`).
- AWS identity calls (sts, ec2 describe-volumes, kms describe-key): confirmed with the SSO Admin role; learner-policy grant not exercised.
- serviceAccountIssuer empty: confirmed.
- Lab shell reaches the internet for AWS calls: confirmed.
- Falco json_output, container metadata, both custom rules loaded: confirmed in part (version not checked).

---

# 2026-11-11 re-run

Captures: `live-run/captures/CPS-4/rr-*.txt`. `lab start cps-4` took 9 m 18 s (module-level start; slow because of the Falco and encryption waits). Note: my first pass ran before `lab start`; the namespace was missing, so those captures were overwritten by a second full pass. 4d was run first with the placeholders (count 2), then 4c again and 4d with `proc.name in (cat, head, tail)` and `fd.name startswith /etc/sample-api/` (count 0).

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 7.9 s | Matches (account null, plain DB_PASSWORD, empty issuer, EncryptionCompleted, KMS Enabled, 11 volumes True) |
| 2a | 2.1 s | 16 lines, matches |
| 2b | 11.5 s | Matches; secret created; rollout done |
| 3a | - | default-deny.yaml printed, matches |
| 3b | 1.6 s | 35 lines, matches |
| 3c | 7.1 s | Matches; 3 policies listed |
| 4a, 4b, 4c | about 1.5 s each | 20, 9, 8 lines; match |
| 4d | 1.4 s | placeholders: count 2; with my lines: 0 |
| 4e | 8.0 s | Matches; last two lines are my condition lines |
| 4f | 2.2 s | Reference rule prints; same as mine |
| 5a / 5b | 1.4 s / 2.6 s | 24 lines; seven PASS, exit 0 |
| Test 1 | 3.7 s | PASS (0, secret DATA 1, password symlink) |
| Test 2 | 2.9 s | PASS (`k8s:enc:aesgcm:v1:`) |
| Test 3 | 2.9 s | PASS (exit=0) |
| Test 4 | 6.0 s | PASS (exit=124) |
| Test 5 | 21.0 s | PASS (CapEff zeros, read-only, Falco line) |
| Test 6 | 19.5 s | PASS (Falco line names the file) |
| Test 7 | 18.7 s | PASS (new events: 0) |
| Test 8 | 9.2 s | PASS (FAIL then seven PASS, exit 1 then 0) |

## Mismatches
1. Test 6: the Falco line shows `command=cat --coreutils-prog-shebang=cat /usr/bin/cat /etc/sample-api/password`, not `command=cat /etc/sample-api/password`; user is `1000950000` (example `1000700000`). Checkpoint ("names the file and the command cat") still holds. Suggested: change the example command text to match, or say "the command text may include extra words".
2. Test 1: `ls -l` shows owner/group `root 1000950000` and a date; fine for "Example only", no change required.
3. Test 8: the second `oc set env ... DB_PASSWORD-` prints `deployment.apps/sample-api updated` and the first prints the same line, plus the rollout waits `Waiting for deployment spec update to be observed...`; expected output does not list these. Minor; add "(oc prints updated and rollout wait lines)".
4. Start time: `lab start cps-4` takes about 9 minutes. If the module states a shorter start time, update it.

Result: PASS (no functional failures).
