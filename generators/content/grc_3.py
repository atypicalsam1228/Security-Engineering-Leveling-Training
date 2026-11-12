"""GRC-3: Automate Evidence Collection (CA-7, CM-3, CM-6). Engineering track, level 3."""

CRED = "credential.helper=!f() { echo username=$GITEA_USER; echo password=$GITEA_TOKEN; }; f"
WORK = "cd /workspace/grc-3/evidence-work\n"
NIST = "nist-sp-800-53r5-full.md"
FEDRAMP = "fedramp-high-baseline.md"

COLLECT_B = '''EVIDENCE_DIR = os.environ["EVIDENCE_DIR"]
CONTROLS = {"CM-6": cm6_fips, "CM-7": cm7_policies, "CM-8": cm8_namespaces}


def main():
    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    controls = {control: collect() for control, collect in CONTROLS.items()}
    body = json.dumps({"collected_at": collected_at, "controls": controls}, sort_keys=True)
    digest = hashlib.sha256(body.encode()).hexdigest()
    name = "evidence-" + collected_at.replace(":", "") + ".json"
    path = os.path.join(EVIDENCE_DIR, name)
    with open(path, "w") as handle:
        handle.write(body)
    with open(path + ".sha256", "w") as handle:
        handle.write(digest + "\\n")
    print("FILE", name)
    print("SHA256", digest)
    print(body)


main()
'''

CRON_HEAD = '''apiVersion: batch/v1
kind: CronJob
metadata:
  name: evidence-collect
  namespace: build
spec:
  schedule: "*/15 * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
          volumes:
            - name: evidence
              persistentVolumeClaim:
                claimName: evidence-pvc
            - name: oc-bin
              emptyDir: {}
          initContainers:
            - name: get-oc
              image: quay.io/openshift/origin-cli:4.22.0
              command: ["cp", "/usr/bin/oc", "/oc-bin/oc"]
              volumeMounts:
                - name: oc-bin
                  mountPath: /oc-bin
          containers:
            - name: collect
              image: registry.access.redhat.com/ubi9/python-312:1
              envFrom:
                - configMapRef:
                    name: evidence-source
'''

CRON_TAIL_SKELETON = '''              env:
                - name: EVIDENCE_DIR
                  value: # WRITE the one folder the collector may write to
                - name: PATH
                  value: /oc-bin:/opt/app-root/bin:/usr/bin:/bin
              command: ["/bin/sh", "-c"]
              args:
                - # WRITE one shell line: fetch the collector from main, then run it
              volumeMounts:
                - name: evidence
                  mountPath: # WRITE where the evidence volume appears
                - name: oc-bin
                  mountPath: /oc-bin
          # WRITE the service account line here, indented like "containers:" above
'''

HEREDOC_B = "cat > collect_b.py <<'EOF'\n" + COLLECT_B + "EOF\ntest -s collect_b.py && echo ok || echo EMPTY\ncat collect_a.py collect_b.py > evidence-scripts/collect_evidence.py\n"
HEREDOC_CRON_HEAD = "cat > cronjob-head.yaml <<'EOF'\n" + CRON_HEAD + "EOF\n" + "test -s cronjob-head.yaml && echo ok || echo EMPTY\n"
HEREDOC_CRON_TAIL = "cat > cronjob-tail.yaml <<'EOF'\n" + CRON_TAIL_SKELETON + "EOF\n" + "test -s cronjob-tail.yaml && echo ok || echo EMPTY\n"

STATUS_URL = "\"$GITEA_URL/api/v1/repos/$GITEA_USER/evidence-scripts"
AUTH = "-H \"Authorization: token $GITEA_TOKEN\" -H \"Content-Type: application/json\""

MODULE = {
    "intent_at_end": True,
    "id": "GRC-3",
    "slug": "AutomateEvidence",
    "title": "Automate Evidence Collection",
    "draft": (
        "Nothing here has run on a live cluster. The review gate reads the collector as text with the Python `ast` module and never runs it, because the script is not yet trusted and would run with cluster read access. "
        "That makes it a floor, not a sandbox: it catches the three mistakes this module names and a path that is built outside EVIDENCE_DIR, and it does not stop a determined author. "
        "The gate runs as a Tekton pipeline that a Gitea push webhook starts through a Tekton Triggers EventListener and that posts a commit status named evidence-review-gate. "
        "The Gitea fields branch protection `enable_status_check`, `status_check_contexts` and `block_admin_merge_override`, the combined status endpoint `commits/{ref}/status`, the status post `statuses/{sha}`, the raw file endpoint with `?ref=` and the merge refusal code 405 for a failed required check were checked against the Gitea main source on 2026-10-29. The Gitea version the lab runs is not pinned, so run `curl -s \"$GITEA_URL/api/v1/version\"` and re-check if it is old. The Tekton Triggers v1beta1 EventListener with an inline binding that has a value matches the Triggers documentation; the push payload field `after` is confirmed on a live Gitea only. "
        "The lab must also allow Gitea to call a private cluster address from a webhook, which Gitea blocks by default. The collector reads the FIPS flag the same way as GRC-2 and carries the same assumption about `spec.fips`. "
        "Step 5 is a writing exercise: the learner writes the end of the CronJob (identity, evidence folder, fetch-and-run command) against a table, and the supplied check-cronjob.py (it needs PyYAML, which the lab image has) holds the file to the spec. The joined reference answer was checked here to parse and to equal the earlier full CronJob. The check script, the exercise and the `oc auth can-i --as` impersonation lines have not run on a live cluster, and the supplied collect_a.py is now placed by the start state (its start-state kit folder) instead of being pasted."
    ),
    "controls": ["CA-7", "CM-3", "CM-6"],
    "mentions": ["CM-7", "CM-8", "SI-7"],
    "unit_values_ok": ["15 minutes", "64 characters", "64 character", "60 seconds", "3 minutes"],
    "tool_why": True,
    "hide_draft": True,
    "hover": True,
    "terms_at_end": True,
    "minutes": {"hands_on": 49, "verify": 24},
    "tools": [
        "OpenShift Container Platform",
        "OpenShift Pipelines (Tekton)",
        "Gitea (in-lab git server)",
        "oc",
        "git",
        "curl",
        "jq",
        "openssl",
        "Python 3",
    ],
    "diagrams": [
        {
            "id": "flow",
            "title": "A collector reaches the schedule only through the gate",
            "caption": "This is the lab (test) setup. You write the collector in the lab shell, test it locally, push it through the review gate on Gitea, and deploy a CronJob that runs only what main holds. In production the git server is replaced by a hosted service, the evidence volume is write-once storage, and missed runs raise alerts. Each step below adds one part, drawn with thick lines.",
            "per_step": True,
            "skip_steps": (1,),
            "rankdir": "LR",
            "step_notes": {
                2: "You read and run the three control checks, which are functions in a collector script in your lab shell.",
                3: "You add the time stamp, the hash and the safe write to the collector, then run the script and the gate in your lab shell.",
                4: "Gitea now requires the gate's pass before main accepts a change. Your push sends the branch to Gitea, the push starts the gate in the build project, the gate posts its result back to Gitea, and a pass lets the pull request merge into main.",
                5: "A scheduled job in the build project fetches the collector from main on Gitea and writes evidence to the evidence volume every 15 minutes.",
            },
            "zones": [
                {"id": "lab", "label": "Your lab", "kind": "boundary"},
                {"id": "shell", "label": "Lab shell", "parent": "lab", "kind": "group"},
                {"id": "cluster", "icon": "aws/group-AWS-Cloud", "label": "Lab cluster (your OpenShift cluster, in AWS)", "parent": "lab", "kind": "boundary"},
                {"id": "gitea", "icon": "brands/gitea", "label": "Gitea (the git server), repository evidence-scripts", "parent": "cluster", "kind": "group"},
                {"id": "build", "icon": "brands/openshift", "label": "Build project", "parent": "cluster", "kind": "group"},
            ],
            "key": {"aws/group-AWS-Cloud": "AWS Cloud", "brands/gitea": "Gitea git server", "brands/openshift": "OpenShift project", "brands/python": "Python script", "brands/gnubash": "Shell session", "brands/tekton": "Tekton pipeline", "k8s/cronjob": "Kubernetes CronJob", "k8s/pvc": "Kubernetes volume claim"},
            "nodes": [
                {"id": "script", "icon": "brands/python", "title": "Your collector", "sub": "Python script collect_evidence.py", "zone": "shell", "s": 2},
                {"id": "local", "icon": "brands/gnubash", "title": "Test in the lab shell", "sub": "Shell session: run the collector, then the gate script", "zone": "shell", "kind": "ok", "s": 3},
                {"id": "pr", "title": "Pull request on Gitea", "sub": "From your pushed branch add-collector", "zone": "gitea", "s": 4},
                {"id": "main", "title": "Branch main", "sub": "The approved source", "zone": "gitea"},
                {"id": "prot", "title": "Branch protection", "sub": "Needs a passing status", "zone": "gitea", "kind": "ok", "s": 4},
                {"id": "cron", "icon": "k8s/cronjob", "title": "Scheduled job", "sub": "Kubernetes CronJob evidence-collect, every 15 minutes", "zone": "build", "s": 5},
                {"id": "vol", "icon": "k8s/pvc", "title": "Evidence volume", "sub": "Kubernetes volume claim evidence-pvc", "zone": "build", "kind": "ok", "s": 5},
                {"id": "gate", "icon": "brands/tekton", "title": "Review gate", "sub": "Tekton pipeline that checks the script text", "zone": "build", "kind": "warn", "s": 4},
            ],
            "edges": [
                {"a": "script", "b": "local", "label": "Tested by", "flat": True, "s": 3},
                {"a": "script", "b": "pr", "n": 1, "label": "Pushed to Gitea", "s": 4},
                {"a": "pr", "b": "gate", "n": 2, "label": "Push starts, by webhook", "s": 4},
                {"a": "gate", "b": "prot", "n": 3, "label": "Posts pass or fail to Gitea", "kind": "ok", "s": 4},
                {"a": "prot", "b": "main", "label": "Guards", "flat": True, "s": 4},
                {"a": "main", "b": "cron", "label": "Fetched by", "s": 5},
                {"a": "cron", "b": "vol", "label": "Writes", "kind": "ok", "s": 5},
            ],
            "why_built": (
                "You write and test the collector in the lab shell on your laptop, the same workspace you used in ENG-0, and nothing leaves it until the gate script passes there. "
                "This module adds Gitea, the git server inside the lab, as the place where the collector is stored and reviewed, because the schedule must run only code that someone approved. "
                "The module also adds the review gate as a pipeline in the build project on the cluster, outside the repository, so an author cannot edit the gate in the same pull request that it judges. "
                "Gitea tells the gate about each push with a webhook, and the gate sends its pass or fail back to Gitea as a status on the commit, which is what branch protection reads. "
                "The scheduled job also lives in the build project, and it downloads the collector from the main branch on Gitea every time, so only an approved version can ever run. "
                "The job writes to its own volume, so a flaw in the collector cannot reach anything else."
            ),
            "setup": [
                ("Lab shell", "A container on your laptop", "You write and test the collector here, so a mistake costs nothing and nothing reaches Gitea until the gate script passes."),
                ("Repository evidence-scripts", "On Gitea, the git server inside the lab", "The collector lives in a repository so every change is a pull request that can be reviewed."),
                ("Branch protection", "A rule on the repository on Gitea", "It turns the review gate into a requirement instead of advice, even for an administrator."),
                ("Review gate", "A pipeline in the build project, started by a webhook from Gitea", "It runs outside the repository, so an author cannot edit it in the pull request it judges."),
                ("Scheduled job", "A CronJob in the build project", "It runs on a timetable with nobody at the keyboard, and it fetches only from main."),
                ("Evidence volume", "A volume claim in the build project", "Evidence outlives each pod, and the job can write nowhere else."),
                ("Service account evidence-runner", "The build project", "The job gets a named, read-only identity instead of borrowing a person's access."),
            ],
            "reading": [
                "1. Your collector: the Python script collect_evidence.py that you build in the lab shell.",
                "2. Test in the lab shell: you run the collector and the gate script here first, so a mistake costs nothing.",
                "3. Pull request on Gitea: the proposed change, opened from your pushed branch add-collector (flow 1).",
                "4. Review gate: the Tekton pipeline in the build project. The push starts it through a webhook (flow 2).",
                "5. Branch protection: the Gitea rule that lets a change merge only when the gate's status is a pass. The gate posts that status back to Gitea (flow 3).",
                "6. Branch main: the approved source. Branch protection guards it.",
                "7. Scheduled job: the CronJob in the build project. It fetches the collector from main and runs it every 15 minutes.",
                "8. Evidence volume: the volume claim where the job writes each time-stamped evidence file.",
            ],
        },
    ],
    "prereq": ["ENG-0 Terminal, Git and Your Lab (typing commands in lab shell, making a file with a heredoc, and clone, commit and push with git)"],
    "lab_needs": [],
    "lab": {
        "start": "lab start grc-3",
        "env": ["GITEA_URL", "GITEA_USER", "GITEA_TOKEN"],
    },
    "objectives": [
        {"label": "Skill", "text": "Write a collector for three controls, pass it through a review gate, merge it to a protected branch, and deploy it as a scheduled job."},
        {"label": "Tools", "text": "`git` and Gitea track and review the collector; a Tekton pipeline runs the review gate; a Kubernetes CronJob runs the collector on a schedule."},
        {"label": "Security Function", "text": "Prevents unreviewed collection code from reaching the schedule. The gate blocks a change that lacks a time stamp, a hash, or a safe write path, and branch protection ensures only gate-approved code runs."},
        {"label": "NIST CA-7 Continuous Monitoring", "text": "The CronJob runs the collector every 15 minutes without a person. Each run writes a time-stamped evidence file, so monitoring is ongoing and every file can be traced to its run."},
        {"label": "NIST CM-3 Configuration Change Control", "text": "Branch protection requires a passing gate status before a change reaches main. The CronJob fetches only from main, so only reviewed and approved code runs on the schedule."},
        {"label": "NIST CM-6 Configuration Settings", "text": "The collector records the FIPS flag, the Kyverno policy names and the namespace names. Each file is time-stamped and hashed, so a later change is visible when two runs are compared."},
    ],
    "requirement": (
        "A regulated system has to show the same evidence (saved answers about the system) again and again, not once. A person who collects it by hand skips weeks, misses a "
        "check, and cannot prove later that the file was not changed. This module replaces the person with a script (a short program) that collects evidence "
        "for three controls (written security requirements), stamps it with the time in UTC (Coordinated Universal Time, the world reference clock) and a SHA-256 hash (a "
        "fingerprint that changes if even one character of the file changes). An automated review gate (a check that fails when the work "
        "is not acceptable) in Gitea (the git server that runs inside your lab) refuses any version of the script that lacks the time stamp, lacks the hash, or writes outside the "
        "evidence folder. Only a script that passed the gate runs on the schedule."
    ),
    "requirement_bullets": [
        "Purpose: show that evidence is collected automatically, can be checked for changes, and only reaches the schedule through a review gate (CA-7, CM-3, CM-6).",
        "You write a collector for three controls, stamp it with a UTC time and a SHA-256 hash, and limit where it may write.",
        "An automated gate reads the script as text and blocks any change that lacks a time stamp, a hash or a safe write path.",
        "A CronJob fetches the collector from main on every run, so only gate-approved code collects evidence.",
    ],
    "mapping": [
        {
            "control": "CA-7 Continuous Monitoring",
            "plain": "Monitor the chosen metrics on a schedule, and use the results.",
            "source": "NIST",
            "tool": "A CronJob in the build project that runs the collector. Explained in section 2.3.",
            "covered": "Section 3, Step 5: the CronJob runs the collector on a schedule and each run writes a new time-stamped evidence file. Section 4, Tests 1 and 2: you read the newest file from the volume and check the hash and the time of one run.",
            "cite": [
                {"file": NIST, "quote": "Ongoing control assessments in accordance with the continuous monitoring strategy"},
            ],
        },
        {
            "control": "CM-3 Configuration Change Control",
            "plain": "Changes are reviewed and approved before they are put into use, and only approved changes are put into use.",
            "source": "NIST",
            "tool": "Gitea branch protection and the review gate pipeline (OpenShift Pipelines, Tekton). Explained in section 2.2.",
            "covered": "Section 3, Step 4: the gate becomes a condition for merging to main. Section 4, Tests 3 and 4: a script that fails the gate is rejected and cannot merge.",
            "cite": [
                {"file": NIST, "quote": "Review proposed configuration-controlled changes to the system and approve or disapprove such changes"},
                {"file": NIST, "quote": "Implement approved configuration-controlled changes to the system"},
            ],
        },
        {
            "control": "CM-6 Configuration Settings",
            "plain": "Changes to settings are monitored and controlled.",
            "source": "NIST",
            "tool": "The collector script, which reads the cluster with oc. Explained in section 2.1.",
            "covered": "Section 3, Steps 2 and 3: you read and complete the collector that records the FIPS flag, the policy names and the namespace names, each with a time and a hash. Section 4, Test 2: you check the hash.",
            "cite": [
                {"file": NIST, "quote": "Monitor and control changes to the configuration settings in accordance with organizational policies and procedures"},
                {"file": NIST, "quote": "Manage, apply, and verify configuration settings for [Assignment: organization-defined system components] using [Assignment: organization-defined automated mechanisms]"},
            ],
        },
    ],
    "intent": [
        {
            "control": "CA-7 Continuous Monitoring",
            "feared": "Evidence is gathered when someone remembers, so the record has gaps exactly where something went wrong.",
            "scope": "The checks the team chose to automate: here, settings for CM-6, policies for CM-7 and an inventory for CM-8.",
            "question": "If the last run was three days ago, would anyone know, and could you show every run?",
            "evidence": "A series of evidence files with times, the schedule, and the job history that shows each run.",
            "sufficient": "Collection runs by itself at a stated frequency and every run leaves a file. NIST leaves the frequency organization-defined (FedRAMP High separately requires configuration scans at least monthly), and the lab runs every 15 minutes.",
            "tieoff": "A missed run is noticed by something other than the script itself. This module shows the last scheduled run (Test 1); GRC-5 measures evidence age.",
            "tool": "A Kubernetes CronJob (a job the cluster starts on a schedule) runs the collector from main (Step 5).",
        },
        {
            "control": "CM-3 Configuration Change Control",
            "feared": "Someone edits the collector so that it quietly stops collecting or writes somewhere it should not, and no one reviews the change.",
            "scope": "The collector script and the rule that decides what may reach the branch the schedule runs.",
            "question": "Could a version of the collector that skips the hash be running on the schedule today?",
            "evidence": "Branch protection settings, the gate's status on each commit, and a rejected pull request that could not merge.",
            "sufficient": "A change reaches the schedule only through a pull request that merges only when the automated review passes. Human review stays a separate step.",
            "tieoff": "A failing gate shows on the pull request, so the author sees it before anyone merges.",
            "tool": "Gitea branch protection requires the evidence-review-gate status (Step 4). Test 4 proves a failing change is refused.",
        },
        {
            "control": "CM-6 Configuration Settings",
            "feared": "A setting is loosened and the evidence record still shows the old, safe value.",
            "scope": "The settings the collector reads: the FIPS flag, the policy list and the namespace list.",
            "question": "What was the value of each setting at the time of the last run, and has that record been altered since?",
            "evidence": "Each evidence file with its time stamp and its hash.",
            "sufficient": "Each value is recorded with a time and a hash. A hash beside the file only detects accidents, because someone who can change the file can change the hash too. GRC-4 adds a signature.",
            "tieoff": "A changed value is reported to the setting owner. This module records; GRC-5 compares with a baseline.",
            "tool": "The collector writes the value, the UTC time and the SHA-256 for three controls (Steps 2 and 3).",
        },
    ],
    "terms": [
        ("Collector", "A script that asks the system questions and writes the answers down as evidence."),
        ("UTC", "Coordinated Universal Time, the world reference time with no daylight-saving changes."),
        ("SHA-256", "A standard way to make a fingerprint (hash) of any content. The fingerprint is 64 characters long, and changing one character of the content changes it completely."),
        ("Evidence directory", "The one folder the collector may write to. Its path comes from the environment variable EVIDENCE_DIR."),
        ("Review gate", "An automated check that must pass before a change can merge."),
        ("Commit status", "A pass or fail mark that a tool attaches to one commit in Gitea."),
        ("Branch protection", "A Gitea rule that limits how a branch may change."),
        ("Webhook", "A call Gitea makes to another service whenever something happens in a repository."),
        ("CronJob", "A Kubernetes object that starts a job on a repeating schedule."),
        ("Init container", "A small container in a pod that runs first and finishes before the main container starts."),
        ("Static check", "A check that reads a script as text and never runs it."),
        ("Control", "A written requirement for how a system is protected or run. Each one has an ID and a name."),
        ("Evidence", "A saved answer to a question about the system, with the time it was collected."),
        ("Time stamp", "The date and time a record was made."),
        ("Hash", "A fixed-length fingerprint of content. The same content always gives the same hash."),
        ("Cluster", "A group of servers that work together as one system. Here it is your own OpenShift cluster in AWS."),
        ("Namespace", "A named section of the cluster that keeps workloads apart. OpenShift also calls it a project."),
        ("Config map", "A stored file or setting that the cluster keeps and can hand to a program."),
        ("Pod", "One running copy of a program inside the cluster."),
        ("Job", "A one-off piece of work the cluster runs once, to the end."),
        ("Service account", "An identity for a program instead of a person."),
        ("Pipeline", "An automated sequence of tasks. Each task runs in its own pod."),
        ("Tekton", "The pipeline engine inside OpenShift Pipelines."),
        ("EventListener", "A Tekton Triggers object that receives web calls, such as a Gitea webhook, and starts a pipeline run."),
        ("Volume claim", "A request for disk space that lasts longer than one pod."),
        ("Gitea", "A git server that runs inside the lab. It holds the repository you push to and the rules for its branches."),
        ("Git", "A tool that records the history of a folder of files and lets people work on separate branches."),
        ("Repository", "A folder of files whose history git records, kept on a server such as Gitea."),
        ("Branch", "A separate line of work in git. The branch named main holds the approved version."),
        ("Commit", "One saved change in git, with a message and an identifier."),
        ("Pull request", "A proposed change that others review before it joins a branch."),
        ("Merge", "Joining the changes of one branch into another, here into main."),
        ("API", "A web address a program can call to read or change something. Gitea has one for rules and statuses, and curl calls it."),
        ("Token", "A secret string that proves who is calling an API. It is used instead of a password."),
        ("Environment variable", "A named value the shell passes to a program, such as EVIDENCE_DIR."),
        ("Kyverno", "A policy engine that checks cluster objects against rules."),
        ("Policy", "A rule the cluster checks. Kyverno is the tool that holds the policies in this lab."),
        ("FIPS", "A US government standard for cryptography. FIPS mode is a setting that makes a system use cryptography validated against a US government standard."),
        ("YAML", "A plain-text format for settings, written as indented lines of name and value. Cluster objects are described in it."),
        ("JSON", "A plain-text format for data: names and values written inside curly braces."),
        ("oc", "The OpenShift command-line tool. It sends your commands to the cluster."),
        ("curl", "A command-line tool that calls a web address. Here it calls the Gitea API."),
        ("jq", "A command-line tool that reads and picks fields out of JSON."),
        ("openssl", "A command-line tool for cryptography. Here it works out a SHA-256 hash a second way."),
        ("Function", "A named block of code that does one job and returns an answer."),
        ("Dictionary", "A Python value that pairs names with values, such as {'fips': True}."),
        ("tkn", "The command-line tool for Tekton. You type tkn to list pipeline runs and read their logs."),
    ],
    "concepts": [
        {
            "heading": "2.1 What makes evidence worth keeping",
            "controls": [
                {"id": 'CM-6 Configuration Settings'},
            ],
            "paras": [
                "Evidence is useful when a stranger can trust it later. Three properties make that possible:",
                {"bullets": [
                    "A time stamp says when the fact was true.",
                    "A SHA-256 hash lets anyone confirm the file has not changed.",
                    "A fixed write directory stops the collector from reaching anything else.",
                ]},
                "The review gate turns these three properties into rules that a change must satisfy before it can merge.",
                {
                    "control": 'CM-6: Configuration Settings',
                    "text": 'The control asks the organization to establish and document configuration settings at the most restrictive mode consistent with operational requirements, implement them, approve any deviations, and monitor and control changes to them. NIST enhancement CM-6(1) asks for automated mechanisms to manage, apply and verify settings. This is done using:',
                },
                {"bullets": [
                    "The collector script: records the FIPS flag, the Kyverno policy names and the namespace names, each with a UTC time and a SHA-256 hash.",
                    "Dated evidence files: a later change to a setting shows up when two runs are compared. Whether a setting is the most restrictive one remains a decision for people.",
                ]},
                "The table shows what the review gate looks for and the mistake each check prevents:",
            ],
            "table": {
                "headers": ["Property", "What the gate looks for", "Mistake it prevents"],
                "rows": [
                    ("Time stamp", "A call to `datetime.now`", "Evidence that cannot be dated"),
                    ("Hash", "A call to `hashlib.sha256` and its `hexdigest`", "Evidence that cannot be checked later"),
                    ("Safe write", "Every file opened for writing has a path built from EVIDENCE_DIR", "A collector that overwrites other files"),
                    ("Reads EVIDENCE_DIR", "The name EVIDENCE_DIR is read from the environment", "A hard-coded folder"),
                ],
            },
        },
        {
            "heading": "2.2 Why the gate reads the script and does not run it",
            "controls": [
                {"id": 'CM-3 Configuration Change Control'},
            ],
            "paras": [
                {"bullets": [
                    "The gate never runs the script, because unreviewed code would run with the gate's cluster access.",
                    "A static check catches only common mistakes. It is a minimum safeguard, not a full defense.",
                    "A person still reviews the pull request as a second layer.",
                    "The gate lives in the build project, outside the repository, so an author cannot edit it in the same pull request.",
                ]},
                {
                    "control": 'CM-3: Configuration Change Control',
                    "text": 'The control asks the organization to decide which changes are configuration-controlled, review them and approve or disapprove them with security and privacy impact in mind, document the decisions, and implement only approved changes. This is done using:',
                },
                {"bullets": [
                    "Gitea branch protection: lets a change to the collector script reach main only through a pull request whose commit shows a passing status from the review gate.",
                    "The review gate (Tekton pipeline): checks the script automatically. A person still reviews the pull request, so the gate supports the control and does not replace review.",
                ]},
            ],
        },
        {
            "heading": "2.3 Running on a schedule",
            "controls": [
                {"id": 'CA-7 Continuous Monitoring'},
            ],
            "paras": [
                {"bullets": [
                    "A CronJob starts a pod on a repeating timetable.",
                    "The job downloads the collector from main on every run, so only a gate-approved version can run.",
                    "The job runs as a service account with read-only cluster access.",
                    "The job's only writable location is the evidence volume.",
                ]},
                {
                    "control": 'CA-7: Continuous Monitoring',
                    "text": 'The control asks the organization to develop a system-level continuous monitoring strategy and carry it out: choose metrics, set the frequencies for monitoring and for assessment, monitor and assess on an ongoing basis, analyze the results, respond, and report. NIST leaves the metrics and frequencies organization-defined. This is done using:',
                },
                {"bullets": [
                    "A Kubernetes CronJob: runs the collector on a schedule, so monitoring happens without a person starting it.",
                    "Time-stamped evidence files: each run writes a new file. Analysis, response and reporting stay with people.",
                ]},
            ],
            "production": "In the real environment the evidence volume is storage that cannot be changed after it is written, the job identity is separate from every human account, and a missed run raises an alert. The lab uses a plain volume and a short schedule.",
        },
    ],
    "steps": [
        {
            "title": "Get the gate and a working copy, and read what the gate checks",
            "learn": "Fetching the gate and reading its failure messages gives you the requirements before you write any code.",
            "takeaway": "The failure messages are the requirements in plain words.",
            "why": "Fetch the review gate from the build project before you write code. Clone the repository from Gitea, because the collector must land there.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p /workspace/grc-3/evidence-work/evidence\n"
                        "cd /workspace/grc-3/evidence-work\n"
                        "oc get configmap review-gate -n build -o jsonpath='{.data.review-gate\\.py}' > review-gate.py\n"
                        f"test -d evidence-scripts || git -c '{CRED}' clone \"$GITEA_URL/$GITEA_USER/evidence-scripts.git\"\n"
                        "cd evidence-scripts\n"
                        f"git config credential.helper '!f() {{ echo username=$GITEA_USER; echo password=$GITEA_TOKEN; }}; f'\n"
                        "git config user.name \"$GITEA_USER\"\n"
                        "git config user.email \"$GITEA_USER@example.invalid\"\n"
                        "cd ..\n"
                        "grep -n 'FAIL' review-gate.py"
                    ),
                    "label": 'Get the gate, clone the repository, and list the failure messages',
                    "intro": "You will now make a working folder, copy the gate script out of the cluster, clone the repository from Gitea, tell git who you are, and list the gate's failure messages. Running this block again is safe.",
                    "expect": "Example only. Your output will differ.\nCloning into 'evidence-scripts'...\n<n>:  ... FAIL timestamp ...\n<n>:  ... FAIL hash ...\n(one failure line for each rule in section 2.1: time stamp, hash, directory and write location, plus one for a file that cannot be read)",
                    "lines": [
                        ("mkdir -p ... and cd ...", "Makes a working folder for this module with an empty evidence folder inside it, and moves into it. Files from other modules cannot collide with yours.", "The gate script, the repository copy and your test evidence all live in this one folder, so you can find them again later."),
                        ("oc get configmap review-gate ... > review-gate.py", "Copies the gate script out of the cluster into your folder. It stays outside the repository, so it is never pushed.", "You write the collector against the gate's rules, so you need the gate in your lab shell to test with before anything is pushed."),
                        ("git -c '...' clone", "Copies the evidence-scripts repository from Gitea into the folder evidence-scripts, unless the folder is already there. The -c part gives git a helper for this one command that prints your Gitea user name and token when git asks for them.", "The collector must end up in this repository on Gitea, so you start from a working copy of it in your lab shell."),
                        ("git config credential.helper ...", "Saves the same helper in this repository so push works. The file stores the variable names, not the token value.", "Lets git push sign in without you typing the token, so the token never lands in a file or on screen."),
                        ("git config user.name / user.email", "Tells git who you are, so each commit carries a name. The address is a placeholder that stays inside this repository.", "Every commit records who made it, and git refuses to commit without a name."),
                        ("grep -n 'FAIL'", "Lists the lines in the gate that print a failure. There is one for each rule in section 2.1.", "The failure messages are the gate's rules in plain words, so reading them tells you what to build before you write anything."),
                    ],
                }
            ],
            "action": "Run the block and read the failure messages. They are the requirements you write against.",
            "checkpoint": "grep prints failure messages for the time stamp, the hash, the directory and the write location.",
        },
        {
            "title": "Read the checks for three controls and run them",
            "learn": "Reading and running the three check functions shows what each one returns before they are joined into a collector.",
            "takeaway": "Each check is one function that asks one question and returns a plain dictionary.",
            "controls": [
                {"id": 'CM-6 Configuration Settings', "how": 'You read and run the three check functions. Each returns a plain dictionary that records one setting.'},
            ],
            "why": "One function per control means a failing check can be identified by name. The lab provides collect_a.py with the three check functions. Step 3 adds the second half and joins the two halves into one collector.",
            "blocks": [
                {
                    "code": WORK + "cat collect_a.py\npython3 -m py_compile collect_a.py\npython3 -c 'import collect_a; print(collect_a.cm6_fips()); print(len(collect_a.cm7_policies()[\"names\"]), len(collect_a.cm8_namespaces()[\"names\"]))'",
                    "label": 'Read the first part of the collector and run its three checks',
                    "intro": 'You will now print collect_a.py, check that it is valid Python, and run its three checks once each against your cluster. The lab saved the file for you when you ran lab start, so there is nothing to paste.',
                    "expect": "Example only. Your names and counts will differ.\n(the text of collect_a.py)\n{'machineconfig': 'rendered-master-<id>', 'fips': True}\n<number of policies> <number of namespaces>",
                    "lines": [
                        ("cd (the working folder)", "Moves into the working folder from Step 1.", "The file collect_a.py is in this folder."),
                        ("cat collect_a.py", "Prints the file so you can read it.", "You read code before you run it, and this is the code Step 3 builds on."),
                        ("python3 -m py_compile collect_a.py", "Asks Python to read the file and check its grammar without running it. Nothing is printed when the file is valid.", "A damaged file shows up now, not later."),
                        ("python3 -c 'import collect_a; ...'", "Loads the file and calls its checks once each: it prints the FIPS answer, then the number of Kyverno policies and the number of namespaces.", "Each check runs alone here, so you see what it returns before Step 3 combines them."),
                        ("The imports at the top", "The lines that load the tools the whole script needs. One makes the fingerprint and another reads the clock.", "Doing this once at the top means every check below can use them, and Step 3 adds no new imports."),
                        ("oc_json()", "Runs oc get with JSON output and returns the result. check=True makes a failed command stop the script with an error, which is the right behavior because partial evidence must never look complete.", "All three checks ask the cluster through this one function, so one rule about errors covers every check."),
                        ("names(kind)", "Returns the sorted names of every object of one kind.", "Two of the checks only need a sorted list of names, so one small helper serves both."),
                        ("cm6_fips()", "Finds the newest control plane node configuration and records whether its fips field is true. This supports the CM-6 check.", "This is the one check that reads a setting, so the evidence shows how the cluster is configured and not only what exists."),
                        ("cm7_policies()", "Records the names of all Kyverno policies. This supports the CM-7 (Least Functionality) check.", "It records which rules the cluster checks, so a removed policy shows up later as a missing name in the evidence."),
                        ("cm8_namespaces()", "Records the names of all namespaces. This supports the CM-8 (System Component Inventory) check.", "It records what exists in the cluster, so an unexpected new namespace shows up later as an extra name in the evidence."),
                    ],
                }
            ],
            "action": "Run the block and read what each check returns. Do not run the whole script yet; it has no code that starts the checks.",
            "checkpoint": "py_compile printed nothing, and the three checks printed a FIPS answer and two counts.",
        },
        {
            "title": "Add the time, the hash and the safe write, then test it",
            "learn": "Adding the time stamp, the hash and the safe write path, then running the gate, turns check functions into evidence that can be verified.",
            "takeaway": "A PASS from the gate on your own machine costs nothing and prevents a gate failure after the push.",
            "controls": [
                {"id": 'CM-6 Configuration Settings', "how": 'You add the UTC time and SHA-256 hash. The gate confirms the collector has both before anything is pushed.'},
            ],
            "why": "collect_b.py adds the UTC time stamp, the SHA-256 hash and the safe write path. Joining both parts gives the complete collector. Run the gate on the joined collector here, before anything is pushed.",
            "blocks": [
                {
                    "code": WORK + HEREDOC_B,
                    "label": 'Add the second part of the collector',
                    "intro": 'You will now save the second part as collect_b.py, then join the two parts into collect_evidence.py inside the evidence-scripts folder. Paste all the lines at once into the lab shell. The block prints ok when collect_b.py has content.',
                    "expect": 'Example only.\nok',
                    "lines": [
                        ("cat > collect_b.py <<'EOF' ... EOF", "Saves the second part as collect_b.py.", "No editor is needed; the paste is the whole file."),
                        ("test -s collect_b.py && echo ok || echo EMPTY", "Prints ok if the file has content and EMPTY if it has none.", "Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again."),
                        ("cat collect_a.py collect_b.py > evidence-scripts/collect_evidence.py", "Joins the two parts, first part first, into the file you will push. It replaces the file each time, so repeating the step never doubles the code.", "The gate and the schedule read one complete script."),
                        ("EVIDENCE_DIR = os.environ[...]", "Reads the allowed folder from the environment. If it is missing the script stops. Nothing is hard-coded.", "The gate checks every write against this name, so reading it from the environment is what lets your script pass the safe-write rule."),
                        ("CONTROLS", "Maps each control to its function.", "The list of checks sits in one place, so adding a fourth control later means adding one line."),
                        ("The call that reads the clock", "The time stamp, taken once, in UTC and to the second.", "This is the call the gate looks for. Evidence without it cannot be dated."),
                        ("json.dumps(..., sort_keys=True)", "Turns the answers into text with a fixed key order. The same facts always give the same text, so the hash is repeatable.", "A second reader can repeat the hash only if the same facts always become the same text."),
                        ("The hash call", "The fingerprint of exactly that text.", "A second reader can later hash the same text and compare, which is the hash check in Test 2."),
                        ("os.path.join(EVIDENCE_DIR, name)", "Builds the file path from the allowed folder and a name that contains the time.", "This is how the script keeps every write inside the allowed folder, which is what the gate checks."),
                        ("The two open calls", "Writes the evidence and then a second file with only the hash. Both paths start from EVIDENCE_DIR.", "The hash file sits next to the evidence file so the two travel together and can be compared."),
                        ("print(...)", "Prints the file name, the hash and the evidence. The scheduled job's log then holds a copy.", "The scheduled job in Step 5 has no screen, so its log is where you will read the file name and hash."),
                    ],
                },
                {
                    "code": (
                        WORK +
                        "export EVIDENCE_DIR=\"$PWD/evidence\"\n"
                        "python3 evidence-scripts/collect_evidence.py | tee run.txt\n"
                        "ls evidence\n"
                        "python3 review-gate.py evidence-scripts/collect_evidence.py"
                    ),
                    "label": 'Run the collector and the gate on your own file',
                    "intro": 'You will now run the collector once, list what it wrote, and run the review gate on the script.',
                    "expect": 'Example only. Your time and hash will differ.\nFILE evidence-<time>.json\nSHA256 <64-character hash>\n{"collected_at": "<time>", "controls": {...}}\nevidence-<time>.json\nevidence-<time>.json.sha256\nPASS: timestamp, hash and write location all present',
                    "lines": [
                        ("cd (the working folder)", "Moves into the working folder.", "The script and the evidence folder are found from here."),
                        ("export EVIDENCE_DIR", "Tells the script where it may write. It is the folder you made in Step 1.", "The script refuses to run without it, so you set it before the first run."),
                        ("| tee run.txt", "Shows the output and also keeps a copy in run.txt.", "You compare the printed hash with the file later, so you keep a copy of what was printed."),
                        ("ls evidence", "Lists what the script wrote: the evidence file and its hash file.", "It confirms the files landed in the allowed folder and nowhere else."),
                        ("python3 review-gate.py ...", "Runs the review gate on your script. A pass prints PASS and exits quietly.", "This is the same check the pipeline will run after your push, so a failure here costs nothing and a failure there blocks a merge."),
                    ],
                },
            ],
            "action": "Paste the first block, then run the second.",
            "checkpoint": "The evidence folder holds two files, one for the evidence and one for its hash, and the gate prints PASS.",
        },
        {
            "title": "Make the gate a condition for merging, then push through it",
            "learn": "Creating the branch protection rule and pushing through the gate proves that only a passing script can reach main.",
            "takeaway": "Branch protection turns the gate from advice into a requirement that even an administrator must follow.",
            "controls": [
                {"id": 'CM-3 Configuration Change Control', "how": 'Main refuses direct pushes and merges only when the gate status is a success. The commit carries the gate\'s verdict.'},
            ],
            "why": "Branch protection makes the gate a requirement, not advice. Blocking admin override means no account can skip the gate. A push to Gitea starts the gate through a webhook.",
            "blocks": [
                {
                    "code": (
                        WORK +
                        "curl -s -o /dev/null -X DELETE " + AUTH + " " + STATUS_URL + "/branch_protections/main\"\n"
                        "curl -s -X POST " + AUTH + " \\\n"
                        "  " + STATUS_URL + "/branch_protections\" \\\n"
                        "  -d '{\"rule_name\":\"main\",\"enable_push\":false,\"enable_status_check\":true,\"status_check_contexts\":[\"evidence-review-gate\"],\"block_admin_merge_override\":true}' | jq '{rule_name, enable_push, enable_status_check, status_check_contexts}'"
                    ),
                    "label": 'Create the branch protection rule',
                    "intro": 'You will now ask the Gitea API to protect main so a change merges only with a passing review gate status. The first line removes an older copy of the rule, so running the block again is safe.',
                    "expect": 'Example only. {\n  "rule_name": "main",\n  "enable_push": false,\n  "enable_status_check": true,\n  "status_check_contexts": [\n    "evidence-review-gate"\n  ]\n}',
                    "lines": [
                        ("cd (the working folder)", "Moves into the working folder.", "Every block starts from the same place."),
                        ("curl -X DELETE .../branch_protections/main", "Removes a rule left from an earlier run. Output is thrown away, and a missing rule is fine.", "Lets you run this block twice without an error about a rule that already exists."),
                        ("curl -X POST .../branch_protections", "Creates the protection rule through the Gitea API (the web interface for programs).", "Doing this before any push is what turns the gate from advice into a requirement."),
                        ("enable_push false", "Nobody can push straight to main.", "Without this, a change could skip the pull request and the gate completely."),
                        ("enable_status_check true", "A pull request needs the listed status before it can merge.", "This is the setting that ties merging to the result the gate posts."),
                        ("status_check_contexts", "The name of the status the gate posts.", "It must match the name the gate posts, or Gitea would wait for a status that never arrives."),
                        ("block_admin_merge_override", "Administrators follow the same rule.", "Your own token belongs to an administrator, so without this you could merge past a failing gate and the later tests would prove nothing."),
                        ("| jq", "Prints the saved rule so you can read it back.", "Reading the saved rule back confirms what Gitea stored and not only what you sent."),
                    ],
                },
                {
                    "code": (
                        WORK +
                        "cd evidence-scripts\n"
                        "git checkout -B add-collector\n"
                        "git add collect_evidence.py\n"
                        "git commit -m \"Add evidence collector for three controls\" || true\n"
                        "git push --force origin add-collector\n"
                        "SHA=$(git rev-parse HEAD)\n"
                        "PR=$(curl -s -X POST " + AUTH + " " + STATUS_URL + "/pulls\" -d '{\"head\":\"add-collector\",\"base\":\"main\",\"title\":\"Add evidence collector\"}' | jq -r '.number')\n"
                        "while ! curl -s -H \"Authorization: token $GITEA_TOKEN\" " + STATUS_URL + "/commits/$SHA/status\" | jq -e '.statuses | length > 0' >/dev/null; do sleep 5; done\n"
                        "curl -s -H \"Authorization: token $GITEA_TOKEN\" " + STATUS_URL + "/commits/$SHA/status\" | jq '{state, checks: [.statuses[] | {context, status}]}'\n"
                        "curl -s -o /dev/null -w \"%{http_code}\\n\" -X POST " + AUTH + " " + STATUS_URL + "/pulls/$PR/merge\" -d '{\"do\":\"merge\"}'\n"
                        "cd .."
                    ),
                    "label": 'Push the collector through the gate and try to merge',
                    "intro": "You will now push your branch, open a pull request, wait for the gate's status, and try to merge. This step needs the cluster to reach the internet: the first gate run pulls a public image, which can take a minute.",
                    "expect": 'Example only. Your branch and commit details will differ.\n(git prints the new branch and the push result)\n{\n  "state": "success",\n  "checks": [\n    {\n      "context": "evidence-review-gate",\n      "status": "success"\n    }\n  ]\n}\n200',
                    "screenshot": {"file": "GRC-3-gitea-pr.png", "alt": "The Gitea pull request with the required check evidence-review-gate passed, before the merge call", "width": 6.0},
                    "lines": [
                        ("cd (the working folder), cd evidence-scripts", "Moves into the working folder, then into the repository copy.", "git acts on the repository you stand in."),
                        ("git checkout -B add-collector", "Makes a branch for your change. A branch is a line of work in git.", "The change must travel as a pull request, so it needs a branch of its own and cannot go straight onto main."),
                        ("git add / commit", "Records only the collector. The evidence folder is outside the repository. The || true keeps a repeat run going when there is nothing new to record.", "The commit is what the gate will review, and it holds only the collector."),
                        ("git push --force origin add-collector", "Sends the branch to Gitea. --force lets a repeat run replace the branch. The push triggers the gate.", "This is what starts the gate. The Gitea webhook sees the push and starts the review in the build project."),
                        ("SHA=$(git rev-parse HEAD)", "Keeps the identifier of your commit, which the gate's status is attached to.", "The gate's result is stored against this commit, so you need its identifier to look the result up."),
                        ("PR=$(curl ... /pulls ...)", "Opens a pull request, a proposed change that others review, and keeps its number.", "Gitea merges only through a pull request, so you open one for your branch and keep its number for the merge."),
                        ("while ! ... jq -e '.statuses | length > 0' ...; do sleep 5; done", "Asks Gitea for the statuses on your commit every five seconds and stops waiting as soon as the gate has posted one, instead of sleeping a fixed minute. The gate posts only its final result, so the first status is the answer. If nothing appears after a few minutes, press Ctrl+C and see the tip.", "The gate runs in the background after the push, so you wait here for its verdict before you ask to merge."),
                        ("commits/$SHA/status", "Asks Gitea for the statuses on your commit.", "This shows the verdict the gate gave your commit, which is what branch protection acts on."),
                        ("pulls/$PR/merge", "Tries to merge. Gitea allows it only if the required status passed.", "Trying the merge is the real test, because it shows Gitea accepting a change that passed."),
                    ],
                },
            ],
            "tip": "The gate is started by a webhook, so there is no button to press. If no status appears after a few minutes, press Ctrl+C, then check that pipeline runs appear with `tkn pipelinerun list -n build`.",
            "action": "Create the rule, then run the second block. Run the second block once; if it stops part way, copy the whole command and the error to your AI assistant before you repeat it.",
            "checkpoint": "The status check is success, the merge returns 200, and main now holds collect_evidence.py.",
        },
        {
            "title": "Write the CronJob that runs it on a schedule",
            "learn": "Writing and deploying the CronJob makes the collector run without a person and fetch only from main, so the schedule inherits the review.",
            "takeaway": "A collector that only runs what main holds cannot skip the gate.",
            "controls": [
                {"id": 'CA-7 Continuous Monitoring', "how": 'You write the identity, the evidence folder and the fetch-and-run command. Each run writes a time-stamped evidence file to the volume.'},
            ],
            "why": "The CronJob fetches the collector from main on every run, so only reviewed code can reach the schedule. The job's only writable location is the evidence volume. You write the identity, the evidence folder and the fetch-and-run command.",
            "blocks": [
                {
                    "code": WORK + HEREDOC_CRON_HEAD,
                    "label": 'Save the first part of the CronJob',
                    "intro": 'You will now save the first part of the CronJob as cronjob-head.yaml in the evidence-work folder. Paste all the lines at once into the lab shell. The file uses spaces only, never tabs. The block prints ok when the file has content.',
                    "expect": 'Example only.\nok',
                    "lines": [
                        ("cat > cronjob-head.yaml <<'EOF' ... EOF", "Saves everything between the first and last line as the file. The quotes around EOF keep the text as typed.", "The file ends in the middle of the container entry on purpose: you write the rest."),
                        ("test -s cronjob-head.yaml && echo ok || echo EMPTY", "Prints ok if the file has content and EMPTY if it has none.", "A doubly pasted block can leave the file empty. If EMPTY shows, paste it again."),
                        ("schedule: \"*/15 * * * *\"", "Every 15 minutes. The lab picked a short time so you can see runs quickly.", "A short gap lets you see several runs in one session instead of waiting a day."),
                        ("concurrencyPolicy: Forbid", "A new run does not start while the last one is still running.", "Two runs at once would compete for the same volume."),
                        ("volumes", "Two volumes: evidence is a persistent volume claim (a request for disk space that lasts longer than one pod) that the lab already made as evidence-pvc and that keeps the files, and oc-bin is a scratch folder that is empty at first.", "Your container entry mounts these by name, so you need the names."),
                        ("initContainers get-oc", "Copies the oc program out of the public image quay.io/openshift/origin-cli:4.22.0 into the oc-bin volume, then ends.", "The Python image has no oc and the collector calls oc. Its fields (name, image, command, volumeMounts) are the pattern for your entry."),
                        ("containers: - name: collect, image, envFrom", "Starts the main container. The image is the public Python image registry.access.redhat.com/ubi9/python-312:1, and envFrom gives the pod the Gitea address and owner name from the config map evidence-source.", "A fixed public version means every learner runs the same tools. The config map holds the address and no secret."),
                    ],
                },
                {
                    "code": WORK + HEREDOC_CRON_TAIL,
                    "label": 'Write the end of the CronJob',
                    "intro": 'You will now write the rest of the file as cronjob-tail.yaml. Replace each WRITE line with your answer, using the table below. Line up the spaces with the lines around it, because YAML reads the spaces as structure. If you paste the block unchanged, the check in 5c fails on purpose. The block prints ok when the file has content; if EMPTY shows, type it again.',
                    "expect": 'Example only.\nok',
                    "lines": [
                        ("env EVIDENCE_DIR", "Write the folder the evidence volume appears at inside the container: /evidence. The same word goes in the volume mount below.", "The collector reads this name and the gate checks that every write starts from it, so the pod and the script must agree on one folder."),
                        ("env PATH (already filled in)", "Puts the oc-bin folder first in PATH, the list of folders the shell searches for programs, so the shell finds the oc that get-oc left there.", "Without it the collector cannot find oc, because oc is not in the Python image."),
                        ("args", "Write one line for the shell to run. Use curl with -sf (-s is quiet, -f fails on a web error) to fetch collect_evidence.py from the main branch and save it as /tmp/collect_evidence.py. The address is $GITEA_URL/$GITEA_USER/evidence-scripts/raw/branch/main/collect_evidence.py. Join the next command to it with && so it runs only if the download worked: python3 /tmp/collect_evidence.py.", "Fetching from main on every run is what makes the schedule inherit the review, and && stops a failed download from running an old or empty file. Write the two variables as shown; the pod fills them in."),
                        ("volumeMounts evidence", "Write the same folder as EVIDENCE_DIR for mountPath.", "A path that differs from EVIDENCE_DIR would send the evidence to the pod's own disk, which is lost when the pod ends."),
                        ("serviceAccountName", "Write the line serviceAccountName: evidence-runner, the read-only identity the lab made. It goes at the same indent as containers: above, after the container entry.", "The job holds read access only, so a flaw in the collector cannot change the cluster."),
                    ],
                },
                {
                    "code": (
                        WORK +
                        "cat cronjob-head.yaml cronjob-tail.yaml > evidence-cronjob.yaml\n"
                        "python3 check-cronjob.py evidence-cronjob.yaml\n"
                        "sed 's/serviceAccountName: evidence-runner/serviceAccountName: default/' evidence-cronjob.yaml > bad-cronjob.yaml\n"
                        "python3 check-cronjob.py bad-cronjob.yaml | grep -v '^PASS'\n"
                        "oc auth can-i list namespaces --as=system:serviceaccount:build:evidence-runner\n"
                        "oc auth can-i list namespaces --as=system:serviceaccount:build:default"
                    ),
                    "label": 'Check your file against the spec, then check the check',
                    "intro": "You will now join your two parts, run the lab's check on the result, run the same check on a copy with the wrong identity, and ask the cluster what each identity may read. If a line starts with FAIL, read the message, which names the property that is wrong, fix it by running the 5b block again with your corrected answers, and then run this block again. An error right after the join usually means cronjob-tail.yaml or cronjob-head.yaml is empty: write it again.",
                    "expect": "Example only. A file that follows the spec prints PASS for every property.\nPASS service account\nPASS evidence folder\nPASS path holds oc\nPASS volume mount\nPASS fetch from main\nPASS address from variables\nPASS stop on bad download\nPASS runs the collector\nFAIL service account: serviceAccountName must be evidence-runner\nyes\n(a warning that namespaces is not namespace scoped may print before each answer; it is harmless)\nno",
                    "lines": [
                        ("cat cronjob-head.yaml cronjob-tail.yaml > evidence-cronjob.yaml", "Joins the two parts, the lab's first and yours second, into the file you will apply. It replaces the file each time, so repeating it is safe.", "oc reads one complete file."),
                        ("python3 check-cronjob.py evidence-cronjob.yaml", "Reads your file and prints PASS or FAIL for eight properties: identity, evidence folder, PATH, volume mount, where the collector is fetched from, that the address comes from variables, that a failed download stops the run, and that the collector is run.", "This is the known answer your file is held to. It reads the file only and does not touch the cluster."),
                        ("sed ... default ... > bad-cronjob.yaml", "Makes a copy that runs as the default service account instead of evidence-runner.", "The check should fail on this copy, because its identity is wrong."),
                        ("check-cronjob.py bad-cronjob.yaml | grep -v '^PASS'", "Runs the check on the bad copy and hides the PASS lines, so only the failure shows.", "A check that has only been seen to pass is not proven. This shows it can say no."),
                        ("oc auth can-i ... --as=...evidence-runner", "Asks the cluster whether the evidence-runner service account may list namespaces. It answers yes.", "The collector needs this read access to do its job."),
                        ("oc auth can-i ... --as=...default", "Asks the same about the default service account. It answers no.", "It shows why the identity line matters: the bad copy would start, and then every check in the collector would fail with a permission error."),
                    ],
                },
                {
                    "code": (
                        WORK +
                        "oc get configmap cronjob-reference -n build -o jsonpath='{.data.cronjob-tail\\.yaml}'"
                    ),
                    "label": 'If you are stuck, or when you have passed: see the reference answer',
                    "intro": 'You will now print the reference tail from the lab and compare it with your own. Do not open the reference until you have tried and run the check in 5c at least once. Yours may differ in wording and still be right if the check passes.',
                    "expect": "Example only. The text of the reference tail, from env: to serviceAccountName: evidence-runner.",
                    "lines": [
                        ("oc get configmap cronjob-reference ...", "Prints the lab's reference version of the end of the CronJob from the config map the lab saved.", "It lets you see one correct version after you have tried your own."),
                        ("-o jsonpath='{.data.cronjob-tail\\.yaml}'", "Picks the one stored file out of the config map. The backslash keeps the dot in the name from being read as a step in the path.", "Prints only the file text and nothing else."),
                    ],
                },
                {
                    "code": (
                        WORK +
                        "oc apply --dry-run=server -f evidence-cronjob.yaml\n"
                        "oc apply -f evidence-cronjob.yaml\n"
                        "oc delete job evidence-manual -n build --ignore-not-found\n"
                        "oc get cronjob evidence-collect -n build -o jsonpath='{.spec.jobTemplate.spec.template.spec.serviceAccountName}{\"\\n\"}'\n"
                        "oc create job evidence-manual --from=cronjob/evidence-collect -n build\n"
                        "oc wait --for=condition=complete job/evidence-manual -n build --timeout=180s\n"
                        "oc logs job/evidence-manual -n build > job.txt\n"
                        "head -n 2 job.txt"
                    ),
                    "label": 'Apply the CronJob and run it once',
                    "intro": 'You will now check the CronJob file with the cluster, apply it, start one run by hand, and read the first lines of the log. This step needs the cluster to reach the internet: the first run pulls two public images, which can take a minute.',
                    "expect": 'Example only. Your names and hash will differ.\ncronjob.batch/evidence-collect created (server dry run)\ncronjob.batch/evidence-collect created\nevidence-runner\njob.batch/evidence-manual created\njob.batch/evidence-manual condition met\n(a line starting Defaulted container may print first; it is harmless)\nFILE evidence-<time>.json\nSHA256 <64-character hash>',
                    "lines": [
                        ("cd (the working folder)", "Moves into the working folder, where the file is.", "oc reads evidence-cronjob.yaml from here."),
                        ("--dry-run=server", "Asks the cluster to check the file without saving it.", "The cluster knows rules the local check does not, such as which fields exist, so a mistake shows up now, before anything is saved."),
                        ("oc delete job evidence-manual ... --ignore-not-found", "Removes a manual job left from an earlier run, if there is one.", "Lets you run this block twice."),
                        ("oc get cronjob ... -o jsonpath=...serviceAccountName", "Reads back from the cluster the identity the CronJob will run as.", "It shows the object the cluster holds is the one you wrote: evidence-runner, not default."),
                        ("oc create job --from=cronjob/...", "Starts one run now, the same way the schedule would.", "You can check the result now instead of waiting for the next scheduled time."),
                        ("oc wait --for=condition=complete", "Waits until the job finishes, up to three minutes. The first run is slower because the images are pulled.", "The log is complete only once the job has finished, so you wait before reading it."),
                        ("oc logs job/... > job.txt", "Keeps the job's log. The script printed the file name, the hash and the evidence.", "The hash check in Test 2 reads the hash from this saved log."),
                        ("head -n 2", "Shows the file name and the hash.", "These two lines are the file name and the hash that the hash check in Test 2 checks."),
                    ],
                },
            ],
            "action": "Save the first part, write the end from the table, run the check until every line says PASS, then apply the file and run the job once.",
            "checkpoint": "Every property prints PASS for your file and the bad copy prints FAIL for the service account. The job completes, and the first two lines of job.txt are FILE with an evidence name and SHA256 with 64 characters.",
        },
    ],
    "verify": [
        {
            "kind": "positive",
            "title": "The scheduled evidence can be read from the volume",
            "controls": [
                {"id": 'CA-7 Continuous Monitoring', "how": 'You read the newest file from the volume and check its time. A file less than 15 minutes old shows runs are arriving on schedule.'},
            ],
            "why": "The scheduled job writes its evidence to a volume, not to your folder, so you cannot just open a file. Mount the volume read-only in a short-lived pod, list the files and read the newest one. Looking at evidence must never be able to change it.",
            "code": (
                "oc get cronjob evidence-collect -n build\n"
                "oc delete pod evidence-view -n build --ignore-not-found\n"
                "oc run evidence-view -n build --restart=Never \\\n"
                "  --image=registry.access.redhat.com/ubi9/ubi-minimal:9.5 \\\n"
                "  --overrides='{\"spec\":{\"containers\":[{\"name\":\"evidence-view\",\"image\":\"registry.access.redhat.com/ubi9/ubi-minimal:9.5\",\"command\":[\"sleep\",\"300\"],\"securityContext\":{\"allowPrivilegeEscalation\":false,\"capabilities\":{\"drop\":[\"ALL\"]}},\"volumeMounts\":[{\"name\":\"evidence\",\"mountPath\":\"/evidence\",\"readOnly\":true}]}],\"volumes\":[{\"name\":\"evidence\",\"persistentVolumeClaim\":{\"claimName\":\"evidence-pvc\",\"readOnly\":true}}]}}'\n"
                "oc wait --for=condition=Ready pod/evidence-view -n build --timeout=120s\n"
                "oc exec evidence-view -n build -- ls -l /evidence\n"
                "LATEST=$(oc exec evidence-view -n build -- sh -c 'ls -t /evidence/*.json | head -n 1')\n"
                "oc exec evidence-view -n build -- cat \"$LATEST\" | jq -r '.collected_at'\n"
                "oc exec evidence-view -n build -- sha256sum \"$LATEST\"\n"
                "oc delete pod evidence-view -n build"
            ),
            "expect": (
                "Example only. Names, sizes and hashes differ. The pod can take about a minute to become ready.\n"
                "NAME               SCHEDULE       TIMEZONE   SUSPEND   ACTIVE   LAST SCHEDULE   AGE\nevidence-collect   */15 * * * *   <none>     False     0        <none>          <age>\n(LAST SCHEDULE is <none> until the first scheduled run; only the manual job has run so far)\n"
                "pod/evidence-view created\npod/evidence-view condition met\n"
                "-rw-r--r--. 1 1000840000 1000840000 1204 Nov  6 14:15 evidence-20261106T141500Z.json\n"
                "-rw-r--r--. 1 1000840000 1000840000   65 Nov  6 14:15 evidence-20261106T141500Z.json.sha256\ndrwx------. 2 root root 16384 Nov  6 14:00 lost+found\n"
                "2026-11-06T14:15:00Z\n<64-character hash>  /evidence/evidence-20261106T141500Z.json\npod \"evidence-view\" deleted from build namespace"
            ),
            "lines": [
                ("oc get cronjob evidence-collect", "Shows the schedule and when it last ran.", "A schedule that stopped is a gap in the evidence."),
                ("oc run evidence-view --overrides=...", "Starts a pod that sleeps for five minutes with the claim evidence-pvc mounted at /evidence.", "A volume can only be read from a pod that mounts it."),
                ("readOnly: true", "Mounts the volume so nothing can be written to it, in the claim and in the mount.", "Looking at evidence must never be able to change it."),
                ("ls -l /evidence", "Lists every evidence file and its hash file.", "One pair per run is what you expect."),
                ("ls -t ... | head -n 1, jq .collected_at", "Picks the newest evidence file and prints when it was collected.", "A time more than 15 minutes old means a run was missed."),
                ("sha256sum", "Hashes the file as it sits on the volume.", "It should match the hash in the hash file beside it."),
                ("oc delete pod evidence-view", "Removes the viewer pod.", "Nothing is left running."),
            ],
            "checkpoint": "The volume holds an evidence file and a hash file for each run, the newest collected_at is less than 15 minutes old, and the viewer pod is deleted.",
        },
        {
            "kind": "positive",
            "title": "The hash in the log matches the evidence",
            "controls": [
                {"id": 'CM-6 Configuration Settings', "how": 'You hash the evidence text from the log with openssl, a second tool, compare it with the hash the collector logged, and check that the time ends in Z, which means UTC. A match shows the logged hash really belongs to that text.'},
            ],
            "why": "A hash in the log proves nothing until you check it. Take the evidence text from the log, hash it yourself with a different tool, and compare the two values. Check that the time stamp ends in Z, which means UTC.",
            "code": (
                WORK +
                "grep '^SHA256' job.txt\n"
                "BODY=$(grep '^{' job.txt)\n"
                "printf '%s' \"$BODY\" | openssl dgst -sha256\n"
                "printf '%s' \"$BODY\" | jq -r '.collected_at'"
            ),
            "expect": (
                "Example only. Your values will differ.\n"
                "SHA256 b8d339e419eb8a2e2d4bb65a0983d4e8cb51b06478172f56bf5a34b92f04ed37\n"
                "SHA2-256(stdin)= b8d339e419eb8a2e2d4bb65a0983d4e8cb51b06478172f56bf5a34b92f04ed37\n"
                "2026-10-29T21:29:18Z"
            ),
            "lines": [
                ("cd (the working folder)", "Moves into the working folder, where job.txt from Step 5 is.", "Both commands read that log."),
                ("grep '^SHA256' job.txt", "Prints the hash the collector logged.", "This is the claim you are about to check."),
                ("openssl ... -sha256", "Hashes the evidence text with a different tool.", "A second tool that agrees is better proof than the script agreeing with itself."),
                ("jq -r '.collected_at'", "Prints the time stamp. A Z at the end means UTC.", "Evidence you cannot date is weak evidence."),
            ],
            "checkpoint": "The two 64-character values are identical, and the time ends in Z, which means UTC.",
        },
        {
            "kind": "negative",
            "title": "The gate rejects a script with no hash, no time stamp, or a write outside the evidence folder",
            "controls": [
                {"id": 'CM-3 Configuration Change Control', "how": 'You make three broken copies of the script and run the same gate on each. Each copy fails with a message that names the missing property, which shows the gate can say no.'},
            ],
            "why": "A gate you have only seen pass is not proven. Make three broken copies of your script, each missing one required property, and run the same gate on each. Each broken copy must fail with a message that says why.",
            "code": (
                WORK +
                "sed 's/hashlib.sha256/hashlib.md5/' evidence-scripts/collect_evidence.py > bad-hash.py\n"
                "python3 review-gate.py bad-hash.py\n"
                "sed 's/datetime.now(timezone.utc)/datetime.fromtimestamp(0, timezone.utc)/' evidence-scripts/collect_evidence.py > bad-time.py\n"
                "python3 review-gate.py bad-time.py\n"
                "sed 's#EVIDENCE_DIR, name#\"/tmp\", name#' evidence-scripts/collect_evidence.py > bad-write.py\n"
                "python3 review-gate.py bad-write.py"
            ),
            "expect": (
                "Example only. Line numbers will differ.\n"
                "FAIL hash: no hashlib.sha256(...).hexdigest(), so the evidence cannot be checked later\n"
                "FAIL timestamp: no call to datetime.now, so the evidence has no collection time\n"
                "FAIL write: line 41 writes to a path not built from EVIDENCE_DIR\n"
                "FAIL write: line 43 writes to a path not built from EVIDENCE_DIR"
            ),
            "lines": [
                ("cd (the working folder)", "Moves into the working folder, where the gate and your script are.", "The relative file names are found from here."),
                ("sed ... > bad-hash.py", "Makes a copy that uses a different hash function.", "The fault is a missing SHA-256 hash."),
                ("sed ... > bad-time.py", "Makes a copy that uses a fixed time instead of the clock.", "The fault is a missing time stamp."),
                ("sed ... > bad-write.py", "Makes a copy that writes to /tmp instead of the evidence folder.", "The fault is a write outside the allowed folder."),
                ("python3 review-gate.py bad-*.py", "Runs the gate on each copy.", "Each must print a FAIL line that names the problem: a gate that can say no is proven."),
            ],
            "checkpoint": "Each broken copy prints at least one FAIL line that names the missing property, and the write copy names the lines that write. A copy that prints PASS means the gate has a hole: stop and report it.",
        },
        {
            "kind": "negative",
            "title": "A pull request with a weakened script cannot merge",
            "controls": [
                {"id": 'CM-3 Configuration Change Control', "how": 'You push a weakened script as a pull request and try to merge it. The failed status and the refused merge show that a disapproved change cannot reach main.'},
            ],
            "why": "The gate on a pushed pull request proves the rule is enforced, not only checked locally. Push a version that swaps the hash function and try to merge it. The webhook should start the gate, the gate should mark the commit as failed, and Gitea should refuse the merge.",
            "code": (
                WORK +
                "cd evidence-scripts\n"
                "git checkout main\n"
                "git pull origin main\n"
                "git checkout -B weaken-hash\n"
                "sed -i 's/hashlib.sha256/hashlib.md5/' collect_evidence.py\n"
                "git commit -am \"Test: use a different hash\"\n"
                "git push --force origin weaken-hash\n"
                "SHA=$(git rev-parse HEAD)\n"
                "PR=$(curl -s -X POST " + AUTH + " " + STATUS_URL + "/pulls\" -d '{\"head\":\"weaken-hash\",\"base\":\"main\",\"title\":\"Test: weaker hash\"}' | jq -r '.number')\n"
                "while ! curl -s -H \"Authorization: token $GITEA_TOKEN\" " + STATUS_URL + "/commits/$SHA/status\" | jq -e '.statuses | length > 0' >/dev/null; do sleep 5; done\n"
                "curl -s -H \"Authorization: token $GITEA_TOKEN\" " + STATUS_URL + "/commits/$SHA/status\" | jq -r '.statuses[] | \"\\(.context) \\(.status)\"'\n"
                "curl -s -o /dev/null -w \"%{http_code}\\n\" -X POST " + AUTH + " " + STATUS_URL + "/pulls/$PR/merge\" -d '{\"do\":\"merge\"}'\n"
                "curl -s -X PATCH " + AUTH + " " + STATUS_URL + "/pulls/$PR\" -d '{\"state\":\"closed\"}' | jq -r '.state'\n"
                "git checkout main\n"
                "cd .."
            ),
            "expect": (
                "Example only. The refusal code depends on your Gitea release.\n"
                "evidence-review-gate failure\n"
                "405\n"
                "closed"
            ),
            "checkpoint": "The status is failure and the merge is refused with a 4xx code, not 200. The last command closes the pull request and prints closed; main is left as it is. To read the reason the gate gave, run `tkn pipelinerun logs --last -n build`.",
            "lines": [
                ("cd (the working folder), git checkout -B weaken-hash", "Moves into the repository copy and makes a branch from the up-to-date main.", "The weak change must travel as a pull request like any other."),
                ("sed -i ... (the hash call)", "Weakens the script by swapping the hash function.", "This is the change the gate must refuse."),
                ("git push --force origin weaken-hash", "Sends the branch to Gitea and starts the gate.", "The webhook, not you, starts the review."),
                ("while ! ... status ...; do sleep 5; done", "Waits until the gate has posted a status on the commit.", "You read the verdict only after it exists."),
                ("evidence-review-gate failure", "The gate marked the commit as failed.", "Branch protection reads this status."),
                ("pulls/$PR/merge prints a 4xx code", "Gitea refuses the merge. 200 would mean the protection is not working.", "Proves the rule is enforced, not only advised."),
                ("PATCH ... closed", "Closes the pull request and leaves main as it was.", "Cleans up after the test."),
            ],
        },
    ],
    "glossary": [
        ("Gitea", "The in-lab git server."),
        ("Pull request", "A proposed change that others review before it joins a branch."),
        ("Tekton Triggers", "The part of OpenShift Pipelines that starts a pipeline when a web call arrives."),
        ("EventListener", "A Tekton Triggers object that receives web calls and starts pipeline runs."),
        ("Hash", "A fixed-length fingerprint of content. The same content always gives the same hash."),
        ("Persistent volume claim", "A request for disk space that lasts longer than one pod."),
        ("Service account", "An identity for a program instead of a person."),
    ],
    "design": [
        {
            "decision": "A static gate that never runs the script, kept outside the repository",
            "how": "The review gate parses the collector as text, looks for a clock call, a hash call and write paths built from the evidence folder, and never executes it. The gate script and its credentials live in the build project, not in the repository under review.",
            "why": "Unreviewed code would otherwise run with the gate's cluster access, and an author who could edit the gate in the same pull request could switch it off.",
            "alternatives": "Advantage of running the submitted script in a sandbox (an isolated test space): it catches behavior that reading the text misses. Drawback: it needs a fully isolated space that the lab does not have, and any gap in it would run code nobody has reviewed with real access.",
        },
        {
            "decision": "The schedule runs only what main holds, and main needs a passing status",
            "how": "Branch protection on main requires the gate's commit status and blocks administrator override. The scheduled job downloads the collector from main on every run.",
            "why": "Only code that passed the gate and merged can ever run, so the schedule inherits the change control.",
            "alternatives": "Advantage of building the script into the job image or a config map: the job does not depend on Gitea being reachable at run time. Drawback: updating it becomes a separate manual step outside the reviewed path, and the running copy can drift from main.",
        },
    ],
    "next": "Next module: GRC-4 Evidence in the Delivery Pipeline: build a pipeline that scans, checks policy, and signs one evidence bundle per run, so a changed bundle can be detected.",
}

MODULE["portability"] = {
    "lead": "The table shows what each part of the lab setup becomes on other platforms and what you change:",
    "bullets": [
        "Works on any OpenShift 4.x cluster with OpenShift Pipelines and a git server that supports webhooks and branch protection (Gitea, GitHub, GitLab).",
        "Change these lab values first: the Gitea URL and credentials, the build project, the evidence volume claim name, and the schedule (*/15 * * * * is a lab value).",
        "On non-OpenShift Kubernetes the pipeline runner can be any pipeline tool that accepts webhooks and posts commit statuses; the collector script itself is portable.",
        "The review gate reads Python text with Python's own parser. Adapting it for another language needs a parser for that language.",
    ],
    "headers": ["Check/part", "In this lab (OpenShift + Gitea)", "On other platforms", "What you change"],
    "rows": [
        ("Review gate trigger", "Gitea push webhook to Tekton Triggers EventListener", "GitHub Actions, GitLab CI, or any CI with webhook support", "The trigger mechanism and status API calls."),
        ("Branch protection", "Gitea branch protection with status check context", "GitHub or GitLab required status checks", "The API calls to create the protection rule."),
        ("Collector script", "Python reading oc get output", "Any language that calls kubectl or the cluster API", "Replace oc with kubectl and adjust check functions."),
        ("Scheduled job", "Kubernetes CronJob in the build project", "GitHub Actions schedule, cron, or Argo Workflows", "The job spec and fetch command."),
        ("Evidence volume", "PersistentVolumeClaim evidence-pvc", "Object storage, NFS, or any persistent volume", "The mount path and PVC name."),
    ],
}
