# GRC-3 live run (2026-11-09; run in parallel with VM-2, so timings are not clean)

No step failed; `lab reset` was not needed. Captures: `live-run/captures/GRC-3/`.

| Step | Wall time | Exit | Result vs module |
| --- | --- | --- | --- |
| `lab start grc-3` | 30.6 s | 0 | INCOMPLETE notice, expected |
| 1a | 4.0 s | 0 | 5 FAIL lines (4 rules plus read); checkpoint met |
| 2a | 6.3 s | 0 | FIPS true, counts "1 87"; checkpoint met |
| 3a | 1.1 s | 0 | ok |
| 3b | 4.8 s | 0 | checkpoint met |
| 4a | 1.4 s | 0 | JSON matches |
| 4b | 20.2 s | 0 | status success, merge 200; checkpoint met |
| 5a | 0.7 s | 0 | ok |
| 5b, WRITE lines unchanged | 0.9 s | 1 | 7 FAIL, 1 PASS, as intended |
| 5b, learner answers | 0.6 s | 0 | ok |
| 5c | 1.8 s | 1 | 8 PASS, bad copy FAILs, can-i yes then no (exit 1 only from the final `no`) |
| 5d | 1.0 s | 0 | matches the answer |
| 5e | 14.8 s | 0 | checkpoint met |
| Test 1 | 50.5 s | 0 | checkpoint met |
| Test 2 | 0.8 s | 0 | identical hashes, time ends in Z |
| Test 3 | 0.9 s | 1 | 4 FAIL lines match; line numbers 41 and 43 instead of 42 and 44 |
| Test 4 | 31.4 s | 0 | result "failure", merge 405, PR "closed" |

## Bugs (wording and expected output only, nothing blocking)
1. 3b gate prints `PASS: timestamp, hash and write location all present`, not a bare `PASS`.
2. Test 1 differs from the example: `ls -l` also shows `lost+found`; `oc get cronjob` has a TIMEZONE column; LAST SCHEDULE is `<none>` not `6m` (only the manual job ran); the pod takes about 50 s with no time hint.
3. 5c `can-i` adds "Warning: resource 'namespaces' is not namespace scoped" and a blank line.
4. 5e `oc logs` prints a "Defaulted container" line.
5. Test 3 line numbers 41 and 43 versus 42 and 44 in the example.

## Notes
- A real 15-minute scheduled run was not waited for, so it is not confirmed.
- `build` also holds `collect-evidence-run-*` PipelineRuns from GRC-2; untouched.

## TODO [live] status
Confirmed: el-gate-listener service on 8080 and `body.after`; the two tekton-triggers cluster roles; images pull, python image has curl, pods reach Gitea; unauthenticated raw fetch; Gitea status endpoint and the 405 refusal. [lab-build] 1, 5, 6 (webhook allowed, git token, FIPS on newest rendered-master) work.

## Screenshot run 2026-11-11
- Step 4b merge returned 409 with an empty body (twice), yet main already holds the merge commit c96fc1f798 and the PR stays open showing "0 commits / already on the target branch". Probable cause: an earlier merge attempt landed but the PR was not marked merged. Needs a clean re-run of GRC-3 from `lab start` to confirm; the PR page was not used as a screenshot because the state is inconsistent.
- Clean re-run: merge returned HTTP 200, PR merged. The earlier 409 came from a stale local clone left over from the first run, not from the module. No module change needed.

## 2026-11-11 re-run
Result: PASS (all steps 1a-5e and Tests 1-4 met their checkpoints). Captures: `captures/GRC-3/rr-*.txt`. No hangs; longest step Test 1 (41 s).

Functional:
- Re-running `lab start grc-3` on a workspace that already ran the module does NOT reset state: the Gitea repo evidence-scripts keeps the earlier merged PR and a collect_evidence.py on main, and `/workspace/grc-3/evidence-work/evidence-scripts` (clone) stays. First attempt therefore showed 1a with no "Cloning into", 3b `ls evidence` with old files, and 4b "nothing to commit", PR 404/405 on merge. To get a clean run I removed the evidence-work folder and deleted the Gitea repo via API, then `lab start` again. Suggest: say in the module/`lab start` that a repeat start keeps the Gitea repo and local clone, or have 50-gitea-evidence-repo.sh recreate the repo and 55-supplied-files.sh clear evidence-work.

Wording / example mismatches (not blocking):
- 4b: example shows only "(git prints the new branch and the push result)"; real push also prints a "Create a new pull request" link. Fine.
- 5c: `can-i` prints "Warning: resource 'namespaces' is not namespace scoped" before each answer (module already notes it). Exit code 1 from the final `no` is expected.
- 5e: "Defaulted container "collect" out of: collect, get-oc (init)" printed (already noted in module).
- Test 1: `ls -l` lists lost+found last (not first as in the example); delete message is `pod "evidence-view" deleted from build namespace`, example says `pod "evidence-view" deleted`. Suggest changing the example text to the latter. Pod ready ~35 s.
- Test 3 line numbers 41/43 now match the example.
