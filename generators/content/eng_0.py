"""ENG-0: Terminal, Git and Your Lab. Foundation of the engineering track; no controls, skills only."""

CRED = "credential.helper=!f() { echo username=$GITEA_USER; echo password=$GITEA_TOKEN; }; f"

MODULE = {
    "id": "ENG-0",
    "slug": "Foundation",
    "title": "Terminal, Git and Your Lab",
    "draft": (
        "Nothing here has run on a live cluster. Assumptions to confirm on the first run. "
        "(1) The health check matches pods by namespace and by part of the pod name, because the deployment names are not confirmed: "
        "loki and grafana in siem, tekton-pipelines in openshift-pipelines, trivy and falco in security-tools, siem-forwarder or collector in openshift-logging, "
        "and any pod in chat, gitea and kyverno. The lab contract lists the namespace build for pipelines, but the Tekton controller normally runs in openshift-pipelines; "
        "if the pods are elsewhere, change the pattern line in lab/states/eng-0/30-sandbox-repo.sh. "
        "(2) The default branch of the repository eng-sandbox is main, as the start state creates it. "
        "(3) git reads the Gitea token through a credential helper that is a one-line shell function; it relies on GITEA_USER and GITEA_TOKEN being exported in lab shell. "
        "(4) The demo-app pod ignores the stop signal, so scaling it to zero takes the stop grace period before the pod is gone; the start state sets that period to 5 seconds on demo-app (lab/states/eng-0/20-demo-app.sh) and the negative test waits for it. "
        "(5) The exact wording of the YAML error message differs between oc releases; the expected output is marked as an example."
    ),
    "controls": [],
    "mentions": [],
    "unit_values_ok": ["2 minutes", "5 seconds", "120 seconds"],
    "minutes": {"hands_on": 40, "verify": 0},
    "tools": ["lab shell", "oc", "git", "Gitea (free, open source)", "curl", "jq"],
    "tool_why": True,
    "hide_draft": True,
    "hover": True,
    "terms_at_end": True,
    "diagrams": [
        {
            "id": "flow",
            "title": "What you touch in this module",
            "caption": "This is the lab (test) setup: you type everything in lab shell, and one learner cluster holds the git server and the platform tools. In production, the git server and the platform tools are shared services that people reach with their own sign-in, not a cluster built for one learner. Each step below adds one part, drawn with thick lines.",
            "per_step": True,
            "rankdir": "TB",
            "step_notes": {
                1: "You open lab shell and make a practice folder with a small file in it.",
                2: "Git copies the sandbox repository from Gitea, and you push one change back to that same repository on Gitea.",
                3: "The oc tool asks the cluster what is running: it reads the sample pod and the log of one platform tool pod.",
                4: "The health check script from the repository asks each platform tool whether its pods are running.",
            },
            "zones": [
                {"id": "shellz", "label": "Lab shell (a container on your computer)", "kind": "boundary"},
                {"id": "cluster", "icon": "aws/group-AWS-Cloud", "label": "Lab cluster (your OpenShift cluster, in AWS)", "kind": "boundary"},
                {"id": "gitz", "icon": "brands/gitea", "label": "Gitea (the git server)", "parent": "cluster", "kind": "group", "labeljust": "r"},
                {"id": "demoz", "icon": "k8s/ns", "label": "Demo namespace", "parent": "cluster", "kind": "group"},
                {"id": "platz", "icon": "k8s/ns", "label": "Platform tool namespaces", "parent": "cluster", "kind": "group"},
            ],
            "key": {"aws/group-AWS-Cloud": "AWS Cloud", "brands/gitea": "Gitea git server", "k8s/ns": "Kubernetes namespace (OpenShift project)", "brands/git": "Git", "brands/openshift": "OpenShift command line tool", "brands/gnubash": "Shell script", "k8s/pod": "Kubernetes pod"},
            "nodes": [
                {"id": "folder", "title": "Practice folder", "sub": "Holds notes.txt", "zone": "shellz", "s": 1},
                {"id": "git", "icon": "brands/git", "title": "Git client", "sub": "Git command line tool: clone, commit, push", "zone": "shellz", "s": 2},
                {"id": "oc", "icon": "brands/openshift", "title": "OpenShift tool", "sub": "OpenShift command line tool oc", "zone": "shellz", "s": 3},
                {"id": "script", "icon": "brands/gnubash", "title": "Health check", "sub": "Shell script health-check.sh", "zone": "shellz", "s": 4},
                {"id": "repo", "icon": "brands/git", "title": "Repository", "sub": "Git repository eng-sandbox, stored on Gitea", "zone": "gitz", "s": 2},
                {"id": "pod", "icon": "k8s/pod", "title": "Sample app pod", "sub": "Kubernetes pod demo-app, status Running", "zone": "demoz", "kind": "ok"},
                {"id": "tools", "title": "Platform tools", "sub": "Pods of each platform tool", "zone": "platz", "kind": "ok"},
            ],
            "edges": [
                {"a": "git", "b": "repo", "label": "Clones from, pushes to", "s": 2},
                {"a": "oc", "b": "pod", "label": "Reads", "kind": "ok", "s": 3},
                {"a": "oc", "b": "tools", "label": "Reads a log", "kind": "ok", "s": 3},
                {"a": "repo", "b": "script", "label": "Supplies", "s": 4},
                {"a": "script", "b": "tools", "label": "Checks", "kind": "ok", "s": 4},
                {"a": "script", "b": "pod", "label": "Checks", "kind": "ok", "s": 4},
            ],
            "why_built": (
                "Lab shell, on your computer, holds every command you need, so nothing is installed and the steps are the same on Mac and Windows. "
                "Your own OpenShift cluster, in AWS, is a real platform you can change or break without affecting anyone else. "
                "Commands in lab shell reach the cluster over the network, signed in with a credential the lab gives you. "
                "Gitea and the platform tools run inside the cluster, so every module starts from the same place."
            ),
            "setup": [
                ("Lab shell", "A container on your laptop", "Same tools and same steps on Mac and Windows, nothing to install, and the lab sets your variables and sign-in for you."),
                ("Lab cluster", "OpenShift on one node in AWS", "A real platform to learn on. It is yours alone, so you can change it, break it and reset it, and lab down removes it so it stops costing money."),
                ("Gitea", "Inside the cluster", "A git server you control, so you can push and review changes without an outside account."),
                ("Platform tools", "Inside the cluster", "Tools such as log storage, pipelines, policy and scanning run beside your work, so later modules build on tools that are already there."),
                ("The connection", "The network, from lab shell to the cluster's API", "One sign-in and one command (oc) work for every module. In this lab the cluster's address is reachable from the internet so your laptop needs no VPN, and credentials control access. A production system would usually keep it private."),
            ],
            "reading": [
                "1. Practice folder: a folder you make in lab shell that holds notes.txt.",
                "2. Git client: the git command in lab shell. It clones from the repository and pushes your change back, on the branch named main.",
                "3. OpenShift tool: the oc command in lab shell. It reads the demo-app pod and the log of one pod of a platform tool (Kyverno).",
                "4. Health check: the script health-check.sh, which comes from the repository and checks the pods of each platform tool and of the sample app.",
                "5. Repository: the eng-sandbox folder and its history, stored on the Gitea server, not on your laptop, until you clone it.",
                "6. Gitea: the git server that runs inside your lab cluster. Git is the tool; Gitea is the server it talks to.",
                "7. Lab cluster: your own OpenShift cluster in AWS. It holds Gitea, the sample app and the platform tools.",
                "8. Sample app pod: the demo-app pod in the demo namespace, status Running. A pod is the smallest running unit on the cluster.",
                "9. Platform tools: the pods of each platform tool, in their own namespaces, such as the log store and the pipeline engine.",
            ],
        },
    ],
    "prereq": ["A running lab and the lab command on your laptop. No other module is needed."],
    "lab_needs": [],
    "lab": {
        "start": "lab start eng-0",
        "env": ["LAB_ID", "GITEA_URL", "GITEA_USER", "GITEA_TOKEN"],
    },
    "requirement": (
        "This module teaches the working habits every engineering module relies on: opening the lab, "
        "moving around files, using git, asking the cluster questions with oc, reading YAML (a plain-text format for settings) "
        "and error messages, and checking that the platform tools are running. "
        "You finish with one script that checks every platform tool."
    ),
    "requirement_bullets": [
        "Purpose: build the working habits every engineering module relies on: using the terminal, git, oc and YAML, and reading error messages.",
        "You open lab shell, clone and change a repository on Gitea, ask the cluster questions with oc, and fix a broken YAML file with a dry run.",
        "You finish by reading and running one script that checks every platform tool and reports one line for each.",
    ],
    "objectives": [
        {"label": "Skill", "text": "Move around the terminal, make and change files, use git with a server, ask the cluster questions with oc, read a YAML error, and read and run a health check script."},
        {"label": "Tools", "text": "`lab shell` gives every learner the same terminal, `git` and Gitea keep and share your files with a history, `oc` asks the cluster what is running, `curl` and `jq` ask the Gitea server for its newest commit, and a shell script checks every platform tool."},
        {"label": "Security Function", "text": "Proves what is running. The health check reports UP or DOWN for each platform tool and exits with a non-zero code when anything is down, and git history records who changed what."},
    ],
    "mapping": [],
    "intent": [],
    "terms": [
        ("Terminal", "A window where you type commands and read the answers."),
        ("Command", "One line you type that tells the computer to do one thing."),
        ("Directory", "A folder. The terminal is always in one directory, called the current directory."),
        ("Workload", "A program that runs on the cluster, such as the sample app demo-app. Running workloads is what the cluster is for."),
        ("Namespace", "A named section of the cluster that keeps workloads apart. OpenShift also calls it a project."),
        ("Cluster", "A group of servers that work together as one system. Here it is your own OpenShift cluster in AWS."),
        ("Container", "A sealed box that holds one program and everything it needs to run, so it runs the same way anywhere."),
        ("YAML", "A plain-text format for settings: lines of name: value, with indentation to show what belongs to what."),
        ("Gitea", "A git server that runs in your lab. It holds the repositories you clone and push to."),
        ("Variable", "A named value the lab sets for you, such as LAB_ID. The dollar sign in front of a name means use its value."),
        ("Token", "A long secret string that works like a password for one program. Gitea gives you one so git can prove who you are when it sends a change. Anyone who holds it can act as you, so never print it or commit it."),
        ("Pod", "The smallest running unit on the cluster: one or more containers together."),
        ("Repository", "A folder whose history git tracks, so you can see what changed and when."),
        ("Commit", "One saved snapshot in git, with a short message."),
        ("Credential helper", "A small command that git runs to get your user name and token when it needs to sign in, so you never type them."),
        ("API", "A set of web addresses that programs use to ask a service questions and get answers."),
        ("Remote", "A copy of the repository on another server. Here the remote is Gitea."),
        ("Script", "A text file of commands that the computer runs from top to bottom."),
        ("Exit code", "A number a command leaves behind when it ends. 0 means success; anything else means a problem."),
        ("Heredoc", "A way to make a file by pasting its text between a first line such as cat > name <<'EOF' and a last line that says EOF."),
        ("Home directory", "Your own folder inside lab shell, written ~. It is kept in the lab-workspace folder on your computer, so what you save there stays between sessions."),
        ("Training folder", "The folder you downloaded to your computer. It holds the lab folder, the modules and the README."),
        ("oc", "The command-line tool for OpenShift. You type oc to ask the cluster questions."),
        ("jq", "A tool that picks one value out of JSON text."),
    ],
    "concepts": [
        {
            "heading": "2.1 The terminal and lab shell",
            "paras": [
                {"bullets": [
                    "A terminal takes one line at a time, runs it, and prints the answer.",
                    "Mac and Windows commands differ, so lab shell (a prebuilt container) gives everyone the same tools.",
                    "The lab keeps passwords and tokens in variables, so you never type or save one.",
                    "Lab shell runs on your computer, and the commands you type in it act on the cluster in AWS (see the picture above).",
                ]},
                "These keys and commands are the ones you use most:",
            ],
            "table": {
                "headers": ["Key or command", "What it does"],
                "rows": [
                    ("Up arrow", "Brings back the last command so you can fix a typo instead of retyping."),
                    ("Tab", "Finishes a word for you. If nothing happens, press Tab twice to see the choices."),
                    ("Ctrl+C", "Stops a command that is running or stuck. It is safe."),
                    ("pwd", "Prints where you are (the current directory)."),
                    ("ls -l", "Lists what is in the current directory, one line per item."),
                    ("cd NAME", "Moves into the directory called NAME. cd .. moves up one level."),
                    ("cat FILE", "Prints a file on the screen. cat -n numbers the lines."),
                ],
            },
        },
        {
            "heading": "2.2 Files, oc and git",
            "paras": [
                {"bullets": [
                    "oc is the command-line tool for OpenShift, and it tells you which workloads (programs the cluster runs, such as demo-app) are up.",
                    "Most oc commands are a verb plus what it acts on: get lists, describe explains, logs prints what a program wrote.",
                    "git records the history of a folder: clone copies a repository, commit saves a snapshot, and push sends it back.",
                    "The git server in this lab is Gitea, which runs inside your lab cluster.",
                ]},
                "These commands answer the questions you ask most:",
            ],
            "table": {
                "headers": ["Command", "What it answers"],
                "rows": [
                    ("oc get pods -n NAME", "Which pods are in this namespace, and are they ready?"),
                    ("oc describe pod POD", "Why is this pod in this state? The Events at the end often say."),
                    ("oc logs POD", "What did the program print? An empty answer is normal for a quiet program."),
                    ("git status", "What has changed since the last commit?"),
                    ("git diff", "Exactly which lines changed?"),
                ],
            },
        },
        {
            "heading": "2.3 Reading YAML and error messages",
            "paras": [
                "YAML describes settings to the cluster. Three rules cover almost everything you will read. Use spaces, never the Tab key. The notes after each arrow are explanations, not part of the file.",
                {"code": (
                    "name: demo-app           <- rule 1: a setting called name, value demo-app\n"
                    "labels:                  <- rule 2: the indented lines below belong to labels\n"
                    "  app: demo-app\n"
                    "ports:                   <- rule 3: each hyphen starts one item in a list\n"
                    "  - 8080\n"
                    "  - 8443"
                )},
                {"bullets": [
                    "The two-space indent is the only thing that puts app: demo-app under labels, so check the spaces.",
                    "An error message is information, not failure.",
                    "The first words say which tool complained. The end usually says what is wrong and where, often with a line number.",
                ]},
            ],
        },
    ],
    "setup": {'title': 'Before you start: install the lab command and start the lab',
     'intro': 'Steps 1 to 4 run inside lab shell, which works only after you install the lab command and start your lab in AWS. '
              'Do this part once, typing in PowerShell on Windows (not Git Bash) or Terminal on Mac, never inside lab shell.',
     'needs': ['The training folder, downloaded to this computer. Unzip it if it came as a zip file. It is the folder that contains the lab '
               'folder, the modules folder and README.md.',
               'Python 3.10 or newer. The first block checks it.',
               'Docker (Docker Desktop on Windows or Mac), open and running, or Podman. The first block checks it.',
               'An AWS account you are allowed to spend in, with credentials saved on this laptop under a profile name. Use a lab account, not '
               'a production one. The profile name is the word in square brackets in the file .aws\\credentials or .aws\\config in your user '
               'folder.',
               'A Red Hat pull secret: a small file OpenShift needs to install. Download it from console.redhat.com and save it as '
               'pull-secret.json (the settings block says where).',
               'A public Route 53 hosted zone (a domain name managed in AWS) in that same AWS account. The cluster gets its address from it.',
               'A budget. The whole track is estimated at about $18 of AWS cost, and the lab bills by the hour until you run lab down.'],
     'blocks': [{'label': 'Install: Check your tools, then install the lab command and build the tools container',
                 'intro': 'You will now move into the training folder, check that Python and Docker work, install the lab command and build the container that lab shell opens.',
                 'sequence': [
                     'First, replace the path in the first line with the folder you downloaded and unzipped (the folder that contains the lab folder).',
                     'Paste the whole block below into the terminal.',
                     'Finally, if your terminal says lab is not recognized, close PowerShell, open a new window, and try again.',
                 ],
                 'lang': 'powershell',
                 'code': 'cd "C:\\path\\to\\Engineering Leveling Training"\n'
                         'python --version\n'
                         'docker --version\n'
                         'pip install -e ./lab\n'
                         'lab build-image',
                 'expect': 'Example only. python --version shows 3.10 or higher, and docker --version shows a version number. pip reports that '
                           'lab was installed. The image build downloads about 400 MB, can take several minutes, and ends without an error.',
                 'lines': [('cd "C:\\path\\to\\..."',
                            'Moves the terminal into the training folder.',
                            'pip and lab need to see the lab folder from here.'),
                           ('python --version', 'Prints the Python version.', 'The lab command needs Python 3.10 or newer.'),
                           ('docker --version',
                            'Prints the Docker version.',
                            'If this fails, install Docker Desktop and open it. lab build-image and lab shell both need a running container '
                            'engine.'),
                           ('pip install -e ./lab',
                            'Installs the lab command so it runs from the lab folder. The -e keeps it pointed there, which lab build-image '
                            'needs to find its files.',
                            'Without it your terminal does not know the word lab.'),
                           ('lab build-image',
                            'Builds the tools container (oc, git, jq, curl and the rest).',
                            'lab shell opens this container, so it must exist first.')]},
                {'label': 'Mac Install: Check your tools, then install the lab command and build the tools container',
                 'intro': 'Mac version of the Windows block above, using Terminal and bash commands.',
                 'sequence': [
                     'First, open Terminal and replace the path in the first line with the training folder you downloaded and unzipped.',
                     'Paste the whole block below into the terminal.',
                     'Finally, if Terminal says lab is not found, close it, open a new window, and try again.',
                 ],
                 'lang': 'bash',
                 'code': 'cd "/path/to/Engineering Leveling Training"\n'
                         'python3 --version\n'
                         'docker --version\n'
                         'pip3 install -e ./lab\n'
                         'lab build-image',
                 'expect': 'Example only. python3 --version shows 3.10 or higher, and docker --version shows a version number. pip reports '
                           'that lab was installed. The image build downloads about 400 MB, can take several minutes, and ends without an '
                           'error.',
                 'lines': [('cd "/path/to/..."',
                            'Moves the terminal into the training folder.',
                            'pip and lab need to see the lab folder from here.'),
                           ('python3 --version', 'Prints the Python version.', 'The lab command needs Python 3.10 or newer.'),
                           ('docker --version', 'Prints the Docker version.', 'If this fails, install Docker Desktop and open it.'),
                           ('pip3 install -e ./lab',
                            'Installs the lab command so it runs from the lab folder.',
                            'Without it your terminal does not know the word lab.'),
                           ('lab build-image',
                            'Builds the tools container (oc, git, jq, curl and the rest).',
                            'lab shell opens this container, so it must exist first.')]},
                {'label': 'Cost Guard: Deploy the cost guard (optional but recommended, once per AWS account)',
                 'intro': 'You will now deploy the cost guard, a small set of AWS resources that warns you about an idle lab and can pause it. The cost guard starts in dry-run mode: it emails what it would do and changes nothing until you turn dry run off.',
                 'sequence': [
                     'Why: without it, a lab you walk away from keeps billing at about $0.77 an hour (an estimate). The commands lab pause, lab resume, lab keep and lab pull also do not work.',
                     'When: deploy it once per AWS account and region, not once per lab. Skip this block if it is already deployed or if you will always run lab down when you stop.',
                     'Risk: the build role of the cost guard has broad permissions, so use a dedicated lab account, never one that holds other work.',
                     'Before you run it: terraform version must print a version. Use the same AWS profile and email as in the settings block, and sign in to AWS first if your profile needs it.',
                 ],
                 'lang': 'powershell',
                 'code': '$env:AWS_PROFILE = "your-aws-profile"\n'
                         'cd terraform\\guard\n'
                         'terraform init\n'
                         'terraform apply -var region=us-east-1 -var alert_email=you@example.com\n'
                         'terraform output -raw guard_bucket\n'
                         'terraform output -raw budget_topic_arn\n'
                         'cd ..\\..',
                 'expect': 'Example only. terraform apply shows a plan and asks you to type yes. It ends with Apply complete and lists the '
                           'outputs. The last two commands print the bucket name (starts with lab-guard-) and the topic address (starts with '
                           'arn:aws:sns). Copy both for the next block. AWS also emails you a subscription message: open it and click Confirm '
                           'subscription, or no guard email will reach you.',
                 'lines': [('$env:AWS_PROFILE',
                            'Names the AWS credentials Terraform uses.',
                            'The guard must be created in the lab account, not another one.'),
                           ('cd terraform\\guard',
                            "Moves into the guard's folder.",
                            'Terraform reads the guard files from the folder it runs in.'),
                           ('terraform init',
                            'Downloads the Terraform plugins the guard needs.',
                            'terraform apply cannot run until this has finished.'),
                           ('terraform apply -var region=... -var alert_email=...',
                            'Creates the guard: a bucket, notification topics, a scheduled function and a build project. Type yes when it '
                            'asks.',
                            "The region must match your lab region, and the email gets the guard's warnings."),
                           ('terraform output -raw guard_bucket',
                            'Prints the guard bucket name.',
                            'Each lab needs it to register with the guard.'),
                           ('terraform output -raw budget_topic_arn',
                            'Prints the budget topic address.',
                            'The lab sends its spend alerts there.'),
                           ('cd ..\\..', 'Moves back to the training folder.', 'The next block and lab up run from there.')]},
                {'label': 'Mac Cost Guard: Deploy the cost guard (optional but recommended)',
                 'intro': 'Mac version of the Windows guard block above, using Terminal and bash commands.',
                 'sequence': [
                     'Use the same AWS profile and email as in the settings block, and sign in to AWS first if your profile needs it.',
                     'Terraform must be installed; terraform version must print a version.',
                 ],
                 'lang': 'bash',
                 'code': 'export AWS_PROFILE="your-aws-profile"\n'
                         'cd terraform/guard\n'
                         'terraform init\n'
                         'terraform apply -var region=us-east-1 -var alert_email=you@example.com\n'
                         'terraform output -raw guard_bucket\n'
                         'terraform output -raw budget_topic_arn\n'
                         'cd ../..',
                 'expect': 'Example only. terraform apply shows a plan and asks you to type yes. It ends with Apply complete and lists the '
                           'outputs. The last two commands print the bucket name (starts with lab-guard-) and the topic address (starts with '
                           'arn:aws:sns). Copy both for the next block. AWS also emails you a subscription message: open it and click Confirm '
                           'subscription, or no guard email will reach you.',
                 'lines': [('export AWS_PROFILE',
                            'Names the AWS credentials Terraform uses.',
                            'The guard must be created in the lab account, not another one.'),
                           ('cd terraform/guard',
                            "Moves into the guard's folder.",
                            'Terraform reads the guard files from the folder it runs in.'),
                           ('terraform init',
                            'Downloads the Terraform plugins the guard needs.',
                            'terraform apply cannot run until this has finished.'),
                           ('terraform apply -var region=... -var alert_email=...',
                            'Creates the guard: a bucket, notification topics, a scheduled function and a build project. Type yes when it '
                            'asks.',
                            "The region must match your lab region, and the email gets the guard's warnings."),
                           ('terraform output -raw guard_bucket',
                            'Prints the guard bucket name.',
                            'Each lab needs it to register with the guard.'),
                           ('terraform output -raw budget_topic_arn',
                            'Prints the budget topic address.',
                            'The lab sends its spend alerts there.'),
                           ('cd ../..', 'Moves back to the training folder.', 'The next block and lab up run from there.')]},
                {'label': 'Lab Settings: Set your lab settings and check them with a dry run',
                 'intro': 'You will now give the lab the settings it needs to build in AWS, then check them without building anything.',
                 'sequence': [
                     'First, save your pull secret as pull-secret.json in the lab-workspace folder. The second line of the block creates that folder.',
                     'Change the quoted values to yours: your AWS profile name, a short lab name, a destroy date a few days from today, and your email.',
                     'Next, if your AWS account has more than one public Route 53 zone, add one more line, $env:BASE_DOMAIN = "your-zone-name", before lab up --dry-run.',
                     'Finally, paste the block. The two guard lines are optional but recommended; leave them out if you skipped the guard block.',
                     'Settings last only for this PowerShell window, so paste them again if you open a new one.',
                 ],
                 'lang': 'powershell',
                 'code': '$env:AWS_PROFILE = "your-aws-profile"\n'
                         'New-Item -ItemType Directory -Force "$HOME\\lab-workspace"\n'
                         '$env:PULL_SECRET_FILE = "$HOME\\lab-workspace\\pull-secret.json"\n'
                         '$env:TF_VAR_lab_id = "eng-yourname"\n'
                         '$env:TF_VAR_region = "us-east-1"\n'
                         '$env:TF_VAR_destroy_after = "2026-11-20"\n'
                         '$env:TF_VAR_alert_email = "you@example.com"\n'
                         '$env:TF_VAR_guard_bucket = "paste-the-guard-bucket-name"\n'
                         '$env:TF_VAR_guard_budget_topic_arn = "paste-the-budget-topic-arn"\n'
                         'lab up --dry-run',
                 'expect': 'Example only. The dry run prints what lab up would do and changes nothing. Read it for an error about a missing '
                           'setting or file, and fix that before you go on.',
                 'lines': [('$env:AWS_PROFILE',
                            'Names the AWS credentials to use.',
                            'lab up passes your credentials into the container by name, so it has to know which profile is yours.'),
                           ('New-Item ... lab-workspace',
                            'Creates the lab-workspace folder in your user folder if it is not there.',
                            'The pull secret and your lab files live there. Keep it on a local folder, not one synced by OneDrive.'),
                           ('$env:PULL_SECRET_FILE',
                            'The path to your Red Hat pull secret file.',
                            'The OpenShift install needs it. lab up refuses to start without it and never prints it.'),
                           ('$env:TF_VAR_lab_id',
                            'A short name for your lab.',
                            'It goes into resource names and tags, so you can find and remove everything the lab creates.'),
                           ('$env:TF_VAR_region', 'The AWS region to build in.', 'Every resource is created there.'),
                           ('$env:TF_VAR_destroy_after',
                            'A date in the form YYYY-MM-DD.',
                            'The lab is removed after this date if you have not run lab down, which caps the cost. Terraform rejects any other '
                            'date format.'),
                           ('$env:TF_VAR_alert_email',
                            'The address for budget and cost-guard warnings.',
                            'You hear about an idle or expensive lab before the bill arrives.'),
                           ('$env:TF_VAR_guard_bucket',
                            'The guard bucket name from the guard block. Optional but recommended: leave this line and the next one out if you '
                            'skipped the guard.',
                            'It registers your lab with the guard so the guard can warn you about it and pause it.'),
                           ('$env:TF_VAR_guard_budget_topic_arn',
                            'The budget topic address from the guard block.',
                            'The lab needs it whenever the guard bucket is set, and refuses to plan without it.'),
                           ('lab up --dry-run',
                            'Shows what lab up would do and changes nothing.',
                            'It catches a missing setting before anything costs money.')]},
                {'label': 'Mac Lab Settings: Set your lab settings and check them with a dry run',
                 'intro': 'Mac version of the Windows block above, using Terminal and bash commands.',
                 'sequence': [
                     'First, save your pull secret as pull-secret.json in the lab-workspace folder. The second line creates that folder.',
                     'Change the quoted values to yours: your AWS profile name, a short lab name, a destroy date a few days from today, and your email.',
                     'Next, if your AWS account has more than one public Route 53 zone, add one more line, export BASE_DOMAIN="your-zone-name", before lab up --dry-run.',
                     'Finally, paste the block. The two guard lines are optional but recommended; leave them out if you skipped the guard block.',
                     'Settings last only for this Terminal window, so paste them again if you open a new one.',
                 ],
                 'lang': 'bash',
                 'code': 'export AWS_PROFILE="your-aws-profile"\n'
                         'mkdir -p "$HOME/lab-workspace"\n'
                         'export PULL_SECRET_FILE="$HOME/lab-workspace/pull-secret.json"\n'
                         'export TF_VAR_lab_id="eng-yourname"\n'
                         'export TF_VAR_region="us-east-1"\n'
                         'export TF_VAR_destroy_after="2026-11-20"\n'
                         'export TF_VAR_alert_email="you@example.com"\n'
                         'export TF_VAR_guard_bucket="paste-the-guard-bucket-name"\n'
                         'export TF_VAR_guard_budget_topic_arn="paste-the-budget-topic-arn"\n'
                         'lab up --dry-run',
                 'expect': 'Example only. The dry run prints what lab up would do and changes nothing. Read it for an error about a missing '
                           'setting or file, and fix that before you go on.',
                 'lines': [('export AWS_PROFILE',
                            'Names the AWS credentials to use.',
                            'lab up passes your credentials into the container by name.'),
                           ('mkdir -p ... lab-workspace',
                            'Creates the lab-workspace folder if it is not there.',
                            'The pull secret and your lab files live there.'),
                           ('export PULL_SECRET_FILE',
                            'The path to your Red Hat pull secret file.',
                            'lab up refuses to start without it and never prints it.'),
                           ('export TF_VAR_lab_id', 'A short name for your lab.', 'It goes into resource names and tags.'),
                           ('export TF_VAR_region', 'The AWS region to build in.', 'Every resource is created there.'),
                           ('export TF_VAR_destroy_after',
                            'A date in the form YYYY-MM-DD.',
                            'The lab is removed after this date if you have not run lab down.'),
                           ('export TF_VAR_alert_email',
                            'The address for budget and cost-guard warnings.',
                            'You hear about an idle or expensive lab before the bill arrives.'),
                           ('export TF_VAR_guard_bucket',
                            'The guard bucket name from the guard block. Optional but recommended: leave this line and the next one out if you '
                            'skipped the guard.',
                            'It registers your lab with the guard so the guard can warn you about it and pause it.'),
                           ('export TF_VAR_guard_budget_topic_arn',
                            'The budget topic address from the guard block.',
                            'The lab needs it whenever the guard bucket is set, and refuses to plan without it.'),
                           ('lab up --dry-run',
                            'Shows what lab up would do and changes nothing.',
                            'It catches a missing setting before anything costs money.')]},
                {'label': 'Settings File: Save the settings in a file so you do not paste them every time',
                 'intro': 'You will now save the settings above in a file, then load that file at the start of each session instead of pasting them. The file holds no passwords.',
                 'sequence': [
                     'First, run the first line. Notepad opens and offers to create the file. Paste the settings lines into it (not the lab up --dry-run line), save, and close. Keep it in lab-workspace, not in a folder that OneDrive syncs.',
                     'If your AWS profile needs a sign-in, run aws sso login --profile your-aws-profile.',
                     'Next, run the second line. Windows blocks script files by default; this line allows scripts in this one window only and changes nothing permanent. Run it each time before loading the file, or loading fails with a red error that says running scripts is disabled on this system.',
                     'Finally, run the third line to load the file. The dot and space at the start matter. Run it each time you open a new PowerShell window.',
                 ],
                 'lang': 'powershell',
                 'code': 'notepad "$HOME\\lab-workspace\\lab-env.ps1"\n'
                         'Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass\n'
                         '. "$HOME\\lab-workspace\\lab-env.ps1"',
                 'expect': 'Example only. Notepad opens. The second line prints nothing. Check that it worked with Get-ChildItem Env:TF_VAR_*, '
                           'which lists your settings.',
                 'lines': [('notepad ...lab-env.ps1',
                            'Opens the settings file for editing, creating it the first time.',
                            'One saved copy replaces pasting the same lines every session.'),
                           ('Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass',
                            'Lets this PowerShell window run script files. It lasts only until you close the window.',
                            'Windows blocks .ps1 files by default, so the next line would fail without it.'),
                           ('. "$HOME\\lab-workspace\\lab-env.ps1"',
                            'Runs the file in this window so its settings stay set.',
                            'Without the leading dot and space the settings vanish when the file ends.')]},
                {'label': 'Mac Settings File: Save the settings in a file so you do not paste them every time',
                 'intro': 'Mac version of the Windows block above, using Terminal and bash commands.',
                 'sequence': [
                     'First, run the first line. nano opens the file. Paste the settings lines (not the lab up --dry-run line), press Control-O then Enter to save, and Control-X to leave.',
                     'If your AWS profile needs a sign-in, run aws sso login --profile your-aws-profile.',
                     'Finally, run the second line to load the file. Run it each time you open a new Terminal window.',
                 ],
                 'lang': 'bash',
                 'code': 'nano "$HOME/lab-workspace/lab-env.sh"\nsource "$HOME/lab-workspace/lab-env.sh"',
                 'expect': 'Example only. nano opens. The second line prints nothing. Check that it worked with env | grep TF_VAR, which lists '
                           'your settings.',
                 'lines': [('nano ...lab-env.sh',
                            'Opens the settings file for editing, creating it the first time.',
                            'One saved copy replaces pasting the same lines every session.'),
                           ('source ...lab-env.sh',
                            'Runs the file in this window so its settings stay set.',
                            'A plain run would set them in a throwaway shell that ends right away.')]},
                {'label': 'AWS Sign-in: If your AWS profile signs in with SSO, give the container temporary keys',
                 'intro': 'You will now give lab shell temporary keys. Lab shell runs in a container that cannot see your AWS sign-in, so an SSO profile (single sign-on) fails there with the error that the config profile could not be found. Copy temporary keys into this PowerShell window and drop the profile name.',
                 'sequence': [
                     'Skip this block if your credentials are plain access keys.',
                     'The keys are secrets: do not paste or print them.',
                     'The keys expire, often after about an hour, so run these lines again right before lab up and whenever you see an expired-token error.',
                 ],
                 'lang': 'powershell',
                 'code': 'aws sso login --profile your-aws-profile\n'
                         'aws configure export-credentials --profile your-aws-profile --format powershell | Invoke-Expression\n'
                         'Remove-Item Env:AWS_PROFILE\n'
                         '$env:AWS_DEFAULT_REGION = "us-east-1"\n'
                         'lab shell\n'
                         'aws sts get-caller-identity',
                 'expect': 'Example only. The first line opens your browser to sign in. The next three print nothing. Inside lab shell, the '
                           'last command prints your AWS account number; type exit to leave lab shell. If it says the profile could not be '
                           'found, you skipped the Remove-Item line.',
                 'lines': [('aws sso login --profile ...',
                            'Signs you in to AWS through your browser.',
                            'The temporary keys come from this sign-in, and it expires.'),
                           ('aws configure export-credentials ... | Invoke-Expression',
                            "Copies temporary keys into this window's settings.",
                            'The container reads keys from settings; it cannot read your sign-in.'),
                           ('Remove-Item Env:AWS_PROFILE',
                            'Removes the profile name from this window.',
                            'The container cannot find that profile, so it would stop with an error.'),
                           ('$env:AWS_DEFAULT_REGION',
                            'Sets the AWS region for the container.',
                            'The profile that normally supplies the region is no longer used.'),
                           ('lab shell', 'Opens the tools container.', 'It is the quickest way to test the keys, before anything costs money.'),
                           ('aws sts get-caller-identity',
                            'Prints which AWS account the keys belong to.',
                            'It confirms the lab will build in the account you meant.')]},
                {'label': 'Mac AWS Sign-in: If your AWS profile signs in with SSO, give the container temporary keys',
                 'intro': 'Mac version of the Windows block above, using Terminal and bash commands.',
                 'sequence': [
                     'The keys are secrets: do not paste or print them.',
                     'The keys expire, often after about an hour, so run these lines again right before lab up.',
                 ],
                 'lang': 'bash',
                 'code': 'aws sso login --profile your-aws-profile\n'
                         'eval "$(aws configure export-credentials --profile your-aws-profile --format env)"\n'
                         'unset AWS_PROFILE\n'
                         'export AWS_DEFAULT_REGION="us-east-1"\n'
                         'lab shell\n'
                         'aws sts get-caller-identity',
                 'expect': 'Example only. The first line opens your browser to sign in. The next three print nothing. Inside lab shell, the '
                           'last command prints your AWS account number; type exit to leave lab shell. If it says the profile could not be '
                           'found, you skipped the unset line.',
                 'lines': [('aws sso login --profile ...',
                            'Signs you in to AWS through your browser.',
                            'The temporary keys come from this sign-in, and it expires.'),
                           ('eval "$(aws configure export-credentials ...)"',
                            "Copies temporary keys into this window's settings.",
                            'The container reads keys from settings; it cannot read your sign-in.'),
                           ('unset AWS_PROFILE',
                            'Removes the profile name from this window.',
                            'The container cannot find that profile, so it would stop with an error.'),
                           ('export AWS_DEFAULT_REGION',
                            'Sets the AWS region for the container.',
                            'The profile that normally supplies the region is no longer used.'),
                           ('lab shell', 'Opens the tools container.', 'It is the quickest way to test the keys, before anything costs money.'),
                           ('aws sts get-caller-identity',
                            'Prints which AWS account the keys belong to.',
                            'It confirms the lab will build in the account you meant.')]},
                {'label': 'Lab Build: Build your lab and load this module',
                 'intro': 'You will now build your lab in AWS and load the starting state for this module. lab up costs money and asks you to type yes.',
                 'sequence': [
                     'First, finish the settings step above, in the same PowerShell or Terminal window.',
                     'Run the commands below. Keep the window open until lab up finishes.',
                     'Mint mode: to install quickly, the lab runs OpenShift in mint mode. lab up creates one long-term access key for a lab-only AWS user, and the cluster stores it as a secret. That key does not expire. In a shared or long-lived account it is a risk, so use a dedicated lab account.',
                     'Finally, run lab down when you stop. It deletes the user and its keys and stops the billing.',
                 ],
                 'screenshot': {'file': 'ENG-0-shot-build.png', 'alt': 'The cost warning that lab up prints before it asks you to type yes', 'width': 6.0},
                 'lang': 'powershell',
                 'code': 'lab up\nlab start eng-0',
                 'expect': 'Example only. lab up finishes after the cluster install (roughly one to one and a half hours, an estimate), then '
                           'lab start reports that eng-0 is loaded.',
                 'lines': [('lab up',
                            'Builds your lab in AWS and installs the cluster. Type yes when it asks.',
                            'The module needs a running cluster to work against.'),
                           ('lab start eng-0',
                            'Loads the starting state for this module.',
                            'It creates the sandbox repository and the demo app that the steps use.')]}],
     'checkpoint': 'The lab command runs, lab up has finished, and lab start eng-0 has reported success. Run lab down whenever you stop, or '
                   'the lab keeps billing.'},
    "steps": [
        {
            "title": "Open lab shell, move around and write small files",
            "learn": "Opening lab shell, then making, reading, copying and deleting a small file, shows how the terminal behaves and where your work is kept between sessions.",
            "takeaway": "Know which directory you are in before you create or delete anything.",
            "why": "lab shell is where every later command runs. You learn to open lab shell, see where you are, make a folder, and read and write a small file.",
            "blocks": [
                {
                    "code": "lab shell",
                    "label": 'Open the lab shell',
                    "intro": 'You will now open lab shell, the tools container. Every command in this module, and in the modules after it, runs inside lab shell. Type this command in the terminal where you started the lab.',
                    "expect": 'Example only. Your prompt changes to show you are now inside the lab shell.',
                    "lines": [
                        ("lab", "The lab helper program installed with the lab.", "It is the entry point for every lab action, so you learn the word you will type most."),
                        ("shell", "Tells it to open the tools container. Your prompt changes to show you are inside.", "Every command in this module and the ones after it runs inside the container, so the first thing to do is get inside it."),
                    ],
                },
                {
                    "code": (
                        "pwd\n"
                        "echo \"$LAB_ID\"\n"
                        "mkdir -p ~/eng-practice\n"
                        "cd ~/eng-practice\n"
                        "printf 'line one\\n' > notes.txt\n"
                        "echo \"line two\" >> notes.txt\n"
                        "cat notes.txt\n"
                        "wc -l notes.txt\n"
                        "grep two notes.txt\n"
                        "cp notes.txt notes-copy.txt\n"
                        "ls -l\n"
                        "rm notes-copy.txt\n"
                        "ls"
                    ),
                    "label": 'Look around, then make and change a small file',
                    "screenshot": {"file": "ENG-0-shot-1b.png", "alt": "The commands from this block and what they print", "width": 5.2},
                    "intro": 'You will now make a practice folder and a small file, then read, copy and delete it.',
                    "expect": 'Example only. Your folder and lab name will differ.\n<your current folder>\n<your lab name>\nline one\nline two\n2 notes.txt\nline two\n(ls -l lists notes.txt and notes-copy.txt)\nnotes.txt',
                    "lines": [
                        ("pwd", "Prints your current directory, so you know where you are.", "Always know which directory you are in before you create or delete anything."),
                        ("echo \"$LAB_ID\"", "Prints a variable. The dollar sign means use the value of. LAB_ID names your lab.", "Confirms the lab set your variables, and shows how you read a variable without ever typing a secret."),
                        ("mkdir -p ~/eng-practice", "Makes a directory named eng-practice in your home directory (the tilde ~ means home). -p means no error if it already exists. Your home directory is kept on your computer, in the lab-workspace folder, so files you save there are still there the next time you open lab shell.", "Gives you a safe practice folder so nothing you do touches real files, and keeps your work between sessions."),
                        ("cd ~/eng-practice", "Moves into it.", "Commands act on the current directory, so you move there before making files."),
                        ("printf 'line one\\n' > notes.txt", "Writes the words line one into a new file. The > sends the output into the file and replaces what was there. The \\n ends the line.", "Shows how to create a file from the terminal, which every later module does with scripts and settings."),
                        ("echo \"line two\" >> notes.txt", "Adds a second line. The >> appends instead of replacing.", "Shows the difference between replacing and appending, a mix-up that can destroy an evidence file."),
                        ("cat notes.txt", "Prints the file.", "Reading a file back is how you check what a command really wrote."),
                        ("wc -l notes.txt", "Counts the lines in the file.", "Counting lets you check a result without reading all of it, for example how many findings a scan returned."),
                        ("grep two notes.txt", "Prints only the lines that contain the word two.", "Finding the one line you need in a long output is the most common reading skill in these modules."),
                        ("cp notes.txt notes-copy.txt", "Copies the file.", "Copying before you change a file keeps a way back."),
                        ("ls -l", "Lists both files with their sizes.", "Confirms both files exist and how big they are before you delete one."),
                        ("rm notes-copy.txt", "Deletes the copy. There is no recycle bin, so check the name before you press Enter.", "Practice deleting on a copy so you learn the care it needs on files that matter."),
                        ("ls", "Shows that only notes.txt is left.", "Check the result of every change; here, that only the original is left."),
                    ],
                },
                {
                    "code": (
                        "cd ~/eng-practice\n"
                        "cat > shopping.txt <<'EOF'\n"
                        "milk\n"
                        "bread\n"
                        "EOF\n"
                        "cat shopping.txt\n"
                        "wc -l shopping.txt"
                    ),
                    "label": 'Make a file with several lines',
                    "screenshot": {"file": "ENG-0-shot-1c.png", "alt": "The shopping.txt file made with a heredoc, then printed and counted", "width": 5.2},
                    "intro": 'You will now make a file by pasting its whole text in one go. Most later modules give you a file this way (the trick is called a heredoc), so learn it now. Paste the whole block at once into lab shell.',
                    "expect": 'Example only.\nmilk\nbread\n2 shopping.txt',
                    "lines": [
                        ("cd ~/eng-practice", "Moves into the practice folder.", "The new file is made in the folder you are standing in, so go there first."),
                        ("cat > shopping.txt <<'EOF'", "Starts a file called shopping.txt. Everything you type after this line, up to the line that says EOF, goes into the file. The quotes around EOF keep the text exactly as typed.", "This is how you make a file of any length with only a paste, so you do not need an editor."),
                        ("milk and bread", "The text of the file, one line each.", "Whatever sits between the first line and EOF is saved as it is, including spaces at the start of a line. YAML needs those spaces."),
                        ("EOF", "Ends the file. It must stand alone at the start of its own line.", "Without it the shell keeps waiting for more text. If that happens, type EOF on a new line and press Enter."),
                        ("cat shopping.txt", "Prints the file you just made.", "Read a file back to check it holds what you meant."),
                        ("wc -l shopping.txt", "Counts the lines: 2.", "A quick check that nothing was lost in the paste."),
                    ],
                },
            ],
            "security": "Never print a variable whose name contains PASSWORD or TOKEN. Printing one puts it on screen and in your terminal history.",
            "tip": "Typed something wrong? Press Up arrow, fix the line, press Enter. Press Tab while typing a long name to finish it.",
            "checkpoint": "cat shows two lines, wc says 2, the last ls lists only notes.txt, and shopping.txt holds milk and bread.",
        },
        {
            "title": "Clone, edit, commit and push with the in-lab git server",
            "learn": "Cloning, committing and pushing, then asking Gitea for its newest commit, shows how a change travels from your folder to the server and how to prove it arrived.",
            "takeaway": "A push is proven only when the server itself shows the change.",
            "why": "You will now copy the sandbox repository from Gitea (the lab's git server), change a file, send the change back, and then confirm on the server that it arrived. Git keeps a record of every change, which is why later modules store their scripts and settings in it.",
            "note": "The lab sets GITEA_URL, GITEA_USER and GITEA_TOKEN for you. A small helper gives the token to git only when git asks, so the token is never written into a file.",
            "blocks": [
                {
                    "code": (
                        "cd ~/eng-practice\n"
                        f"git -c '{CRED}' clone \"$GITEA_URL/$GITEA_USER/eng-sandbox.git\"\n"
                        "cd eng-sandbox\n"
                        f"git config credential.helper '!f() {{ echo username=$GITEA_USER; echo password=$GITEA_TOKEN; }}; f'\n"
                        "git config user.name \"$GITEA_USER\"\n"
                        "git config user.email \"$GITEA_USER@example.invalid\"\n"
                        "ls\n"
                        "git log --oneline"
                    ),
                    "label": 'Copy the sandbox repository from Gitea',
                    "intro": 'You will now copy the eng-sandbox repository from the lab git server (Gitea) into your practice folder and tell git who you are. The copy is a working copy, and every commit you make carries your name.',
                    "expect": "Example only. Your commit code will differ.\nCloning into 'eng-sandbox'...\nREADME.md  broken.yaml  health-check.sh\n<hash> <newest commit message>\n<hash> ... (a few older commit lines; the sandbox holds several commits, so your list will be longer than one line)",
                    "lines": [
                        ("git -c '...' clone URL", "Copies the repository eng-sandbox from Gitea into a new folder. The -c part gives git a helper for this one command that prints your Gitea user name and token when git asks for them.", "Later modules keep scripts and settings in git, so you start by getting a working copy from the lab's server."),
                        ("cd eng-sandbox", "Moves into the copy.", "git commands act on the repository you are standing in."),
                        ("git config credential.helper ...", "Saves the same helper in this repository so push works. The file stores the variable names, not the token value.", "Lets push sign in without you typing the token, so the token never lands in a file or on screen."),
                        ("git config user.name / user.email", "Tells git who you are, so each commit carries a name. The address is a placeholder that stays inside this repository.", "Every commit records who made it, and git refuses to commit without a name."),
                        ("ls", "Lists the files that came with the repository: README.md, broken.yaml and health-check.sh.", "See what came with the repository before you change anything."),
                        ("git log --oneline", "Lists the snapshots, newest first, one line each.", "The history is the record of who changed what and when, which is why git is used for scripts and evidence."),
                    ],
                },
                {
                    "code": (
                        "echo \"Checked by $GITEA_USER during ENG-0.\" >> README.md\n"
                        "git status\n"
                        "git diff\n"
                        "git add README.md\n"
                        "git commit -m \"Add a line to the README\"\n"
                        "git push origin main"
                    ),
                    "label": 'Change a file, save it and send it to Gitea',
                    "screenshot": {"file": "ENG-0-shot-2b-diff.png", "alt": "The diff with the new line marked +, then the commit", "width": 5.6},
                    "intro": 'You will now add a line to the README, look at the change, save it as a commit and push it. A commit is a saved snapshot with a message; a push sends it to Gitea so other people, and the automated checks in later modules, can see it. Work inside the eng-sandbox folder.',
                    "expect": 'Example only. Your commit code will differ.\nOn branch main\n(git status lists README.md as modified)\n(git diff shows your new line marked with a plus sign)\n[main <hash>] Add a line to the README\n 1 file changed, 1 insertion(+)\n(the push prints the remote address and ends with main -> main)',
                    "lines": [
                        ("echo ... >> README.md", "Adds one line to the end of the README.", "Make a small, harmless change to practice the save cycle."),
                        ("git status", "Shows README.md as modified: git sees a change it is not saving yet.", "Check what git sees before you save, so you do not commit a file by accident."),
                        ("git diff", "Shows the exact lines added, marked with a plus sign.", "Read the exact change before you save it, the habit that catches mistakes and stray secrets."),
                        ("git add README.md", "Marks the file to be saved in the next snapshot.", "Choose which changes go into the snapshot; nothing is saved without this."),
                        ("git commit -m ...", "Saves the snapshot with a short message after -m.", "The message is the record a reviewer reads later."),
                        ("git push origin main", "Sends the snapshot to the remote named origin (Gitea), on the branch named main.", "Gitea is where other people and the automated checks in later modules can see your change."),
                    ],
                },
                {
                    "code": (
                        "curl -s -H \"Authorization: token $GITEA_TOKEN\" \\\n"
                        "  \"$GITEA_URL/api/v1/repos/$GITEA_USER/eng-sandbox/commits?limit=1\" | jq -r '.[0].commit.message'\n"
                        "curl -s -H \"Authorization: token $GITEA_TOKEN\" \\\n"
                        "  \"$GITEA_URL/api/v1/repos/$GITEA_USER/eng-sandbox/raw/README.md?ref=main\" | tail -n 1"
                    ),
                    "label": 'Check from the server side that the push arrived',
                    "intro": 'You will now ask Gitea itself for its newest commit and for the last line of the README it now holds. Asking the server proves the push reached it, not only your own copy. A pass prints Add a line to the README, then Checked by and your user name.',
                    "expect": 'Example only. Your user name will differ.\nAdd a line to the README\nChecked by <your user> during ENG-0.',
                    "lines": [
                        ("curl -s -H ... /commits?limit=1", "Asks the Gitea API (the web addresses that programs use to talk to Gitea) for the newest commit. The header carries the token without printing it.", "Confirms from the server's side that your push arrived, instead of trusting your own screen."),
                        ("jq -r '.[0].commit.message'", "Picks the message of the first commit from the answer.", "Shows how to pull one field out of a long JSON reply, which most later checks do."),
                        ("curl ... /raw/README.md?ref=main | tail -n 1", "Asks Gitea for the README as it is on the main branch, then keeps only its last line.", "Shows the file as the server holds it, so you see your line without a web login."),
                    ],
                },
            ],
            "security": "Never put a password or token in a file you commit. Git keeps every version forever, so deleting it later does not remove it from the history.",
            "checkpoint": "The first curl prints Add a line to the README, and the second prints Checked by and your user name.",
        },
        {
            "title": "Ask the cluster questions with oc, and read YAML and an error",
            "learn": "Asking the cluster read-only questions and checking a broken YAML file with a dry run shows how to find a mistake before it reaches the cluster.",
            "takeaway": "Read the error, find the line, and dry-run a file before you apply it.",
            "why": "Most of these modules start by asking the cluster what is true and reading the answer. The oc commands here only read, so they change nothing. You then practice reading a YAML error and fixing it, using broken.yaml, the settings file that came with the repository.",
            "blocks": [
                {
                    "code": (
                        "oc whoami\n"
                        "oc projects\n"
                        "oc get pods -n demo\n"
                        "oc describe pod -n demo -l app=demo-app | head -n 20\n"
                        "oc logs -n demo -l app=demo-app --tail=5\n"
                        "pod=$(oc get pods -n kyverno -o name | head -n 1)\n"
                        "oc logs -n kyverno \"$pod\" --tail=3"
                    ),
                    "label": 'Ask the cluster who you are and what is running',
                    "intro": 'You will now run read-only oc commands that list projects and pods and show logs. Most later modules start by asking the cluster what is running, so this is the habit they rely on.',
                    "expect": 'Example only. Your names and ages will differ.\n<your user name>\n(a list of projects that includes demo)\nNAME  READY  STATUS  RESTARTS  AGE\ndemo-app-<hash>  1/1  Running  <n>  <age>\n(describe prints several sections; the Events are at the end)\n(the demo app is quiet, so its logs may print nothing)\n(the last three lines of a busy kyverno pod)',
                    "lines": [
                        ("oc whoami", "Prints who the cluster thinks you are.", "Before you ask the cluster anything, confirm who it thinks you are; a wrong login explains many surprises."),
                        ("oc projects", "Lists the projects (namespaces) you can see. Find demo in the list.", "Learn which namespaces you can see, which tells you what you are allowed to ask about."),
                        ("oc get pods -n demo", "Lists the pods in the namespace demo. -n means namespace. Read READY and STATUS.", "The fastest check that a workload is running: read READY and STATUS."),
                        ("oc describe pod ... -l app=demo-app", "Explains the pod picked by the label app=demo-app. A label is a tag on an object. head -n 20 keeps the first twenty lines.", "When something is not as expected, the Events at the end often say why."),
                        ("oc logs ... --tail=5", "Prints the last five lines the program wrote. The demo pod is quiet, so an empty answer is correct.", "Shows what a program wrote; an empty answer tells you the program is quiet, not broken."),
                        ("pod=$(oc get pods -n kyverno ...)", "Stores the name of the first pod in kyverno in a variable. The dollar and parentheses run a command and keep its output.", "Saves a pod name so the next command can use it without you copying a long name."),
                        ("oc logs -n kyverno \"$pod\" --tail=3", "Prints the last three lines of that pod. This one is busy, so you see text.", "Compare with the quiet demo pod: a busy pod shows text, so you learn what normal looks like for each."),
                    ],
                },
                {
                    "code": (
                        "cd ~/eng-practice/eng-sandbox\n"
                        "cat -n broken.yaml\n"
                        "oc apply --dry-run=client -f broken.yaml"
                    ),
                    "label": 'Read the broken settings file and let oc find the error',
                    "screenshot": {"file": "ENG-0-shot-3b.png", "alt": "The numbered file and the error that names line 5", "width": 6.3},
                    "intro": 'You will now print a settings file with line numbers and ask oc to check it without applying it. A dry run vets a file before it can touch the cluster, whoever wrote it. Work inside the eng-sandbox folder.',
                    "expect": 'Example only. The wording comes from oc.\n(the file is printed with a line number on each line)\nerror: error parsing broken.yaml: ... line <n>: ...',
                    "lines": [
                        ("cat -n broken.yaml", "Prints the settings file with line numbers. Look at the indent of each line: one line starts one space in, where the lines around it start at zero or two.", "Line numbers let you match the file to the error message that comes next."),
                        ("oc apply --dry-run=client -f broken.yaml", "Asks oc to read the file and check it without sending it anywhere. A dry run changes nothing. The error names a line number, which can be the line just above the real mistake.", "A free way to find a mistake in a settings file before it can affect the cluster; the error names the line."),
                    ],
                },
                {
                    "code": (
                        "sed -i 's/^ data:/data:/' broken.yaml\n"
                        "git diff\n"
                        "oc apply --dry-run=server -f broken.yaml\n"
                        "git restore broken.yaml"
                    ),
                    "label": 'Fix the indentation, check it with the cluster, then undo',
                    "screenshot": {"file": "ENG-0-shot-3c.png", "alt": "The fix, the one-line diff and the cluster check ending in server dry run", "width": 6.3},
                    "intro": 'You will now fix the one-space mistake, ask the cluster to check the file without applying it, and restore the original. The server dry run is stricter than the client dry run in 3b. Stay in the same folder.',
                    "expect": 'Example only. (sed prints nothing)\n(git diff shows the one line changed)\nconfigmap/eng-sandbox-note created (server dry run)\n(git restore prints nothing)',
                    "lines": [
                        ("sed -i 's/^ data:/data:/' broken.yaml", "Edits the file in place: a line that starts with one space and then data: loses the space.", "Fixes the one indentation mistake the error pointed at."),
                        ("git diff", "Shows the one line you changed.", "Confirms you changed only that line and nothing else."),
                        ("oc apply --dry-run=server -f broken.yaml", "Asks the cluster itself to check the file and say what it would do, without doing it.", "The cluster checks the fixed file against its own rules, which catches problems the local check cannot. For example, a namespace that does not exist passes the local check but fails here."),
                        ("git restore broken.yaml", "Puts the broken file back, so the repository stays as it was and you can practice again.", "Resets the file so you can repeat the exercise, and shows how git undoes a change."),
                    ],
                },
            ],
            "note": "A dry-run answer ends with (dry run) or (server dry run), as in created (server dry run). Nothing was created. If you run oc apply without a dry run, the cluster does change.",
            "checkpoint": "The first dry run fails with a line number at or just above the one-space line (line 6 of the file); the second says configmap/eng-sandbox-note created (server dry run).",
        },
        {
            "title": "Read and run the platform health check",
            "learn": "Reading health-check.sh and then running it shows how one script turns many cluster questions into one UP or DOWN line per tool and an exit code.",
            "takeaway": "A script's exit code tells other programs whether the check passed.",
            "why": "The engineering modules build on tools that must already be running: Loki, Grafana, Mattermost, Gitea, Tekton pipelines, Kyverno, the Trivy operator, Falco and the log collector. The repository you cloned holds one script that checks every tool in that list and prints one line each. Read the script line by line before you run it, then run it.",
            "blocks": [
                {
                    "code": (
                        "cd ~/eng-practice/eng-sandbox\n"
                        "cat -n health-check.sh"
                    ),
                    "label": 'Print the health check script to read it',
                    "intro": 'You will now print the health check script with line numbers so you can read it before you run it. Work inside the eng-sandbox folder.',
                    "expect": 'Example only. The script text is printed with a number on each line. The table below explains the parts that matter.\n(the numbered lines of the shell script)',
                    "lines": [
                        ("lines 3 and 4: set -u, down=0", "set -u stops the script if it uses a variable that was never set. down counts the tools that are not healthy.", "Sets up the counter that decides whether the whole check passes."),
                        ("lines 6 to 9: report()", "A function (a named group of commands) that prints one line: UP or DOWN, the tool, its namespace, and a short detail. Any state other than UP adds one to down.", "One place formats every result, so all the lines look the same and are easy to scan."),
                        ("lines 11 to 15: check() and its oc and jq lines", "Takes a name, a namespace and part of a pod name. It asks oc for the pods in that namespace as JSON. Then jq keeps the pods whose name matches and skips pods that finished a one-time job. It prints two numbers: how many pods, and how many of them are not Running or have a container that is not ready.", "The core of the script: ask the cluster for a tool's pods and count them."),
                        ("lines 16 to 19: the first if", "If oc printed nothing, the namespace could not be read, so the tool is reported DOWN and the function stops with return.", "A tool whose namespace cannot be read must be reported down, not skipped."),
                        ("lines 20 to 27: read and the second if", "The read line splits the two numbers into two variables, the pod count and the not-ready count. The if branches then decide. No pods at all is DOWN. Any pod not ready is DOWN. Otherwise the tool is UP.", "A tool is up only if it has pods and none of them is not ready."),
                        ("lines 30 to 39: the check lines", "One line per tool, with the namespace and the part of the pod name to match. A dot matches every pod in the namespace. A tool with several pods is UP only when all of them are ready.", "One line per platform tool; adding a tool to the check means adding a line."),
                        ("lines 41 to 46: the final if", "Prints a summary. The exit 1 gives the script a non-zero exit code when anything is down, so another program can tell.", "The exit code lets other scripts and pipelines use this check to stop on a failure."),
                    ],
                },
                {
                    "code": (
                        "bash health-check.sh\n"
                        "echo \"exit code: $?\"\n"
                        "git log --oneline -n 2\n"
                        "git status --short"
                    ),
                    "label": 'Run the health check and confirm your work',
                    "intro": 'You will now run the script you just read, print its exit code, and check that your commit is the newest and nothing is left unsaved. Stay in the same folder.',
                    "expect": 'Example only. Your pod counts and commit codes will differ.\nUP    <tool>  <namespace>  <n> pods ready\n(ten lines like this: nine platform tools and the sample app)\nAll tools up.\nexit code: 0\na1b2c3d Add a line to the README\n9f8e7d6 Add the platform health check\n(git status prints nothing)',
                    "lines": [
                        ("bash health-check.sh", "Runs the script with bash. It only reads from the cluster.", "Runs the whole check in one command and gives you one line per tool."),
                        ("echo \"exit code: $?\"", "Prints the exit code of the script. The question mark variable holds the exit code of the last command.", "Shows how a script tells other programs whether it passed: 0 for yes, anything else for no."),
                        ("git log --oneline -n 2", "Shows the two newest snapshots.", "Your commit is the top line, and the health check commit is below it."),
                        ("git status --short", "Lists files with unsaved changes. Nothing is printed when everything is saved.", "An empty answer means you left no loose change behind."),
                    ],
                },
            ],
            "note": "The script matches pods by namespace and part of the pod name. If a tool shows DOWN, run oc get pods -n NAMESPACE for that line and read the STATUS column before you decide anything. If every pod there looks healthy, the check may be matching the wrong name: say so to the lab team.",
            "checkpoint": "Ten lines are printed, one for each of nine platform tools and one for the sample app, then All tools up. and exit code 0. Your commit is on top of the log, and git status prints nothing.",
        },
    ],
    "verify": [],
    "waivers": {
        "verify": "ENG-0 has no separate Verify section: the health check and the git checks run once, in Step 4b, and the negative case is Step 3b (a broken file that oc rejects). Decided with the module owner 2026-11-03.",
        "your_turn": "The YOUR TURN lines were removed on reviewer feedback; the optional command list at the end replaces them.",
    },
    "glossary": [
        ("Cluster", "A group of servers that work together as one platform."),
        ("Variable", "A named value. The dollar sign in front of the name means use the value of."),
        ("Clone", "Copy a repository from a server to your folder."),
        ("Push", "Send your saved commits to the remote repository."),
        ("Label", "A key=value tag on a cluster object, used to pick objects, such as app=demo-app."),
        ("Dry run", "A check that reads and validates a file without making any change."),
        ("Deployment", "A cluster object that keeps a set number of copies of a program running."),
        ("Function (shell)", "A named group of commands in a script that you can call by name."),
        ("JSON", "A text format for data, made of names and values in braces. oc and jq can both read it."),
    ],
    "design": [
        {
            "decision": "Token reaches git through a credential helper",
            "how": "Git gets the Gitea user name and token from a one-line credential helper that reads GITEA_USER and GITEA_TOKEN from the variables the lab sets. The helper is passed once with the clone command and then saved in the repository settings as variable names, not values.",
            "why": "The token value is never typed or written to a file, so a commit or a copied folder cannot leak it, and the lab sets the variables for every learner.",
            "alternatives": "Advantage of putting the token in the clone address or in a stored credentials file: it is the simplest thing to type and needs no helper. Drawback: the token then lands in shell history or on disk, and git keeps it in the repository settings.",
        },
    ],
    "next": "Next module: ENG-1, the second foundation module. After it you can start at level 2 in any dimension: GRC, vulnerability management, security data and incident response, cloud and platform security, AI development, or architecture and design. Each one starts with its own lab start command.",
}


def _command_list(module: dict) -> list[dict]:
    groups = [{"heading": "Start: on your computer", "code": "lab up\nlab start eng-0"}]
    for n, step in enumerate(module["steps"], start=1):
        groups.append({"heading": f"Step {n}. {step['title']}", "code": "\n\n".join(b["code"] for b in step["blocks"])})
    groups.append({"heading": "When you stop: on your computer, not in lab shell", "code": "lab down"})
    return groups


MODULE["portability"] = {
    "bullets": [
        'Linux commands, git and curl port as is. The Gitea steps work against any git server that accepts a user name and a token.',
        'The oc steps work on any OpenShift 4.x cluster. On other Kubernetes platforms, oc becomes kubectl.',
        'Change these lab values first: the variables GITEA_URL, GITEA_USER and GITEA_TOKEN, the namespace demo, and the namespaces named in health-check.sh.',
        'lab shell and the lab command only exist in the lab. Elsewhere, open a terminal that has git, curl, jq and a kubeconfig (the file that holds your cluster address and sign-in).',
    ],
    "headers": ["Check", "In this lab (OpenShift)", "On other platforms", "What you change"],
    "rows": [
        ('Shell', 'lab shell, with LAB_ID and the Gitea variables set for you', 'Any terminal with the same tools', 'Set the variables yourself, or use your own git host.'),
        ('Git clone, commit, push', 'Gitea at GITEA_URL, token through a credential helper', 'Any git host that accepts a token', 'The address and the token variables.'),
        ('Server-side check', 'curl to the Gitea API under /api/v1/repos', "The host's own API, or git log on a fresh clone", 'Replace the check.'),
        ('Cluster questions', 'oc whoami, oc projects, oc get pods -n demo', 'kubectl get namespaces, kubectl get pods -n your-namespace', 'The tool name and the namespace.'),
        ('YAML check', 'oc apply --dry-run=client and --dry-run=server', 'kubectl apply --dry-run=client and --dry-run=server', 'The tool name.'),
        ('health-check.sh', "Reads pods in the lab's tool namespaces", 'The same script, with your namespaces', 'The namespace and pod name patterns.'),
    ],
}

MODULE["command_list_intro"] = (
    "You do not need this section. The Command List lists every command from the steps above, in order and with no explanation, "
    "for repeating the module or finding a command fast. The commands for Step 1 onward run in lab shell; "
    "the first command of Step 1 opens it."
)
MODULE["command_list"] = _command_list(MODULE)
