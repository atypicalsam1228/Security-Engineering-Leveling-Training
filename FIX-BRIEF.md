# Prerequisite-gap fix brief

Applies to every module except ENG-0 (already fixed; use it as the pattern). Read `BUILD-BRIEF.md` and `ENG-BUILD-BRIEF.md` for the schema and rules, `LAB-CONTRACT.md` for variables, and `generators/content/eng_0.py` for the finished style.

## Who the learner is

A person on their own laptop (Mac or Windows) who downloaded the training folder, installed `lab`, and ran `lab up`. They know only what the module and ENG-0 have told them. They have no editor, no browser logins, no instructor.

## What the shared tools now do (do not repeat it in your module)

- `lab` is installed on the laptop only. The renderer already prints, above Step 1 of every module: where `lab start` and `lab reset` are typed (laptop terminal, not lab shell), and "if a step fails: `lab reset <id>`, repeat once, then copy the error to your AI assistant". Do not add your own copies of these.
- `~` and `$HOME` inside lab shell are now persistent (they live in the learner's lab-workspace folder). Files under `~` survive closing lab shell. `$HOME` paths in start states and steps are therefore correct; leave them. Start-state scripts run with the same HOME.
- Verify tests now require a `lines` table (same shape as step blocks: `(part, what it does, why)` or `(part, what it does)`), rendered under the code and expected output. The validator errors without it.
- The validator ignores the body of a heredoc (`cat > f <<'EOF' ... EOF`) when it checks commands and variables.
- `terraform`, `ansible-playbook`, `ansible-lint`, `ansible-galaxy` are in the lab image.

## Fix every item below in your modules (edit `generators/content/<id>.py`; never hand-edit `modules/`)

1. **Creating files.** Anywhere a step says "paste into a file", "save as", "create a file" or similar, give the whole file as a heredoc block: `cat > NAME <<'EOF'` ... `EOF` (quoted EOF so `$` stays literal). Put `cd` to the working folder first. No editor exists. If the text needs a real `$` expanded, say so. Keep each file at most about 30 lines; explain it line by line in `lines`. Check for tabs: YAML and Makefile-free text only, spaces only.
2. **Working folder.** Every block that uses a relative file starts with `cd <folder>` (including every verify block). The first block that needs a folder creates it (`mkdir -p`). Never assume the learner is still where the last step left them.
3. **Variables across steps.** If a block uses a variable another block set (`IP`, `POD`, ...), set it again in that block, or have it read the value again. Each block must run alone after `lab start`.
4. **Browser steps.** Do not send the learner to a web page that needs a login. Replace with a command that prints the same fact (curl to the API with the token header, `oc get route`, `oc logs`). If a page is genuinely needed, print its address with a command and tell them the login comes from the variable name; never ask them to print a password or token.
5. **Images the pipeline pulls.** Nothing builds `tools/lab-shell:lab`, `tools/trivy:lab` or `tools/python-test:lab`. Use public, version-pinned images from vendor registries instead, and record the image and tag in `lab_needs`:
   - Trivy: `ghcr.io/aquasecurity/trivy:0.76.1`
   - Python tests: `registry.access.redhat.com/ubi9/python-312` (check the tag exists)
   - Terraform: `docker.io/hashicorp/terraform:1.17.0` is not pull-safe from the cluster (rate limits); prefer running Terraform in lab shell and checking the committed plan.json in the pipeline, as IAC-2 already does, and use the python image for the gate
   Never use `REGISTRY_HOST` for an image that nothing pushes. If a pipeline step needs only python3 and curl, use the python-312 image.
6. **Git against Gitea in a module other than ENG-0.** The first git block must include the credential helper and identity, copied from ENG-0 step 2 (`-c credential.helper=...` for clone, `git config credential.helper`, `user.name`, `user.email`). Do not assume ENG-0 ran.
7. **Infrastructure the module assumes.** For each service the module touches (Gitea, Grafana, Loki, Mattermost, Tekton, Kyverno, Trivy operator, Falco, the `alloy` collector): confirm that the start state or the lab contract provides it. If the start state can create it with `oc`/curl, add it to the start state (follow `lab/states/<id>/`; keep the existing test rules in `lab/tests/test_state_files.py`). If only the lab build can provide it, list it in `lab_needs` and `lab/states/<id>/TODO.md` (numbered as the tests require). SDR-5 needs a Mattermost team `lab`, a channel and a token; SDR-4 needs the `alloy` Deployment. Do not add anything to `LAB-CONTRACT.md`.
8. **Internet.** If a step downloads from outside (Trivy database, CISA KEV, EPSS feeds, package indexes, container registries), say so in the step intro, in one line: "This step needs the lab shell to reach the internet." and list it in `lab_needs`.
9. **Prerequisites.** `prereq` lists only modules whose content the learner must already know, each with a short phrase of what they need from it. Remove modules the module does not lean on. If the module leans on earlier knowledge (for example how to start a pipeline, port-forward), either teach it in one block where first used or name the exact earlier step. Every module must still work alone after `lab start <id>`: any artifact an earlier module created must be created by this module's start state.
10. **Reruns and resets.** A step must be safe to run twice (use `--dry-run=client -o yaml | oc apply -f -`, `mkdir -p`, `|| true` where harmless). A start state must not delete the learner's work unexpectedly; if `lab start` or `lab reset` removes a work folder (for example `/workspace/iac-3`), say so in one sentence where the module mentions starting over, and never advise "run lab start again" for a failed step unless wiping is intended.
11. **"Tell the instructor" / "say so to the lab team" / similar.** Replace with: copy the whole command and error and ask your AI assistant.
12. **`next` line.** Format exactly: `Next module: <ID> <Title from the list below>: <one sentence>.` There must be a space after the id. For the last module of a dimension, say it is the last and point to one concrete other module. Check the title against the list below.
13. **Terms.** Every technical word the learner meets before it is explained goes into the module's `terms` (with a plain one-sentence meaning). At minimum check: token, webhook, secret, config map, pod, namespace, service account, RBAC, kubeconfig, oc, jq, tkn, Tekton, pipeline, task, Terraform and provider, plan, state, ARN, Loki, LogQL, Kyverno, Falco, Trivy, SBOM, CVE, KEV, EPSS, Mattermost, Gitea, Grafana, PromQL where they appear. A term used in a step must have an entry in `terms` (hover uses it) or be defined in the sentence where first used. Do not add terms the module never uses (the validator warns).
14. **Verify tests.** Add `lines` to every verify entry: one row per command or output line that matters, plain words, and why.
15. **Small bugs found by audit** are listed under your modules below. Also reread your module once for a step that says something the code does not do, an expected output no command prints, or a number that does not match.
16. **Mac.** Commands inside lab shell are the same on Mac and Windows. Only commands typed on the laptop (outside lab shell) differ; if your module has any, give the Mac line beside the PowerShell line.

## Do not

- Edit `render.py`, `validate.py`, `doc_builder.py`, `order.py`, `common_terms.py`, `checks/*`, `LAB-CONTRACT.md`, READMEs, `lab/labcli/*`, `lab/image/*`, or `terraform/`. If a change there is needed, say so in your report.
- Add best-practice padding, new learning goals, or new controls. Fix gaps only. Keep the minute totals (`minutes`) honest: if you add blocks, add the time.
- Regenerate a `.docx` that has Word comments. Before each render run: `python -c "import zipfile,sys;print('comments' in ' '.join(zipfile.ZipFile(sys.argv[1]).namelist()))" modules/<file>.docx`; if it prints True, do not render that module and report it.
- Mention "live cluster not run" caveats in your chat report.

## Finish

For each module: `cd generators && python validate.py <ID>` until 0 errors and 0 warnings (add genuinely valid new words to `checks/allowlist.txt` only if the word is a real tool or term; never allowlist a deliberate typo); then `python render.py <ID>`. If you changed anything in `lab/states/<id>/`, run `cd lab && python -m pytest tests -q` and make it pass. Final report under 200 words: modules done, items you could not fix and why, and anything you need changed in a shared file.

## Module titles (for the `next` lines)

ENG-0 Terminal, Git and Your Lab; ENG-1 How Traffic Moves; GRC-2 Run Evidence Collection; GRC-3 Automate Evidence Collection; GRC-4 Evidence in the Delivery Pipeline; GRC-5 Continuous Control Monitoring Design; VM-2 Scan and Hand Off; VM-3 Triage and Track Fixes; VM-4 Prioritize by Context and Validate; VM-5 Risk-Based Gate in Delivery; SDR-2 Triage an Alert by Runbook; SDR-3 Investigate and Tune; SDR-4 Build Detections and Pipelines; SDR-5 Detection as Code; CPS-2 Apply a Hardening Baseline; CPS-3 Least-Privilege Roles and Baselines; CPS-4 Secure a Workload End to End; CPS-5 Guardrails Developers Inherit; AID-2 Check AI-Written Scripts Before Running; AID-3 AI-Assisted Automation Under Review; AID-4 Build a Constrained Triage Agent; AID-5 Safe Adoption Pattern for Agents; ARC-2 Trace the Security Stack; ARC-3 Measure Before Choosing; ARC-4 Test Two Designs; ARC-5 Verify a Reference Architecture; IAC-1 Run a Supplied Baseline as Code; IAC-2 Deliver a Baseline as Code with Terraform; IAC-3 Terraform or Ansible: Choose by Evidence.

## Known issues by module

- ENG-1: copies its kit to `$HOME/net` (fine now); "paste into a file" steps; variables reused across steps; check the `next` line.
- GRC-2: where `lab start` runs (renderer covers); check terms (token, webhook).
- GRC-3: assumes git credential helper and identity; Gitea token and branch protection set-up; "paste into a file"; prereq lists GRC-2 (keep only if the module reads its output).
- GRC-4: prereq lists GRC-3 though not leaned on; Trivy database download needs internet; pipeline image.
- GRC-5: leans on earlier GRC content; state what it needs or add a start-state artifact.
- VM-2: terms; internet for the Trivy database.
- VM-3: "paste into a file"; terms.
- VM-4: Test 2 refers to Step 3 but means Step 4; variables reused across steps; KEV/EPSS feeds need internet; rerun fails.
- VM-5: images `tools/trivy:lab` and `tools/python-test:lab` are not built anywhere (use item 5); "paste into a file".
- SDR-2: Mattermost and Grafana web logins are not given (item 4).
- SDR-3: Grafana login; variable reuse across steps.
- SDR-4: needs the `alloy` Deployment; prereq claims ENG-0 teaches port-forward (it does not; teach it where first used); "paste into a file".
- SDR-5: needs a Mattermost team `lab`, a channel and a token; "paste into a file"; `next` line.
- CPS-2: `next` line missing the space after the id.
- CPS-3: prereq lists CPS-2 though not leaned on; "paste into a file"; `next` line.
- CPS-4: never creates its working folder; `$IP` reused across steps; leans on CPS-3; `next` line.
- CPS-5: never creates its working folder; "paste into a file"; vague `next` line.
- AID-2: Grafana/Mattermost login if used; `next` line; "tell the instructor".
- AID-3: reruns fail; "tell the instructor"; `next` line.
- AID-4: never creates its working folder; reruns fail; leans on AID-3; `next` line.
- AID-5: never creates its working folder; reruns fail; "tell the instructor"; `next` line.
- ARC-2: start state copies its kit to `$HOME/arc` (fine now); Test 3 expects a summary line that no command prints; "tell the instructor"; `next` line.
- ARC-3: prereq lists ARC-2 and ENG-0 beyond need; "tell the instructor"; `next` line.
- ARC-4: leans on ARC-2/3; `next` line.
- ARC-5: reruns fail; hash expectations; vague `next` line; check start-state `$HOME/arc`.
- IAC-1: the `next` line names IAC-2 with the wrong title (see list); reruns; terms (provider, state, plan).
- IAC-2: `lab/states/iac-2/30-gitea-repo.sh` lines 22 and 23 use `"openshift\.io/.*"` and `"pod-security\.kubernetes\.io/.*"` inside a Terraform string: a single backslash is an invalid HCL escape and `terraform init` fails. Use `[.]` as `lab/states/iac-3/kit/terraform/main.tf` does (`["openshift[.]io/.*"]`, `["pod-security[.]kubernetes[.]io/.*", "security[.]openshift[.]io/.*"]`) and fix the same text if it appears in the module. `tools/lab-shell:lab` image (item 5); "paste into a file"; git identity; `next` line names IAC-3 with the wrong title.
- IAC-3: its start state deletes `/workspace/iac-3`, so "start the step over" advice would wipe the learner's work (item 10); prereq lists modules it does not need; `ls -l` expectation lists `.terraform`, which `ls -l` does not show because it is a hidden folder.
