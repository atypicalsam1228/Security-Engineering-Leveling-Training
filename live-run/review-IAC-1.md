# Review IAC-1 (final pass 2026-11-11)

## Checklist
- [x] A. Accuracy: live run 2026-11-10 proved commands; draft updated to match
- [x] B. Coherency: start state, next line, step cross-references and screenshot alt text checked against order.py
- [x] C. Brief compliance: no lab domain, email, account ID or secret; validate.py 0 errors, 0 warnings
- [x] D. Compliance claims checked against Sources/FedRAMP and NIST text
- [x] E. render.py succeeded

## Findings
| Finding | Severity | Fix |
| --- | --- | --- |
| CM-2 frequency said org-defined; FedRAMP assigns at least annually and when a significant change occurs | DRIFT, MEDIUM | Added with FedRAMP cites; source NIST; FedRAMP |
| CM-6 omitted FedRAMP requirement for DoD STIGs then CIS Level 2 | DRIFT, MEDIUM | Added with cites |
| Stale draft; 'colour' spelling | LOW | Rewritten, changed to color |

## Vault review report
Claims reviewed: 7. Verified: 5. DRIFT (corrected): 2. UNVERIFIED: 0.

## UNRESOLVED
- Module does not run the annual review (stated)
- Baseline is a lab example, not a STIG or CIS configuration (stated)
