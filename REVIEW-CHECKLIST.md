# Module Review Checklist

Run this on every module after it is complete. A module is "reviewed" only when every box is checked or a finding is recorded and fixed. Record results in the review log for that module.

## A. Accuracy (commands and products)

- [ ] Every command, flag and subcommand exists in the current vendor docs (OpenShift 4.22 and the tool's own docs). Cite the doc URL for each non-obvious one.
- [ ] Every YAML kind, apiVersion and field is confirmed (`oc explain`, vendor reference, or a server dry run step before the apply).
- [ ] Operator names, channels, namespaces and CRD names match the operator catalog / docs.
- [ ] Version-specific behavior is stated for the lab's version, not assumed.
- [ ] Every command shown is in `checks/commands.txt`; new technical words are in `checks/allowlist.txt`.
- [ ] Expected output blocks match what the command really prints (shape and wording), not invented output.
- [ ] Anything not confirmable is marked in the `draft` text with the validation command that confirms it.

## B. Coherency (does it hold together)

- [ ] Start state: `lab start <id>` state matches the end state of the module before it in the order, or the module's `lab_needs` list says what it needs.
- [ ] Prerequisites are true and complete for the new order (nothing used before it is taught).
- [ ] Every term is defined at first use and appears in `terms` and `glossary`; no unused terms.
- [ ] Each step has why, code, line-by-line table, action, checkpoint; at most 5 steps.
- [ ] The positive test passes and the negative test fails for the reason the text says.
- [ ] The verify tests actually prove the mapped control, not a different one.
- [ ] The control mapping rows match what the steps do; nothing mapped but untaught, nothing taught but unmapped.
- [ ] Timed work is at most 90 minutes (aim 45 + 20) and is plausible for the steps.
- [ ] Environment variables used are in `lab.env` and in LAB-CONTRACT.md.
- [ ] `next` line names the next module in the order and says what it adds.
- [ ] The tool table lists exactly the module's tools, with working overview links.

## C. Brief compliance (BUILD-BRIEF.md)

- [ ] No scenario, no fictional or real company, no meeting quotes.
- [ ] The word "squishy" does not appear; perimeter-only protection wording used instead.
- [ ] The learner writes no document.
- [ ] No invented number, period or threshold; every number with a unit traces to a cite or `unit_values_ok`.
- [ ] Source labels in the mapping table are only NIST and FedRAMP and match the cited file.
- [ ] ASCII only; no smart quotes, no emoji, no dashes other than a hyphen.
- [ ] Free or low-cost tools from the lab contract only.
- [ ] `python validate.py <ID>` shows 0 errors and 0 warnings.

## D. Compliance claims (/rmf-vault review)

- [ ] Every control ID, parameter, timeframe, agency name and process owner is checked against the vault (Wiki first, Sources if no Wiki hit).
- [ ] DRIFT items corrected in the module.
- [ ] UNVERIFIED items flagged or removed.
- [ ] Source of each value is classified correctly (NIST text, FedRAMP value, or a value the lab chooses) before any gap is flagged.
- [ ] Only hard requirements are cited; no best practice presented as a requirement.

## E. Final

- [ ] `python render.py <ID>` succeeds; `.docx` opens and the tool table links work.
- [ ] Review file written to the review log for that module with findings, fixes and anything left unresolved.
