# Review ENG-0 (final pass 2026-11-11)

Checked: coherence (order.py: ENG-0 is 1 of 29, ENG-1 follows; ENG-1 prereq is ENG-0), health-check.sh line ranges vs 4a capture (all match), step cross-references (3b/3c, 4b), screenshot alts match their steps, no lab domain/email/account ID/secret (only you@example.com and example.invalid placeholders).

| Finding | Severity | Fix |
| --- | --- | --- |
| "next" named GRC-2; order puts ENG-1 next | medium | Rewritten to point to ENG-1 |
| 3a: live run shows a "Defaulted container" line first | low | Added note to expected output |
| validate warnings "eval", "repos" | low | Appended to checks/allowlist.txt |
| 4b fails live (Trivy operator OOMKilled, 512Mi limit) | lab bug | Not a module fault; module text correct |

Vault review: module has no controls, agency names or parameters. Claims reviewed 0; verified 0; drift 0; unverified 0. Cost figures ($18, $0.77/h) are marked estimates and traced to ARCHITECTURE-DECISIONS.md (author estimate, unmeasured).

UNRESOLVED: raise Trivy operator memory limit in lab build and re-run 4b on an idle lab; 2a sandbox repo has 4 commits (module already says longer list); start script prints INCOMPLETE; $18/$0.77 figures unmeasured.
