# VM-5 live run (2026-11-10; run in parallel with SDR-4/5 and others, timings not clean)

`lab start vm-5` 22 s (INCOMPLETE notice, 5 [live] items). Every step and Test ran. **Step 4g has three blockers that needed workarounds.** Captures: `live-run/captures/VM-5/` (`4g-wa.txt` to `4g-wa4.txt` are failed or aborted attempts and diagnosis; `4g-wa5.txt` is the run that worked). Scripts `vm5_<step>.sh` in the scratchpad.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 3.5 s | Matches; 10 files; serious 8, serious_fixable 5, critical_fixable 2 |
| 1b, 1c | 3.7, 2.8 s | Match (KEV list 1773 IDs; `10 policy.json`) |
| 2a to 2c | 2.5 to 2.9 s | Match; own 3 conditions give 14 lines |
| 2d | 3.1 s | 8 cases not yet right, then `ok: all 10 cases` |
| 2e | 3.8 s | One differing line (own `bool()` wrap), allowed |
| 2f, 3a to 3c | 2.0 to 2.4 s | Match (3a line count not checked against "about 36") |
| 3d | 2.0 s | Exit 1; blocking libalpha, libindia (critical-fixable), libdelta (high-fixable-overdue); exceptions `{"active":1,"expired":1,"invalid":2}` |
| 4a to 4f | 1.7 to 4.1 s | Match (8 keys; 23, 43, 67, 37, 63 lines) |
| 4g as written | 5.9 s | **FAILED**: `tkn pipeline start` stops at a prompt |
| 4g with workarounds | 25 s, 18 s, 113 s, 58 s | Clone passes, scan passes (about 1 min 50 s on the first run for the Trivy and Java DB downloads), gate fails with `"blocked":true`, 137 blocking findings; summary kept: `{"blocked":true,"blocking":137,"expired_exceptions":0,"mean_days_to_fix":null}` |
| 5a | 4.7 s | After-fix run exit 0, `{"blocked":false,"blocking":0,"expired_exceptions":1,"mean_days_to_fix":21.8}`. Matches |
| 5b | 2.5 s | `9 adopt-gate.json`, matches |
| 5c | about 3 s | Coverage 1 of 4 (25%), then 3 of 4 (75%); see notes |
| Test 1 | 3.5 s | `fixed_count` 5, mean 21.8, max 40. Matches |
| Test 2 | 2.9 s | Matches |
| Test 3 | 2.9 s | Exit 1, libgolf blocked by known-exploited only. Matches |
| Test 4 | 2.9 s | Error, exit 2, no `none.json`. Matches |

## Bugs
1. **BLOCKER 4g: `tkn pipeline start` prompts for `git-revision`.** No `-p git-revision=` and no `--use-param-defaults` in the command; without a terminal it dies with `Error: EOF`, and a learner gets an unexplained prompt. Add `--use-param-defaults` or `-p git-revision=main`.
2. **BLOCKER 4g: clone fails with "SSL certificate problem: self-signed certificate in certificate chain".** The `git-clone` task does not trust the lab Gitea route; the credential is linked but no CA is given. Workaround: patched the clone param `SSL_VERIFY=false` (param name `SSL_VERIFY`, not `sslVerify`). Proper fix: bind `ssl-ca-directory` to the existing `config-trusted-cabundle` ConfigMap in build (untested), or pass `SSL_VERIFY=false` in `risk-gated-release.yaml` with a note. team-b-release and team-c-release have the same clone and would fail the same way.
3. **BLOCKER 4g: gate task rejected with `[User error] more than one PersistentVolumeClaim is bound`.** `risk-gate` uses two PVC workspaces (source, ledger) but Tekton `coschedule: workspaces` allows one PVC per task. One PVC with two subPaths left the clone pod Pending (affinity rules). `oc patch tektonconfig` (coschedule disabled) was blocked as a shared-cluster change and not applied. Workaround: `-w name=ledger,emptyDir=`, so the ledger does not persist between runs and the module's persistence claim is unverified. Real fix: set `coschedule` to `disabled` or `pipelines` in the lab build, or put the ledger on the same PVC another way.
4. Fixed sample exception dates (module "2026-10-29", gate run with `--today`); lab date is 2026-11-10; nothing breaks.

## Notes
- 137 blocking findings in the first pipeline run (external exposure, age 0 days, `vm-app` base image); the module only says "a list"; tell learners to expect a long one.
- 5c: pipeline `detections` (another module in namespace build) has no matching spec path, its patch printed "The request is invalid", so coverage ended at 3 of 4 (75%), not 100%. Shared namespace affects this count.
- `--last` in 5a was the right run by luck; other modules share namespace build.
- Left in the lab: build objects `risk-gate-config`, PVCs `risk-source-pvc` and `risk-ledger-pvc`, tasks `risk-scan` and `risk-gate`, pipeline `risk-gated-release` (patched `SSL_VERIFY=false`), team-b-release and team-c-release patched with the gate, failed and good PipelineRuns, an affinity-assistant pod; `/workspace/vm-5`.

## TODO [live] status
Confirmed: Trivy image `ghcr.io/aquasecurity/trivy:0.76.1` runs with `sh`, `sed`, `head`, `trivy`; `ubi9/python-312:1` runs `python3`; Tekton ConfigMap workspace via `config=` and a failing gate step keeps the Task result; JSON patch applies to team-b and team-c; internet from the lab shell and pipeline pods; the real catalog lists none of the fictional CVE-2099 IDs.
Partly: git credential annotation matching the Gitea host (clone worked with TLS off, credential use not shown). Not confirmed: ledger persistence; the right fix for the self-signed clone failure.
