# Review VM-4 (final pass 2026-11-11)

A. Accuracy: skipped per brief (live runs proved commands). [x]
B. Coherency: start state (VM-3 files via vm-tools), Next = VM-5 (same-dimension convention as VM-3), screenshots alt match steps. [x]
C. Brief compliance: validate 0 errors, 0 warnings. [x]
D. Compliance claims: see report. [x]
E. No lab domain, email, account ID or secret in text (placeholder example.invalid only). [x]

| Finding | Severity | Fix |
| --- | --- | --- |
| 1a example listed rank.py first; ls is alphabetical | low | example reordered |
| 3c example omitted report-svc P1 / batch-old P3 rows and exception action | low | example and checkpoint updated |
| Test 1 pair order differs from example | low | note added |
| Stale "zero KEV matches" claim | low | already corrected in 2d note (about eight) |
| 5a push prints remote: lines | low | expect already says harmless |

Vault report: claims reviewed 10 (RA-5(d), RA-7, CA-5(b), CM-3(b,c) quotes; org-defined response times and frequency; CISA KEV; RA-5/CA-5/CM-3/RA-7 IDs; Rev 5). Verified 10, DRIFT 0, UNVERIFIED 0. Lab 15/30/90 days and 30-day exception are labeled lab choices, not framework values.

UNRESOLVED: rank.py/deadlines.py not diffed against the VM-3 reference; Route admission/fetch through route not checked live.
