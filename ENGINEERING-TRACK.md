# Engineering Leveling Training

Target Audience: Someone with basic cybersecurity and IT knowledge who wants to do hands-on security engineering work.

Goal: Learn to do security engineering work on a real system. You will collect compliance evidence, find and prioritize vulnerabilities, investigate alerts and write detections, harden and secure a workload, use AI tools and agents safely, and test and verify security designs. Every module is hands-on: you run real tools on your own OpenShift cluster in AWS, prove each change works with a test, and prove what fails when the control is removed. By the end you can automate the work, deliver it through an automated review, and design a pattern a whole team can inherit.

Each module has at most five steps. You run it in your lab shell on your own cluster. Start any module with `lab start <id>`, for example `lab start grc-3`.

## Suggested order

1. Start with ENG-0, then ENG-1. Every other module assumes ENG-0 and its earlier modules in the same dimension. The cloud and platform security and the architecture modules also use what ENG-1 teaches about how traffic moves.
1. Then take one level across all seven dimensions, in this order: GRC-2, VM-2, SDR-2, CPS-2, AID-2, AI-1, ARC-2, IAC-1; then GRC-3, VM-3, SDR-3, CPS-3, AID-3, AI-3, ARC-3, IAC-2; then GRC-4, VM-4, SDR-4, CPS-4, AID-4, AI-2, ARC-4, IAC-3; then GRC-5, VM-5, SDR-5, CPS-5, AID-5, ARC-5. This is the order the `lab modules` command lists.
1. Or take one dimension through its levels in order (infrastructure as code has three modules). Each level builds on the one before it in the same dimension and says what it assumes.

## Phase 1: Foundation

Why first: every later module uses the terminal, git, the oc command and the platform health check from ENG-0, and the picture of how a call travels from a name to a pod from ENG-1.

### ENG-0 - Terminal, Git and Your Lab

This module teaches the working habits every engineering module relies on: opening the lab, moving around files, using git, asking the cluster questions with oc, reading YAML (a plain-text format for settings) and error messages, and checking that the platform tools are running. You finish with one script that checks every platform tool.

What you will do:

- Open lab shell, move around and write small files
- Clone, edit, commit and push with the in-lab git server
- Ask the cluster questions with oc, and read YAML and an error
- Read and run the platform health check

Tools and services: lab shell, oc, git, Gitea (free, open source), curl, jq

### ENG-1 - How Traffic Moves

Almost everything you secure in this track is traffic between two things: a pod calling a service, a user reaching an app, a tool calling the cluster. This module teaches how that traffic moves and how to tell where it stopped, so a blocked connection stops being a mystery.

What you will do:

- Read the addresses and the ranges they come from
- Follow a name through DNS to the Service
- Add a Route and read where TLS ends
- Find the blocked hop
- Write the hop check

Tools and services: lab shell, oc, curl, OpenSSL, Python 3, jq, NetworkPolicy

## Phase 2: GRC Engineering

Why this order: you run evidence collection by hand, automate it, put it in the delivery pipeline, then design continuous monitoring across controls.

### GRC-2 - Run Evidence Collection

A regulated system must keep proving that it still looks the way its documents say it does. A collector script reads four things from the cluster and writes the answers into one dated evidence file, for controls CA-7, CM-6 and SC-13.

What you will do:

- Fetch and read the collector
- Run the collector from the lab shell and read the evidence
- Run the same collector in a pipeline
- Check one field against its source
- Write one check of your own

Tools and services: OpenShift Container Platform, OpenShift Pipelines (Tekton), Kyverno (free, open source), oc, tkn, jq, Python 3

### GRC-3 - Automate Evidence Collection

A regulated system has to show the same evidence (saved answers about the system) again and again, not once. A person who collects it by hand skips weeks, misses a check, and cannot prove later that the file was not changed.

What you will do:

- Get the gate and a working copy, and read what the gate checks
- Read the checks for three controls and run them
- Add the time, the hash and the safe write, then test it
- Make the gate a condition for merging, then push through it
- Write the CronJob that runs it on a schedule

Tools and services: OpenShift Container Platform, OpenShift Pipelines (Tekton), Gitea (in-lab git server), oc, git, curl, jq, openssl, Python 3

### GRC-4 - Evidence in the Delivery Pipeline

A regulated system has to show, for every release, that it was tested and that the proof was not changed afterwards. A scan report sitting in a build log proves little: anyone with access could edit it, and nothing says which run made it.

What you will do:

- Make the evidence signing key and check the ingredients
- Decide how the policy check runs, using the cluster's own answers
- Save the tasks, and write the policy check script yourself
- Wire the pipeline, run it, and read the bundle

Tools and services: OpenShift Pipelines (Tekton), Trivy (free, open source), Kyverno (free, open source), Cosign (free, open source), OpenSSL, oc, tkn, jq

### GRC-5 - Continuous Control Monitoring Design

Continuous monitoring (checking controls again and again instead of once a year) is only useful if a team can answer three questions at any time: which controls have evidence produced by a machine, how old is that evidence, and has anything changed since the last approved state? This module builds that for one team namespace (a named section of the cluster, which is the group of servers that runs your lab).

What you will do:

- Choose the scope and look at what the cluster already records
- Convert policy reports into assessment-results JSON
- Capture a baseline and detect drift
- Measure coverage and evidence age
- Run it on a schedule and make it reusable

Tools and services: Kyverno policy reports (free, open source), python3, jq, oc

## Phase 3: Vulnerability Management

Why this order: you scan and hand off findings, track fixes, prioritize by context, then gate delivery on risk.

### VM-2 - Scan and Hand Off

A regulated system must be scanned for known flaws, and the people who decide what to fix must receive the results in a form they can rely on. This module runs four supplied scans, hands the findings to a lead as one JSON record stored in the cluster, and teaches you to escalate a scan that failed or only partly ran instead of reporting zero findings.

What you will do:

- Fetch the supplied files and scan the image
- Scan the repository checkout
- Scan the cluster configuration
- Write an inventory of the image and scan it
- Hand the findings to the lead

Tools and services: OpenShift Container Platform, Trivy (free, open source), Gitea (free, open source), oc, git, jq

### VM-3 - Triage and Track Fixes

Scan results are only useful if somebody works through them in a sensible order and every finding (a flaw or bad setting that a scan reports) has a tracking item and a due date. This module replaces a repeated manual task with a short script: it ranks findings by severity score and by whether a fix exists, opens exactly one tracking item per finding in Gitea (the git server that runs in your lab) with a due date from its severity, and, after a fix, re-scans and closes the items that are really gone.

What you will do:

- Fetch the supplied files and scan the main branch
- Write the ranking code
- Write the Gitea code
- Pass the review gate, then open the items
- Re-scan the fix and close what is gone

Tools and services: OpenShift Container Platform, Trivy (free, open source), Gitea (free, open source), python3, oc, git, curl, jq

### VM-4 - Prioritize by Context and Validate

The same flaw does not carry the same risk everywhere. A critical flaw in a service that is running, reachable from outside the cluster (the group of servers that run your lab) and part of a critical project is urgent.

What you will do:

- Collect the facts from the cluster
- Scan the images and add exploit evidence
- Build the plan
- Suppress with an expiry and record the exception
- Fix through a branch and a pull request, then prove it

Tools and services: OpenShift Container Platform, Trivy (free, open source), Gitea (free, open source), python3, oc, git, curl, jq

### VM-5 - Risk-Based Gate in Delivery

A gate (a pipeline step that stops the run when a rule is broken) that blocks every finding stops delivery and trains people to bypass it. A gate that blocks nothing is decoration.

What you will do:

- Choose the rules from evidence
- Write the rule check, and read the exception code
- Read the ledger, write the gate, and run it on fixtures
- Run the gate as a shared task in a pipeline
- Measure, and make the gate the default

Tools and services: OpenShift Container Platform, OpenShift Pipelines (Tekton), Trivy (free, open source), Gitea (free, open source), python3, tkn, oc, jq

## Phase 4: Security Data and Incident Response

Why this order: you triage an alert from a runbook, investigate and tune, build detections, then manage them as code.

### SDR-2 - Triage an Alert by Runbook

A regulated system must have people who look at what the monitoring tools raise (an alert is a message that a rule matched), work out quickly whether it is a real problem, and report what they find. They must also notice when the logs (lines of text that programs save about what happened) they depend on are missing or late, because an empty search result does not mean nothing happened.

What you will do:

- Fetch the runbook and read the four alerts
- Triage the privilege-change alert (A-101)
- Triage the failed sign-in burst (A-102)
- Triage the shell opened in a pod (A-103)

Tools and services: Loki and Grafana (free, open source), Mattermost (free, open source), OpenShift Container Platform, oc, curl, jq, python3

### SDR-3 - Investigate and Tune

A regulated system must analyze what its monitoring finds and keep the monitoring useful. An alert (a message sent when a rule matches) that fires all day is ignored, and an alert tuned so far that it misses a real attack is worse than none.

What you will do:

- Separate the noise from the bursts
- Follow the account and write the facts
- Apply the threshold to the rule and the panel
- Run the review gate

Tools and services: Loki LogQL (free, open source), Grafana alerting and dashboards (free, open source), OpenShift Container Platform, oc, curl, jq, python3

### SDR-4 - Build Detections and Pipelines

A regulated system must detect threats with automated tools that act on events soon after they happen, and must correlate records from different sources to see the whole attack. In this module you build the detections yourself.

What you will do:

- Write the labeling stage in the Alloy pipeline
- Write three detections
- Test the detections against recorded scenarios
- Follow the actor and build the timeline
- Contain the suspect pod

Tools and services: Loki LogQL (free, open source), Grafana Alloy (free, open source), OpenShift Container Platform, NetworkPolicy, oc, curl, jq, python3

### SDR-5 - Detection as Code

A regulated system must control changes to its configuration, and detections are configuration: a changed threshold or a deleted rule changes what the system can see. Changes must be tested and validated before they take effect.

What you will do:

- Clone the repository and write the pod-exec detection
- Write the test runner
- Write the deploy script and the pipeline
- Push, run the pipeline and prove the gate
- Prove the alert is delivered

Tools and services: Gitea, Tekton (OpenShift Pipelines), Grafana alerting (free, open source), Loki (free, open source), Mattermost, OpenShift Container Platform, oc, tkn, git, curl, jq, python3

## Phase 5: Cloud and Platform Security

Why this order: you apply a baseline, limit permissions, secure a whole workload, then build guardrails developers inherit.

### CPS-2 - Apply a Hardening Baseline

A regulated system must run each workload with the least power it needs and fixed limits on what it may use. The settings must be checked against a published checklist.

What you will do:

- Look at the workload and get the supplied files
- Apply the pod security labels
- Apply the hardening patch, the quota and the default-deny rule
- Run the supplied scan and try a bad pod while it runs
- Read the results and find out why one fails

Tools and services: OpenShift Container Platform, OpenShift Compliance Operator, Pod security admission (built into OpenShift), oc, jq

### CPS-3 - Least-Privilege Roles and Baselines

A regulated system must give each program only the permissions it needs, block network traffic that nobody approved, and run each container (a sealed box holding one program) with no extra powers on the node (a server in the cluster). In this module you write all three for one workload (a program the cluster runs): a minimal role for its service account (the identity a program runs as), a default-deny network policy (a rule that blocks all traffic to and from a pod (one or more containers running together) unless another rule allows it) and a hardened security context (the safety settings on a container).

What you will do:

- Measure what the service account can do today
- Write the review gate
- Write the minimal role and replace the broad binding
- Close the network and harden the container
- Write a scoped cloud policy and test it by simulation

Tools and services: OpenShift Container Platform, Kubernetes RBAC and NetworkPolicy (included with OpenShift), oc, jq, python3, AWS CLI (iam simulate-custom-policy, no changes made)

### CPS-4 - Secure a Workload End to End

A regulated workload (a program the cluster runs) must run under its own identity (the account it acts as) with only the permissions it needs, keep its secrets (sensitive values such as passwords) out of its settings and encrypted where they are stored, accept traffic only from approved callers, and run with no extra powers. Nothing here is new on its own.

What you will do:

- Collect the evidence
- Give it its own identity and move the password into a secret
- Set the network boundaries
- Harden the container and write a Falco rule
- Write the check that proves it

Tools and services: OpenShift Container Platform, Kubernetes secrets, RBAC and NetworkPolicy (included with OpenShift), Falco (free, open source), AWS CLI (read-only calls), oc, jq, python3

### CPS-5 - Guardrails Developers Inherit

A regulated platform team does not harden each workload by hand. It builds the protections into the way a project is created and the way a workload (a program the cluster runs) is admitted, so a developer inherits them without asking.

What you will do:

- Measure the baseline before any guardrail
- Build the project template
- Generate default-deny and a fallback quota with Kyverno
- Mutate to safe defaults and validate against unsafe settings
- Measure again on both creation paths

Tools and services: OpenShift Container Platform (project request template), Kyverno (free, open source), oc, jq, python3

## Phase 6: AI Development

Why this order: AID-2 is optional; you check AI-written scripts, put AI-assisted automation under review, build a constrained agent, then set the safe-adoption pattern. No model account or key is needed; a stand-in model gives scripted answers.

### AID-2 - Check AI-Written Scripts Before Running

This module is optional. Take it if you will run scripts an AI assistant wrote; AID-3 and AID-4 do not depend on it.

What you will do:

- Get the scripts and search them for risky lines
- See what the unsafe scripts would do, without letting them

Tools and services: bash, grep, oc, curl, jq, Stub model service (provided by the lab)

### AID-3 - AI-Assisted Automation Under Review

A regulated system may use a model (a program that writes text when you ask) to save time, but nothing a model returns may be trusted because it looks right. A model answer is text.

What you will do:

- Set up, then review a drafted shape check and write the test that catches its flaw
- Write the summary script and log every exchange
- Push the branch, run the review gate and merge
- Check a query the model drafted against known data

Tools and services: Python (python3), git, Gitea (in-lab git server), OpenShift Pipelines (Tekton), Loki (free, open source), Stub model service (provided by the lab), oc, tkn, curl, jq

### AID-4 - Build a Constrained Triage Agent

An agent is a loop in which a model (a program that writes text when you ask) proposes the next step and a program carries it out. The danger is that the model reads text written by someone else, such as a log line, and that text can steer what it proposes.

What you will do:

- Give the agent a view-only identity
- Write the command allowed list
- Write the loop: validate, log, cap and stop
- Run a clean triage and read the trail

Tools and services: Python (python3), oc, Loki (free, open source), Stub model service (provided by the lab), curl, jq

### AID-5 - Safe Adoption Pattern for Agents

A regulated system adopts agents only when every agent (a loop in which a model, a program that writes text when you ask, proposes the next step and a program carries it out) starts inside the same limits, whoever builds it. A person who writes a new agent should not have to remember to give it a read-only identity (the name the cluster knows a program by), keep secrets (small sensitive values, such as passwords) out of it, or close its network.

What you will do:

- Make the project defaults come with the label
- Refuse agent workloads that carry write power or secrets
- Alert when the agent identity acts outside its list
- Start a probe, build the attempt set and measure the block rate

Tools and services: Kyverno (free, open source), Kubernetes NetworkPolicy, Grafana alerting (free, open source), Loki (free, open source), Stub model service (provided by the lab), Python (python3), oc, curl, jq

## Phase 7: Architecture and Design

Why this order: you trace the security stack, choose an admission mode, test two designs, then verify a reference architecture.

### ARC-2 - Trace the Security Stack

A regulated system must be described in a way a reader can check. A supplied script reads the live cluster and writes one map of the sample project: its parts, who may talk to whom, and which rules refuse a request and which only record it.

What you will do:

- List the parts yourself
- Run the script and keep its output
- Read each part of the map
- Check claim C1: what talks to what
- Check claims C2 and C3: what is enforced and what is only logged

Tools and services: OpenShift Container Platform, Kubernetes NetworkPolicy, Kyverno (free, open source), oc, jq, python3

### ARC-3 - Choose an Admission Mode

A security design choice should rest on what you can show, not on habit. The choice here is whether the Kyverno rules for one project should run in Audit mode, which records a violation, or in Enforce mode, which refuses the request.

What you will do:

- Confirm the starting condition
- Write the test script and pass the review gate
- Collect all three conditions, and test the gate meanwhile
- Read back the table, then turn it into a check on one requirement

Tools and services: OpenShift Container Platform, Kyverno (free, open source), oc, jq, python3

### ARC-4 - Test Two Designs

A regulated system needs more than a rule that says who may talk to whom. It needs to know whether the rule survives an attacker who copies what the rule looks at.

What you will do:

- Build both designs
- Write the attack cases and the harness
- Run the cases against both designs and choose by evidence
- Break each design on purpose and read the state it ends in

Tools and services: OpenShift Container Platform, Kubernetes NetworkPolicy, Red Hat OpenShift Service Mesh 3 (Istio based), oc, jq, python3

### ARC-5 - Verify a Reference Architecture

A reference architecture is only useful to other teams if the running system (your cluster, the group of servers your lab runs on) provably matches it, and keeps matching it. This module makes the allowed flows between four components (separately running parts) into data: a short YAML file (a plain-text list format).

What you will do:

- State the allowed flows as data
- Generate the network policies and the admission check
- Build the conformance test
- Try to add something nobody listed
- Measure how fast drift is caught

Tools and services: OpenShift Container Platform, Kubernetes NetworkPolicy, Kyverno (free, open source), oc, jq, python3

## Phase 8: Infrastructure as Code

Why this order: you run a supplied baseline as code with Terraform and Ansible, then deliver your own change through a review gate, then choose between the two tools by evidence. This dimension has three modules, numbered in sequence.

### IAC-1 - Run a Supplied Baseline as Code

A regulated system's settings must be kept in files that people can review and run again, not typed one at a time. You run supplied files with Terraform and Ansible and read what each tool reports before and after it acts.

What you will do:

- Fetch and read the supplied Terraform folder
- Plan, read the plan, apply the saved plan
- Make a change by hand, find it and repair it
- Run the supplied playbook with Ansible
- Compare what each tool says

Tools and services: OpenShift Container Platform, Terraform (free, open source), Ansible (free, open source), oc, jq

### IAC-2 - Deliver a Baseline as Code with Terraform

A regulated system must keep its baseline configuration (the agreed secure settings of a system) under configuration control, change it only through review, and notice when the running system no longer matches it. In this module you build the baseline for one namespace (a named section of the cluster) as Terraform, writing the rule of the role yourself (a tool that creates and changes systems from text files): the namespace itself, a resource quota (a cap on what the namespace may use), a default-deny network policy (a rule that blocks all traffic until another rule allows it) and a minimal role and role binding (a list of allowed actions and the link that gives it to an account).

What you will do:

- Get a working copy and write the namespace and quota
- Add the default-deny policy, the role and the binding
- Save the plan gate and run it on the good plan
- Deliver the change through review, then apply the saved plan
- Write the drift check and run it

Tools and services: Terraform (with the hashicorp/kubernetes provider), Gitea (in-lab git server), OpenShift Pipelines (Tekton), OpenShift Container Platform, oc, git, jq, python3, tkn (Tekton command-line tool)

### IAC-3 - Terraform or Ansible: Choose by Evidence

A regulated system keeps its environments (a namespace is one) matching an approved baseline, and notices and responds when a setting changes without approval. Two common tools hold such a baseline as code: Terraform and Ansible.

What you will do:

- Write the Ansible version of the baseline and lint it
- Apply it and prove a second run changes nothing
- See what the tools list, then close the gap
- Combine the checks into one gate

Tools and services: Terraform (free), Ansible with the kubernetes.core collection and ansible-lint (free, open source), OpenShift Container Platform, oc, python3

## Reference: controls and timed minutes

Timed work is hands-on plus verify. Reading is not timed.

| Module | Title | Controls | Minutes |
| --- | --- | --- | --- |
| ENG-0 | Terminal, Git and Your Lab | none | 40 |
| ENG-1 | How Traffic Moves | none | 60 |
| GRC-2 | Run Evidence Collection | CA-7, CM-6, SC-13 | 68 |
| VM-2 | Scan and Hand Off | RA-5, SI-2 | 62 |
| SDR-2 | Triage an Alert by Runbook | AU-6, IR-4, AU-5 | 56 |
| CPS-2 | Apply a Hardening Baseline | CM-6, CM-7, SC-6 | 61 |
| AID-2 | Check AI-Written Scripts Before Running | CM-3, IA-5(7), SA-11 | 40 |
| AI-1 | Put the Model Behind a Gateway | SC-7, AC-3, SC-5 | 55 |
| ARC-2 | Trace the Security Stack | PL-8, CM-8, SC-7 | 56 |
| IAC-1 | Run a Supplied Baseline as Code | CM-2, CM-3, CM-6 | 56 |
| GRC-3 | Automate Evidence Collection | CA-7, CM-3, CM-6 | 71 |
| VM-3 | Triage and Track Fixes | RA-5, SI-2, SA-11 | 72 |
| SDR-3 | Investigate and Tune | SI-4, AU-6, IR-4 | 68 |
| CPS-3 | Least-Privilege Roles and Baselines | AC-6, SC-7, CM-6 | 66 |
| AID-3 | AI-Assisted Automation Under Review | SI-10, AU-12, CM-3, SA-11 | 70 |
| AI-3 | Watch the Model Gateway and Respond to Abuse | SI-4, AU-6, IR-4 | 55 |
| ARC-3 | Choose an Admission Mode | SA-8, CM-7, AU-12 | 55 |
| IAC-2 | Deliver a Baseline as Code with Terraform | CM-2, CM-3, CM-6 | 67 |
| GRC-4 | Evidence in the Delivery Pipeline | SA-11, SI-7, CM-6 | 71 |
| VM-4 | Prioritize by Context and Validate | RA-5, RA-7, CA-5, CM-3 | 67 |
| SDR-4 | Build Detections and Pipelines | SI-4, SI-4(2), AU-6(3), IR-4(2) | 77 |
| CPS-4 | Secure a Workload End to End | AC-6, IA-5, SC-28, SC-7 | 74 |
| AID-4 | Build a Constrained Triage Agent | AC-6, CM-7, SI-10, AU-12 | 63 |
| AI-2 | Check a Model File Before You Use It | SI-7, CM-14, SR-4 | 50 |
| ARC-4 | Test Two Designs | SC-7, SC-8, SC-24, SA-8 | 51 |
| IAC-3 | Terraform or Ansible: Choose by Evidence | CM-2, CM-3, CM-6 | 63 |
| GRC-5 | Continuous Control Monitoring Design | CA-7, CM-6, CM-3 | 60 |
| VM-5 | Risk-Based Gate in Delivery | RA-5, SI-2, SA-11 | 70 |
| SDR-5 | Detection as Code | CM-3, CM-3(2), SI-4(2) | 72 |
| CPS-5 | Guardrails Developers Inherit | CM-2, CM-7, SC-7, SC-6 | 72 |
| AID-5 | Safe Adoption Pattern for Agents | AC-6, SC-7, SI-4, SA-11 | 75 |
| ARC-5 | Verify a Reference Architecture | PL-8, SC-7, CM-2, CM-8 | 62 |
