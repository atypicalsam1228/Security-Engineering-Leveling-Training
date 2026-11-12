# Review GRC-4 (final pass 2026-11-11)

## Sections
- [x] A. Accuracy: skipped web re-verification per brief; live runs (2026-11-09/10) confirmed cosign flags, entrypoint, Kyverno dry run, Tekton configMap volume, image pulls, signing in pipeline.
- [x] B. Coherency: start state follows GRC-3 (its next line names GRC-4); next line GRC-5 is the dimension's next module; Module N of 29 comes from order.py; 4 steps; screenshot alt text matches step labels (1a, 2a, 3b, 4b, test1-4); live-run fixes already in content (runAsUser 65532 on publish, StepFailed reasons, either-order Test 4, "over a hundred" Test 3, Waiting-for-logs note, test -s guard, ASN.1 error note).
- [x] C. Brief compliance: validate 0 errors, 0 warnings. No lab domain, email, account ID or secret in text.
- [x] D. Compliance claims checked against Sources/NIST-800-53/nist-sp-800-53r5-full.md.
- [x] E. render.py succeeded.

## Findings
| Finding | Severity | Fix |
| --- | --- | --- |
| `draft` text said "Nothing here has run on a live cluster" and listed items since confirmed | Low (hidden draft) | Rewrote with live-run status and what remains unconfirmed |
| 4 validator spelling warnings (Kyverno's, Tekton's, Grype, sigstore) | Low | Appended to checks/allowlist.txt |
| Findings-file blockers (PVC size, reset TaskRun, publish uid, demo image 59 findings) | n/a | Already fixed in lab/content: evidence-app uses registry.k8s.io/pause:3.10; publish has runAsUser 65532 |

## Vault review report
Claims reviewed: 9 (SA-11 a/c/d + org-defined frequency/depth; SI-7 a + org-defined actions; CM-6 a/d; control titles; Rev 5 source). Verified 9. Drift 0. Unverified 0. No agency names, timeframes or FedRAMP values are claimed.

## UNRESOLVED
- Clean end-to-end live run with the evidence-app (pause) image after the fixes: confirm Step 1 prints 0, Step 4 succeeds, Tests 1-4 pass as written.
- lab/states/grc-4/10-demo-app.sh and reset.d header still say "NOT YET RUN ON A LIVE CLUSTER" (lab file, not edited).
