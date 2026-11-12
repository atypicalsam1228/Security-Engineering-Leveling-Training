# Review GRC-5 (final pass 2026-11-11)

## Sections
- [x] A. Accuracy: skipped per brief_final2 (live runs 11-10 and 11-11 proved all commands).
- [x] B. Coherency: position 23 of 29; previous in order IAC-3, next VM-5; start state independent (lab start grc-5); timings 41+19 min unchanged; step cross-refs (Step 2-5, Tests 1-4) match; `-c monitor` fix present.
- [x] C. Brief compliance: validate 0 errors, 0 warnings; render ok.
- [x] D. Compliance claims reviewed against vault (Sources/NIST-800-53/nist-sp-800-53r5-full.md).
- [x] E. No lab domain, email, account ID or secret in text.

## Findings
| Finding | Severity | Fix |
| --- | --- | --- |
| "next" said SDR-2 follows; order.py has VM-5 after GRC-5 | Medium | Rewritten to VM-5 Risk-Based Gate in Delivery; VM-5 added to mentions |
| 1a: Kyverno ClusterPolicy deprecation warning prints first | Low | Note added to expect |
| Test 2: real output has created/condition met/deleted lines | Low | Note added to expect |
| 1a lists other modules' policies | Info | Already covered by checkpoint |
| 5a prints only control-monitor.yaml | Info | Expect already says "a line naming control-monitor.yaml" |
| validate warned on 'wgpolicyk' | Low | Appended to checks/allowlist.txt |

## Vault review report
Claims reviewed: 8 (CA-7 c quote, CM-6 d quote, CM-3 b quote, CA-7 metrics/frequency org-defined, CM-6 summary, CM-3 summary, CM-7/CM-8/SI-7/SA-11 labels, 15/120 minute values stated as lab values). Verified 8, DRIFT 0, UNVERIFIED 0. Lab values are labelled as not framework requirements.

## UNRESOLVED
- Not checked live: Kyverno background scan interval; the CronJob's own scheduled run (draft text already says so).
