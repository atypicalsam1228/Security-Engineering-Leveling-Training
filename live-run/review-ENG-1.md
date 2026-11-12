# Review ENG-1 (final pass 2026-11-11)

## Sections
- [x] A Accuracy: skipped web-doc check per brief; live runs proved commands (all steps and Tests matched except items below, now fixed in text).
- [x] B Coherency: follows ENG-0 in order.py; next is GRC-2 (matches order.py); "Module 2 of 29" consistent; 5 steps; prereq ENG-0.
- [x] C Brief compliance: validate 0 errors, 0 warnings; render OK.
- [x] D Compliance claims: module has no controls and no framework claims. Nothing to verify; vault not queried.
- [x] E No lab domain, email, account ID or secret in text (placeholders only).

## Findings
| Finding | Severity | Fix |
| --- | --- | --- |
| 3b used exit 60 promise; plain curl and --cacert /dev/null do not give 60 | high | Already `env -u CURL_CA_BUNDLE -u SSL_CERT_FILE` in file; corrected the lines-table wording ("list is empty" was wrong); added `env` to checks/commands.txt (append) |
| 4a/4c Expected omitted oc "command terminated with exit code N" line | medium | Added to both Expected blocks |
| 2b Expected: HTTP/1.0 and Server line | low | Added Server line, reworded note |
| Test 2 delete line text | low | Now "... deleted from net-lab namespace" |
| Draft text said never run live | low | Updated |
| Step 2 note | low | Notes the line recurs in Step 4 |

## Vault review report
Claims reviewed 0; verified 0; drift 0; unverified 0.

## UNRESOLVED
- Re-run 3b and 4a/4c once to confirm the new Expected text (not re-run live in this pass).
