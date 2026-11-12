# AID-3 live run (2026-11-10; ran parallel with SDR-5, timings not clean)

`lab start aid-3` 39 s, INCOMPLETE notice (9 TODO items). Followed the module as written; **Step 4b has three blockers** worked around with `tkn` flags, one new ConfigMap and a pipeline patch, all in namespace `build`. Everything else passed first time, no reset. Captures: `live-run/captures/AID-3/`.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 11.6 s | Matches; count 3, branch add-summarizer; the tunnel dies with each container, so later blocks reopen it |
| 2a to 2c | 2.5 to 2.9 s | ok each |
| 2d | 3.0 s | Matches; traceback header reads `test_boolean.BooleanCountTest` (Python-version noise) |
| 2e | 3.4 s | Matches; 5 tests OK |
| 2f | 3.2 s | Reference text prints, fuller than the example |
| 3a | 2.8 s | `ailog.py` identical to the module; all 8 `LOKI_*`/`GITEA_*` variables present |
| 3b | 2.9 s | ok |
| 3c | 6.7 s | `{"summary": "Three findings in two tiers. ...", "severity": "high", "count": 3}` |
| 4a | 6.4 s | 5 files, 121 insertions; push prints four `remote:` lines the example omits |
| 4b as written | 3.6 s | **FAILED** (blocker 1) |
| 4b with `--use-param-defaults` | 11.8 s | **FAILED** (blocker 2) |
| 4b with CA workspace, emptyDir | 20.9 s | **FAILED** (blocker 3) |
| 4b with CA workspace and PVC template | 53.6 s | GATE PASSED, `success` (includes first pull of python-312) |
| 4c | 5.7 s | PR 1 merged, HTTP 200 |
| 5a | 10.3 s | `pushed 8 events to app=ai-fixture` |
| 5b | 6.8 s | Drafts match (good, wide `{app=~".+"} ... [30d]`, wrongfield `event="login_failure"`) |
| 5c, 5d | 2.8, 2.9 s | ok |
| 5e | 4.3 s | `PASS ... {'alice': 3, 'bob': 1}`, exit 0 |
| Test 1 | 2.9 s | Matches |
| Test 2 | 16.8 s | Five distinct REJECTED reasons, each exit 1; Loki counts 1 per request id. Matches |
| Test 3 (with workarounds) | 34.4 s | Five FAIL lines and GATE FAILED match; `gate failed, as expected`; 405; PR 2 opened |
| Test 4 | 4.7 s | Matches exactly |

## Bugs
1. **BLOCKER 4b and Test 3: `tkn pipeline start` prompts for `gate-image`.** No `-p gate-image` given; without a terminal it dies with `Error`, a learner with one gets an unexplained prompt. Add `--use-param-defaults` to both commands. (Same as VM-5.)
2. **BLOCKER 4b and Test 3: clone fails with `SSL certificate problem: self-signed certificate in certificate chain`.** The `git-clone` task does not trust the Gitea route (same as VM-5). `SSL_VERIFY=false` was denied by the permission classifier, so it was not used. Workaround keeping TLS on: ConfigMap `lab-ca` in `build` from `/workspace/.lab/ca-bundle.crt` (120 certs), pipeline patched with an optional workspace `ssl-ca` bound to the clone task's `ssl-ca-directory`, run with `-w name=ssl-ca,config=lab-ca`; the clone log then shows `GIT_SSL_CAINFO=.../ca-bundle.crt` and a successful clone. Proper fix: bake the CA ConfigMap and the workspace into `20-pipelines-and-gate.sh` and the module command.
3. **BLOCKER 4b and Test 3: `-w name=source,emptyDir=` leaves the gate with an empty folder.** An emptyDir is per task pod, so `review-gate` does not see what `clone` wrote; the first CA-fixed run reported `FAIL summarize.py: file not found`, `FAIL tests: need at least 4 tests...`, `GATE FAILED` although the branch is correct. Workaround: `-w name=source,volumeClaimTemplateFile=<yaml>` with a 100Mi ReadWriteOnce claim. Real fix: a volumeClaimTemplate in the module command, or clone and gate in one task. A TODO [live] item already flagged the flag as unconfirmed.
4. **Test 3 passes for the wrong reason** with the unchanged module commands: `gate failed, as expected` and 405 come from blockers 1 to 3, not from the bad script. If 4b's gate fails first, a `failure` status is written to the commit; in this run the later `success` on the same SHA replaced it and the merge returned 200.
5. 4a: `git push` prints four `remote:` lines (same as VM-4).

## Notes
- Total command time well under 5 minutes against the module's 72 (excluding the blockers).
- Test 4 ran about 8 minutes after the 5a seed, so FIXTURE never triggered. Idempotency of re-running 4b/4c (second-run PR reuse, merge error) not tested.
- No shared cluster settings changed; Tekton coschedule untouched; `demo` and `siem` not written to.
- Left in the lab: Gitea PR 1 (merged), PR 2 (bad-summarizer, unmerged), branches, fixture events under `app=ai-fixture`; in `build`: ConfigMap `lab-ca`, patched pipeline `ai-script-review` (workspace `ssl-ca`), 4 PipelineRuns plus per-run PVCs; files in `/workspace/aid-3/ai-tools`.

## TODO [live] status
Confirmed: Loki push endpoint and gateway path with all `LOKI_*` variables, Test 1 reads records back; Loki instant query with basic auth, three drafts behave (good passes, wrongfield returns nothing, wide refused by scope), clock agrees with Loki; `oc port-forward svc/stub-model`; branch protection (405 on the bad PR, good PR merged 200 after the `ai-script-review` success status; admin override not tried); `GITEA_*` exported; `gitea_put_file` updated `ailog.py`/`seed_fixture.py`/`scope.py` on first start (already-protected-main case untested); `ubi9/python-312:1` pulled and `python3 -m unittest` works; git-clone cluster resolver works.
Not confirmed or failed: `--exit-with-pipelinerun-error`; `-w name=source,emptyDir=` does not work for the two-task gate; git-clone cannot reach Gitea without a CA workspace.
