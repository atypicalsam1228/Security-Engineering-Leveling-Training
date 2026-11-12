"""AID-2: Check AI-written scripts before running them (CM-3, IA-5, SA-11)."""

NIST = "nist-sp-800-53r5-full.md"

MODULE = {
    "intent_at_end": True,
    "id": "AID-2",
    "slug": "ReadFirst",
    "title": "Check AI-Written Scripts Before Running",
    "draft": (
        "Run live on 2026-11-10; every step and test passed (see live-run/findings-AID-2.md). The stub model service is in project ai-lab and Step 1 reaches it with oc port-forward svc/stub-model, which the lab oc accepts. "
        "Test 3 returns an empty pod list with exit status 0 for a project that does not exist, then a NotFound error from the final oc get project. In Step 1 the findings are listed by line number, so the order differs from a by-kind listing. "
        "On 2026-11-12 the module was cut to an optional two-step module: the syntax check, the real sandbox run and the chat refusal post were removed (the post was not checked for arrival in the channel). "
        "The sandbox project is a separate project, not a security boundary: the learner is cluster-admin, so the harness, not the project, keeps the unsafe scripts harmless."
    ),
    "controls": ["CM-3", "IA-5(7)", "SA-11"],
    "mentions": ["IA-5", "SI-7", "AC-6"],
    "unit_values_ok": ["40 minutes"],
    "minutes": {"hands_on": 28, "verify": 12},
    "tools": ["bash", "grep", "oc", "curl", "jq", "Stub model service (provided by the lab)"],
    "tool_why": True,
    "hide_draft": True,
    "hover": True,
    "terms_at_end": True,
    "diagrams": [
        {
            "id": "review",
            "title": "Read first, run second",
            "caption": "This is the lab (test) setup. A stand-in assistant hands you three scripts, and you search every script for risky lines. The unsafe scripts only ever run inside a print-only harness. In production the assistant is reached through an approved service the organization controls and its scripts go through code review first. Each step below adds one part, drawn with thick lines.",
            "per_step": True,
            "rankdir": "TB",
            "step_notes": {
                1: "The stub model service in project ai-lab hands over three scripts, which are saved as files in your review folder. Search commands then read each script and mark the risky lines. Nothing has run yet.",
                2: "The two unsafe scripts run inside a print-only harness in your review folder. It shows what they would have done and changes nothing in the cluster.",
            },
            "zones": [
                {"id": "shell", "label": "Lab shell, your review folder (a container on your computer)", "kind": "boundary"},
                {"id": "aws", "icon": "aws/group-AWS-Cloud", "label": "Lab cluster (your OpenShift cluster, in AWS)", "kind": "boundary"},
                {"id": "ailab", "icon": "brands/openshift", "labelloc": "b", "label": "Project ai-lab", "parent": "aws", "kind": "group"},
                {"id": "sandbox", "icon": "brands/openshift", "labelloc": "b", "label": "Project ai-sandbox", "parent": "aws", "kind": "group"},
            ],
            "key": {"brands/python": "Python program", "brands/gnubash": "Bash script or command", "k8s/cm": "Kubernetes config map", "brands/openshift": "OpenShift project", "aws/group-AWS-Cloud": "AWS Cloud"},
            "nodes": [
                {"id": "stub", "icon": "brands/python", "title": "Stub model service", "sub": "Python service in project ai-lab, fixed answers", "zone": "ailab"},
                {"id": "scripts", "icon": "brands/gnubash", "title": "Three scripts to review", "sub": "Bash script files a, b and c", "zone": "shell", "s": 1},
                {"id": "checks", "icon": "brands/gnubash", "title": "Search checks", "sub": "Command grep marks risky lines", "zone": "shell", "kind": "warn", "s": 1},
                {"id": "harness", "icon": "brands/gnubash", "title": "Print-only harness", "sub": "Stand-in oc, curl and rm that only print", "zone": "shell", "kind": "warn", "s": 2},
                {"id": "evidence", "icon": "k8s/cm", "title": "Evidence config map", "sub": "Kubernetes config map sandbox-evidence", "zone": "sandbox"},
            ],
            "edges": [
                {"a": "stub", "b": "scripts", "label": "Supplies, through a port forward", "s": 1},
                {"a": "scripts", "b": "checks", "label": "Read by", "s": 1},
                {"a": "checks", "b": "harness", "label": "Unsafe ones go to", "kind": "warn", "s": 2},
                {"a": "harness", "b": "evidence", "label": "Leaves the real objects unchanged", "kind": "ok", "s": 2},
            ],
            "why_built": (
                "You type in lab shell, a container on your computer, and the scripts you review are saved as files in a folder there. "
                "Everything else runs on your own OpenShift cluster in AWS. "
                "The stub model service in project ai-lab plays the assistant and hands out the same three scripts every time, so every learner sees the same results and needs no model account or key. "
                "The sandbox project ai-sandbox holds an evidence config map that an unsafe cleanup would delete, so you can show later that nothing was touched. "
                "The checks and the harness run in lab shell, and the harness replaces oc, curl and rm, so the unsafe scripts cannot reach the cluster."
            ),
            "setup": [
                ("Lab shell and your review folder", "In lab shell, on your laptop", "The checks and the harness run here, so you read and test scripts away from the cluster."),
                ("Stub model service", "Pods in project ai-lab on the lab cluster", "It plays the assistant with fixed answers, so every learner gets the same three scripts and needs no account or key."),
                ("Port forward", "From lab shell to the stub service in project ai-lab", "The service is only reachable inside the cluster, so a tunnel is the simplest way to reach it from lab shell."),
                ("Print-only harness", "A folder named shim inside your review folder, placed first on the command search path (PATH, the list of folders the shell searches for a command)", "Scripts that call oc, curl or rm reach the stand-ins, so they can run to the end while nothing leaves lab shell."),
                ("Sandbox project ai-sandbox", "On the lab cluster", "A separate project holds the objects an unsafe cleanup would delete, so you can show they are still there. It is a habit, not a wall, because you are the cluster administrator."),
            ],
            "legend": [
                ("Stub model service", "A small program in project ai-lab that plays the assistant. It gives the same three scripts every time."),
                ("Three scripts to review", "The files script-a.sh, script-b.sh and script-c.sh, saved in your review folder. One is safe and two are not."),
                ("Search checks", "Search commands you run in lab shell. They look for risky words and read the scripts and never run them."),
                ("Print-only harness", "Stand-in commands for oc, curl and rm. They print what a script asked for instead of doing it."),
                ("Evidence config map", "A stored object in ai-sandbox named sandbox-evidence. It must still be there after the harness run."),
                ("Project ai-lab", "A named section of the lab cluster that holds the stub model service."),
                ("Your review folder", "The folder in lab shell that holds the scripts, the harness."),
                ("Project ai-sandbox", "A named section of the lab cluster where nothing important lives. It holds the evidence config map."),
            ],
            "reading": [
                "1. Stub model service: a small Python service in project ai-lab that gives the same three scripts every time.",
                "2. Three scripts to review: the files script-a.sh, script-b.sh and script-c.sh, saved in your review folder.",
                "3. Search checks: grep reads each script and marks the risky lines. It never runs it.",
                "4. Print-only harness: stand-in oc, curl and rm commands that print what an unsafe script asked for instead of doing it.",
                "5. Evidence config map: sandbox-evidence in ai-sandbox, which must still be there after the harness run.",
                "6. Project ai-lab: the lab cluster project that holds the stub model service.",
                "7. Your review folder: the folder in lab shell that holds the scripts and the harness.",
                "8. Project ai-sandbox: the lab cluster project where nothing important lives.",
            ],
        },
    ],
    "prereq": ["ENG-0 Terminal, Git and Your Lab (terminal, git, oc basics and the lab shell)"],
    "lab_needs": [],
    "lab": {
        "start": "lab start aid-2",
        "env": [],
    },
    "objectives": [
        {"label": "Skill", "text": "Optional module. Fetch three scripts from an assistant, search them for risky lines, and run the unsafe ones only through a print-only harness to see what they would do."},
        {"label": "Tools", "text": "`grep` searches for deletes, downloads and secret-like names. A harness of stand-in `oc`, `curl` and `rm` commands prints what a script would do. `oc` reads results back from the cluster. `curl` and `jq` fetch the scripts from the stub model service."},
        {"label": "Security Function", "text": "Detects a hidden delete and an embedded token before anything runs, and blocks the script: the unsafe scripts only ever run inside the print-only harness."},
        {"label": "NIST CM-3 Configuration Change Control", "text": "The print-only harness shows what each proposed script would change before it is allowed to change anything, so a person can decide to refuse it."},
        {"label": "NIST IA-5(7) Authenticator Management | No Embedded Unencrypted Static Authenticators", "text": "`grep` searches each script for secret-like names that are given a value, which finds the token written into script-c.sh and gives its line number."},
        {"label": "NIST SA-11 Developer Testing and Evaluation", "text": "`grep` and the harness are two different tests of each script, and their saved output is the evidence. A script that fails is refused, not fixed and run."},
    ],
    "requirement": (
        "This module is optional. Take it if you will run scripts an AI assistant wrote; AID-3 and AID-4 do not depend on it. "
        "A regulated system must not change because someone, or something, wrote a command that looked helpful. "
        "This module teaches the habit of reading, searching and test-running an assistant's script before it touches the system, and stopping when it fails."
    ),
    "requirement_bullets": [
        "Optional module, about 40 minutes. Purpose: stop a script an AI assistant wrote from changing the system before a person has read it (CM-3, IA-5(7), SA-11).",
        "You build a short review routine: a search for risky lines and a print-only run of the unsafe scripts.",
        "You run it on three scripts from a stand-in assistant: one safe, one with a hidden delete, and one with an embedded token and an unreviewed download.",
    ],
    "mapping": [
        {
            "control": "CM-3 Configuration Change Control",
            "plain": "Review each proposed change to the system and approve or refuse it before it is made.",
            "source": "NIST",
            "tool": "The print-only harness (stand-in oc, curl and rm commands). Explained in section 2.1.",
            "covered": "Section 3, Step 2: run the two unsafe scripts through the harness and read what they would do. Section 4, Test 2: the harness showed the harm and it did not happen.",
            "cite": [
                {"file": NIST, "quote": "Review proposed configuration-controlled changes to the system and approve or disapprove"},
                {"file": NIST, "quote": "Document configuration change decisions associated with the system"},
            ],
        },
        {
            "control": "IA-5(7) Authenticator Management | No Embedded Unencrypted Static Authenticators",
            "plain": "No password, token (a long secret string that proves who you are) or key is written into a script or an application in readable form.",
            "source": "NIST",
            "tool": "grep, searching for secret-like names in each script. Explained in section 2.2.",
            "covered": "Section 3, Step 1: search for embedded secrets and read the line number.",
            "cite": [
                {"file": NIST, "quote": "Ensure that unencrypted static authenticators are not embedded in applications or other"},
            ],
        },
        {
            "control": "SA-11 Developer Testing and Evaluation",
            "plain": "Whoever writes the code tests it and keeps the results, and the flaws found are corrected.",
            "source": "NIST",
            "tool": "grep and the print-only harness, with the sandbox project ai-sandbox as the place to check nothing was lost. Explained in section 2.1.",
            "covered": "Section 3, Steps 1 and 2: two different checks on the scripts an assistant wrote. Section 4, Tests 1 to 3: read and keep the results.",
            "cite": [
                {"file": NIST, "quote": "Produce evidence of the execution of the assessment plan and the results of the testing and evaluation"},
                {"file": NIST, "quote": "Correct flaws identified during testing and evaluation"},
            ],
        },
    ],
    "intent": [
        {
            "control": "CM-3 Configuration Change Control",
            "feared": "A change reaches the system without anyone reading it first, so the first person to learn what it does is the system.",
            "scope": "Every script that can change the cluster, whoever or whatever wrote it, including an assistant.",
            "question": "Before this script ran, did a person read it, and can they say what it would change?",
            "evidence": "The review results for each script: what was found, what was decided, and proof that a refused script did not run.",
            "sufficient": "Each change is reviewed for its security effect before it is made, and the decision is recorded. NIST leaves how long change records are kept to the organization. Here the harness output you save is the record.",
            "tieoff": "Someone other than the script's author is told when a script is refused. The lab stops at saving the harness output; in a team you would tell the author and the owner.",
            "tool": "Step 1 searches each script, and the print-only harness (stand-in commands that print what a script asked for instead of doing it) in Step 2 shows its effect without making it.",
        },
        {
            "control": "IA-5(7) Authenticator Management | No Embedded Unencrypted Static Authenticators",
            "feared": "A password or token pasted into a script is copied to every place the script goes, and cannot be taken back.",
            "scope": "Scripts and applications the team writes or accepts, including ones an assistant writes.",
            "question": "Does this script contain anything that proves who it is, and where did that value come from?",
            "evidence": "The result of a search for secret-like values in each script, with line numbers.",
            "sufficient": "No script carries a fixed password, token or key. A secret written into a script is treated as exposed and replaced.",
            "tieoff": "The person who owns the credential is told it is exposed so it can be replaced.",
            "tool": "A search for names such as token, secret and password (Step 1) finds the embedded value and its line number.",
        },
        {
            "control": "SA-11 Developer Testing and Evaluation",
            "feared": "Code is trusted because it came from a confident source, and nobody tested it.",
            "scope": "Code the team runs, including code produced by an assistant.",
            "question": "What testing did this script go through before it touched the system, and where is the result?",
            "evidence": "The search results and the harness output for each script.",
            "sufficient": "Each script is checked by more than one method, because it can pass one check and fail another. NIST has the organization select the kinds of testing (unit, integration, system, regression) and define how often and the depth and coverage. The lab uses two checks.",
            "tieoff": "A flaw found in a script goes back to whoever asked the assistant for it, and the script is not run until it is corrected and checked again.",
            "tool": "grep and the harness are two different checks. Test 3 shows why a clean exit alone proves little.",
        },
    ],
    "terms": [
        ("Assistant", "A program that writes text on request, including scripts. It can be wrong, and it can be steered by what it reads."),
        ("Script", "A text file of commands that the computer runs from top to bottom."),
        ("oc", "The command-line tool for OpenShift. You type oc to ask the cluster questions."),
        ("jq", "A tool that picks one value out of JSON text."),
        ("Stub model service", "A small program that stands in for a model. It returns a fixed answer for each request id, so every output in this module is repeatable. It needs no key and no internet access."),
        ("Cluster", "A group of servers that work together as one system. Here it is your own OpenShift cluster in AWS."),
        ("Project", "A named section of the cluster that keeps workloads apart. OpenShift also calls it a namespace."),
        ("Harness", "A set of stand-in commands that print what a script asked for instead of doing it."),
        ("Sandbox project", "A project where nothing important lives. Here it holds the objects you check were not touched."),
        ("Hardcoded secret", "A password, token or key written directly into a script."),
        ("Token", "A long secret string that proves who you are, used in place of a password."),
        ("Pipe", "The | symbol, which sends the output of one command into the next command."),
        ("Pipe to a shell", "Running whatever a download returns, by sending it straight into bash. You cannot read it first."),
        ("Pinned", "Fixed to one exact version, so the same thing is fetched every time. A download from a path that says latest is not pinned."),
        ("Trap", "A shell command that runs when a script ends or fails, often away from the part you are reading."),
        ("Port forward", "A tunnel from your shell to a service inside the cluster, so a command in lab shell can reach it."),
        ("PATH", "The list of folders the shell searches, in order, to find a command you type."),
        ("Config map", "A stored file or setting that the cluster keeps and can hand to a program."),
        ("Deployment", "A cluster object that keeps a set number of copies of a program running."),
        ("Pod", "The smallest running unit on the cluster: one or more containers together."),
        ("Phase", "The state a pod is in, such as Running or Succeeded."),
        ("Volume claim", "A request for storage that a program uses to keep its data."),
        ("Cluster-admin", "The strongest role in the cluster. A person with it can read and change everything."),
        ("Exit status", "A number a command leaves behind when it ends. 0 means success and anything else means a problem."),
        ("JSON", "A plain-text format for data: names and values written inside curly braces."),
    ],
    "concepts": [
        {
            "heading": "2.1 Why a script is read before it is run",
            "controls": [
                {"id": "CM-3 Configuration Change Control"},
                {"id": "SA-11 Developer Testing and Evaluation"},
            ],
            "paras": [
                {"bullets": [
                    "An assistant cannot see your system and does not live with the result, so a script it writes is only a proposal. Review it like a change request.",
                    "A script that looks correct can hide a delete in a function that runs only when the script exits, or a download that runs code nobody has read.",
                    "Reading only the top of a file misses a hidden delete or an unread download, so this module uses two checks instead of one read.",
                ]},
                {
                    "control": "CM-3: Configuration Change Control",
                    "text": "The control asks the organization to decide which types of change are configuration-controlled, to review each proposed change with its security and privacy impact in mind, to approve or disapprove it, and to document the decision. This is done using:",
                },
                {"bullets": [
                    "The print-only harness (stand-in oc, curl and rm commands): shows what a proposed script would change without letting it change anything, which is the review.",
                    "The grep search: points the reviewer to the risky lines before the script runs.",
                ]},
                {
                    "control": "SA-11: Developer Testing and Evaluation",
                    "text": "The control asks the developer of a system component to test it, produce evidence of the testing and its results, and correct the flaws found. NIST has the organization select the kinds of testing (unit, integration, system, regression) and define how often and the depth and coverage. Here an assistant is treated like any other author of code. This is done using:",
                },
                {"bullets": [
                    "grep: shows where deletes, downloads, exit handlers (traps) and secret-like names are, and cannot find words you did not think to search for.",
                    "The print-only harness: shows the exact commands the script would run, and cannot show what a downloaded script would have done.",
                ]},
            ],
        },
        {
            "heading": "2.2 The three scripts in this module",
            "controls": [
                {"id": "IA-5(7) Authenticator Management | No Embedded Unencrypted Static Authenticators"},
            ],
            "paras": [
                {"bullets": [
                    "The stub model service returns the same three scripts every time, so you can practice the checks and compare your results with the expected output. Real assistants are less predictable.",
                    "script-a.sh reports the pod phases (the state each pod is in) in a project, and does exactly that, read-only.",
                    "script-b.sh claims to remove finished pods, but when it exits it also deletes config maps and volume claims (requests for storage).",
                    "script-c.sh claims to install a helper and send a status report, and it carries a token written into the script (a hardcoded secret). script-c.sh also sends a download that is not pinned (not fixed to one exact version) straight into bash, which is called a pipe to a shell.",
                ]},
                {
                    "control": "IA-5(7): Authenticator Management | No Embedded Unencrypted Static Authenticators",
                    "text": "The enhancement asks the organization to ensure that unencrypted static authenticators are not embedded in applications or other forms of static storage, which NIST says includes access scripts. This is done using:",
                },
                {"bullets": [
                    "grep: searches each script for secret-like names that are given a value, which finds the token written into script-c.sh.",
                    "The line number: tells the owner where the token is without repeating its value, so it can be replaced without spreading it further. Do not paste the token anywhere.",
                ]},
            ],
            "production": "In the real environment an assistant is reached through an approved service the organization controls, and scripts it writes go through code review before they reach a shared repository (the stored copy of the team's code). The lab practices only the reading and testing part.",
        },
    ],
    "steps": [
        {
            "title": "Get the scripts and search them for risky lines",
            "learn": "Three searches point to the exact lines that delete, download or carry a secret, so you read those lines instead of whole files.",
            "takeaway": "A search tells you where to read, but it only finds what you thought to search for.",
            "controls": [
                {"id": 'SA-11 Developer Testing and Evaluation', "how": 'Searching is a test of each script. The line numbers it prints are the evidence that points to the two scripts that fail.'},
                {"id": 'IA-5(7) Authenticator Management | No Embedded Unencrypted Static Authenticators', "how": 'The search for secret-like names given a value finds the line in script-c.sh where a token is written into the file.'},
            ],
            "why": "The stub model service runs in project ai-lab on port 8080 and returns three fixed scripts. You reach it through a port forward (a tunnel from your shell to a service in the cluster) and save each answer as a file. Reading every line does not scale, so you search first and read the lines the search points to. Three searches cover commands that delete or download, values that look like secrets, and web addresses the script contacts.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p /workspace/aid-2/review\n"
                        "cd /workspace/aid-2/review\n"
                        "curl -s http://127.0.0.1:8089/healthz >/dev/null || { oc port-forward -n ai-lab svc/stub-model 8089:8080 & sleep 3; }\n"
                        "curl -s http://127.0.0.1:8089/healthz\n"
                        "for id in a b c; do\n"
                        "  curl -s -X POST http://127.0.0.1:8089/v1/answer -d \"{\\\"request_id\\\": \\\"script-$id\\\"}\" | jq -r .reply > \"script-$id.sh\"\n"
                        "done\n"
                        "ls -l"
                    ),
                    "label": 'Open a tunnel to the stub and save the three scripts',
                    "intro": 'You will now open a tunnel to the stub model service, ask it for the three scripts and save each one as a file.',
                    "expect": 'Example only. Your sizes and dates will differ. If the tunnel was already open, the Forwarding line does not appear.\nForwarding from 127.0.0.1:8089 -> 8080\n<short status in JSON>\ntotal <n>\n-rw-r--r-- 1 <user> <group> <size> <date> script-a.sh\n-rw-r--r-- 1 <user> <group> <size> <date> script-b.sh\n-rw-r--r-- 1 <user> <group> <size> <date> script-c.sh',
                    "lines": [
                        ("mkdir -p ... , cd ...", "Makes a folder for this work and moves into it, so files from other modules cannot collide with yours. Every later block that uses these files starts with a cd to this same folder.", "Everything you fetch and write in this module lands here, which keeps the review in one place."),
                        ("curl -s ... >/dev/null || { oc port-forward ... 8089:8080 & sleep 3; }", "Asks the stub if it already answers on port 8089. Only if it does not, it opens a tunnel from port 8089 in your shell to port 8080 of the stub service and keeps it running in the background (the &).", "The stub service is only reachable inside the cluster, so every request in this step goes through this tunnel. Checking first stops a second tunnel from failing with an address already in use error."),
                        ("curl -s http://127.0.0.1:8089/...", "Asks the stub if it is up. It should answer with a short status in JSON (a plain-text format for data).", "A quick check that the tunnel works before you ask for scripts, so a failure later is not a mystery."),
                        ("for id in a b c", "Repeats the next command once for each of a, b and c.", "There are three scripts to fetch, and one loop avoids typing the same request three times."),
                        ("-d \"{...script-$id...}\"", "Sends the request id script-a, script-b or script-c. The stub picks its fixed answer by this id only.", "The stub picks its answer by this id alone, so this is how you choose which of the three scripts you get."),
                        ("jq -r .reply > script-$id.sh", "Takes the reply text out of the JSON answer and saves it as a file.", "The answer is wrapped in JSON, and you need the plain script text as a file you can check."),
                    ],
                },
                {
                    "code": (
                        "cd /workspace/aid-2/review\n"
                        "grep -nE 'curl|\\| *(ba)?sh|rm -rf|delete|trap|eval|sudo|chmod' script-*.sh\n"
                        "grep -nEi '(token|secret|password|passwd|key)[A-Za-z_]*=' script-*.sh\n"
                        "grep -nE 'https?://' script-*.sh"
                    ),
                    "label": 'Search the scripts for deletes, downloads, secrets and web addresses',
                    "intro": 'You will now run three searches over all three scripts, which only read the files.',
                    "expect": 'Example only. <n> is a line number and the text after it is the line the search matched. Lines come in file and line-number order, so the trap line may come after the delete lines.\nscript-b.sh:<n>:<a line with a delete>\nscript-b.sh:<n>:<a second line with a delete>\nscript-b.sh:<n>:<a line with a trap>\nscript-c.sh:<n>:<a line that downloads and pipes into bash>\nscript-c.sh:<n>:<a line with the report call to curl>\nscript-c.sh:<n>:<a line that gives a token a value>\nscript-c.sh:<n>:<a line with a web address>\nscript-c.sh:<n>:<a second line with a web address>\n(script-a.sh does not appear in any result)',
                    "lines": [
                        ("cd /workspace/aid-2/review", "Moves into the review folder from the first block.", "The searches read the three script files in that folder."),
                        ("grep -nE '...' script-*.sh", "Searches all three scripts for lines that match, and prints the file name and line number of each. -E allows the | to mean or.", "Reading every line does not scale, so you let the search point to the lines worth reading."),
                        ("curl", "A command that downloads from a web address.", "A download is the first sign that a script may run code you have not read."),
                        ("\\| *(ba)?sh", "A pipe into sh or bash, which runs whatever arrives.", "This is the worst pattern, because it runs whatever arrives without anyone reading it."),
                        ("rm -rf|delete", "Commands that remove files or cluster objects.", "A removal in a tidy-up script is how data disappears, so you want to see every one."),
                        ("trap", "A command that runs when the script exits or fails, often not where you are looking.", "A command hidden in an exit handler runs when the script ends, away from the part you were reading."),
                        ("(token|secret|password|passwd|key)[A-Za-z_]*=", "A name that sounds like a secret being given a value. -i ignores upper and lower case.", "A fixed secret in a script is copied wherever the script goes, so you find every one before the script is shared or run."),
                        ("https?://", "Every web address the script contacts.", "Each address is a place the script sends data to or takes code from, and you decide whether you trust it."),
                    ],
                }
            ],
            "note": "script-a.sh does not appear in any result, which is expected for a script that only reads. To read a hit, print that line with sed -n 'LINEp' FILE (for example sed -n '12p' script-b.sh), or a range such as sed -n '8,14p' script-b.sh.",
            "checkpoint": "You can name the hidden delete in script-b.sh, and the token and the download piped into bash in script-c.sh, each with its line number.",
        },
        {
            "title": "See what the unsafe scripts would do, without letting them",
            "learn": "The harness lets both unsafe scripts run to the end but only prints their commands, so you see the hidden deletes and the token with no effect on the cluster.",
            "takeaway": "You can see what an unsafe script would do without letting it do it.",
            "controls": [
                {"id": 'CM-3 Configuration Change Control', "how": 'The printed commands show the effect of each proposed change without making it, which is what a decision to refuse the script would rest on.'},
                {"id": 'SA-11 Developer Testing and Evaluation', "how": 'The print-only run is a second kind of test. Its saved output, harness-b.txt, is the evidence that Verify reads.'},
            ],
            "why": "A harness is a folder of stand-in commands placed first on PATH (the list of folders the shell searches for a command). When a script calls oc, curl or rm it gets the stand-in, which prints the command and does nothing, so the script runs as written.",
            "blocks": [
                {
                    "code": (
                        "cd /workspace/aid-2/review\n"
                        "mkdir -p shim\n"
                        "for tool in oc curl rm; do\n"
                        "  printf '%s\\n' '#!/bin/bash' \"echo \\\"WOULD RUN: $tool \\$*\\\" >&2\" > \"shim/$tool\"\n"
                        "  chmod +x \"shim/$tool\"\n"
                        "done\n"
                        "cat shim/oc"
                    ),
                    "label": 'Create the print-only stand-in commands',
                    "intro": 'You will now make three stand-in commands that print what they are asked and do nothing else.',
                    "expect": 'Example only. The last command shows one stand-in.\n#!/bin/bash\necho "WOULD RUN: oc $*" >&2',
                    "lines": [
                        ("cd /workspace/aid-2/review", "Moves into the review folder from Step 1.", "The shim folder is made inside it, next to the scripts."),
                        ("for tool in oc curl rm", "Makes one stand-in for each command a script might use to change something.", "oc changes the cluster, curl sends and fetches data and rm deletes files, so these are the three to replace."),
                        ("printf ... > shim/$tool", "Writes a two-line program: a bash header, then a line that prints WOULD RUN and the arguments it received. The output goes to the error stream (a second output channel), so a pipe, which passes one command's output to the next, does not carry it away.", "A stand-in that only prints lets the script run to the end as written while nothing reaches the cluster."),
                        ("chmod +x", "Makes each stand-in runnable.", "The shell skips a file that is not marked runnable, and it would then find the real command instead."),
                        ("cat shim/oc", "Shows one stand-in so you can read it.", "Reading the stand-in confirms it only prints, before you trust it with a harmful script."),
                    ],
                },
                {
                    "code": (
                        "cd /workspace/aid-2/review\n"
                        "PATH=\"$PWD/shim:$PATH\" bash script-b.sh ai-sandbox 2>&1 | tee harness-b.txt\n"
                        "PATH=\"$PWD/shim:$PATH\" bash script-c.sh ai-sandbox"
                    ),
                    "label": 'Run the two unsafe scripts through the harness',
                    "intro": 'You will now run script-b.sh and script-c.sh with the stand-ins first on the search path, so nothing reaches the cluster.',
                    "expect": 'Example only. The first four lines come from script-b.sh and the last two from script-c.sh.\nWOULD RUN: oc get pods -n ai-sandbox --field-selector=status.phase==Succeeded -o name\ntidy complete for ai-sandbox\nWOULD RUN: oc delete pod --field-selector=status.phase==Succeeded -n ai-sandbox\nWOULD RUN: oc delete configmap,pvc --all -n ai-sandbox --wait=false\nWOULD RUN: curl <a download of an installer>\nWOULD RUN: curl <a report call that includes the token>',
                    "lines": [
                        ("cd /workspace/aid-2/review", "Moves into the review folder, where the shim folder and the scripts are.", "$PWD/shim only points at the stand-ins when you are standing in this folder."),
                        ("PATH=\"$PWD/shim:$PATH\"", "For this one command only, puts the shim folder first in the search path.", "Only this one command sees the stand-ins, so the rest of your shell still runs the real commands afterward."),
                        ("bash script-b.sh ai-sandbox", "Runs the script with the sandbox project name as its argument. Every oc, curl and rm in it reaches a stand-in.", "Running the script as written shows its real behavior, including what it does after it says it is done."),
                        ("2>&1 | tee harness-b.txt", "Shows the output and also saves it in a file, so Verify can count and search it without running the script again.", "The saved output is the evidence the Verify tests read, so you never run the unsafe script a second time."),
                    ],
                },
            ],
            "security": "The harness covers only the commands you made stand-ins for. A script that calls another program, or uses its own full path to a command, bypasses it, so a harness run never proves a script is safe.",
            "checkpoint": "script-b.sh prints a delete of finished pods and a delete of all config maps and volume claims in ai-sandbox, after its own message says it is done. script-c.sh prints a download of an installer and a report call that includes the token in plain text.",
        },
    ],
    "verify": [
        {
            "kind": "positive",
            "title": "Nothing in the sandbox project was lost",
            "controls": [
                {"id": 'SA-11 Developer Testing and Evaluation', "how": 'The config map and the deployment still being there is the evidence that the harness run did not also delete anything.'},
            ],
            "why": "The unsafe scripts ran only through the harness in Step 2. Now confirm that the objects an unsafe cleanup would have deleted are still there in the real project.",
            "code": (
                "oc get configmap/sandbox-evidence deployment/sandbox-pod -n ai-sandbox -o name"
            ),
            "expect": (
                "Example only. The command names the two objects, because OpenShift adds its own config maps to every project.\n"
                "configmap/sandbox-evidence\n"
                "deployment.apps/sandbox-pod"
            ),
            "lines": [
                ("oc get configmap/sandbox-evidence deployment/sandbox-pod -n ai-sandbox -o name", "Asks the cluster for the two named objects in the sandbox project and prints only their names.", "Both objects are what an unsafe cleanup would have deleted. Naming them avoids confusion with the config maps OpenShift adds to every project."),
                ("configmap/sandbox-evidence", "The evidence config map is still there.", "A review must not remove evidence."),
                ("deployment.apps/sandbox-pod", "The sandbox deployment is still there.", "It shows the harness run changed nothing."),
            ],
            "checkpoint": "Both the config map sandbox-evidence and the deployment sandbox-pod are listed, so the harness run changed nothing.",
        },
        {
            "kind": "negative",
            "title": "The harness shows the harm and the harm did not happen",
            "controls": [
                {"id": 'CM-3 Configuration Change Control', "how": 'The counted harness output shows what the refused script would have done, and Test 1 shows it did not run for real.'},
                {"id": 'SA-11 Developer Testing and Evaluation', "how": 'The saved harness output is the test result and the reason the script was refused.'},
            ],
            "why": "Count what the hidden-delete script tried to do in the harness output you saved in Step 2, which proves it is unsafe.",
            "code": (
                "cd /workspace/aid-2/review\n"
                "grep -c 'WOULD RUN' harness-b.txt\n"
                "grep 'delete' harness-b.txt"
            ),
            "expect": (
                "Example only. The delete lines come from your harness-b.txt.\n"
                "3\n"
                "WOULD RUN: oc delete pod --field-selector=status.phase==Succeeded -n ai-sandbox\n"
                "WOULD RUN: oc delete configmap,pvc --all -n ai-sandbox --wait=false"
            ),
            "lines": [
                ("cd /workspace/aid-2/review", "Moves into the review folder, where Step 2 saved harness-b.txt.", "The saved output is a file in that folder."),
                ("grep -c 'WOULD RUN' harness-b.txt", "Counts the lines where a stand-in command was asked to act. The answer is 3: one read-only listing and the two deletes.", "It shows how many commands the script tried, without running the script again."),
                ("grep 'delete' harness-b.txt", "Prints the two delete attempts.", "These are the deletes the script hid behind a message that said it was done."),
            ],
            "checkpoint": "The harness shows two deletes you never asked for and counts three attempted commands.",
        },
        {
            "kind": "negative",
            "title": "A clean result from a safe script can still be wrong",
            "controls": [
                {"id": 'SA-11 Developer Testing and Evaluation', "how": 'The script exits cleanly on a project that does not exist, so a clean exit proves little. The flaw to correct is the missing input check.'},
            ],
            "why": "Run the safe script, which only lists pods, against a project that does not exist. The safe script finishes with exit status 0 (the number a command leaves behind, where 0 means success) and no error. The script does not check its input, so confirm the input yourself before you trust an empty answer.",
            "code": (
                "cd /workspace/aid-2/review\n"
                "bash script-a.sh no-such-project\n"
                "echo \"exit status: $?\"\n"
                "oc get project no-such-project"
            ),
            "expect": (
                "Example only. The wording of the last line depends on your oc version.\n"
                "checked project: no-such-project\n"
                "exit status: 0\n"
                "Error from server (NotFound): namespaces \"no-such-project\" not found"
            ),
            "lines": [
                ("cd /workspace/aid-2/review", "Moves into the review folder, where script-a.sh is.", "The safe script is a file in that folder."),
                ("bash script-a.sh no-such-project", "Runs the safe script against a project that does not exist.", "It shows what a script does with a bad input."),
                ("checked project: no-such-project", "The script says it checked a project that is not there.", "A clean-looking report is not proof that the input was right."),
                ("echo \"exit status: $?\"", "Prints how the script ended. 0 means success.", "A clean exit status says nothing about whether the answer is right."),
                ("oc get project no-such-project", "Asks the cluster whether the project exists. It answers NotFound.", "This is the check the script should have made first."),
            ],
            "checkpoint": "The script reports that it checked a project that does not exist, and exits cleanly. Your next step when a result is empty is to check the input, not to run the script again with other options.",
        },
    ],
    "waivers": {
        "your_turn": "The YOUR TURN lines were removed on reviewer feedback (ENG-0); the optional command list at the end replaces them.",
    },
    "glossary": [
        ("Assistant", "A program that writes text on request, including scripts."),
        ("Stub model service", "A stand-in for a model that returns fixed answers, so results are repeatable."),
        ("Harness", "Stand-in commands that print what a script asked for instead of doing it."),
        ("Sandbox project", "A project where nothing important lives."),
        ("Hardcoded secret", "A password, token or key written directly into a script."),
        ("Pinned", "Fixed to one exact version, so the same thing is fetched every time."),
        ("PATH", "The list of folders the shell searches for a command."),
        ("Port forward", "A tunnel from your shell to a service inside the cluster."),
    ],
    "design": [
        {
            "decision": "Layer two checks before a script runs",
            "how": "Each script gets a pattern search and then a print-only run with stand-in commands placed first on the path. The two unsafe scripts are never run for real.",
            "why": "No single check is enough, because a search finds only what was thought of and the print-only run covers only the commands it stands in for.",
            "alternatives": "Careful human reading alone is the alternative. Advantage: a reader can judge intent and context that no tool sees. Drawback: it is slow, and a hidden delete in an exit handler is easy to miss in a long file.",
        },
        {
            "decision": "Refuse unsafe scripts and name lines, not values",
            "how": "The unsafe scripts are not run for real and not fixed, and you note only file names and line numbers.",
            "why": "A token written into a script is already exposed, and repeating it would spread it further. The owner still needs enough detail to act.",
            "alternatives": "Fixing the script and running it anyway is the alternative. Advantage: a working result arrives sooner. Drawback: the fix is unreviewed, the owner is never told, and the exposed token is never replaced.",
        },
        {
            "decision": "Use a stand-in model service with fixed answers",
            "how": "A scripted service in the cluster returns the same three scripts by request id, with no model account or key involved.",
            "why": "Fixed answers let the learner compare results with expected output, and there is no key to protect.",
            "alternatives": "A real hosted model is the alternative. Advantage: it shows how unpredictable real answers are. Drawback: answers vary between runs, a key must be kept safe, and the expected-output checks no longer work.",
        },
    ],
    "next": "Next module: AID-3 AI-Assisted Automation Under Review: you check a model's answer against one exact shape, log every exchange, and merge the script only after an automated review passes.",
}

MODULE["portability"] = {
    "bullets": [
        "The review habit ports as is. Pattern search and print-only run need only bash, grep and the scripts you are given.",
        "Change these lab values first: the stub URL (http://127.0.0.1:8089 through a port forward to svc/stub-model in ai-lab), and the sandbox project ai-sandbox.",
        "Outside the lab the scripts come from a real assistant or a pull request, so the save-to-file step changes. The checks after it stay the same.",
        "The print-only run only covers the commands you shim. Add a shim for every tool the script calls before you trust the output.",
    ],
    "headers": ["Check/part", "In this lab", "On other platforms", "What you change"],
    "rows": [
        ("Getting the scripts", "curl to the stub model service through oc port-forward", "A real assistant, a pull request or a file someone sent you", "Save the script to a file in your own review folder. Drop the port forward."),
        ("Pattern search", "grep -nE", "The same", "Nothing. Add patterns for the tools your scripts call."),
        ("Print-only run", "Shim files for oc, curl and rm placed first on PATH", "The same", "Add a shim for each other tool the script calls."),
        ("Check that nothing changed", "oc and the project ai-sandbox with the sandbox-evidence config map", "kubectl and a throwaway namespace, or a disposable VM or container", "The tool name and the namespace. Keep the sandbox free of real data."),
    ],
}
