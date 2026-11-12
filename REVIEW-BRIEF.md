# Reviewer Brief

You review one engineering leveling training module for accuracy, coherency and compliance claims, then fix real problems.

Project: <project> (use forward slashes in bash). Read first: REVIEW-CHECKLIST.md (sections A-E), BUILD-BRIEF.md (rules), LAB-CONTRACT.md (lab), generators/order.py (module sequence; the module before yours in the order is what your start state must follow), and your module file generators/content/<id lower, hyphen to underscore>.py. The rendered copy is in modules/.

## Method

A. Accuracy: verify commands, flags and YAML against CURRENT official docs (OpenShift 4.22 at docs.redhat.com, and each tool's own docs; use WebFetch/WebSearch, and context7 tools if available). Do not guess. Mark anything unconfirmable in the module's `draft` text with the validation command that confirms it.

B. Coherency: start state vs the previous module in order, prereqs, terms defined at first use, verify tests prove the mapped control, at most 5 steps, timing, lab.env vars vs LAB-CONTRACT.md.

C. Brief compliance: every BUILD-BRIEF rule.

D. Compliance claims: perform the /rmf-vault review procedure yourself. Vault: the compliance vault configured for /rmf-vault (Wiki/ first via Grep, then Sources/). Extract every control ID, parameter, timeframe, agency name, process owner and revision claim in the module. Classify each VERIFIED / DRIFT / UNVERIFIED. Correct DRIFT in the module; flag or remove UNVERIFIED. Watch for: "org-defined" where FedRAMP assigns a hard value, US-CERT (must be CISA), cross-control contamination, hardcoded implementation choices presented as requirements, IA-5(1) / 800-63B deprecations, arbitrary evidence windows. Before flagging a gap, check document type, responsible population and authoritative owner. Per BUILD-BRIEF, quote only framework documents and never attribute a value to an internal document. Never modify Sources or the vault.

## Fixes

Edit ONLY your module's content file, plus append-only additions to generators/checks/commands.txt and generators/checks/allowlist.txt (re-read right before editing, since other reviewers append concurrently; one entry per line, lowercase for allowlist). Never rewrite another module. ASCII only. After fixing run `cd generators && python validate.py <ID>` until 0 errors and 0 warnings, then `python render.py <ID>`.

## Output

Write the review log for that module: sections A-E with checked/unchecked boxes, a findings table (finding, severity, fix or why not), the vault review report (claims reviewed, verified, drift, unverified), and an UNRESOLVED list (live-lab tests needed, lab needs, decisions for the user). Reply in under 200 words: findings fixed, drift/unverified counts, unresolved list. Do not commit anything.
