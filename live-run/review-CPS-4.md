# Final review CPS-4 (2026-11-11)

A Accuracy: skipped by brief; live runs 2026-11-10 and 11-11 passed all steps and tests. [x]
B Coherency: follows SDR-4 in order, standalone start `lab start cps-4`, Module 20 of 29, 76 min, next = CPS-5 (matches order.py), 5 steps. [x]
C Brief compliance: validate.py 0 errors, 0 warnings. [x]
D Compliance claims: [x]  E No lab domain, email, account ID or secret in text (placeholders only). [x]

| Finding | Severity | Fix |
| --- | --- | --- |
| Test 6 example showed a short Falco line; live output is raw JSON with extra command words | Low | Expect text rewritten |
| Test 8 expect omitted oc updated / rollout wait lines | Low | Note added |
| Start time ~9 min for lab start | Info | Not stated in module; no change |

Vault review: 9 claims reviewed (AC-6, IA-5(h), IA-5(7), SC-28, SC-7(a), SC-7(5), quotes x4), 9 verified, 0 drift, 0 unverified. Source: nist-sp-800-53r5-full.md.

UNRESOLVED: learner-policy grant for AWS describe calls not exercised live (only SSO Admin); Falco version not checked; kubeapiserver Encrypted condition not checked; non-root read of mode-400 file confirmed implicitly by Test 6 only.
