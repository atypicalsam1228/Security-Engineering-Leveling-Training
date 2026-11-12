# Final review SDR-3 (2026-11-11)

## Coherence
- [x] Start state: follows SDR-2 (prereq lists SDR-2 and ENG-0); SDR-2 "Next module" names SDR-3; SDR-3 "Next module" names SDR-4, whose prereq names SDR-3.
- [x] Module N of 29 matches order.py (29 entries); timing 50+19 minutes.
- [x] Step cross-references (Step 1 to 5, Tests 1 and 2) match; checkpoints consistent (noise 4, peaks near 9 and 16, threshold 6, band 4-8).
- [x] No lab domain, email, account ID or secret in text.

## Findings
| Finding | Severity | Fix |
|---|---|---|
| Alt text of SDR-3-shot-4b-grafana.png said threshold line "below both bursts"; capture shows counts of 20-70 (larger test run), noise above the line | Medium | Alt text now states counts differ from Step 3 |

## Vault review (NIST 800-53 Rev 5 full text, Sources)
Claims reviewed: 8 (6 quotes, SI-4 a/d/e wording, AU-6 a/b/c org-defined frequency/activity/personnel, IR-4 a-d, mentions IR-5/AU-3/AC-7/SI-4(5) exist). Verified 8, DRIFT 0, UNVERIFIED 0. (Wiki not searched; Sources hit directly.)
Lab thresholds (4 to 8) are stated as lab choices, not framework values.

## UNRESOLVED
- Recapture SDR-3-shot-4b-grafana.png from a run with only exercise records (live-run capture; not touched).
- Grafana 13 API deprecations and classic-condition support remain flagged in draft (confirm live).
