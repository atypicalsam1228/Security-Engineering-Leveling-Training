# CPS-3 final review 2026-11-11

Checked: A (skipped, live-run proved commands), B coherence (start state via lab start, Next module convention matches CPS-2, 52+16 min), C brief, D vault, E no lab domain/email/account/secret in text.

| Finding | Severity | Fix |
| --- | --- | --- |
| Step 3b expected output lacked note that exit code 1 after final "no" is normal | low | note added |
| Step 4b expected output omitted rollout "Waiting for deployment" line | low | line added |
| Step 5 note covered AccessDenied only, not "Unable to locate credentials" | medium | note extended |

Already fixed earlier: delete line wording, 1a header line, Test 3 exit-124 line.

## Vault report
Claims reviewed 6 (AC-6 text, SC-7 text, SC-7(5) quote, CM-6 quote, CM-3/CM-7/AC-3 mentions, org-defined CM-6 configurations). Verified 6 against nist-sp-800-53r5-full.md. Drift 0. Unverified 0.

## Unresolved
- Real learner identity (not Admin SSO) calling iam:SimulateCustomPolicy is untested.
- Prereq lists only ENG-0 while order places SDR-3 before CPS-3; left as is (lab start sets state).
