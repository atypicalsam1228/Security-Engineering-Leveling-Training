# Security Engineering Leveling Training

A stand-alone, hands-on training that teaches the technical skills of a security engineer as the work grows from guided tasks to team-level design. Learners work on their own real OpenShift single-node cluster in AWS, run each exercise with real tools, then run a test that shows it works and a test that shows the failure when it is removed.

STATUS: DRAFT. All 29 modules are written, validated and rendered, and the lab command-line tool passes its unit tests. Nothing has been run against a live cluster or on AWS yet. Commands follow vendor documentation and are validated (`--dry-run=server`, `oc explain`, `--help`) before they are applied, but expect field-name corrections on the first live run.

`ENGINEERING-TRACK.md` (and `ENGINEERING-TRACK.docx`, the same content) is the learner overview: audience, goal, suggested order, and each module with its steps and tools. This README covers setup, the lab, cost, layout and the build tools.

See [MODULES.md](MODULES.md) for what each of the 29 modules covers and why.

## Before you start (checklist)

These are personal to you and are not in this repository. Have all of them before you run `lab up`.

- [ ] **AWS account you may spend in**, with credentials in your environment (for example `AWS_PROFILE`). Use a lab account, not production. A full run is about $18 (an estimate).
- [ ] **AWS permissions** to create VPCs, EC2, KMS, S3, IAM, SNS, budgets and Route 53 records.
- [ ] **EC2 quota** for the cluster instance (default `m6i.4xlarge`, 16 vCPU) in your region. A new account may need a Service Quotas increase for "Running On-Demand Standard instances".
- [ ] **Red Hat pull secret.** Sign in with a free Red Hat account, download it from the Red Hat console, and save it as a file in your lab workspace (for example `~/lab-workspace/pull-secret.json`). It is tied to you; do not share or commit it.
- [ ] **A public Route 53 hosted zone** in the same AWS account, for a domain you own (or a subdomain delegated to Route 53). A domain costs money and DNS delegation can take time, so set this up first.
- [ ] **Python 3.10 or newer** and **podman or docker**. On Windows, use PowerShell or Windows Terminal, not Git Bash.
- [ ] **Terraform variables** `TF_VAR_lab_id`, `TF_VAR_region`, `TF_VAR_destroy_after`, `TF_VAR_alert_email` (see `terraform/README.md`). To use `terraform/bastion/provision-learner.ps1`, also set `LAB_ALERT_EMAIL`, `LAB_BASE_DOMAIN` and `LAB_AWS_ACCOUNT_ID`.

## 1. Setup

### Requirements
- A laptop (Mac or Windows) with Python 3.10 or newer and podman or docker. On Windows, run `lab` from PowerShell or Windows Terminal, not Git Bash (`lab shell` needs a real terminal), and keep the workspace (`LAB_WORKSPACE`, default `~/lab-workspace`) on a local folder, not one synced by OneDrive.
- An AWS account you may spend in, with your credentials in the normal environment (for example `AWS_PROFILE`). Use a lab account, not a production one.
- A Red Hat pull secret for OpenShift, saved as a file inside your lab workspace (for example `~/lab-workspace/pull-secret.json`). `lab up` refuses to start without it, and never prints it or puts it in git.
- A base domain hosted in Route 53 in the same AWS account: a public hosted zone. If the account has exactly one public zone, `lab up` uses it; otherwise set `BASE_DOMAIN`. The cluster gets the name `<cluster_name>.<base domain>`.
- A budget. The estimate is about $18 per learner for a full run; it is an estimate, not a quote. The lab sets a budget alarm and a destroy-after date.

### Steps
0. Download the training folder to your computer and unzip it if it came as a zip. The folder that contains `lab/`, `modules/` and this README is the one you work from; open PowerShell or Terminal in it.
1. Build the tools container: `python lab/lab.py build-image` (see `lab/image/README.md`). Or install the tool with `pip install -e ./lab` and run `lab build-image`.
2. Set the lab variables Terraform needs (`TF_VAR_lab_id`, `TF_VAR_region`, `TF_VAR_destroy_after`, `TF_VAR_alert_email`; see `terraform/README.md`), and the install inputs: `PULL_SECRET_FILE` (path to your pull secret, under the workspace; required), `BASE_DOMAIN` (optional), `SSH_PUBLIC_KEY_FILE` (optional, under the workspace; a fresh key is made otherwise).
3. `lab up` builds your lab in AWS and installs the cluster. It costs money and asks you to type `yes`. The whole run takes roughly one to one and a half hours, an estimate (the cluster install is about 45 to 70 minutes of that). `lab up --skip-cluster` builds the AWS infrastructure only.
4. `lab modules` lists the 29 modules. `lab start eng-0`, then open `modules/ENG-0-Foundation.md` (or the `.docx`), then ENG-1.
5. `lab down` destroys the lab. Run it every time you stop.

### The lab command
All hands-on work goes through one tool, `lab` (see `lab/README.md`). Every command that changes something accepts `--dry-run`.

| Command | What it does |
|---|---|
| `lab modules` | List modules in the recommended order |
| `lab build-image` | Build the tools container (oc, kubectl, jq, curl, git, openssl, terraform, aws, python3, cosign, trivy, tkn, argocd, session-manager-plugin) |
| `lab up` | Build your lab in AWS with Terraform, then install the cluster (`--skip-cluster` stops after the infrastructure). Costs money |
| `lab platform` | Install Gitea, Mattermost, Keycloak, Loki, Grafana, Kyverno, Trivy, Falco and the pipeline and GitOps operators on a running lab. `lab up` runs it for you; run it again if it stopped part way (safe to repeat). `--only NN` runs one script |
| `lab shell` | Open the tools container with your workspace and lab variables. Run the commands inside the module steps in it. Type `lab` commands themselves (`lab up`, `lab start`, `lab reset`, `lab down`) on your own computer, not inside it |
| `lab start <module>` | Load the module's starting state (example: `lab start grc-3`) |
| `lab break <module> <fault>` | Apply a named, common operational fault to practice spotting it (`--list` shows the choices, `--all` applies every fault). Optional practice. Only modules with a "Break It and Watch" section have faults |
| `lab restore <module> <fault>` | Undo a fault (`--all` undoes every fault in the module) |
| `lab reset <module>` | Return the module to its starting state |
| `lab keep`, `lab pause`, `lab resume`, `lab pull` | Cost-guard commands; see `COST-CONTROLS.md` |
| `lab status` | Show engine, workspace, which modules are applied, and any fault still active |
| `lab down` | Destroy the cluster (via the bastion), then the AWS infrastructure. Run it every time you stop |

### Working a module
1. Read **Why This Matters**: the requirement in plain words, the control mapping table, and the investigation questions already answered for each control. This is reading and is not timed.
2. Read **The Tools** (what each tool is, why it is used, how the pieces fit together) and, where present, **Design decisions**.
3. Do **Implement**: at most five steps. Each step gives the reason, commands with a line-by-line table, an action and a checkpoint.
4. Do **Verify**: at least one positive and one negative test. Run each command and compare what you see with the expected output shown; nothing is graded for you.
5. Optional: if the module has a **Break It and Watch** section, you may apply a fault with `lab break`, follow the detection path, then `lab restore`. Skipping it costs nothing, and nothing later depends on it.

Timed work is 50 to 75 minutes per module (hands-on plus verify). Start any module alone with `lab start <id>`; each start state builds everything the module needs.

### Two modes
- **Ready Lab**: prebuilt starting state; you implement the module's steps.
- **Architect**: each module has a brief; you design and build it yourself, then run the same checks.

### First run: measure the cluster size
The cluster instance (`instance_type`, default `m6i.4xlarge`) is a placeholder and has never been measured. On your first full run, measure it and set the size from what you see. This is the largest hourly charge, so it is worth doing once.

1. After `lab up` finishes and before any module, run inside `lab shell`: `oc adm top node` and `oc describe node | grep -A8 "Allocated resources"`. Write down the CPU and memory used.
2. Work the heaviest modules (the SDR and CPS modules), then repeat both commands. Also run `oc get pods -A --field-selector=status.phase=Pending`.
3. Read the result:
   - Any pod stuck Pending with an insufficient cpu or memory event: the node is too small. Raise `instance_type`.
   - CPU and memory both under about half of the node at the heaviest point: the node is larger than needed. Lower `instance_type` one size (for example `m6i.2xlarge`) on the next run.
4. `instance_type` must match `install-config.yaml` (see `terraform/README.md`). Record the size you settled on in `terraform/README.md` under cost notes, with the date.

## 2. Cost controls

A forgotten lab keeps billing. The optional cost guard (see `COST-CONTROLS.md`) warns an idle learner, saves lab files and pauses the lab after 2 idle hours (about $0.35 a day while paused, an estimate), destroys it after 7 paused days or when its spend limit is crossed, and ships with `dry_run` on so it only emails until an operator turns it off.

- `lab down` is the way to stop all billing at once. Closing the laptop does not stop AWS billing. Afterwards confirm in the AWS console that nothing tagged with your lab id remains.
- `lab keep [HOURS]` tells the guard you are still working; `lab pause` and `lab resume` pause and bring back the lab; `lab pull` copies the newest save to your computer.
- Compliance-locked log objects cannot be deleted before their retention ends (1 day by default).
- Nothing here has run on AWS. All figures are estimates.

## 3. Repository layout

| Path | What it holds |
|---|---|
| `modules/` | Rendered modules (`.docx`, `.md`) and `img/` diagrams: one main diagram and one image per step |
| `generators/` | Module content (`content/<id>.py`), the renderer (`render.py`), the validator (`validate.py`), the scripted accuracy checks (`accuracy_auto.py`), the document builder (`doc_builder.py`), the diagram system (`module_diagrams.py`), tool links (`tool_links.py`) and the module order (`order.py`) |
| `lab/` | The `lab` command-line tool, tests, tools image and per-module start states (`lab/states/<id>/`) |
| `terraform/` | Lab infrastructure for one learner, a sweeper for expired labs, a cost guard (`terraform/guard/`), and scripts. Read `terraform/README.md` before applying anything |
| `ENGINEERING-TRACK.md`, `ENGINEERING-TRACK.docx` | Learner overview: goal, suggested order, modules by phase (built by `generators/track_overview_doc.py`) |
| `ENG-BUILD-BRIEF.md`, `BUILD-BRIEF.md` | The module schema and writing rules |
| `COST-CONTROLS.md` | How idle labs are warned, saved and paused, then destroyed; the spend limit |
| `ARCHITECTURE-DECISIONS.md` | Lab-level architecture decisions with reasons, alternatives and weak points to revisit |
| `TOOL-REFERENCE.md`, `tool-reference/` | Vendor best practices and guidance for every tool, with sources |
| `LAB-CONTRACT.md` | What every module may assume about the lab: namespaces, tools, pinned versions, environment variables |
| `ACCURACY-CHECK.md` | The accuracy checks and which are scripted |
| `DIAGRAM-CHECKLIST.md` | Rules every diagram must pass |
| `REVIEW-BRIEF.md`, `REVIEW-CHECKLIST.md` | How modules are reviewed |

## 4. Rendering and validating the content

From `generators/`:

    python validate.py --all     # citations, ASCII, banned words, commands, variables (takes a few minutes)
    python accuracy_auto.py      # scripted accuracy checks
    python render.py --all       # writes modules/*.docx, *.md and img/*.png
    python render.py GRC-2       # render one module (with no arguments nothing is rendered)

The validator checks every cited quotation against the framework source text, so the NIST and FedRAMP documents must be available locally; without them the citation checks cannot run (the validator warns). Optional private checks (real-name scan, internal source folders) read a JSON map kept outside the project: set `ENG_SOURCE_MAP`, or use `~/.eng-training/source_map.json`. `ENG_PUBLIC_SOURCES` adds more source folders. Diagrams need Graphviz.

From `lab/`: `python -m pytest -q`. From `terraform/guard/`: `python -m pytest -q tests`.

## 5. Rules the content follows

- Citations come only from NIST and FedRAMP. No real organization, program or internal document is named or quoted.
- Where a control leaves a value organization-defined, the lab chooses one and says so.
- Free or low-cost tools only (listed in `LAB-CONTRACT.md`).
- The learner writes no documents.
- Every term is defined inline at first use.

## 6. Known open items

- Nothing has run on a live cluster; all modules are DRAFT.
- The tools image has not been built (needs a running container engine).
- Installer IAM is not yet scoped to cluster ARNs (needs a live install).
- Cluster install: `terraform/scripts/lab-install.sh` renders `terraform/templates/install-config.yaml.tpl` and drives the bastion, but none of it has run on AWS. Install time, the `m6i.4xlarge` size and the 120 GB root volume are estimates or placeholders.
- Kyverno is pinned to 1.19.2. CPS-5 and the ARC modules use ClusterPolicy, which the Kyverno project plans to remove in 1.20; they must move to ValidatingPolicy before the pin is raised.
- Terraform: `lab up` has not been applied; see "Not verified" in `terraform/README.md`.
