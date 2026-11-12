# AID-4 live run (2026-11-10; ran parallel with SDR-5, timings not clean)

`lab start aid-4` 18 s, INCOMPLETE notice (4 TODO items). Followed the module as written, no reset, no fixes. Every step and test passed first time; no blockers. Captures: `live-run/captures/AID-4/`. For 2d and 2e each ____ was filled with the module's reference answer. About 2.5 min of command time against the module's 67 min.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 10.9 s | Matches; can-i yes, no, no; log shows 2 ERROR and 2 NOTE TO AI ASSISTANT lines |
| 2a to 2c | 2.7 to 3.1 s | `ok` each |
| 2d | 3.3 s | One MISMATCH on the replicasets case, `10 cases, 1 mismatches`, exit 1, as intended |
| 2e | 3.2 s | `10 cases, 0 mismatches` |
| 2f | 4.6 s | `configmap/triage-policy created`, then 0 mismatches on the stored copy |
| 2g | 4.0 s | Reference files match |
| 3a | 3.7 s | Extracts `ailog.py` then `audit.py` (example shows the reverse) |
| 3b | 2.7 s | `audit.py` identical to the module |
| 3c, 3d, 3e | 2.7 to 3.3 s | ok; py_compile silent |
| 4a | 16.9 s | Exit 0, 7 AUDIT lines; 7 records read back from Loki after the 5 s sleep |
| Test 1 | 2.9 s | 7 and 1, matches |
| Test 2 | 13.1 s | Pod counts 4 and 4; refused record, exit 4; dry-run delete Forbidden |
| Test 3 | 30.6 s | 6, `step_cap` record, 0, `stopped` record. Matches; STOP removed |
| Test 4 | 10.1 s | Three reasons match |

## Mismatches (cosmetic, no bugs)
1. 1a: the port-forward also prints `Forwarding from [::1]:8089 -> 8080`; the `view added` line reads `clusterrole.rbac.authorization.k8s.io/view added: "system:serviceaccount:ai-lab:triage-agent"`.
2. 4a, Test 2, 3, 4: the backgrounded `oc port-forward` prints `Forwarding from ...` and repeated `Handling connection for 8089` lines (up to 12 in Test 3), absent from the examples; a learner could mistake them for errors. Add a note or redirect to /dev/null.
3. 4a: the Loki trail is sorted by the full line, so same-second records come out of event order (`allowed 2` before `result 1`, `result 3` after `finish 4`); the module says "in time order". Use `sort -k1,1 -s`, sort by Loki's nanosecond timestamp, or note the interleaving.
4. 3a: `oc extract` lists `ailog.py` first.
5. Test 2: the dry-run delete returns one Forbidden line per pod (4 lines), the example shows one.
6. Test 2 risk: project `demo` is shared with SDR-5 and other modules; the pod count was 4 during Test 2 and 2 later. A pod appearing or disappearing between the two `wc -l` calls fails the "counts must match" check for an unrelated reason. Did not happen in this run.

## TODO [live] status
Confirmed: [live] 1 `view` role (as `triage-agent`, get pods, replicasets, events, services, describe deployment and logs work; can-i yes for get pods, no for get secrets and delete pods; dry-run delete Forbidden); [live] 3 Loki push and audit field names (records under `app=triage-agent` with labels `kind` and `step`; fields `kind`, `time`, `step`, `command`, `chars`, `summary`; all 7 read back via `LOKI_CA_FILE`, `LOKI_USER`, `LOKI_PASSWORD`, `LOKI_URL`, never printed); [live] 2 noisy-app admitted under the restricted security context (runAsUser 1000840000, no escalation, all capabilities dropped; the injected NOTE line shows in its log); [lab-build] 3 `LOKI_*` variables present in the lab shell. The INCOMPLETE notice still lists all four, so the TODO.md markers can be flipped.

## Notes
- No shared cluster settings changed, TLS never weakened, nothing touched in `siem`. In `demo` the only change was the module's `view` role binding for `triage-agent`.
- Not tested: fail-closed exit status 6 (Loki unreachable) has no module test.
- Left in the lab: `ai-lab` service account `triage-agent`, ConfigMaps `triage-policy`, `aid4-kit`, `aid4-ref`; the view RoleBinding in `demo`; `triage-agent` records in Loki; files in `/workspace/aid-4/agent` (stored/, run.log, __pycache__).
