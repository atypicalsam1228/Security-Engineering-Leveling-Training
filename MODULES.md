# Module catalog

The 32 modules in the recommended order. Each is a 50 to 75 minute hands-on block with verify tests. Control IDs are NIST SP 800-53 Rev 5.

**Tracks:** ENG = Engineering foundations; GRC = Governance, risk and compliance evidence; VM = Vulnerability management; SDR = Security detection and response; CPS = Container and platform security; AI = AI workload security; AID = AI-assisted engineering; ARC = Security architecture; IAC = Infrastructure as code.

| # | Module | What it covers and why |
|---|---|---|
| 1 | **ENG-0** Terminal, Git and Your Lab | Build the working habits every module relies on: terminal, git, oc, YAML, and reading error messages. |
| 2 | **ENG-1** How Traffic Moves | Learn how traffic moves between a pod, a Service and the outside, and how to tell where a blocked call stopped. |
| 3 | **GRC-2** Run Evidence Collection (CA-7, CM-6, SC-13) | Show, on a given day, that the system still matches what its documents say. |
| 4 | **VM-2** Scan and Hand Off (RA-5, SI-2) | Find known flaws in what the system runs and hand the decision-maker a result they can rely on. |
| 5 | **SDR-2** Triage an Alert by Runbook (AU-6, IR-4) | Review what monitoring raises, decide quickly whether it is real, and check that the logs you rely on arrive on time. |
| 6 | **CPS-2** Apply a Hardening Baseline (CM-6, CM-7, SC-6) | Run a workload with the least power and smallest resource allowance it needs, and check it against a checklist. |
| 7 | **AID-2** Check AI-Written Scripts Before Running (optional) (CM-3, IA-5(7), SA-11) | Stop a script an AI assistant wrote from changing the system before a person has read it. |
| 8 | **AI-1** Put the Model Behind a Gateway (SC-7, AC-3, SC-5) | Put the model behind a gateway that checks a token, limits request rates and sizes, and is the only path to the model. |
| 9 | **ARC-2** Trace the Security Stack (PL-8, CM-8, SC-7) | Show that the written description of a system matches what is really running. |
| 10 | **IAC-1** Run a Supplied Baseline as Code (CM-2, CM-3, CM-6) | Keep settings in reviewable files so the approved state can be shown and a hand-made change found. |
| 11 | **GRC-3** Automate Evidence Collection (CA-7, CM-3, CM-6) | Collect evidence automatically, detect changes to it, and let it reach the schedule only through a review gate. |
| 12 | **VM-3** Triage and Track Fixes (RA-5, SI-2, SA-11) | Give every scan finding a tracking item and due date, and work them in a sensible order. |
| 13 | **SDR-3** Investigate and Tune (SI-4, AU-6, IR-4) | Investigate an incident with your own log searches, then tune a noisy alert so it stays useful. |
| 14 | **CPS-3** Least-Privilege Roles and Baselines (AC-6, SC-7, CM-6) | Give each program only the permissions it needs, enforced at the network and container level. |
| 15 | **AID-3** AI-Assisted Automation Under Review (SI-10, AU-12, CM-3, SA-11) | Treat a model reply as an input to check, log every exchange, and control a script that calls a model as a change. |
| 16 | **AI-3** Watch the Model Gateway and Respond to Abuse (SI-4, AU-6, IR-4) | Detect a burst of rejected requests at the gateway, follow a short runbook, and rotate the token. |
| 17 | **ARC-3** Choose an Admission Mode (SA-8, CM-7, AU-12) | Choose between Audit and Enforce from test results instead of habit. |
| 18 | **IAC-2** Deliver a Baseline as Code with Terraform (CM-2, CM-3, CM-6) | Keep the namespace baseline as reviewed files, change it only through a gate, and detect drift. |
| 19 | **GRC-4** Evidence in the Delivery Pipeline (SA-11, SI-7, CM-6) | Produce tamper-evident proof per release that the image was scanned and the change policy-checked. |
| 20 | **VM-4** Prioritize by Context and Validate (RA-5, RA-7, CA-5, CM-3) | Rank findings by whether the workload runs, is exposed and is critical, and by known exploitation. |
| 21 | **SDR-4** Build Detections and Pipelines (SI-4, SI-4(2), AU-6(3), IR-4(2)) | Detect three attack behaviors automatically, prove each detection works, then follow one account and isolate the pod it reached. |
| 22 | **CPS-4** Secure a Workload End to End (AC-6, IA-5, SC-28, SC-7) | Apply all four workload protections to one program without a script, choosing between options using cluster evidence. |
| 23 | **AID-4** Build a Constrained Triage Agent (AC-6, CM-7, SI-10, AU-12) | Show a prompt-injected instruction cannot reach the cluster when the loop enforces an allowed list and a view-only identity. |
| 24 | **AI-2** Check a Model File Before You Use It (SI-7, CM-14, SR-4) | Sign a model file with its hash and refuse a changed file or an edited manifest before it loads. |
| 25 | **ARC-4** Test Two Designs (SC-7, SC-8, SC-24, SA-8) | Find out whether a pod-label rule still protects the database when an attacker copies the label. |
| 26 | **IAC-3** Terraform or Ansible: Choose by Evidence (CM-2, CM-3, CM-6) | Keep a namespace on its baseline, pick the tool by what each one reports, and catch the change neither tool sees. |
| 27 | **GRC-5** Continuous Control Monitoring Design (CA-7, CM-6, CM-3) | Answer coverage, freshness and drift questions continuously for one team namespace. |
| 28 | **VM-5** Risk-Based Gate in Delivery (RA-5, SI-2, SA-11) | Show vulnerability blocking is automated, evidence-based and measurable. |
| 29 | **SDR-5** Detection as Code (CM-3, CM-3(2), SI-4(2)) | Show every detection change is approved, tested and recorded, and the event-to-alert path is automated. |
| 30 | **CPS-5** Guardrails Developers Inherit (CM-2, CM-7, SC-7, SC-6) | Build guardrails so every new namespace starts protected and ordinary workloads pass first try. |
| 31 | **AID-5** Safe Adoption Pattern for Agents (AC-6, SC-7, SI-4, SA-11) | Show platform policy, not agent-author discipline, enforces the same limits for every agent project. |
| 32 | **ARC-5** Verify a Reference Architecture (PL-8, SC-7, CM-2, CM-8) | Show a running system matches its reference architecture and keeps matching it. |

See `ENGINEERING-TRACK.md` for the steps in each module, and `modules/` for the module documents.
