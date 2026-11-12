# Module Build Brief

You are writing training modules for the engineering leveling track. Read this brief, `ENG-BUILD-BRIEF.md`, `LAB-CONTRACT.md`, and a finished example such as `generators/content/grc_2.py` before writing.

## Audience and goal

Security engineers at the start of their technical path, with little keyboard experience. They learn to implement and check the security tooling a regulated system needs. Each module teaches one skill end to end.

## What a module contains (the schema in grc_2.py)

1. Intent first: a plain requirement paragraph, a control mapping table, and the investigation questions already answered for each control (author feared, scope, operational question, evidence, sufficient, tie-off, how this module's tool satisfies it). These are reading, not work.
2. Terms table, then concepts: what the tool is, why we use it, how it works. Keep it short.
3. Implement: at most 5 steps. Each step has why, code blocks each with a line-by-line table, an action, a checkpoint. Optional note, security, tip callouts.
4. Verify: at least one positive and one negative test with expected output. The negative test breaks something on purpose and shows the failure.
5. Glossary and a next line.

Timed work is hands-on plus verify, 90 minutes at most (aim for 45 + 20). Reading is not timed.

## Rules from the user (all mandatory)

- No scenario, no fictional company, no real organization names, no meeting quotes.
- Never write the word "squishy". For the idea of weak internal protection say "perimeter-only protection" and ask "Is traffic protected only at the boundary, or also between internal components?"
- Define every technical term inline the first time it appears, in a short parenthetical or sentence, for example "internal components (the separate pieces inside the system that talk to each other, such as the web front end and the database)". Also fill `terms` and `glossary`.
- The learner writes no documents. Everything is a command, a config applied to the lab, or a check.
- Organization-defined parameters: the lab picks the value and says so ("the lab uses 15 days"). Never attribute a value, rule or quote to an internal document. Quotes in `cite` entries come only from framework documents: NIST in `Sources/NIST-800-53/nist-sp-800-53r5-full.md`, FedRAMP in `Sources/FedRAMP/`.
- Every number with a unit in prose (30 days, 15 minutes) must appear in a cited framework quote, or be listed in `unit_values_ok` when it is a value the lab chooses or a wait time. Where a framework leaves a parameter organization-defined, say so and say the lab chooses the value.
- Source labels in the mapping table: `NIST`, `FedRAMP` (combine with `;`). Every mapping row needs `cite` entries (file name plus an exact quote) from files that match the labels. The validator checks the quote exists.
- Free or low-cost tools only, from the lab contract. Use the tool list in LAB-CONTRACT.md. Do not debate stack choices.
- ASCII only. No smart quotes, no dashes other than a hyphen, no emoji. Use plain words.
- Commands must be real. Check flags and API versions against vendor documentation (use the context7 tools, or web search and fetch for Red Hat, Kyverno, Keycloak, Trivy and so on). Where you cannot confirm a field, add a validation command (`oc explain`, `--dry-run=server`, `--help`) before the apply and say so in the module's `draft` text. Learners only use variables from the lab contract; list the ones a module uses in `lab.env`.
- Commands the validator does not know are flagged. Check the command is real, then add it to `generators/checks/commands.txt`. Add legitimate technical words to `generators/checks/allowlist.txt` (one per line, lowercase).

## Files

- Write `generators/content/<id lower, hyphen to underscore>.py` defining `MODULE` (for example `grc_3.py`, `vm_2.py`).
- Validate: `cd "<project>/generators" && python validate.py <ID>`. Fix every error. Review every warning (spelling, unused terms) and fix real ones.
- Render: `python render.py <ID>`.
- Use forward slashes in bash commands. Use the Write and Edit tools for files.

## When you finish

Reply in under 200 words: files written, validator result, and a bullet list of anything unresolved (parameters the frameworks leave organization-defined, commands you could not confirm, lab needs).
