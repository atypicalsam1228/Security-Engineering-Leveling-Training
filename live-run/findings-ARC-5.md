# ARC-5 live run (2026-11-10; run in parallel with AID-5, timings not clean)

All 15 blocks ran. Step 2c failed once and passed on retry; everything else passed first time. No fixes, no `lab reset`. Captures: `live-run/captures/ARC-5/run1-*.txt` (`run1-2c-retry.txt` for the retry). `lab start arc-5` 34 s, INCOMPLETE notice (4 [live] items plus Kyverno as a platform need). Kyverno was already installed; 4 pods running in arc-ref.

| Step | Wall | Result |
| --- | --- | --- |
| 1a, 1b | 3.3, 2.4 s | Match (`11 flows.yaml`; `flows file OK: 3 flows, 4 components`) |
| 2a, 2b | 2.6, 2.0 s | Parse OK |
| 2c first run | 51.7 s | **FAILED**: admission policy Ready, default-deny created, 3 allow policies refused (webhook connection refused) |
| 2c retry | 20.4 s | Pass; hash 6d328d57c080 (same as the module's Test 2); 4 policies carry the label |
| 3a to 3c | 2.8 to 3.3 s | Parse OK |
| 3d | 11.6 s | Matches: coverage 100, pairs_tested 12, unlisted_pairs_blocked 9, drift empty, exit 0 |
| 4a | 5.2 s | Both refused, naming `policy-from-flows` and `known-components` |
| 5a | 136.8 s | Detected in 9.1 to 13.1 s (worst case 19.1 to 23.1 s); all recovered; module says "a few minutes", took 2.3 min |
| Test 1 | 11.2 s | `true` |
| Test 2 | 2.1 s | Matches exactly (hash 6d328d57c080, `identical`) |
| Test 3 | 2.3 s | Two FAIL lines, exit 1. Matches |
| Test 4 | 11.5 s | Exit 1 and the four drift lines match, including both hashes |

## Bugs
1. **2c can fail on the Kyverno webhook.** `oc apply` of the network policies failed with `failed calling webhook "validate.kyverno.svc-fail" ... dial tcp ...:9443: connect: connection refused`. All four Kyverno pods restarted at about 18:46 (restart count 3 to 4), the same minute. They had already restarted 3 times in 80 minutes, so Kyverno was unstable; likely load, or a restart triggered by AID-5's cluster-wide policy changes (undetermined). The module's `oc wait ... Ready` returned before the webhook served, so a learner could hit this. Fix: wait for the Kyverno admission controller rollout, or retry in 2c.
2. 2c retry prints "configured" and "unchanged", not "created".
3. `kyverno.io/v1 ClusterPolicy is deprecated` warning on every apply, wait and get; not in the module.

## TODO [live] status
All confirmed: Kyverno accepts `operations [CREATE, UPDATE]` in `match.any[].resources`, rule-level `failureAction: Enforce` and the pattern `api | cache | db | web`; `oc exec deploy/NAME -c app` works for all four (12 probes in about 11 s wall); deleting a NetworkPolicy or `arc-ref-flows` is detected and recovered by the drift timer; python3 3.9.25 with PyYAML 5.4.1 runs all scripts.

Left in the lab: arc-ref with 4 deployments, 4 generated network policies and `arc-ref-flows`; files in `$HOME/arc` (generated/*, flows-extra.yaml, drift-extra.json).
