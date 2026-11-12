"""ARC-3: Choose an Admission Mode (security architecture, level 3)."""

NIST = "nist-sp-800-53r5-full.md"

ARC = "\"$HOME/arc"

MEASURE_PY = (
    "import json\n"
    "import os\n"
    "import statistics\n"
    "import subprocess\n"
    "import sys\n"
    "import time\n"
    "\n"
    "mode = sys.argv[1]\n"
    "cases = os.path.expanduser(\"~/arc/cases\")\n"
    "names = [\"ok\", \"root\", \"latest\", \"nolimits\"]\n"
    "SAMPLES = 25\n"
    "\n"
    "\n"
    "def admit(name):\n"
    "    cmd = [\"oc\", \"create\", \"-n\", \"arc-measure\", \"--dry-run=server\", \"-f\", \"%s/%s.yaml\" % (cases, name)]\n"
    "    start = time.perf_counter()\n"
    "    done = subprocess.run(cmd, capture_output=True, text=True)\n"
    "    return (time.perf_counter() - start) * 1000, done.returncode == 0\n"
    "\n"
    "\n"
    "outcomes = {n: (\"allowed\" if admit(n)[1] else \"denied\") for n in names}\n"
    "samples = sorted([admit(\"ok\")[0] for _ in range(SAMPLES)][1:])\n"
    "print(json.dumps({\n"
    "    \"mode\": mode,\n"
    "    \"n\": len(samples),\n"
    "    \"median_ms\": round(statistics.median(samples), 1),\n"
    "    \"p95_ms\": round(samples[int(len(samples) * 0.95)], 1),\n"
    "    \"outcomes\": outcomes,\n"
    "}))"
)

MODULE = {
    "intent_at_end": True,
    "id": "ARC-3",
    "slug": "Choose",
    "title": "Choose an Admission Mode",
    "draft": (
        "Run live on 2026-11-10 (see live-run/findings-ARC-3.md). Confirmed: oc create --dry-run=server goes through the Kyverno webhook, the report resource is policyreport (Kyverno 1.19.2 puts the pod name in the report scope, not in each result, and the supplied snapshot.py reads it there), the root test pod is not given runAsNonRoot by the security context admission, and the :latest negative cases run. "
        "In Enforce mode the load deployment is created with no pods and the replica set reports FailedCreate events; Kyverno also records policy events for arc-measure. The exact event reason string was not confirmed. The settle time was enough for reports and metrics to catch up. "
        "Timings include the oc client start-up and are noisy when other work runs on the cluster, so read them as relative. Every oc get clusterpolicy prints a deprecation warning. "
        "The lab chooses 25 timing samples, 20 load pods and a 60 second settle time. kit/cases/latest.yaml and kit/load.yaml deliberately use the :latest image tag as negative cases; every other image is pinned to ubi-minimal 9.5."
    ),
    "controls": ["SA-8", "CM-7", "AU-12"],
    "mentions": [],
    "unit_values_ok": ["60 seconds", "60 second", "15 seconds"],
    "minutes": {"hands_on": 38, "verify": 17},
    "tools": ["OpenShift Container Platform", "Kyverno (free, open source)", "oc", "jq", "python3"],
    "tool_why": True,
    "hide_draft": True,
    "hover": True,
    "terms_at_end": True,
    "diagrams": [
        {
            "id": "measure",
            "title": "One choice, three conditions, one table",
            "caption": "This is the lab (test) setup: you send test requests and read back what each condition lets through and records, a review gate checks your script, and a supplied script prints the three conditions side by side. In production you would not switch the live policy or create load pods: you would run this test on a non-production cluster, then set the chosen mode through a reviewed change. Each step below adds one part, drawn with thick lines.",
            "per_step": True,
            "rankdir": "LR",
            "setup": [
                ("Lab shell", "A container on your laptop", "The test script, the review gate and the comparison all run here and keep their files here, so every condition is tested from the same place."),
                ("Project arc-measure", "On your cluster", "The test pods and load pods live here, so the test touches only this project."),
                ("Kyverno policy arc-baseline", "A cluster-wide object checked by Kyverno", "One policy in two modes lets you change only the mode between conditions."),
                ("Kyverno", "Project kyverno on your cluster", "It is the platform tool you are choosing a mode for."),
                ("Result files", "The results folder in the arc folder in lab shell", "One file for each condition lets the table and the requirement check read the same results."),
            ],
            "step_notes": {
                1: "The lab starts with a project, four test pod files in your arc folder and the Kyverno policy as an Audit file and an Enforce file. No policy is applied to the cluster yet.",
                2: "You write the test script in your arc folder in lab shell, and the review gate reads it before anything runs.",
                3: "For each condition you switch the policy in the cluster, send test requests from lab shell to the cluster, add 20 load pods to the project, and save what each mode refused and recorded in result files in your arc folder.",
                4: "The comparison script reads the result files in your arc folder and prints the table of outcomes and records on your screen. A jq filter over the same files then prints the name of the condition that meets the requirement.",
            },
            "zones": [
                {"id": "cluster", "icon": "aws/group-AWS-Cloud", "label": "Your cluster (your OpenShift cluster, in AWS)", "kind": "boundary"},
                {"id": "proj", "icon": "brands/openshift", "label": "Project arc-measure", "parent": "cluster", "kind": "group"},
                {"id": "kyv", "icon": "brands/openshift", "label": "Project kyverno", "parent": "cluster", "kind": "group", "labeljust": "r"},
                {"id": "shell", "label": "Your lab shell", "kind": "boundary"},
            ],
            "key": {"k8s/pod": "Kubernetes pod", "brands/python": "Python script", "brands/json": "JSON file", "brands/openshift": "OpenShift project", "aws/group-AWS-Cloud": "AWS Cloud"},
            "nodes": [
                {"id": "cases", "title": "Four test pod files", "sub": "In the arc folder, each breaks one rule", "zone": "shell"},
                {"id": "load", "title": "Twenty load pods", "icon": "k8s/pod", "sub": "Kubernetes pods that break all rules", "zone": "proj", "s": 3},
                {"id": "pol", "title": "Kyverno policy arc-baseline", "sub": "Kyverno policy: none, Audit or Enforce", "zone": "kyv"},
                {"id": "timer", "title": "Test script", "icon": "brands/python", "sub": "Python script measure.py you write", "zone": "shell", "s": 2},
                {"id": "gate", "title": "Review gate", "icon": "brands/python", "sub": "Python script review_gate.py", "zone": "shell", "kind": "warn", "s": 2},
                {"id": "res", "title": "Result files", "icon": "brands/json", "sub": "JSON files, one per condition", "zone": "shell", "s": 3},
                {"id": "cmp", "title": "Comparison table", "sub": "Outcomes and records", "zone": "shell", "kind": "ok", "s": 4},
                {"id": "req", "title": "Requirement check", "sub": "A jq filter you can run again", "zone": "shell", "kind": "ok", "s": 4},
            ],
            "edges": [
                {"a": "cases", "b": "pol", "label": "Dry runs checked by", "s": 1},
                {"a": "gate", "b": "timer", "label": "Reviews", "kind": "warn", "s": 2},
                {"a": "timer", "b": "cases", "label": "Sends as dry runs", "s": 3},
                {"a": "load", "b": "pol", "label": "Recorded or refused", "s": 3},
                {"a": "timer", "b": "res", "label": "Writes", "s": 3},
                {"a": "res", "b": "cmp", "label": "Read", "kind": "ok", "s": 4},
                {"a": "res", "b": "req", "label": "Filtered", "kind": "ok", "s": 4},
            ],
            "why_built": (
                "You work in lab shell on your laptop, and the tool you are choosing a mode for runs on your own cluster. "
                "This module adds a project named arc-measure, four test pod files in your arc folder, and a Kyverno policy that you switch between no policy, Audit and Enforce, so the same requests can be sent under three conditions. "
                "The test script and the review gate run in lab shell because they only send requests and read files, so they cannot change the cluster except through the dry-run requests and the load pods you ask for. "
                "The result files stay in lab shell, one for each condition, so the comparison script and the requirement check read the same results. "
                "Kyverno runs in its own project on the cluster, apart from the project it guards. "
            ),
            "reading": [
                "1. Four test pod files: pod definitions in your arc folder. One is fine and three each break one rule (root user, latest image tag, no limits). They are sent as dry runs, so no pod is created.",
                "2. Twenty load pods: pods in the arc-measure project that break every rule on purpose, so each mode has something to record.",
                "3. Kyverno policy arc-baseline: the one policy you switch between no policy, Audit and Enforce. It checks every request to create a pod in arc-measure.",
                "4. Test script: the Python script measure.py you write. It sends the four test requests and records whether each was allowed or denied.",
                "5. Review gate: the supplied script review_gate.py. It reads your test script and fails it if it makes a common mistake.",
                "6. Result files: one JSON file for each condition, holding what each request did and what was recorded.",
                "7. Comparison table: printed by the supplied compare.py, with one column for each condition.",
                "8. Requirement check: a jq filter over the result files that prints the name of each condition that meets the requirement. You can run it again whenever the cluster changes.",
            ],
        },
    ],
    "prereq": [
        "ENG-0 Terminal, Git and Your Lab (typing commands in lab shell, making a file with a heredoc, reading oc output)",
    ],
    "lab_needs": [],
    "lab": {
        "start": "lab start arc-3",
        "env": [],
    },
    "objectives": [
        {"label": "Skill", "text": "Test the Audit and Enforce modes of one Kyverno policy against a no-policy baseline, read what each mode lets through and records, and write the choice as a check you can rerun."},
        {"label": "Tools", "text": "Kyverno policy arc-baseline is the rule being tested, `oc` sends the test requests as dry runs, a Python test script you write collects the outcomes, a review gate script fails a careless test script, and `jq` turns the results into the name of the condition that meets the requirement."},
        {"label": "Security Function", "text": "Proves what each mode does before it is chosen. The table shows which rule-breaking requests Audit lets through and Enforce blocks, and which records each mode leaves behind."},
        {"label": "NIST SA-8 Security and Privacy Engineering Principles", "text": "The test script, the review gate and a jq filter apply one principle: test each option the same way before choosing. The jq filter makes the choice a check anyone can rerun."},
        {"label": "NIST CM-7 Least Functionality", "text": "Kyverno policy arc-baseline restricts what a pod may ask for, and four test pods show which requests Audit lets through and Enforce blocks."},
        {"label": "NIST AU-12 Audit Record Generation", "text": "Kyverno policy reports and cluster events are the records each mode generates, and the snapshot script counts them after 20 load pods."},
    ],
    "requirement": (
        "A security design choice should rest on what you can show, not on habit. "
        "The choice here is whether the Kyverno rules for one project should run in Audit mode, which records a violation, or in Enforce mode, which refuses the request. "
        "You test both against a no-policy baseline and turn the table into a check on one requirement."
    ),
    "requirement_bullets": [
        "Purpose: choose between Audit and Enforce mode from test results instead of habit (SA-8, CM-7, AU-12).",
        "You write a short Python test script that sends four pod requests to the cluster as dry runs, and a review gate checks that test script.",
        "You run the test script under three conditions (no policy, Audit, Enforce), read the table compare.py prints, and turn the table into a requirement check with jq.",
    ],
    "mapping": [
        {
            "control": "SA-8 Security and Privacy Engineering Principles",
            "plain": "Design choices follow stated engineering principles and are made before the system is built or changed.",
            "source": "NIST",
            "tool": "The test script, the review gate, the comparison script and a jq filter over the result files. Explained in section 2.1.",
            "covered": "Section 3, Steps 2 to 4: write and gate the test script, collect three conditions, read back the table and write the criterion as a check. Section 4, Test 2: the comparison refuses incomplete data.",
            "cite": [
                {"file": NIST, "quote": "Apply the following systems security and privacy engineering principles in the specification, design, development, implementation, and modification of the system and system components"},
            ],
        },
        {
            "control": "CM-7 Least Functionality",
            "plain": "Allow only what the mission needs and block the rest.",
            "source": "NIST",
            "tool": "Kyverno policy arc-baseline in Audit and Enforce mode, with four test pods that each break one rule. Explained in section 2.1.",
            "covered": "Section 3, Step 3: collect the outcome of each test request under each condition. Section 3, Step 4: print the table of outcomes.",
            "cite": [
                {"file": NIST, "quote": "Prohibit or restrict the use of the following functions, ports, protocols, software, and/or services"},
            ],
        },
        {
            "control": "AU-12 Audit Record Generation",
            "plain": "The system produces records of the events that matter.",
            "source": "NIST",
            "tool": "Kyverno policy reports and cluster events, counted by the kit script snapshot.py. Explained in section 2.1.",
            "covered": "Section 3, Step 3: snapshot.py counts what each mode recorded. Section 3, Step 4: read the records rows of the table. Section 4, Test 1: the record count follows from the load.",
            "cite": [
                {"file": NIST, "quote": "Provide audit record generation capability for the event types the system is capable of"},
            ],
        },
    ],
    "intent": [
        {
            "control": "SA-8 Security and Privacy Engineering Principles",
            "feared": "A design choice is made because it sounds safer or because a colleague preferred it, and it later turns out to block real work or to protect nothing.",
            "scope": "One well-bounded choice in the system design, here the mode of the project's admission rules.",
            "question": "What would you test to know which option is right, and what result would change your mind?",
            "evidence": "The criteria, the test results for each option under the same test, and the check that applies the criteria.",
            "sufficient": "Each option is tested the same way, including a condition with nothing applied as a baseline. NIST leaves the principles organization-defined. The lab chooses a simple one: test each option under the same test before choosing.",
            "tieoff": "Someone owns the criteria and reruns the test when the tool or the cluster changes.",
            "tool": "The test script, the review gate, the comparison and the criterion check (Steps 2 to 4).",
        },
        {
            "control": "CM-7 Least Functionality",
            "feared": "A request for more power than a workload needs gets through because the rule that should stop it only writes a note.",
            "scope": "Requests to create pods in the project.",
            "question": "For each kind of rule-breaking request, does the cluster refuse it or only note it?",
            "evidence": "The outcome of each of four test requests under each mode.",
            "sufficient": "Only Enforce mode restricts anything. The table shows which of the four requests each mode allows. Which functions to prohibit or restrict is organization-defined.",
            "tieoff": "A rule that is only recorded has an owner and a date by which it is either enforced or removed.",
            "tool": "The four test pods and the outcome rows of the comparison table.",
        },
        {
            "control": "AU-12 Audit Record Generation",
            "feared": "A rule-breaking request is allowed and no record of it exists, or a refusal leaves no trace.",
            "scope": "What the policy engine records for the project.",
            "question": "After a rule-breaking request, what record exists, and where would you find it?",
            "evidence": "Counts of policy report results and events for each mode, tied to the pods that caused them.",
            "sufficient": "The table shows, for each mode, which kind of record exists and how many. The system components that must generate records are organization-defined.",
            "tieoff": "Someone reads the records. ARC-3 only shows that they exist.",
            "tool": "The snapshot step and the records rows of the comparison table.",
        },
    ],
    "terms": [
        ("Audit mode", "The setting in which a rule lets a request through and records a violation."),
        ("Enforce mode", "The setting in which a rule refuses a request that breaks it."),
        ("Kyverno", "A program in your cluster that checks every request to create or change something against rules, called policies, and can refuse or record the request."),
        ("Cluster", "A group of servers that work together as one system. Here it is your own OpenShift cluster."),
        ("Project", "A named section of the cluster that keeps one set of work apart from others. Here it is arc-measure. OpenShift also calls it a namespace."),
        ("Pod", "One running copy of a program in the cluster."),
        ("Script", "A text file of commands or program code that the computer runs from top to bottom."),
        ("Condition", "One setup you test. Here there are three: no policy, Audit mode and Enforce mode."),
        ("Kit", "The files that lab start puts in your arc folder: test pods, policy files, helper scripts and the review gate."),
        ("Latest tag", "A tag that always points at the newest version of a program image, so the program can change without notice."),
        ("Sample", "One timing taken from one request by the test script. Many samples give a fairer picture than one."),
        ("Warm-up", "Extra time the first request takes because nothing is ready yet. It says nothing about the policy, so the script drops it."),
        ("Wall clock", "The ordinary time of day on the computer. It can jump when the system time changes, so it is a poor way to time a short request."),
        ("Snapshot", "A kit script that creates the load pods, waits, and records report counts and event counts for one condition."),
        ("Event", "A short note the cluster records when something happens to an object, such as a pod that could not be created."),
        ("Exit code", "The number a command leaves behind when it ends. 0 means success. Any other number means something needs attention."),
        ("Admission", "The check the cluster makes on a request to create or change an object, before the object is saved."),
        ("Dry run", "A request the cluster checks fully but does not save. With --dry-run=server the check includes the admission rules."),
        ("Median", "The middle timing in the test script's output: half of the requests were faster. Not the point of this module."),
        ("p95", "The timing that 95 of 100 requests beat. Part of the test script's output, not the learning goal."),
        ("Policy report", "The list of violations Kyverno records for pods that break a rule."),
        ("Review gate", "A script that fails when the work given to it is not acceptable, so a person does not have to catch the same mistakes every time."),
        ("oc", "The command-line tool for OpenShift. You type oc to ask the cluster questions."),
        ("jq", "A tool that picks one value out of JSON text."),
        ("Heredoc", "A way to make a file by pasting its text between a first line such as cat > name <<'EOF' and a last line that says EOF."),
        ("Load pods", "Twenty small pods that break every rule on purpose, including the no-latest rule through a deliberate :latest image tag, created to give each mode something to record."),
    ],
    "concepts": [
        {
            "heading": "2.1 Why test each mode",
            "controls": [
                {"id": "SA-8 Security and Privacy Engineering Principles"},
                {"id": "CM-7 Least Functionality"},
                {"id": "AU-12 Audit Record Generation"},
            ],
            "paras": [
                {"bullets": [
                    "A Kyverno rule in Audit mode lets a request through and records the violation, and in Enforce mode it refuses the request. The policy file differs by one word, so the difference is easy to overlook.",
                    "A rule that only records can be mistaken for a rule that protects, so each mode gets the same four requests and the same 20 load pods.",
                    "A test run the same way every time can be repeated by someone else and rerun after an upgrade.",
                ]},
                {
                    "control": "SA-8: Security and Privacy Engineering Principles",
                    "text": "The control asks the organization to apply organization-defined systems security and privacy engineering principles in the specification, design, development, implementation and modification of the system. NIST leaves the principles open, and the lab applies one: test each option under the same test before choosing. This is done using:",
                },
                {"bullets": [
                    "The test script (measure.py): sends the same four requests under every condition, so every option gets the same test.",
                    "The review gate (review_gate.py): fails a test script that makes a common mistake, so the results can be trusted.",
                    "The comparison script and a jq filter: put the results side by side and turn the choice into a check anyone can rerun.",
                ]},
                {
                    "control": "CM-7: Least Functionality",
                    "text": "The control asks the organization to configure the system to provide only organization-defined mission essential capabilities, and to prohibit or restrict organization-defined functions, ports, protocols, software and services. This is done using:",
                },
                {"bullets": [
                    "Kyverno policy arc-baseline: restricts what a pod may ask for, and its mode decides whether a request that breaks a rule is refused (Enforce) or only noted (Audit).",
                    "Four test pod files: three each break one rule (root user, latest image tag, no limits) and one is fine, so the table shows which requests each mode lets through. Only Enforce mode restricts anything.",
                    "oc create with --dry-run=server: sends each pod file through the cluster's admission check without saving a pod.",
                ]},
                {
                    "control": "AU-12: Audit Record Generation",
                    "text": "The control asks the organization to provide audit record generation capability for the event types the system can audit, on organization-defined system components, to let organization-defined personnel or roles select which event types each component logs, and to generate audit records for those events. This is done using:",
                },
                {"bullets": [
                    "Kyverno policy reports: list the failed results Kyverno recorded, which in Audit mode is one for each rule a load pod breaks.",
                    "Cluster events: short notes the cluster records when something happens, such as a pod that could not be created in Enforce mode.",
                    "The snapshot script (snapshot.py): creates the 20 load pods and counts the reports and events for each mode, so the table shows what record exists and how many.",
                ]},
            ],
        },
    ],
    "steps": [
        {
            "title": "Confirm the starting condition",
            "learn": "Checking that no policy exists, and that the platform adds no non-root setting of its own, makes the none condition a true baseline. The root test pod is then refused later only because of Kyverno.",
            "takeaway": "A fair comparison starts from a baseline you have checked.",
            "why": "The three conditions must differ in one thing only. The lab already installed Kyverno in the kyverno project, and the cluster pulls ubi-minimal images from registry.access.redhat.com. Two kit cases (the latest test pod and the load pods) use the :latest tag on purpose to break the no-latest rule; the other test pods use the pinned 9.5 tag.",
            "blocks": [
                {
                    "code": (
                        "oc get clusterpolicy arc-baseline --ignore-not-found\n"
                        f"oc create -n arc-measure --dry-run=server -f {ARC}/cases/root.yaml\" -o jsonpath='{{.spec.securityContext}}{{\"\\n\"}}'"
                    ),
                    "label": 'Confirm the starting condition',
                    "intro": 'You will now confirm that no policy exists yet and ask the cluster what it adds on its own to the root test pod. The command changes nothing on the cluster.',
                    "expect": 'Example only. Names and times will differ.\nNothing is printed for the first command (no policy named arc-baseline yet). Policies from other modules may exist; they do not apply in arc-measure.\nThe security settings of the pod, which should not include runAsNonRoot.',
                    "lines": [
                        ("oc get clusterpolicy arc-baseline --ignore-not-found", "Looks for this module's policy by name and prints nothing if it does not exist. Nothing printed is the answer you want.", "The none condition means this module's policy is absent. This proves the starting point is the one you think it is."),
                        ("--dry-run=server ... -o jsonpath", "Asks the cluster to check the root test pod (the one that does not say it must run as non-root) without saving it, and prints the security settings it would have. With no policy, non-root should not be set.", "Checks that the platform adds nothing of its own, because if it did, the root case would be refused for the wrong reason."),
                    ],
                }
            ],
            "controls": [
                {"id": "CM-7 Least Functionality", "how": "Confirming that no policy exists gives the none condition a clean starting point, so later refusals are credited to Kyverno and not to the platform."},
            ],
            "note": "If runAsNonRoot is already true, the platform adds it before Kyverno sees the pod, so the root case would be refused for the wrong reason. Stop and ask your AI assistant, with the command and its output.",
            "checkpoint": "No arc-baseline policy exists, and the root pod's security settings do not include runAsNonRoot.",
        },
        {
            "title": "Write the test script and pass the review gate",
            "learn": "Saving measure.py and running the review gate gives you one test script that sends the four requests as dry runs. A pass means it avoids the mistakes the gate looks for.",
            "takeaway": "Gate the test script before you trust the results it makes.",
            "controls": [
                {"id": "SA-8 Security and Privacy Engineering Principles", "how": "One test script, passed through a gate that fails common mistakes, tests every condition the same way, so the results can be trusted."},
            ],
            "why": "The script sends the four test requests to the cluster as dry runs and records whether each is allowed or denied.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p \"$HOME/arc\"\n"
                        "cd \"$HOME/arc\"\n"
                        "cat > measure.py <<'EOF'\n"
                        + MEASURE_PY
                        + "\nEOF\n"
                        "ls -l measure.py"
                    ),
                    "label": 'Save the test script',
                    "expect": 'Example only. Date and size will differ.\n-rw-r--r-- 1 <user> <group> <size> <date> measure.py',
                    "intro": 'You will now make the test script measure.py in your arc folder by pasting the whole block at once into the lab shell. The paste prints only the file listing; you run measure.py in Step 3.',
                    "look_for": [
                        "Look for the mode taken from the command line: the result file must say which condition it measured.",
                        "Look for the --dry-run=server option: the cluster runs every admission check but saves nothing, so you can repeat the request.",
                    ],
                    "lines": [
                        ("cd ... cat > measure.py <<'EOF' ... EOF", "Moves into the arc folder and writes everything between the first and last line into measure.py. The quotes around EOF keep the text exactly as typed.", "The lab has no editor, so a paste is how you make a file. The script text is Python (a programming language), which the lab shell already has as python3."),
                        ("`mode = sys.argv[1]`", "Takes the condition name (none, audit or enforce) from the command line.", "The result file must say which condition it measured, or three files could not be told apart."),
                        ("cases, names, SAMPLES", "Where the test pods are, which four there are, and how many timing samples (one timing from one request) the script takes.", "Keeps the four cases and the sample size in one place, so every condition is measured the same way."),
                        ("`def admit(name)`", "Sends one dry-run create request and returns how long it took and whether it was accepted.", "One small function means every request is sent and timed in the same way."),
                        ("--dry-run=server", "The cluster runs every admission check but saves nothing, so you can repeat it without creating objects.", "The timing must include the admission check, and a dry run lets you repeat it many times without creating anything."),
                        ("`time.perf_counter()`", "A clock built for measuring short intervals. It does not jump when the system time changes.", "A clock that can jump would give a wrong delay, and the gate rejects scripts that use one."),
                        ("outcomes = {...}", "Runs each of the four cases once and writes allowed or denied for each.", "These four answers are what the table later shows as what each mode lets through."),
                        ("[...][1:] inside sorted(...)", "Takes 25 timings in the order they were made, drops the first one, which includes warm-up, and sorts the other 24.", "The first request is slower for reasons unrelated to the policy, so leaving it out keeps the median fair."),
                        ("statistics.median, p95", "Reports the middle timing and the 95th percentile, not the mean, which one slow outlier can distort.", "The median shows the usual delay and the p95 shows the slow tail, which an average would hide."),
                    ],
                },
                {
                    "code": f"cd {ARC}\"\npython3 review_gate.py measure.py",
                    "label": 'Run the review gate on your script',
                    "intro": 'You will now run the supplied review gate on your script. The gate only reads the file.',
                    "expect": 'Example only. If your script has a mistake, you see one FAIL line for each rule it breaks.\nreview gate: PASSED',
                    "lines": [
                        ("cd ...", "Moves into the arc folder.", "The gate and your script are both there."),
                        ("review_gate.py measure.py", "Reads your script without running it and prints one FAIL line for each rule it breaks, then PASSED or FAILED.", "Catches the common mistakes before you spend minutes collecting results you could not trust."),
                    ],
                },
            ],
            "tip": "Save the script as $HOME/arc/measure.py. The gate's rules are in review_gate.py if you want to read them.",
            "checkpoint": "The gate prints review gate: PASSED.",
        },
        {
            "title": "Collect all three conditions, and test the gate meanwhile",
            "learn": "Running the loop switches the policy for each condition, sends the four requests and counts the reports and events each mode records. You end with one result file for each condition.",
            "takeaway": "Collect every condition the same way, and show that the gate can fail.",
            "controls": [
                {"id": "SA-8 Security and Privacy Engineering Principles", "how": "The careless script fails the gate with exit code 1, which shows the gate can reject a poor test script."},
                {"id": "CM-7 Least Functionality", "how": "The result files record whether each of the four requests is allowed or denied under each condition, which shows what each mode restricts."},
                {"id": "AU-12 Audit Record Generation", "how": "The snapshot script creates 20 load pods and saves the count of policy report results and events each mode produced."},
            ],
            "why": "For each condition the loop switches the policy, sends the requests, gates the output and runs the snapshot. The snapshot creates 20 load pods, waits 60 seconds and counts what was recorded. Each condition takes about two minutes, so the loop runs in the background while you test the gate.",
            "blocks": [
                {
                    "code": (
                        f"mkdir -p {ARC}/results\"\n"
                        "{ for mode in none audit enforce; do\n"
                        f"  bash {ARC}/set_mode.sh\" \"$mode\"\n"
                        f"  python3 {ARC}/measure.py\" \"$mode\" > {ARC}/results/$mode.json\"\n"
                        f"  python3 {ARC}/review_gate.py\" {ARC}/measure.py\" {ARC}/results/$mode.json\" && python3 {ARC}/snapshot.py\" \"$mode\"\n"
                        f"done; }} > {ARC}/loop.log\" 2>&1 &\n"
                        "echo \"loop started in the background\""
                    ),
                    "label": 'Start the loop that collects all three conditions',
                    "intro": 'You will now start a loop in the background that switches the policy, sends the test requests, gates the output and takes a snapshot of the records for each condition. The loop takes about six minutes in all.',
                    "expect": 'Example only.\nloop started in the background',
                    "lines": [
                        ("{ for mode in none audit enforce; do ... done; } > loop.log 2>&1 &", "Repeats the lines between for and done once for each condition, writes everything they print to loop.log, and runs the whole loop in the background so you can carry on.", "Runs all three conditions without you waiting at the keyboard, in the same order each time."),
                        ("set_mode.sh \"$mode\"", "Removes the load pods, then removes the policy (none) or applies it in that mode, and waits until it is ready.", "Each condition must start clean, otherwise leftovers from the last one would change the numbers."),
                        ("measure.py \"$mode\" > results/$mode.json", "Runs your script and saves its output for this condition.", "Produces the outcome rows for this condition."),
                        ("review_gate.py ... && snapshot.py", "Runs the gate on your script and on this condition's result file. The snapshot runs only if the gate passes.", "A result file from a poor script must not feed the table, so the snapshot waits for the gate."),
                        ("snapshot.py", "Creates the load pods, waits, then adds report counts and event counts to the same result file.", "Adds what each mode records, which the test script alone cannot see."),
                    ],
                },
                {
                    "code": (
                        f"python3 {ARC}/review_gate.py\" {ARC}/bad_measure.py\"\n"
                        "echo \"exit code $?\""
                    ),
                    "label": 'Run the gate on the careless script',
                    "intro": 'You will now run the gate on the careless script from the kit while the loop works. The gate only reads the file.',
                    "expect": 'Example only. The wording of each line will differ.\nSix FAIL lines, one for each rule the careless script breaks.\nreview gate: FAILED\nexit code 1',
                    "lines": [
                        ("review_gate.py bad_measure.py", "Runs the same gate on the careless script from the kit. The kit's bad script times with a wall clock, takes one sample and does not discard it, creates a real pod and reports no median, which together break the six rules. The gate only reads the file, so it does not disturb the loop.", "Shows that the gate really fails a careless script, which you cannot know from seeing it pass."),
                        ("echo \"exit code $?\"", "Prints the exit code (the number a command leaves behind when it ends) of the gate. A rejected script returns 1.", "A pipeline reads this number and not the words, so you check that it is 1 for a rejected script."),
                    ],
                },
                {
                    "code": (
                        f"tail -f {ARC}/loop.log\"\n"
                        f"ls {ARC}/results\""
                    ),
                    "label": 'Follow the loop and list the result files',
                    "intro": 'You will now follow the loop log until all three conditions are saved, then list the result files. Press Ctrl+C to stop the tail.',
                    "expect": 'Example only.\nLog lines from set_mode.sh, measure.py and snapshot.py.\nsnapshot saved (three times, once for each condition)\naudit.json  enforce.json  none.json',
                    "lines": [
                        ("tail -f loop.log", "Follows the loop's log. Press Ctrl+C when the third snapshot saved line appears. Ctrl+C stops only the tail, not the loop.", "Lets you watch the loop make progress, so you know when to move on."),
                        ("ls results", "Lists the result files.", "Confirms the three files exist before you try to compare them."),
                    ],
                },
            ],
            "note": "If the gate fails inside the loop, read its FAIL lines in loop.log, fix measure.py and run the loop again. Do not run lab start for this module again after this step: it clears the results folder.",
            "tip": "To redo one condition, run: bash \"$HOME/arc/set_mode.sh\" audit && python3 \"$HOME/arc/measure.py\" audit > \"$HOME/arc/results/audit.json\" && python3 \"$HOME/arc/snapshot.py\" audit",
            "checkpoint": "The careless script prints six FAIL lines, review gate: FAILED and exit code 1. Three files exist in the results folder: none.json, audit.json and enforce.json. The log shows snapshot saved three times.",
        },
        {
            "title": "Read back the table, then turn it into a check on one requirement",
            "learn": "Printing the comparison table shows which of the four requests each mode refused and which records it left. Writing the requirement as a jq filter over the same files names the condition that meets it, and the filter can be rerun whenever the tool or the cluster changes.",
            "takeaway": "Only Enforce refuses a rule-breaking request, and a decision written as a runnable check does not have to be argued again.",
            "controls": [
                {"id": "CM-7 Least Functionality", "how": "The outcome rows show which of the four requests each mode refused, and only Enforce refuses any."},
                {"id": "AU-12 Audit Record Generation", "how": "The record rows show that Audit and Enforce each left reports or events and that the none condition left none. Verify checks the Audit count."},
                {"id": "SA-8 Security and Privacy Engineering Principles", "how": "The jq filter writes the requirement down, so the choice follows from written criteria that anyone can rerun."},
            ],
            "why": "The comparison script reads the three result files and prints, for each condition, which requests were allowed or denied and which records exist. A decision that cannot be rechecked will be argued again, so the filter then asks one question of the same files: which condition refuses the root request and also leaves a record?",
            "blocks": [
                {
                    "code": (
                        f"python3 {ARC}/compare.py\""
                    ),
                    "label": 'Print the table of outcomes and records',
                    "intro": 'You will now print the comparison table from the three result files.',
                    "expect": 'Example only. All numbers will differ.\nA table with one column for each condition (none, audit, enforce): what each of the four requests did and what was recorded. It also holds timing and memory rows from the supplied script, which this module does not use.',
                    "lines": [
                        ("compare.py", "Prints one column per condition: what each of the four requests did and what was recorded. It stops with an error if a result is missing or too small.", "Reads back what each mode refused and recorded, which is the evidence that Enforce restricts and Audit only records."),
                    ],
                },
                {
                    "code": (
                        f"jq -r 'select(.outcomes.root == \"denied\" and (.report_fail_results + .policy_events + .failed_create_events) > 0) | .mode' {ARC}/results/\"*.json\n"
                        f"bash {ARC}/set_mode.sh\" none"
                    ),
                    "label": 'Write the requirement as a filter and reset the project',
                    "intro": 'You will now run a jq filter over the three result files and reset the project.',
                    "expect": 'Example only.\nenforce\n(set_mode.sh none prints its progress as it removes the policy and the load)',
                    "lines": [
                        ("select(.outcomes.root == \"denied\" and ... > 0)", "Keeps only a condition that refused the root request and also left at least one record of any kind.", "Writes the requirement as a check anyone can rerun, so the choice is not argued from memory."),
                        ("| .mode", "Prints the name of each condition that passes.", "Gives the answer as the name of the condition that meets the requirement."),
                        ("set_mode.sh none", "Removes the policy and the load so the project is back to the starting condition.", "Puts the project back to the starting condition so the next run starts clean."),
                    ],
                }
            ],
            "note": "Read only the request outcome rows and the record rows. Each of the 20 load pods breaks three rules, so in Audit mode expect three failed results per pod.",
            "tip": "Change the requirement and rerun the first line, for example to require that the compliant case is still allowed or that no load pod is created.",
            "checkpoint": "The table has three columns. In Enforce the load pods created is 0 and the root request is denied. In none the root request is allowed. The Audit count is checked in Verify. Only enforce is printed by the first line of the filter block.",
        },
    ],
    "verify": [
        {
            "kind": "positive",
            "title": "The record count follows from the load",
            "controls": [
                {"id": "AU-12 Audit Record Generation", "how": "Each load pod breaks three rules, so Audit mode should hold three failed results for each pod, and this test checks that count."},
            ],
            "why": "A number you can derive independently is a number you can trust. Each load pod breaks three rules, so Audit mode should hold three failed results per pod.",
            "code": f"jq '.report_fail_results == (.load_pods_created * 3)' {ARC}/results/audit.json\"",
            "expect": "Example only.\ntrue",
            "lines": [
                (".report_fail_results", "The number of failed results the Audit snapshot counted in the policy report.", "This is what Kyverno recorded."),
                (".load_pods_created * 3", "The 20 load pods created, times the three rules each one breaks.", "This is what the load predicts, worked out without looking at the report."),
                ("== ... true", "Prints true when the two counts are equal.", "A match shows the records follow from the load. false means the counts differ, so compare the two numbers in the result file."),
            ],
            "checkpoint": "The answer is true. If it is false, rerun the audit condition once in case the reports were slow, then compare report_fail_results with load_pods_created in audit.json.",
        },
        {
            "kind": "negative",
            "title": "The comparison refuses incomplete data",
            "controls": [
                {"id": "SA-8 Security and Privacy Engineering Principles", "how": "Removing one result file shows the comparison stops with exit code 2 instead of printing a table with a column missing."},
            ],
            "why": "A table with a column missing would look fine and mislead. Move one result away and run the comparison.",
            "code": (
                f"cp {ARC}/results/enforce.json\" {ARC}/results/enforce.hold\"\n"
                f"rm {ARC}/results/enforce.json\"\n"
                f"python3 {ARC}/compare.py\"\n"
                "echo \"exit code $?\"\n"
                f"cp {ARC}/results/enforce.hold\" {ARC}/results/enforce.json\"\n"
                f"rm {ARC}/results/enforce.hold\""
            ),
            "expect": (
                "Example only. The path will differ.\n"
                "STOP: missing /root/arc/results/enforce.json: run all three conditions before comparing\n"
                "exit code 2"
            ),
            "lines": [
                ("cp ... enforce.hold, rm ... enforce.json", "Keeps a copy of the Enforce result and removes the original.", "Makes one condition missing, as if a run had failed."),
                ("python3 compare.py", "Tries to print the table with only two of three conditions.", "A table with a column missing would look fine and mislead, so it must refuse."),
                ("STOP: missing ...", "The comparison names the missing file and prints no table.", "A clear stop is the safe failure."),
                ("exit code 2", "2 means the comparison could not run on the data it was given.", "Other programs read this number, not the words."),
                ("cp ... enforce.hold ..., rm ... enforce.hold", "Puts the file back and removes the spare.", "Leaves your results as they were."),
            ],
            "checkpoint": "A STOP message and exit code 2, and no table. Put the file back, as the last line does.",
        },
    ],
    "waivers": {
        "your_turn": "The YOUR TURN lines were removed on reviewer feedback (ENG-0); the optional command list at the end replaces them.",
    },
    "glossary": [
        ("Admission", "The check the cluster makes before it saves a new or changed object."),
        ("Audit mode", "The rule mode that allows a request and records a violation."),
        ("Enforce mode", "The rule mode that refuses a request that breaks the rule."),
        ("Dry run", "A request checked fully by the cluster but not saved."),
        ("Median", "The middle value: half the timings were faster."),
        ("p95", "The timing that 95 of 100 requests were faster than."),
        ("Review gate", "A script that fails when the work given to it is not acceptable."),
        ("Policy report", "The list of violations Kyverno records."),
    ],
    "design": [
        {
            "decision": "Test Audit and Enforce against a no-policy baseline",
            "how": "One script sends the four test requests as dry runs under three conditions: no policy, Audit and Enforce, and records whether each was allowed or denied. A snapshot of records is taken for each condition.",
            "why": "The no-policy condition shows what happens with nothing applied, and an identical method makes the result repeatable after an upgrade.",
            "alternatives": "A dedicated load tool is the alternative. Advantage: it tests behavior under heavy traffic. Drawback: more setup and time, and a result that is harder for a learner to read.",
        },
        {
            "decision": "Pass the test script through a review gate",
            "how": "A gate script rejects a test script that uses a wall clock, skips the dry run, takes too few samples, keeps the first sample or reports no median, and rejects a result file with missing keys.",
            "why": "These are the common mistakes, and a gate makes them impossible to miss although it cannot prove the script correct.",
            "alternatives": "Peer review alone is the alternative. Advantage: a reviewer can catch unusual flaws that a fixed rule list would not. Drawback: it depends on the reviewer's attention every time.",
        },
    ],
    "next": "Next module: ARC-4 Test Two Designs: run the same attack cases against two ways of isolating workloads and compare what each blocks.",
}

MODULE["portability"] = {
    "bullets": [
        "The method ports as is. It sends a server-side dry run of four manifests and records whether each is allowed or denied.",
        "Change these lab values first: the project arc-measure, the policy name arc-baseline, the kyverno project, the cases folder $HOME/arc/cases, and the commands in set_mode.sh that switch the Kyverno mode.",
        "Server-side dry run works with kubectl as well: kubectl create --dry-run=server. The oc create in measure.py becomes kubectl create.",
        "set_mode.sh, snapshot.py and review_gate.py are lab files. Copy them if you keep them, and adjust the namespaces and policy names inside.",
    ],
    "headers": ["Check/part", "In this lab", "On other platforms", "What you change"],
    "rows": [
        ("Test script", "measure.py calls oc create --dry-run=server in arc-measure", "The same call with kubectl", "The tool name in the command list, and the namespace."),
        ("Switching modes", "set_mode.sh changes the Kyverno policies in the lab", "The same, if Kyverno is installed", "The policy names and the namespace the script targets."),
        ("Policy results", "Policy reports and events read by snapshot.py", "The same, if Kyverno policy reports are installed", "The namespace. Replace the check if you use another policy engine."),
        ("Review gate", "review_gate.py is a plain Python script", "Runs anywhere Python 3 runs", "Nothing."),
        ("Test images", "ubi-minimal 9.5 and latest from registry.access.redhat.com", "Any image your cluster can pull, with one pinned and one latest", "The image names in the case files."),
    ],
}
