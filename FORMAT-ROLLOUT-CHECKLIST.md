# Learner-format rollout checklist

Pilot: GRC-2 (done, owner comments applied). The rest follow the same format. A module is done only when all columns are ticked.

## The changes (what every module gets)

| # | Change | Where it shows | Applies to |
|---|---|---|---|
| 1 | Hover definitions for technical words in "Why This Matters" (pod, cluster, and so on) | Underlined words | All (done by the renderer) |
| 2 | Row label "Control Intent" replaces "What the control author feared" | Intent table | All (done by the renderer) |
| 3 | A line above each text picture: "This is a picture. It is not a command" | Concept sections with a text diagram | All (done by the renderer) |
| 4 | Control mapping table: "Source of the value" becomes "Tool or service"; "Where this module covers it" names the sections | Section 1 | Modules with controls |
| 5 | Steps split into lettered parts (1a, 1b ...), each with a lead line saying what the learner is about to do and where to type it | Section 3 | All |
| 6 | Expected output under each command, marked "Example only" (file bodies the learner only reads are exempt) | Section 3 | All |
| 7 | Fetched or supplied files: a "Look for these as you read" list (what to look for and what it means) | Section 3 | Where a file is only read |
| 8 | Control tags in titles, plain text, no highlight, for example "(CA-7 Continuous Monitoring)"; several controls are listed together | Concept, step and test titles | Modules with controls |
| 9 | First time a control appears: its title and an italic description, no more than 4 sentences, checked against the vault | Concept sections | Modules with controls |
| 10 | After that: a "How this meets the control" note at the bottom of the step or test: what the control asks, what the learner does here, what it produces (no more than 4 sentences, italic) | Steps and tests | Modules with controls |
| 11 | "What Each Control Is For" moves to the end (before the glossary), five rows per control instead of seven | Section 5 or 6 | Modules with controls |

## Gates (all must pass)

- [x] `python validate.py --all`: 0 errors, 0 warnings (the validator now enforces changes 4 to 6 and 8 to 11)
- [x] `python accuracy_auto.py` passes (Engineering)
- [x] Control wording checked against the vault by an independent reviewer (about 380 claims in IL5 and 480 in Engineering; drift and unverified items fixed, listed below)
- [x] Word check by script on every file: no highlight, no comments left, hover links work, headings in order, italic control text, lettered parts with lead line and code, notes at most 4 sentences
- [ ] Owner opened the Word file

## Modules

| Module | Content written | Validator 0/0 | Word check | Owner opened |
|---|---|---|---|---|
| AID-2 | [x] | [x] | [x] | [ ] |
| AID-3 | [x] | [x] | [x] | [ ] |
| AID-4 | [x] | [x] | [x] | [ ] |
| AID-5 | [x] | [x] | [x] | [ ] |
| ARC-2 | [x] | [x] | [x] | [ ] |
| ARC-3 | [x] | [x] | [x] | [ ] |
| ARC-4 | [x] | [x] | [x] | [ ] |
| ARC-5 | [x] | [x] | [x] | [ ] |
| CPS-2 | [x] | [x] | [x] | [ ] |
| CPS-3 | [x] | [x] | [x] | [ ] |
| CPS-4 | [x] | [x] | [x] | [ ] |
| CPS-5 | [x] | [x] | [x] | [ ] |
| ENG-0 | [x] | [x] | [x] | [ ] |
| ENG-1 | [x] | [x] | [x] | [ ] |
| GRC-2 (pilot) | [x] | [x] | [x] | [ ] |
| GRC-3 | [x] | [x] | [x] | [ ] |
| GRC-4 | [x] | [x] | [x] | [ ] |
| GRC-5 | [x] | [x] | [x] | [ ] |
| SDR-2 | [x] | [x] | [x] | [ ] |
| SDR-3 | [x] | [x] | [x] | [ ] |
| SDR-4 | [x] | [x] | [x] | [ ] |
| SDR-5 | [x] | [x] | [x] | [ ] |
| VM-2 | [x] | [x] | [x] | [ ] |
| VM-3 | [x] | [x] | [x] | [ ] |
| VM-4 | [x] | [x] | [x] | [ ] |
| VM-5 | [x] | [x] | [x] | [ ] |

## Not done

- Page-image check in Word: sampled, not complete. GRC-2 pages were exported through Word and viewed (lettered parts, expected output, picture caption, control descriptions, notes, end section). Remaining modules were checked from the .docx file contents only. Open each file in Word and tick the last column.
- The expected output in each step is example-shaped and marked "Example only". None of it was captured from a live cluster.
