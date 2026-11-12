# Live run findings

Run started 2026-11-09 against the live lab. Commands run exactly as in the rendered module, through the lab tools container (`labrun.sh`, same image and environment as `lab shell`). Times are wall-clock for command execution only (no reading time). Nothing is fixed during the run; every problem is logged here.

## GRC-2 Run Evidence Collection (clean sequential timing)

`lab start grc-2` applied all eight state files; it then printed INCOMPLETE with the six TODO items (expected).

| Step | Wall time | Result vs module |
| --- | --- | --- |
| 1a fetch + wc/grep | 2.0 s | Matches: 52 lines, 4 `"get"`, empty grep (exit code 1 is the empty grep, not an error) |
| 2a collector + 4 jq | 6.2 s | Matches: complete true, 4 collected, fips true, `{"total":1,"ready":1}` |
| 3a describe + clusterrole | part of 3b | Matches. One task `collect`; four rules get/list |
| 3b pipeline start, diff | 27.2 s | Matches: Succeeded, age 0, `same` |
| 4a node FIPS | 7.7 s (with 5a) | Matches: kernel `1`, configured `true` |
| 5a data + explain | see above | **Differs** (bug 1) |
| 5b-5f | 16.1 s total | 5d, 5e, 5f match; 5c **differs** (bug 1) |
| Test 1 | with Test 2 | Matches (run duration 23 s, service account evidence-runner) |
| Test 2 | 14.2 s | Matches exactly: Succeeded, complete=false, two Forbidden errors with the same wording |

Total command time about 75 s against "about 71 minutes (52 hands-on, 19 verify)" in the header. The header is reading and typing time, so no change is proposed yet.

### Bugs
1. **Step 5 root_pods check returns 0, not 1.** OpenShift admission (restricted SCC) sets `runAsNonRoot: true` on the legacy-batch container, so the "every container" test treats it as enforcing non-root. Live output: `{"total":2,"without_non_root":0,"names":[]}` and 5a shows the container-level `runAsNonRoot: true` on legacy-batch and none on payments-api's container (the reverse of what 5a's expected output says). The pod-level tsv in 5c does print `unset` for legacy-batch, so the checkpoint "the pod shown as unset is the one listed in names" fails. Also affects the reference answer in `evidence-reference` and `lab/states/grc-2` TODO item 5. Fix options: make the check read the Deployment pod templates (what was declared) rather than live pods, or change the sample workloads, or compare pod-level only. Needs a decision.
2. **5a expected output is wrong in the same way**: the pod names carry different hashes (fine, example), but the settings are reversed at container level.

### Notes
- Tekton log shows `warning: unsuccessful cred copy: ".docker" ... permission denied` from the `get-oc` step. Harmless; Step 3 says only "the task log streams". Consider adding one line saying this warning is expected.
- `oc debug` prints a "Starting pod / Removing debug pod" block; the module already says it may appear.
- TODO `[live]` items: 1 (Forbidden on machineconfigs/apiservers, ok on namespaces/clusterpolicies) confirmed; 2 (images pull) confirmed; 3 (Kyverno Ready condition counted, ready=1) confirmed; 4 (rendered-master spec.fips true) confirmed; 5 **fails** (bug 1).
