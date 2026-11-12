# Review GRC-3 (final pass 2026-11-11)

## Sections
- [x] A Accuracy: skipped per brief (live runs proved commands).
- [x] B Coherency: previous module in order is IAC-1 (no start-state dependency; `lab start grc-3`). Next module GRC-4 matches the dimension convention used by GRC-2 and IAC-1 and GRC-4's title. Timings 49/24 unchanged. Screenshot alt matches step 4b.
- [x] C Brief rules: validate 0 errors, 0 warnings.
- [x] D Compliance claims (vault Sources, NIST SP 800-53 Rev 5 full text, FedRAMP High baseline).
- [x] E No lab domain, email, account ID or secret (placeholder `@example.invalid` only).

## Findings
| Finding | Severity | Fix |
| --- | --- | --- |
| Test 1 example listed lost+found first; real `ls -l` lists it last | Low | Reordered example |
| Test 1 delete message differed from live output | Low | Now `pod "evidence-view" deleted from build namespace` |
| CA-7 sufficiency note omitted FedRAMP High monthly configuration scan requirement | Low | Added parenthetical (verified in fedramp-high-baseline.md) |
| 3 spelling warnings (webhooks, workflows) | Low | Added to allowlist (append-only) |
| Repeat `lab start grc-3` keeps Gitea repo and local clone | Medium | Not a module text fix; see unresolved |

## Vault review report
Claims reviewed: 14 (CA-7, CM-3, CM-6, CM-6(1) text and 5 cited quotes; CM-7, CM-8, SI-7 names; CA-7 frequency org-defined; CM-6 wording). Verified 14. Drift 0. Unverified 0.
(Quotes wrap across lines in the source; text matches NIST Rev 5.)

## UNRESOLVED
- Lab: repeated `lab start grc-3` does not reset the Gitea repo or /workspace/grc-3/evidence-work (50-gitea-evidence-repo.sh / 55-supplied-files.sh should recreate/clear), or the module should say so.
- Real 15-minute scheduled run not observed live.
