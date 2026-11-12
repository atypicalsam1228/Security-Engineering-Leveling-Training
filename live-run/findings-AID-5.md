# AID-5 live run (2026-11-10) - PARTIAL, lab paused mid-run

Ran `lab start aid-5` through Step 4a. 3a rule creation unconfirmed; 4b to 4e and Tests 1 to 3 not run. Captures: `live-run/captures/AID-5/` (previous partial run in `AID-5-prev/`). Extracted blocks `a5r_*.sh` in the scratchpad.

## Blocker
The guard paused the lab at about 18:03Z (no heartbeat for 19 h, `keep_until` 08:31Z lapsed): master `stopped`, bastion `terminated`. This hit every parallel run. `lab keep 12` worked (until 2026-11-11T06:06Z); `lab resume` (written 18:06:55Z) was still waiting after about 25 min because the bastion held the guard. `lab keep` and `lab resume` need AWS credentials exported in the shell. Nothing was started by hand.

| Step | Wall | Result |
| --- | --- | --- |
| `lab start aid-5` | 26 s | Runs; INCOMPLETE notice (6 [live], 1 [lab-build]) |
| 1a to 1d | 2.2 to 3.1 s | Match |
| 1e | 18.5 s | Passes first time |
| 2a to 2d | 2.3 to 2.7 s | Match |
| 2e | 8.9 s | try-agent refused, try-other allowed (see bug 1) |
| 2f | 2.8 s | diff exits 1, only the message line differs |
| 2g | 13.5 s | All six policies READY True |
| 3a | 16 s | Printed nothing; module expects `agent-out-of-list`; API went down, re-run |
| 4a | 2.9 s | Matches |
| 4b | 46 s | FAIL: connection refused (lab paused, not a module bug) |
| 4c to 4e, Tests 1 to 3 | not run | |

## Bugs
1. **2e hides the learner's message.** `2>&1 | head -n 3` shows `error: failed to create clusterrolebinding: admission webhook "validate.kyverno.svc-fail" denied the request:`, a blank line and `resource ClusterRoleBinding//try-agent was blocked due to the following policies`. The policy's own message is on line 6. Expected text ("Error from server: ... <your message>") is wrong. Show more lines (for example `head -n 8`) and fix the example.
2. Every Kyverno apply prints the `ClusterPolicy is deprecated` warning; 2e and 2g also print `kyverno-reports-controller requires permissions get,list,watch ...` warnings. None are in the examples.
3. 2g dry run says `configured`, not `created`, because 2e already applied the file.
4. 1e `oc explain` prints about 60 lines, covered by a placeholder.

## TODO [live] status
Confirmed: Kyverno 1.19.2 generate fields, `&trigger` anchor, X() anchors in the pod policy (not yet exercised against pods), `[?!contains]` JMESPath; aggregate ClusterRole label generates the four objects; 2d filter rule works.
Not confirmed: OVN enforcement and DNS at openshift-dns 5353; audit field names for impersonation; Grafana rule-group interval and detection time; probe image `ubi9/python-311:1` and probe pod admission.

Left in the lab: six agent-* ClusterPolicies, project `agents`, ClusterRole `kyverno-agent-baseline`, files in `/workspace/aid-5/guardrails`, maybe a Grafana rule `agent-out-of-list` (3a is safe to re-run).

Next: re-run 3a, 4b to 4e and Tests 1 to 3 once the API answers (Test 3 takes 5 to 15 min, Test 2 about 3 min).

# AID-5 resume run (2026-11-10 18:40Z to 18:58Z) - COMPLETE

API answered on the first poll (node Ready). Agents project and six agent-* policies were still there; no `lab start` needed. Captures: `captures/AID-5/*-rerun.txt`.

| Step | Wall | Result |
| --- | --- | --- |
| 3a | 6.1 s | Prints `agent-out-of-list`, matches |
| 4b | 10.5 s | pod created, condition met, matches (probe image and admission work) |
| 4c, 4d | 2 s each | ok |
| 4e | 23.4 s | Matches exactly: 16 items, 12 of 13 (92.3 percent), 3 of 3, missed E-13, exit 0 |
| Test 1 | 25.2 s | MISMATCH: agents 4 of 4, agents-b 3 of 4 after 10 s, agents-c 0 of 4. agents-b was 4 of 4 about 100 s later. 10 s is too short; generate (UpdateRequest) was still Pending |
| Test 2 | 72.2 s | Matches: 5 of 13, misses E-01..E-06, E-12, E-13; then 12 of 13 and E-13 |
| Test 3 | 358 s | Forbidden message matches. Pre-wait for the rule to go quiet took about 290 s; then `alert firing after 65 seconds` (module example 140 s) |

## Mismatches
1. Test 1: sleep 10 gives 3 of 4 under load. Raise to 30 to 60 s or add a wait loop; note generation can take a minute.
2. Test 3: module example 140 s vs 65 s; fine as "example only". State that the quiet-wait before the request can take about 5 min after Test 2 and 4e.
3. Kyverno deprecation and reports-controller warnings appear in Test 2 output (known, bug 2).

## TODO [live] status (now confirmed)
- OVN enforcement and DNS 5353: E-11 (cluster API) blocked, B-03 (model service by name) allowed, so both the deny and the 5353 DNS rule work.
- Audit field names: the LogQL (`json | objectRef_resource ...`) matched and the alert fired, so the fields work.
- Grafana: rule group `agents` interval 60 s, `for` 0s; detection 65 s measured.
- Probe image `ubi9/python-311:1` and probe pod admission: pod Ready in 10.5 s under the baseline and guardrail policies.
- X() anchors against pods: E-01 to E-04 blocked, B-01 compliant pod allowed.
Remaining: only the earlier bug list (2e head -n 3 hides message, warnings, 2g "configured", 1e long output).
Left in lab: namespaces agents-b, agents-c, probe pod agent-probe, port-forward 8089 inside a finished container (gone).
