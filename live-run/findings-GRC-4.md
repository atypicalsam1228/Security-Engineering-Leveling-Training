# GRC-4 live run (2026-11-09; run in parallel with VM-3 and SDR-2, timings not clean)

**BLOCKED at Step 4b.** The pipeline cannot complete as built, so no bundle exists and Tests 1 and 2 could not pass. Captures: `live-run/captures/GRC-4/`. Note: cap.sh shows the wrapper's exit code (0) for every step, so real failures show only in the output.

| Step | Time | Result |
| --- | --- | --- |
| `lab start grc-4` | 17.6 s | OK; INCOMPLETE notice (4 [live], 1 [lab-build]) |
| 1a | 13.4 s | OK. Kyverno pods Running, policy READY True, flags-accepted, cosign.pub header OK, digest OK. **Trivy count 59, not 0** |
| 2a | 4.6 s | Matches: Enforce, dry run denied naming grc-enforce-no-latest-tag, report count 0 |
| 3a, 3b, 3c | 0.7, 1.2, 0.6 s | Match |
| 3d (agent's own lines) | 0.6 s | 461 bytes; matched the reference |
| 3e, 3f | 0.7, 0.6 s | OK |
| 3g | 3.9 s | OK. 3 tasks created; 3 extra tasks listed (evidence-collect, evidence-gate-check, evidence-gate-report) that the module output omits |
| 3h | 19.3 s | Matches: result admitted |
| 3i | 1.3 s | Matches |
| 4a | 0.7 s | OK |
| 4b | 48.5 s | **FAIL**: scan step fatal, Trivy DB download "no space left on device" at /workspace/evidence/.trivy/db/trivy.db |
| `lab reset grc-4` | 600 s | **FAIL**: reset.d/10-remove-grc-4-work.sh timed out (exit 124) |
| `lab start` + 1a, 3g, 4b retry | 15 s, 4.9 s, 5.8 s, 38.2 s | 4b **FAIL again**, same disk error |
| Test 1 | 0.8 s | FAIL: "unexpected end of JSON input" (bundle.json empty) |
| Test 2 | not run | needs a bundle |
| Test 3 | 24 s | Scan fails with empty results from the disk error, not from nginx:1.16 findings (no "blocking findings: N"). **False pass** |
| Test 4 | 28 s | Scan fails on the disk error, policy task never ran; expected "scan Succeeded, policy Failed" not seen |

## Bugs
1. **Evidence volume too small.** `evidence-work` is a 1Gi PVC (gp3-csi); the Trivy database (TRIVY_CACHE_DIR on the volume) does not fit. Failed twice. Fix: enlarge to about 5Gi or move the cache to an emptyDir.
2. **Reset hangs.** The TaskRun `evidence-policy-run-<id>` from 3h (`tkn task start`) is not deleted by `reset.d/10-remove-grc-4-work.sh`, which only deletes PipelineRuns labelled evidence-bundle. Its completed pod keeps the PVC in use, so `evidence-work` sticks in Terminating and the reset times out after 10 minutes. Workaround used once: `oc delete taskrun evidence-policy-run-cfkl9 -n build`, then `lab start grc-4`. The script header also says "NOT YET RUN ON A LIVE CLUSTER".
3. **Trivy count is 59.** Step 1a says to tell the AI assistant when nonzero, and the Step 4 good run would stop. Even with disk space the gate would fail on the demo image (ubi9/ubi-minimal). This is TODO [lab-build] 4: the demo-app base image should have no HIGH/CRITICAL findings. Test 3's nginx:1.16 result would then look the same as the good run.
4. Cosign and Kyverno ClusterPolicy deprecation warnings are not in the module (harmless).

## TODO [live] status
Confirmed: Kyverno server-side dry run, autogen Deployment rule, policy Ready; Tekton configMap volume, python3 /admit/admit.py, python on PATH; trivy, python-312, origin-cli pull fine; cosign `--use-signing-config=false` and `--tlog-upload=false` accepted locally in the lab shell.
Not confirmed (never reached): cosign v3.1.4 entrypoint, Trivy DB in pipeline pods (download starts from mirror.gcr.io but fails on disk), nginx:1.16 pull, compact bundle verify, signing inside the pipeline.
Failed: [lab-build] 4 demo image clean of HIGH/CRITICAL (59 findings).

State left behind: `build` has the retry's tasks, pipeline and failed runs; `evidence-work` is rebound.

---

# GRC-4 re-run (2026-11-10, after the PVC and reset fixes; parallel with CPS-4)

Captures: `live-run/captures/GRC-4/*-r3.txt` (plus `4b-workaround*`, `wa2-r3`, `dbg*-r3`, `cand-r3`, `test-4-wa-r3`).

**Both fixes verified live. The module still cannot pass as written: two blockers; Tests 1, 2 and 4 passed only with logged workarounds.**

## Fix verification
- **PVC 5Gi: verified.** `evidence-work` bound at 5Gi (Pending until the first pod). Trivy DB downloaded in about 6 s from mirror.gcr.io; "no space left on device" is gone.
- **Reset TaskRun deletion: verified.** With a leftover `evidence-policy-run-*` and 8 PipelineRuns, `lab reset grc-4` took 2m40s (not 600 s). The script header still says "NOT YET RUN ON A LIVE CLUSTER".

## Timings and results
| Step | Time | Result |
| --- | --- | --- |
| `lab start grc-4` | 28.9 s | OK, fresh state |
| 1a | 11.1 s | Matches except Trivy count **59** (not 0); extra Kyverno and cosign deprecation warnings |
| 2a | 9.8 s | Matches |
| 3a to 3f | 2.4 to 3.5 s | Match; 3d identical to the reference (461 bytes) |
| 3g | 27.7 s | Matches; `tkn task list` shows exactly 3 tasks (the earlier extras were stale state) |
| 3h | 14.0 s | **Mismatch**: `--showlog` prints "Waiting for logs..." and returns with no `[admit]` line; the TaskRun Succeeded about 86 s later |
| 3i, 4a | 3.2, 2.6 s | Match |
| 4b | 107.2 s | **FAIL**: "blocking findings: 68" at the scan gate, no bundle |
| Test 1 straight after 4b | 2.9 s | FAIL: `unexpected end of JSON input` (empty bundle.json) |

## Workarounds used (not module fixes)
1. Ran the pipeline with `gcr.io/distroless/static-debian12:latest` in place of the demo digest (0 HIGH/CRITICAL; ubi9/ubi-minimal:latest has 14, nginx:1.16 has 166).
2. The `publish` step crashed with `PermissionError: [Errno 13] ... 'bundle.sigstore.json'`: cosign (uid 65532) writes the file as `-rw-------`, the python-312 publish step (uid 1001) cannot read it. Failed in 3 pipeline runs. Workaround: `runAsUser: 65532` on the publish step (`/workspace/grc-4/eb-wa.yaml`); the run then Succeeded in 35 s. The patched `evidence-bundle` task stayed in the cluster until the final `lab reset`.

| Test (with workaround) | Time | Result |
| --- | --- | --- |
| Test 1 | 2.6 s | PASS: "Verified OK"; extra tlog warning line |
| Test 2 | 2.7 s | PASS in substance; error is `invalid signature when validating ASN.1 encoded signature`, does not name tampered.json |
| Test 3 (nginx:1.16) | 39.8 s | PASS in substance: 166 blocking findings (module says 92); reason prints `scan StepFailed`, not `scan Failed` |
| Test 4 literal | 19.0 s | **FAIL as written**: scan gate stops at 68, policy never runs |
| Test 4 with distroless | 25.1 s | PASS in substance; reasons `policy StepFailed` then `scan Succeeded` (order reversed) |

## Bugs
1. **Demo image fails the gate** (68 in the pipeline, 59 from the lab shell; trivy versions weigh vendor severity differently). Open TODO [lab-build] 4. Blocks 4b, Test 1, 2, 4.
2. **Publish step cannot read the cosign signature file.** Blocks every successful run. Fix: share a uid between sign and publish (runAsUser 65532 worked).
3. 3h `--showlog` returns early on the first run (image pull); add a note or use `tkn taskrun logs --last`.
4. Tekton reasons are `StepFailed`; Test 4 reason order reversed.
5. Test 3 count (92 vs 166) and Test 2 error text do not match.
6. Extra warnings (Kyverno deprecation, cosign flags, tlog on verify), harmless.
7. After a failed run Test 1 gives "unexpected end of JSON input"; a `test -s bundle.json` guard would be clearer.
8. `lab reset grc-4` takes 2m40s; header comment "NOT YET RUN" is stale.

## TODO [live] status
Confirmed: Kyverno dry run and autogen rule; Tekton configMap volume and admit.py; trivy, python-312, origin-cli and cosign:v3.1.4 (entrypoint `/ko-app/cosign`) pull in pipeline pods; Trivy DB reachable and fits 5Gi; nginx:1.16 pullable; cosign flags accepted; bundle verifies in the lab shell with the public key; tampered copy fails; signing inside the pipeline works.
Failed: [lab-build] 4 demo image not clean. New failure: publish step cannot read the signature.

State left: `lab reset grc-4` was run last, namespace clean. `/workspace/grc-4` holds stale files (`eb-wa.yaml`, `eb-dbg.yaml`).
