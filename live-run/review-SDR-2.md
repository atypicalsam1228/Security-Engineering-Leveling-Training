# SDR-2 final review (2026-11-11)

## Coherence
- [x] Start state: follows VM-2 in order; lab start sdr-2; prereq ENG-0. Position 5 of 29; "Next module" SDR-3 matches dimension convention. Timing 42+18=60.
- [x] Step cross-references (Step 3 post reused in Test 2), screenshot alt text match steps.
- [x] No lab domain, email, account ID or secret in text.
- [x] Live-run wording mismatch (gaps ok lines) added to Step 5 expect.

## Findings
| Finding | Severity | Fix |
| --- | --- | --- |
| Draft said frameworks leave AU-6 frequency org-defined; FedRAMP assigns "at least weekly" (vault: Sources/FedRAMP baselines, AU-6 (a)-1) | DRIFT, medium | Draft and AU-6 intent "sufficient" now state FedRAMP at least weekly; NIST text unchanged |
| Step 5 example lacked ok lines | low | Added |

## Vault report
Claims reviewed 9 (AU-6 a/b/c, frequency, IR-4 phases and comparable/predictable, AU-5 a, AU-5 params, Rev 5, lab limits are lab choices). Verified 8, DRIFT 1 (fixed), UNVERIFIED 0 compliance claims.
AU-5(a) time period and recipients: org-defined in NIST and FedRAMP (verified). FedRAMP AU-5(b) overwrite oldest record not claimed in module.

## UNRESOLVED
- Real Falco/Keycloak/audit-body assumptions remain in draft (needs live cluster with real sources).
