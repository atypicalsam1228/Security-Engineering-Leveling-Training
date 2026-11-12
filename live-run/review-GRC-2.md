# Review GRC-2 (final pass 2026-11-11)

## Sections
- [x] A. Accuracy: skipped per brief_final2 (live run proved commands); no findings file existed.
- [x] B. Coherency: ENG-1 "Next module" names GRC-2; GRC-2 "Next module" names GRC-3; GRC-3 prereq/collector references GRC-2 consistently; prereq ENG-0 fine. Position/timing are generated from order.py.
- [x] C. Brief compliance: validate 0 errors, 0 warnings.
- [x] D. Compliance claims reviewed (vault: Sources/NIST-800-53).
- [x] E. No lab domain, email, account ID or secret in text (only public quay.io / redhat.com image names).

## Findings
| Finding | Severity | Fix |
|---|---|---|
| 5 spelling warnings on "grc" (grc2-workloads) | low | appended `grc` to checks/allowlist.txt |

## Vault review report
Claims reviewed: 9. Verified: 9 (CA-7 d quote; CM-6 a, c, d wording; SC-13 a quote; "organization-defined" for CA-7 metrics/frequencies, CM-6 secure configs, SC-13 uses; control names). Drift: 0. Unverified: 0. The 24-hour stale limit is labelled a lab choice, not a framework value.

## UNRESOLVED
- render.py failed: modules/GRC-2-RunEvidence.docx is locked (open in Word). Close it and rerun `python render.py GRC-2`. Content was not changed except allowlist, so only a re-render is needed.
