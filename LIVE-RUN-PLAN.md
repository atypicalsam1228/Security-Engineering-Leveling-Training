# Live run plan: run every module against the real lab

Goal: run each module step by step in the lab shell, record real timings, outputs and bugs, capture CLI output images, and find better integration chances between modules.

## Ground rules
- The user runs `lab up` (about 48 min, about $0.77/h) and says when it is up. Once the user gives the initial go-ahead, Claude does not ask again for `lab down`, `lab pause` or the AWS changes the modules call for.
- Screenshots: redacted PNGs go in `modules/img/` named `<ID>-shot-<step>-<what>.png` (AWS console pages end in `-aws`). Unredacted originals stay outside the project in a private folder (`<private-folder>/Screenshot-Originals/`), never committed.
- Claude follows the rendered module exactly as a learner would. No fixes while running; every problem goes in the findings log.
- Redact account IDs, tokens and hostnames before anything goes in a module.
- Use `lab keep` so the lab is not paused mid-run, and `lab down` when finished.

## Phase 0: before the run (no cost)
1. Run `python -m pytest lab/tests -q` and `python validate.py --all` once more to get a clean baseline.
2. Build the run order from `lab modules` (recommended order) and note each module's start state with `lab start <ID>`.
3. Collect the 160 or so `[live]` and `[lab-build]` items from `lab/states/*/TODO.md` into one checklist, so each is closed or confirmed as it is met.

## Phase 1: lab up and platform check (about 1 h)
1. `lab up`, then `lab platform`, then `lab status`.
2. Confirm the in-lab services answer: Gitea, Loki, Grafana, Mattermost, Kyverno, Tekton.
3. Time each stage and log any failure.

## Phase 2: run the modules in order
Order: ENG-0, ENG-1, GRC-2..5, VM-2..5, SDR-2..5, CPS-2..5, AID-2..5, ARC-2..5, IAC-1..3.

For every module:
1. `lab start <ID>`, then follow the module top to bottom in the lab shell, one command at a time.
2. Record per step: wall time, exit code, real output, and whether it matches the "Example only" output.
3. Record per test: pass or fail and the real result.
4. Capture each command's output as a terminal-style PNG for the `screenshot` key, redacted. Labeled as rendered from captured output.
5. Use `lab reset <ID>` and re-run a failed step once, as the module tells the learner to.
6. Close the module's `[live]` items in its TODO.md.
7. Write a findings entry: bugs (command fails, wrong expected output, wrong count), unclear wording, time estimates that are off, missing prerequisites.

Known items to confirm live: SDR-3 `lastError` field, Grafana and Mattermost routes (SDR-5, AID-5), project `siem` contents (Loki, `mm-api` secret), CPS-2 Step 5 empty-FAILED case, ARC-3 gate, IAC-3 drift check.

## Phase 3: browser screenshots (Claude in Chrome)
Tool screenshots, not only AWS: OpenShift console, Grafana, Keycloak, Gitea, Mattermost, Argo CD, Loki (through Grafana), Kyverno and Tekton pages in the OpenShift console, plus AWS console pages that a step names. For each module, capture the page each step or test says to look at, once the step has run so the page shows real data. The user connects Chrome first and signs in to AWS; tool logins use the lab's own credentials, which Claude never types into a page unless the user says so, and passwords are never shown in a capture.

## Phase 4: findings pass
1. Fix bugs in content, kit scripts and lab states; re-render; re-run the changed step to confirm.
2. Update time estimates in each module from the real timings.
3. Integration chances: look for places where one module's output feeds the next (for example GRC evidence into IAC drift checks, VM findings into the SDR alert path, ARC modes into CPS guardrails) and add "carry this forward" steps or links.
4. Re-run validate, render, tests and a checklist pass. Commit.

## Outputs
- `LIVE-RUN-FINDINGS.md`: one table per module (step, time, result, bug, fix).
- A timing table for the track overview.
- CLI output images in `modules/img/` plus browser screenshots.
- Updated modules and a commit.

## Cost control
- Batch modules into sessions so the lab is not idle; pause with `lab pause` between sessions.
- `lab down` at the end of each working day unless the user says otherwise.
