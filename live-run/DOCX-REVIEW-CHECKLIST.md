# Word-doc review checklist (2026-11-11)

Review the `.docx`, not just the `.md`. Fix at the source (`generators/content/<id>.py`, or the helper in `generators/`), then `cd generators && python render.py <ID>` and `python validate.py <ID>`. Never edit a `.docx` by hand. Never run `lab up/down/reset`. Do not read or print passwords. Append new allowed words to `generators/checks/allowlist.txt` only if the word is legitimate.

## How to inspect
- Text, tables, sections, images: `python-docx` (`import docx`). Image count: `len(doc.inline_shapes)`.
- Pictures of the pages: export with Word, then view with PyMuPDF (`import fitz`):
  `powershell -c "$w=New-Object -ComObject Word.Application;$d=$w.Documents.Open('<abs path>',$false,$true);$d.ExportAsFixedFormat('<abs pdf in scratchpad>',17);$d.Close($false);$w.Quit()"`
  Then render each page to PNG and look at it with Read. Close Word when done. If the file is open in Word, report it and skip it.

## A. Page and layout
| # | Check |
|---|---|
| A1 | Page orientation fits the content (landscape if any table is wide) |
| A2 | Every table fits the page: landscape width at most 13680 twips (9.50 in); portrait at most the text width. No cell text cut off at the right edge |
| A3 | No table row split in a way that hides the header row; header rows repeat or sit on one page |
| A4 | No heading stranded at the bottom of a page; no blank page; no page with only one line |
| A5 | Code blocks do not run off the page; long lines wrap or are short enough to read |
| A6 | Fonts are consistent (body, headings, code in a monospace font); no stray colours |
| A7 | Collapsed sections ("Command List", "Terms") are present and usable if the module has them |

## B. Screenshots and diagrams
| # | Check |
|---|---|
| B1 | Every picture shows: opens, is sharp, is not stretched, is not wider than the page |
| B2 | Each picture sits under the step it shows, with a caption or alt text that names that step |
| B3 | The picture content matches the expected output printed in the step (same command, same result) |
| B4 | Nothing sensitive in any picture: no email, user name, account ID, lab domain, token, password, secret |
| B5 | Diagrams show: icons render, labels readable, key row present, no overlapping boxes |
| B6 | Image count in the docx equals the image count the `.md` references |

## C. Structure and wording
| # | Check |
|---|---|
| C1 | Sections run "Section 1. Module Overview" onward with no skipped or repeated number |
| C2 | Title, "Module N of 29" and the "Next module" line are right for this module (`generators/order.py`) |
| C3 | At most 5 steps; each step has a stated time; the total time is stated |
| C4 | Every step has: what you do, the command, what you should see, what it proves |
| C5 | Tests/negative tests present where the module defines them |
| C6 | Plain language: no unexplained jargon, no filler sentences, no "type this in the lab shell" lines |
| C7 | No leftover markdown marks in the docx (`**`, backticks, `##`, `|---|`, `<br>`, `&nbsp;`) |
| C8 | No placeholder text (TODO, TBD, XXX, lorem, `<...>` not meant as a variable) |
| C9 | Numbered lists restart correctly; bullets render as bullets |
| C10 | Hyperlinks work and point to the right tool or doc; no raw long URLs breaking layout |

## D. Content accuracy
| # | Check |
|---|---|
| D1 | Commands in the docx equal the commands in the `.md` and the live capture (`live-run/captures/<ID>/`) |
| D2 | Expected output matches the capture apart from values that change (names, times, IDs) |
| D3 | Control IDs are Rev 5 format (AC-2, IA-5(f)); control names match NIST 800-53 Rev 5; no US-CERT (use CISA) |
| D4 | No prescribed interval where Rev 5 says organization-defined; FedRAMP values only where the vault assigns them (`<rmf-vault>`, Wiki then Sources, read-only) |
| D5 | Tool names, versions and flags are right for the tool as used in the lab |
| D6 | Cost and time numbers are labelled as estimates unless measured |
| D7 | No lab domain, email, account ID or secret in the text |

## Report format
Per document: PASS / FAIL per row (only list FAILs with page or heading), what you fixed, what you could not fix. Finish with one line: `fixed N, open M`.
