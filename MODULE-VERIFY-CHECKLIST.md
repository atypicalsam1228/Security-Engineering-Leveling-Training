# Module verification checklist (format of 2026-11-06)

Source of the rules: the 23 Word comments on GRC-2 (see `grc2_comments_2026-11-06.md` in memory), `lab-workspace/backups/rollout-20261106`, and the NIST wording rules in the rollout brief.
Batch 1 (this pass): AID-2, AID-3, AID-4, AID-5, ARC-2, ARC-3, ARC-4, ARC-5, CPS-2, CPS-3, CPS-4, CPS-5, ENG-1.
Batch 2 (not yet verified): ENG-0, GRC-2 to 5, IAC-1 to 3, SDR-2 to 5, VM-2 to 5.

Read the rendered `modules/<ID>-*.md`. Check the source `generators/content/<id>.py` only to find the cause of a failure. Do not edit anything. Report PASS / FAIL / N/A per item, with the line number or heading for every FAIL.

## A. Automated gates (run these first)

| # | Check | How |
|---|---|---|
| A1 | Validator shows 0 errors | `cd generators && python validate.py <ID>` (no `-I`) |
| A2 | `.md` is newer than the content `.py` and render.py (not stale) | compare file times |
| A3 | `.docx` exists and is newer than the `.md` minus a minute | compare file times |
| A4 | Section headings run "Section 1. Module Overview" to the last section, in order, with no repeated or skipped number | grep `^## ` |

## B. Structure and deletions

| # | Check |
|---|---|
| B1 | Section 1 is titled "Module Overview" |
| B2 | Section 1 has rows in this order: Skill, Tools, Security Function, then one "NIST <ID> <Name>" row per control |
| B3 | The Tools row names each tool and what it does |
| B4 | Security Function says something concrete (detects, blocks, proves). Generic wording ("improves security") is a FAIL |
| B5 | Each NIST row names the tool used for that control and what it does for it |
| B6 | Requirement is 3 or 4 short bullets: purpose, what you build, how you run it |
| B7 | No "How it secures the system" label, no lab-needs row, no architect text |
| B8 | No concept section that only defines a term ("What X is") |
| B9 | No ASCII picture and no "This is a picture. It is not a command" line |
| B10 | No sentence "Type these commands in the lab shell" or "Type this command in the lab shell" |
| B11 | No filler sentences that teach nothing (for example "Never run a script you have not read", "X does not decide ..."). List any you find |
| B12 | Control mapping table is near the end, not in Section 1 or 2 |
| B13 | Reference material sits at the end so the learner reaches Step 1 quickly |
| B14 | "Command List" and "Terms" sections are collapsed (if the module has them) |

## C. Wording and layout

| # | Check |
|---|---|
| C1 | Step intros start "You will now ..." (no "You are about to") |
| C2 | No paragraph longer than 3 lines outside code blocks and tables |
| C3 | Explanatory text is bullets, one fact per bullet |
| C4 | Every step has a learning point ("learn") that says what running it achieves and what function it provides, not a general rule |
| C5 | Every step has a takeaway of one sentence |
| C6 | Control text follows "The control asks the organization to ... This is done using:" then bullets, with tool names |
| C7 | "How this meets the control" notes are 1 or 2 short sentences and do not repeat an earlier section |
| C8 | Control tags are present on steps and tests that need them |
| C9 | No stale section references ("Explained in section 2.2") that point at a heading that no longer exists |
| C10 | No list that runs straight into a table without a lead line |

## D. Diagrams

| # | Check |
|---|---|
| D1 | Each diagram caption says it is the lab (test) setup and what production does differently |
| D2 | The reading lists the boxes as numbered bold lines "1. Name: what it is", in order, and every box in the picture appears |
| D3 | Every number or word in the reading or a step ("start", "arrow 3") exists in the picture |
| D4 | No step diagram that shows nothing new |
| D5 | Node titles start with a capital letter |

## E. Portability ("Using this in other environments")

| # | Check |
|---|---|
| E1 | The section is present (ARC-5 has none yet; mark FAIL) |
| E2 | 3 or 4 bullets plus a 4-column table: Check/part, In this lab, On other platforms, What you change |
| E3 | Lab-only values are named (URLs, namespaces, project names, tokens) |
| E4 | A platform equivalent you cannot confirm says "Replace the check" rather than a guess |

## F. Commands, tests and accuracy

| # | Check |
|---|---|
| F1 | Every step has its commands with an expected-output block marked as an example |
| F2 | The module still has a negative test (a case that must fail) and a deploy plus read-back step |
| F3 | Commands match the backup copy in `lab-workspace/backups/rollout-20261106/content/<id>.py` (diff the command lines; any change needs a reason) |
| F4 | NIST statements match the vault. Authoritative files: `Sources/NIST-800-53/nist-sp-800-53r5-full.md`, `Sources/FedRAMP/fedramp-moderate-baseline.md` |
| F5 | "Organization-defined" is used where NIST leaves the value open. FedRAMP values appear only if the baseline file assigns them. No invented frequencies |
| F6 | CISA, not US-CERT. Rev 5 control IDs |
| F7 | Technical scope only: no task that asks the learner to write documentation |

## Report format (per module, under 150 words)

`<ID>: PASS | FAIL (n items)`, then one line per FAIL: item number, location, what is wrong, the exact fix. Add `UNVERIFIED:` for any claim you could not check in the vault.
