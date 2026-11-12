# VM-2 live run findings (2026-11-09)

Start: `lab start vm-2` took 13.7 s; ended with the INCOMPLETE notice listing the 5 [live] TODO items (expected). Captures: live-run/captures/VM-2/. No reset was needed; no step failed.

| Step | Wall time | Exit | Result vs module |
| --- | --- | --- | --- |
| 1a fetch files + image scan | 124.9 s (first DB download) | 0 | handoff.sh extracted; 362 findings, 284 fixable; scans.tsv 1 line. Matches CHECKPOINT. |
| 2a clone + repo scan | 2.7 s | 0 | requirements.txt (5 pins) listed; `requirements.txt 30`; scans.tsv 2 lines. Matches. |
| 3a config scan | 31.1 s | 0 | HIGH 3, LOW 10, MEDIUM 4 (module example shows only HIGH and MEDIUM); scans.tsv 3 lines. Matches CHECKPOINT. |
| 4a SBOM | 3.8 s | 0 | CycloneDX, spec 1.7, 119 components; sbom 362, image 362. Matches. |
| 5a hand-off | 6.6 s | 0 | stored; 4 scans all complete; escalate true (image 39 critical, repo 2, sbom 39). Matches. |
| Test 1 | 2.9 s | 0 | true / exit code: 0. Pass. |
| Test 2 | 2.9 s | 0 | 39 / 39. Pass. |
| Test 3 | 1.1 s | 0 | []. Pass. |
| Test 4 | 4.6 s | 0 | FATAL ... SBOM decode error; failed, critical null, escalate true. Pass. |
| Test 5 | 6.3 s | 0 | partial, critical 0, escalate true; configmap deleted. Pass. |

## Bugs
No blocking bugs. Minor wording and expectation drift:
1. Step 3a: real output includes a `LOW 10` line; module example lists only HIGH and MEDIUM ("Example only", so cosmetic, but the example could include LOW).
2. Step 1a: first run took about 2 minutes (DB download plus image pull). Module says "a few minutes", so consistent. Later steps are fast because the cache is warm.
3. Test 5: real delete message is `configmap "vm-handoff-test" deleted from security-tools namespace`; module shows `configmap "vm-handoff-test" deleted`. Cosmetic.
4. Step 3a takes about 31 s with no output (trivy config check-bundle download); learner may think it hangs. Not mentioned in the module.
5. Test 4: Trivy error text is `SBOM decode error: unknown scanning is not yet supported`; matches the module's loose `FATAL ... unable to ... SBOM ...` pattern only roughly (no "unable to"). Example is flagged as differing by release, so cosmetic.
6. Test 2 and 4a example numbers (27) differ from real (39 critical); flagged "Example only".

## Notes
- Trivy version 0.76.1. CycloneDX spec 1.7.
- Hand-off record also holds `exit_code` and `report` fields per scan, which the field table in 2.2 does not list (extra, harmless).
- Recorded exit code for the broken SBOM scan was 1; empty folder scan 0 with a report that has no Results key (as the module describes).
- Gitea user is `labadmin`; clone with the extra header worked first time.
- Step 5 CHECKPOINT "escalate is true only if a scan has a critical finding": real run escalate true, correct.

## TODO [live] status
1. Trivy DB and docker.io reachable; trivy fs on requirements.txt reports findings; trivy config on a folder; empty-folder JSON shape: CONFIRMED (empty.json has no Results key).
2. oc extract configmap --confirm; jq and trivy present in lab shell: CONFIRMED.
3. Pins produce findings with fixes: CONFIRMED (30 findings, 30 fixable; 2 critical, 12 high).
4. Gitea reachable, certificate trusted, clone with extra header: CONFIRMED.
5. CycloneDX components for nginx:1.16; trivy sbom flags work; SBOM names cover PkgName (Test 3 gave []); truncated SBOM exits non-zero (exit 1): CONFIRMED.

## 2026-11-11 re-run
Result: PASS. Steps 1a-5a and Tests 1-5 all met their checkpoints; no hangs (warm Trivy cache: step 3a 13.5 s, all others under 7 s). Captures: `captures/VM-2/rr-*.txt`.

Functional: none. Hand-off record: 4 scans complete, escalate true (image 39 critical, repo 2, sbom 39); Test 1 true/exit 0; Test 2 39 = 39; Test 3 `[]`; Test 4 status failed/null/escalate true; Test 5 partial/0/escalate true.

Wording only:
- Test 2 example shows 27 critical; real is 39 (flagged "Example only", fine). Same drift as the 2026-11 earlier run.
- Test 4: real Trivy line is `FATAL Fatal error run error: sbom scan error: ... SBOM decode error: unknown scanning is not yet supported`; matches the loose pattern in the example.
- Earlier findings now fixed in the module: 3a example lists LOW; the 30-second silent wait is mentioned; Test 5 delete message matches (`deleted from security-tools namespace`).
- 1a: `oc extract` printed no file list in this run; output is handoff.sh then 362 then 284, matching the example.
