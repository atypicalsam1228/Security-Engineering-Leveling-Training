# Review IAC-2 (final pass 2026-11-11)

## Checklist
- [x] A. Accuracy: live run 2026-11-10 proved commands; draft updated to match
- [x] B. Coherency: start state, next line, step cross-references and screenshot alt text checked against order.py
- [x] C. Brief compliance: no lab domain, email, account ID or secret; validate.py 0 errors, 0 warnings
- [x] D. Compliance claims checked against Sources/FedRAMP and NIST text
- [x] E. render.py succeeded

## Findings
| Finding | Severity | Fix |
| --- | --- | --- |
| CM-2 frequency org-defined; FedRAMP assigns value | DRIFT, MEDIUM | Fixed with cites |
| CM-6 said values are org-defined and lab chooses; FedRAMP requires STIGs then CIS Level 2 | DRIFT, MEDIUM | Reworded, cites added |
| Stale draft | LOW | Rewritten |

## Vault review report
Claims reviewed: 7. Verified: 5. DRIFT (corrected): 2. UNVERIFIED: 0.

## UNRESOLVED
- Terraform not in cluster; gate checks committed plan.json (stated)
