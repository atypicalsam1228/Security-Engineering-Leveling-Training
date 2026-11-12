# Accuracy Check

What to verify on every module (25 modules) and how. Extends `REVIEW-CHECKLIST.md`; run it as a whole before a release. Each item has an id so a report can cite it. Method: AUTO = a script I can rerun, VAULT = checked against the framework text with `/rmf-vault review` (Wiki first, then Sources), DOCS = checked against vendor documentation, READ = a person or agent reads the module against the live files.

## 1. Framework claims (VAULT)

| Id | Check |
|---|---|
| F1 | Every control ID cited exists in NIST SP 800-53 Rev 5 and its title is right. Rev 5 wording only (no Rev 3 or Rev 4 terms). |
| F2 | Every quoted sentence in a `cite` entry appears exactly in the named source file, and the label (NIST, FedRAMP) matches the file's folder. (AUTO also runs this in `validate.py`.) |
| F3 | Every parameter stated in prose or in the "what it requires" column (a time, a count, a threshold, an owner) is in the cited text. Values the framework leaves organization-defined are said to be the lab's choice, never attributed to a framework. |
| F4 | Where FedRAMP assigns a value, the module uses that value, not the NIST placeholder. |
| F5 | Only hard requirements are presented as requirements. Practice advice is worded as practice. |
| F6 | The mapping row, the investigation answers and the steps agree: nothing mapped but not taught, nothing taught but not mapped. |
| F7 | The agency name is CISA (not US-CERT) wherever an agency is named; no real organization, program or internal document is named. |

## 2. Technical claims (DOCS)

| Id | Check |
|---|---|
| T1 | Every command, subcommand and flag exists in the vendor documentation for the pinned version (`LAB-CONTRACT.md`: OpenShift 4.22, Kyverno 1.19.2, Grafana 13.2.4, Trivy 0.76.1, Cosign 3.1.4, and so on). |
| T2 | Every YAML kind, apiVersion and field exists in that version. Anything unconfirmed has a validation command before the apply and a line in the module's `draft` text. |
| T3 | Every API path and payload (Loki, Grafana, Gitea, Mattermost, Tekton, Keycloak) matches the product's documentation. |
| T4 | Every container image reference exists and is pinned (tag or digest, never `latest`, except a labeled negative case). |
| T5 | The "expect" output blocks match what the command prints (shape and wording). Counts that depend on a changing database are described, not fixed. |
| T6 | The positive test passes and the negative test fails for the reason the text gives. |
| T7 | Code written for the tools image runs on its Python 3.9 and its listed tools only. |

## 3. Consistency (AUTO and READ)

| Id | Check |
|---|---|
| C1 | `validate.py` shows 0 errors and 0 warnings for each module. (AUTO) |
| C2 | Titles, controls and minutes in `ENGINEERING-TRACK.md` match the module files. (AUTO) |
| C3 | Every prerequisite names a real module that comes earlier in the order, or is clearly background. Every `next` line names the right following module. (AUTO and READ) |
| C4 | Every module has a start state folder with `README.md` and `TODO.md`; `lab.start` names the right id; every `lab.env` variable is in `LAB-CONTRACT.md`. (AUTO) |
| C5 | Every `lab_needs` item is listed in the module's `TODO.md`. (AUTO, `test_state_files.py`) |
| C6 | Each step has why, code, line table, action and checkpoint, at most 5 steps; timed work is within 90 minutes (target 75). (AUTO) |
| C7 | Each diagram matches its steps: every node and arrow in the diagram appears in the step text, and nothing in the steps is missing from the diagram. (READ) |
| C8 | Terms and glossary entries are used in the text. (AUTO) |

## 4. Format (AUTO)

| Id | Check |
|---|---|
| X1 | ASCII only in module text and code. |
| X2 | Banned words and names absent from the whole project (validator list and the private name map), including start states, briefs and the overview. |
| X3 | Every `.docx` is portrait or landscape to match its widest table, and every table fits the page width. |
| X4 | Control IDs in the rendered files use the `AC-2` and `IA-5(f)` form. |
| X5 | The `.md` and `.docx` for a module come from the current content file (re-render and compare). |

## 5. Result log

Findings are written to a reviews folder kept outside the project, one file per group of modules, with the verdict for each id above (VERIFIED, DRIFT with the fix applied, or UNVERIFIED with what is needed). A summary is in `SUMMARY.md` in that folder.
