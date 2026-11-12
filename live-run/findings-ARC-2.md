# ARC-2 live run (2026-11-10; run in parallel with SDR-5, timings not clean)

All steps and tests ran once and passed; no reset. `lab start arc-2` 31.4 s, INCOMPLETE notice with 6 items (the Kyverno platform tool plus 5 [live] items). Kyverno was present, so the preflight passed (the earlier ARC-5 start, with the API down, printed the misleading "Kyverno CRD missing" message). Captures: `live-run/captures/ARC-2/`. No overlap with SDR-5: ARC-2's two ClusterPolicies match only pods in `arc-lab`; probe pods and the `stray` deployment were created in `arc-lab` and deleted afterwards.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 5.6 s | 3 deployments (web, api, db on `ubi9/python-311:1`), 3 network policies (`api-from-web`, `db-from-api`, `default-deny-ingress`); 13 cluster policies, not 2 (other modules' policies; checkpoint allows) |
| 2a | 10.1 s | `components=3 flows=2 admission=8 gaps=0`, exit 0 (admission 8, not 2) |
| 3a | 2.4 s | Components, mechanisms and flows match (web to api, api to db, port 8080); admission lists 8 policies (Enforce: arc-require-nonroot and three agent-guardrails; Audit: arc-disallow-latest and others); see bug 1 |
| 4a | 26.8 s | web to api 200, web to db blocked, api to db 200, api to web blocked. Matches; OVN enforces the policies |
| 5a | 5.3 s | Refused by `validate.kyverno.svc-fail` naming `arc-require-nonroot`: "Pods in arc-lab must set runAsNonRoot to true"; pod NotFound. Matches |
| 5b | 41.6 s | Pod created; `policyreports` true, `clusterpolicyreports` false; fail line for `arc-disallow-latest`, `no-latest-tag` with an empty third column (bug 2) |
| Test 1 | 4.0 s | MATCH |
| Test 2 | 4.0 s | STOP message, exit 2, 0-byte file. Matches |
| Test 3 | 11.4 s | `components=4 flows=2 admission=8 gaps=1`, exit 1, gap `{"type":"unmapped","name":"stray",...}`. Matches |

## Bugs and mismatches
1. **Claims C2 and C3 name the wrong policies (most important).** The map says C2 is "a request that breaks agent-guardrails is refused in arc-lab" and C3 "a request that breaks agent-baseline is allowed, and a violation is recorded", but Step 5 and the checkpoint test `arc-require-nonroot` and `arc-disallow-latest`. The script picks the first Enforce and first Audit policy it finds, which are other modules' policies. Pin the claim policies to the `arc-*` names.
2. **5b third column is empty.** The module expects `probe-latest`; `.resources[0].name` is empty in Kyverno 1.19.2 reports. Probably the `scope` field; the report was gone when probed after the pod deletion. Cause not confirmed.
3. Admission count is 8, not 2. The Step 3 checkpoint says "one policy is Enforce, one is Audit" but the map shows four Enforce and four Audit rows; say to find the `arc-` rows.
4. Step 4 takes 26.8 s (each blocked path waits out a 4 s timeout plus `oc exec` startup).

## Notes
- Every `oc` call prints the Kyverno `ClusterPolicy is deprecated` warning, not in the module (filtered from the display, present in the capture files).
- `$HOME/arc` resolves to `/workspace/.lab/home/arc`, which matches the expected "/root/arc" only in form.
- Test 3's text says the stray pod is refused and never becomes ready; not checked because the test commands do not show it.
- Left in the lab: `arc-lab` with web, api, db and the two ARC-2 policies; `$HOME/arc/map.json`, `map-stray.json`, an empty `map-missing.json`. No probe pods or `stray` deployment remain.

## TODO [live] status
Confirmed: Kyverno 1.19.2 honours rule-level `failureAction` and the `autogen-controllers=none` annotation (Enforce refused probe-root, Audit let probe-latest in); Audit violations appear in `policyreports` (`policyreport`/`polr`) with a fail result for `arc-disallow-latest`; `ubi9/python-311:1` starts non-root and `$HOME` is the lab shell home; OpenShift SCC admission does not add `runAsNonRoot` to probe-root (refused); OVN-Kubernetes enforces network policies (web to db and api to web blocked). Platform tool: Kyverno was running, preflight passed.
