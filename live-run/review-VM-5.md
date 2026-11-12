# Review VM-5 (final pass, 2026-11-11)

## Sections
- [x] A. Accuracy: skipped web re-verification per brief; live run 2026-11-10 proved commands. Live blockers (prompt, TLS, two PVCs) were already fixed in the content file (--use-param-defaults, ssl-ca=lab-ca, single risk-pvc).
- [x] B. Coherence: start state follows VM-4 (its Next line names VM-5); lab-ca ConfigMap exists in the VM-5 start state; order.py puts SDR-5 after VM-5.
- [x] C. Brief compliance: validate 0 errors, 0 warnings.
- [x] D. Compliance claims: see report.
- [x] E. No lab domain, email, account ID or secret in text.

## Findings
| Finding | Severity | Fix |
| --- | --- | --- |
| "Next" pointed to CPS-5; order.py gives SDR-5 Detection as Code | High | Next line rewritten |
| Draft text stale (tools/trivy:lab images, ConfigMap/KEV items now confirmed) | Medium | Draft rewritten to current live state |
| Step 3 checkpoint claimed fictional IDs not on real list, nothing in the step shows it | Low | Clause removed |
| Step 5 coverage may stay below 100% when another module leaves an unpatchable team- pipeline in build | Medium | Note added to expected output; draft notes it |
| "ghcr" spelling warning | Low | Added to allowlist.txt (append) |

## Vault review report
Claims reviewed: 6 (RA-5 automate vulnerability management; RA-5d response times/risk assessment; SI-2(3)a measure time; SI-2(3)b benchmarks; SA-11c evidence; SA-11d verifiable flaw remediation). Verified 6 against Sources/NIST-800-53/nist-sp-800-53r5-full.md. Drift 0. Unverified 0 (15/30/90 days and 30-day exception limit are labelled as lab choices; agency CISA for KEV correct).

## UNRESOLVED
- Not re-run live since fixes: single shared PVC with ledger beside clone (earlier attempt with two subPaths left clone pod Pending), lab-ca as ssl-ca workspace for git-clone.
- Ledger persistence between pipeline runs never confirmed.
- Step 5 coverage depends on other modules' pipelines in shared namespace build (live run ended 75%).
- Fixed exception dates (2026-10-29) vs lab date; harmless.
