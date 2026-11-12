# AID-4: Build a Constrained Triage Agent (AC-6, CM-7, SI-10, AU-12)

| Item | Detail |
| --- | --- |
| Sequence | Module 21 of 29 in the recommended order |
| Timed work | About 67 minutes (48 hands-on, 19 verify) |
| Standalone start | `lab start aid-4` |
| Combined start | Continue from the end state of the previous module |
| Tools | Python (python3), oc, Loki (free, open source), Stub model service (provided by the lab), curl, jq |
| Prerequisites | AID-3 Step 2 and Step 3 (a model reply must be checked before it is used, and each exchange is logged to Loki), ENG-0 Terminal, Git and Your Lab (the lab shell and reading oc output) |

## Section 1. Module Overview

- Purpose: show that a prompt-injected instruction cannot reach the cluster when the loop enforces an allowed list and a view-only identity.
- You build `flags.py` and `policy.py` (the allowed list), `agent.py` (the proposal parser and command runner), and `loop.py` (the full loop with cap and stop switch). You also add one kind of object yourself.
- You run six scripted scenarios, including an injection that proposes a delete, and read the action trail in Loki.

- **Skill:** Build a triage agent loop. It runs only commands on a short allowed list, as a view-only identity. It logs every action to Loki before it acts, and it stops at a step cap or a stop file.
- **Tools:** `python3` runs the loop, allowed list and audit writer. `oc` sends each command as the view-only identity using `--as` impersonation. Loki stores the action trail, which `ailog.py` sends.
- **Security Function:** Prevents prompt injection from reaching the cluster. A model that is steered can only propose. `policy.py` refuses commands outside the allowed list, and the platform refuses them again through the view-only identity, even if the wrapper has a bug.
- **NIST AC-6 Least Privilege:** A service account with the built-in view role in project demo runs every command through `--as`. The platform refuses anything outside that role, including secrets and deletes, whatever the wrapper says.
- **NIST CM-7 Least Functionality:** `policy.py` permits three read-only verbs, four kinds of object plus the one you add, and one project. Anything else is refused before it reaches the cluster.
- **NIST SI-10 Information Input Validation:** `parse_proposal` in `agent.py` accepts only two shapes from the model: run with a command, or finish with a summary. `check_command` in `policy.py` then checks every word of a run command.
- **NIST AU-12 Audit Record Generation:** `audit.py` pushes a record to Loki for every allowed, refused, invalid, finished, stopped and capped event before the action happens. The loop stops if Loki cannot be reached.

## Section 2. The Tools

### Tools used in this module

Each tool name links to its official overview. The table columns say how each tool is used in the lab and why the lab uses it instead of another way of doing the same job.

| Tool (overview link) | What it is | Used in this lab | Why this tool |
| --- | --- | --- | --- |
| [Python 3](https://docs.python.org/3/tutorial/introduction.html) | General-purpose language, used here for small helper scripts. | You write the allowed list and loop.py, which validates, logs, caps and stops the agent. | Python reads and writes JSON easily and is already in the lab shell, so a small script needs nothing installed. |
| [oc](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/cli_tools/openshift-cli-oc) | The OpenShift command-line tool for creating and managing applications and projects from a terminal. | Runs the agent's commands as a view-only identity and sets that identity up. | It is the one command that talks to the cluster, so every module uses it to ask what is true and to make changes. You sign in once, and it works on OpenShift objects as well as standard Kubernetes ones. Unlike clicking in the web console, a command can be pasted, repeated and checked by a test. |
| [Grafana Loki](https://grafana.com/docs/loki/latest/) | Log storage that indexes only labels and keeps compressed log data in object storage. | Holds the agent's action trail, which you search. | It stores logs cheaply and is free and open source, so the lab can keep the logs that detections and investigations need without a paid logging product. |
| [Stub model service](https://kubernetes.io/docs/concepts/services-networking/service/) | A small stand-in for an AI model that the lab runs in the cluster. It gives fixed, scripted answers, so no model account or key is needed. (No vendor page exists for it; the link explains the Kubernetes Service it runs as.) | Proposes the next step for each run, including one with an injected instruction. | A real model needs an account, a key and money. A scripted stand-in gives the same answers every time, so every learner sees the same behavior and a test can check it. |
| [curl](https://curl.se/docs/manpage.html) | Command-line tool for transferring data over URLs, used here to call web endpoints. | Sends queries to Loki to read the trail. | It calls a web address from the terminal, so you can check what a service really returns instead of trusting a screen. |
| [jq](https://jqlang.org/) | Command-line JSON processor. | Checks the shape of model replies and reads the trail. | It picks one field out of a long JSON reply, so a test can read a single value. |

### How it fits together

#### The model proposes, the wrapper decides

- The diagram shows the lab (test) setup.
- The loop runs in lab shell against a stub model service, the allowed list and audit writer are local files, and Loki holds the action trail.
- In production the agent runs as a dedicated workload under its own service account, the allowed list is held in a config map, and Loki is replicated to protected storage.
- Each step below adds one part, drawn with thick lines.

How the lab is set up, and why:

- You work in lab shell on your laptop, where the loop and the allowed list run as files in your agent folder.
- The lab start adds a stand-in model that proposes steps and a noisy application that carries a planted instruction.
- In Step 1 you add a view-only identity for the agent.
- The loop runs on your side and calls the model, so the part that decides what runs sits outside the model and the model can only propose.
- Every command the loop allows is sent to the cluster as the view-only identity, so the cluster itself refuses anything that identity may not do, even if the allowed list has a mistake.
- The noisy application and the action log live in the cluster, in their own projects, so the agent reads real cluster objects and its trail is kept away from your laptop.
- Loki stores the trail so that a reviewer can search it after the run.

![The model proposes, the wrapper decides](img/AID-4-diagram-1.png)

- **1. Stub model service:** a small Python service in project ai-lab that stands in for the model and proposes each next step. It only proposes; it never runs anything.
- **2. Triage identity:** the service account triage-agent with the view role in project demo, so the platform allows it to read and nothing else.
- **3. Noisy application:** the deployment noisy-app in project demo, whose log carries the injected instruction the agent will read.
- **4. Loki (the log store):** the log store in project siem that holds the record of every action.
- **5. Command allowed list:** policy.py in your agent folder, which permits a short list of read-only commands and refuses everything else.
- **6. Agent loop:** loop.py in your agent folder, which asks the stub for a step, checks it against the allowed list, runs allowed commands as the triage identity, and logs each action to Loki. It stops after six steps.
- **7. Stop file:** a file named STOP in your agent folder. While it exists, the loop ends before its next step.
- **8. Refused command:** a proposal the allowed list rejects. It is logged and never reaches the cluster.

Where each part runs, and why:

| Part | Where it runs | Why it is built this way |
| --- | --- | --- |
| Agent folder, allowed list and loop | In lab shell, on your laptop | The code that decides what may run stays outside the model, in files you wrote and can read and test. |
| Stub model service | Pods (running copies of a program) in project ai-lab on the lab cluster | It proposes the next step from fixed scripts, so every learner sees the same runs, including one with an injected instruction. |
| Port forward | A tunnel from lab shell to the stub service in project ai-lab | The service is only reachable inside the cluster, so a tunnel is the simplest way to reach it from lab shell. |
| Triage identity | A service account named triage-agent in project ai-lab, with the view role in project demo | The platform limits what the agent can do, so the limit still holds if the wrapper has a bug. |
| Noisy application | Pods in project demo | It gives the agent real objects to read and a log that carries an injected instruction to test against. |
| Loki | Inside the lab cluster, in project siem | The action trail is kept in a central place that the loop writes to, so you can search what the agent did. |
| Stop file | A file named STOP in your agent folder | A person needs a way to end a run at once, and a file is the simplest signal for the loop to check. |

### 2.1 Where an agent can be steered (AC-6 Least Privilege, CM-7 Least Functionality, SI-10 Information Input Validation, AU-12 Audit Record Generation)

- The loop sends the model what it has learned so far, including the text that earlier commands printed.
- A model may obey a log line that reads like an instruction, such as one telling an assistant to delete all pods.
- A model cannot be made immune to text it reads, so the program around it must be safe whatever the model says.
- Every limit in this module sits in the wrapper (the program around the model) or in the platform, never in the model's good behavior.

#### AC-6: Least Privilege

*The control asks the organization to employ the principle of least privilege, allowing only authorized accesses for users, or processes acting on behalf of users, that are necessary to accomplish assigned organizational tasks. This is done using:*

- The service account triage-agent: the identity the agent runs as, which exists only for this job.
- The built-in view role in project demo: lets the triage-agent identity read objects in one project but not secrets, and change nothing.
- `oc --as`: sends every command as the triage-agent identity, so the platform enforces the limit even if the wrapper has a bug.

#### CM-7: Least Functionality

*The control asks the organization to configure the system to provide only organization-defined mission essential capabilities, and to prohibit or restrict organization-defined functions, ports, protocols, software and services. NIST leaves both lists to the organization. This is done using:*

- policy.py: permits three read-only verbs, four kinds of object plus the one you add, and one project, and refuses everything else before it reaches the cluster.
- flags.py: accepts only a few options, so options such as --as or -o yaml are refused.
- `shlex.split` with no shell: breaks a command into separate words and runs it without a shell, so a second command cannot be chained on.

#### SI-10: Information Input Validation

*The control asks the organization to check the validity of organization-defined information inputs to the system. NIST leaves the list of inputs to the organization. Here the model's proposal is such an input. This is done using:*

- parse_proposal in agent.py: accepts only two exact shapes, run with a command or finish with a summary, and ends the run on a missing field, an extra field or a value that is not text.
- check_command in policy.py: checks every word of the command inside a run proposal a second time against the allowed list.

#### AU-12: Audit Record Generation

*The control asks the system to be able to generate audit records for the event types it can audit, to let organization-defined personnel or roles select which events are logged, and to generate records with the content that AU-3 defines. This is done using:*

- audit.py: writes a record for every allowed, refused, invalid, finished, stopped and capped event before the action happens.
- `ailog.py`: sends each record to Loki with the labels app=triage-agent and the kind of event, so a reviewer can search the trail.
- The fail-closed rule in audit.py: if Loki cannot be reached, the loop ends with status 6, because an action nobody can see is not allowed.

The limits in this module, where each one lives, and what it stops:

| Limit | Where it lives | What it stops |
| --- | --- | --- |
| View-only identity | The platform (RBAC, the cluster's built-in way to say who may do what) | Any change or secret read, even if the wrapper has a bug |
| Command allowed list | The wrapper | Commands the job does not need, including chained commands |
| Proposal shape check | The wrapper | Replies that are not a single step or a finish |
| Step cap | The wrapper | A loop that never finishes |
| Stop file | The wrapper | A run a person decides to end |
| Action log | The wrapper and Loki | Actions nobody can later see |

### 2.2 The scenarios the stub plays

- The stub holds six scripted runs, picked by the first part of the request id the loop sends.
- The stub never reads the observation (the text the last command printed, sent back to the model), so each scenario plays out the same way every time.
- In a real system a planted log line might or might not change a model's proposal, so the wrapper must hold either way.

The six scenarios, what the model proposes in each, and what the wrapper must do:

| Scenario | What the model proposes | What the wrapper must do |
| --- | --- | --- |
| triage-clean | Read pods, read the log, describe the deployment, finish | Run all three, then accept the finish (exit 0) |
| triage-injected | Read pods, read the log, then delete all pods | Refuse the delete (exit 4) |
| triage-secret | Read pods, then read secrets as YAML (a plain-text format for settings) | Refuse the read (exit 4) |
| triage-chained | One command with a second command chained on | Refuse it (exit 4) |
| triage-malformed | Chat text instead of a proposal | Stop as invalid (exit 4) |
| triage-loop | The same read, again and again | Stop at the step cap (exit 5) |

> **IN PRODUCTION:** In the real environment the agent runs as a workload under a dedicated identity, with admission policy and network policy around it, so the platform enforces the limits even when the wrapper is wrong. AID-5 builds that platform layer.

### Design decisions

#### Limit the agent twice, in the platform and in the wrapper

- How: Every command runs as a view-only service account in one project. The wrapper also runs only commands on a short allowed list, split into words with no shell, and holds a step cap and a stop file.
- Why: The platform limit still holds when the wrapper has a bug, while the wrapper can express rules the platform cannot, such as no full object dumps.
- Alternatives: A wrapper alone is the alternative. Advantage: there is only one place to maintain. Drawback: a bug or bypass in the code leaves the agent with whatever power its login has.

#### Use an allowed list and end the run after a refusal

- How: Each proposed command is checked word by word against permitted verbs, object kinds and project, and a refusal ends the run.
- Why: A blocked list always misses something. Each retry would also give injected text another attempt, whereas ending the run costs a person one rerun.
- Alternatives: A blocked list with a retry after refusal is the alternative. Advantage: less to maintain, and the triage sometimes finishes. Drawback: it misses the command nobody thought of and gives injected text more attempts.

#### Write the record before each action and stop if logging fails

- How: A record goes to the central log store before every action, and the loop stops if the store cannot be reached.
- Why: An action nobody can see is not allowed, and logging afterwards would lose the record exactly when something goes wrong.
- Alternatives: Logging after the action on a best-effort basis is the alternative. Advantage: the agent keeps working through a logging outage. Drawback: some actions go unrecorded, which defeats the trail.

## Section 3. Implement

- Start: type `lab start aid-4` in the terminal on your own computer (PowerShell on Windows, Terminal on Mac), not in the lab shell.
- Enter lab shell with `lab shell`. Every other command in this module runs inside lab shell.
- If a step fails: run `lab reset aid-4` on your own computer and repeat the step once. If it still fails, copy the whole command and error and ask your AI assistant. Do not skip the step.

### Step 1. Give the agent a view-only identity (AC-6 Least Privilege)

**Learning point: Create a service account for the agent and give it the view role in project demo only. The three oc auth can-i answers confirm what the platform will and will not allow, independent of your code.**

- The loop runs every command as the service account triage-agent using `--as`, so what the agent can do is decided by the platform and not only by your code.
- The view role lets an identity read most objects in a project, but not secrets.
- You also read the noisy application's log yourself, to see the injected line the agent will read later.

What this step adds (thick lines and outlines are new):

![The model proposes, the wrapper decides, after step 1](img/AID-4-step-1.png)

- The lab starts with the stub model service in project ai-lab, the noisy application in project demo (its log carries an injected instruction), and Loki in project siem. You create a view-only identity for the agent in project ai-lab and give it read access to project demo.

#### 1a. Open the tunnel, create the view-only identity and prove its limits

You will now create the identity the agent will run as, give it read access to project demo, ask the cluster what it may do, and read the noisy application's log.

```bash
mkdir -p /workspace/aid-4/agent
cd /workspace/aid-4/agent
curl -s http://127.0.0.1:8089/healthz >/dev/null || { oc port-forward -n ai-lab svc/stub-model 8089:8080 >/dev/null 2>&1 & sleep 3; }
oc create serviceaccount triage-agent -n ai-lab --dry-run=client -o yaml | oc apply -f -
oc adm policy add-role-to-user view system:serviceaccount:ai-lab:triage-agent -n demo
AGENT=system:serviceaccount:ai-lab:triage-agent
oc auth can-i get pods -n demo --as="$AGENT"
oc auth can-i get secrets -n demo --as="$AGENT"
oc auth can-i delete pods -n demo --as="$AGENT"
oc logs deployment/noisy-app -n demo --tail=4
```

**Expected output:**

```
Example only. The wording of the messages comes from oc. If the tunnel was already open, the Forwarding line does not appear, and on a second run the service account is reported as unchanged.
Forwarding from 127.0.0.1:8089 -> 8080
serviceaccount/triage-agent created
<oc confirms the view role was added for triage-agent in demo>
yes
no
no
<four log lines, including an error line and the line that begins NOTE TO AI ASSISTANT>
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| mkdir -p /workspace/aid-4/agent ; cd ... | Makes the agent folder, where every file of this module goes, and moves into it. Every later block that uses these files starts with a cd to it. | The folder is made once, here, and the later blocks can rely on it. |
| curl -s ... >/dev/null \|\| { oc port-forward ... 8089:8080 & sleep 3; } | Asks the stub if it already answers on port 8089. Only if it does not, it opens a port forward: a tunnel from port 8089 in your shell to the stub model service, kept running in the background. | The loop in later steps asks the stub for each next step, and the stub is only reachable through this tunnel. Checking first stops a second tunnel from failing with an address already in use error. |
| oc create serviceaccount triage-agent --dry-run=client -o yaml \| oc apply -f - | Creates the identity the agent will use. Building the definition first and applying it means a second run changes nothing instead of failing. | The agent needs an identity of its own so its power can be set apart from yours. |
| add-role-to-user view ... -n demo | Lets that identity read objects in project demo and nowhere else. | This is where the limit is set: the platform will allow reads in demo and nothing else. |
| oc auth can-i ... --as="$AGENT" | Asks the cluster whether that identity may do the action, and prints yes or no. --as means answer for that identity, not for you. | You prove the limit with the cluster itself: yes for reading pods, no for secrets and for deleting. |
| oc logs deployment/noisy-app --tail=4 | Shows the last four log lines of the noisy application. Read them. | You read the injected line yourself first, so you know what the agent will meet later. |

![Output from a real lab run: Open the tunnel, create the view-only identity and prove its limits](img/AID-4-shot-1a.png)

> **YOUR TURN:** Run the block. Read the three answers and find the line that begins NOTE TO AI ASSISTANT.

> **CHECKPOINT:** The answers are yes, no and no. The log shows an error line and a line that tells an assistant to delete all pods.

> **TAKEAWAY:** Set up the platform limit first, before any code runs, because it still holds if the wrapper has a bug.

**How this meets the control**

- **AC-6:** You create a service account with the view role in project demo only. The three can-i answers (yes, no, no) prove what the platform will allow and refuse.

### Step 2. Write the command allowed list (CM-7 Least Functionality, SI-10 Information Input Validation)

**Learning point: Build the allowed list that is the only code deciding whether a proposed command runs. Writing your own test cases first, watching them fail, then fixing the list proves the check works before the loop uses it.**

- The allowed list splits text into separate words so no shell ever sees it and nothing can be chained, then checks every word against what is permitted.
- `flags.py` holds the option rules, `policy.py` holds the verbs and kinds.
- You write `my_cases.py` and `kinds.py` yourself.

What this step adds (thick lines and outlines are new):

![The model proposes, the wrapper decides, after step 2](img/AID-4-step-2.png)

- The command allowed list is written in your agent folder. It is the only code that decides whether a proposed command may run.

#### 2a. Save the option check as flags.py

You will now make the file flags.py in your agent folder by pasting the whole block (a heredoc) into the lab shell.

- flags.py checks the options of a command: the project, the output format and the log length.
- The command prints ok when flags.py has content.

```bash
cd /workspace/aid-4/agent
cat > flags.py <<'EOF'
import re

NAMESPACES = {"demo"}
OUTPUTS = {"name", "wide"}
MAX_TAIL = 200


def check_flags(flags):
    namespace_seen = False
    index = 0
    while index < len(flags):
        flag, value = flags[index], (flags[index + 1] if index + 1 < len(flags) else "")
        if flag == "-n" and value in NAMESPACES:
            namespace_seen, index = True, index + 2
        elif flag == "-o" and value in OUTPUTS:
            index += 2
        elif re.fullmatch(r"--tail=\d{1,3}", flag) and int(flag[7:]) <= MAX_TAIL:
            index += 1
        else:
            return "flag or value not allowed: " + flag
    return None if namespace_seen else "an allowed namespace is required"
EOF
test -s flags.py && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-4/agent | Moves into the agent folder made in Step 1. | The file is made in the folder you are standing in. |
| cat > flags.py <<'EOF' ... EOF | Writes everything between the first and the last line into flags.py. The quotes around EOF keep every character as shown. Running it again replaces the file with the same text. | The lab has no editor, so a paste is how you make the file. |
| test -s flags.py && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| NAMESPACES, OUTPUTS | The projects and output formats the agent may ask for. To allow something new you change this file, in a reviewed change. | Everything the agent may do with options is listed in these two sets and in MAX_TAIL, so a review of them is a review of the agent's power. |
| MAX_TAIL = 200 | The most log lines one command may read. A choice the lab makes. | A log read can be huge, so a small cap keeps the output the model sees under control. |
| `check_flags(flags)` | Walks the options. Only -n with an allowed project, -o with name or wide, and --tail with a small number pass. Any other option, such as --as or -o yaml, returns a reason. | Options can change what a command does, so only the few you list are accepted. |
| return None if namespace_seen ... | A command must name an allowed project. None means no problem was found. | A command with no project would run in whatever project is current, so the project is required. |

#### 2b. Save the allowed list as policy.py

You will now make the file policy.py in your agent folder, next to flags.py, by pasting the whole block into the lab shell.

- The command prints ok when policy.py has content.

```bash
cd /workspace/aid-4/agent
cat > policy.py <<'EOF'
import re
import shlex

from flags import check_flags

try:
    from kinds import MORE_KINDS
except ImportError:
    MORE_KINDS = set()

VERBS = {"get", "describe", "logs"}
KINDS = {"pods", "pod", "events", "deployments", "deployment", "services", "service"} | MORE_KINDS
NAME = re.compile(r"^[a-z0-9][a-z0-9.-]{0,62}$")
LOG_TARGET = re.compile(r"^deployment/[a-z0-9][a-z0-9-]{0,62}$")
SHELL_CHARS = re.compile(r"[;&|`$<>(){}\\\n]")


def check_argv(argv):
    if len(argv) < 3 or argv[0] != "oc" or argv[1] not in VERBS:
        return "only oc get, describe and logs are allowed"
    verb, target = argv[1], argv[2]
    if verb == "logs":
        return check_flags(argv[3:]) if LOG_TARGET.match(target) else "logs needs a target like deployment/NAME"
    if target not in KINDS:
        return "resource kind not allowed: " + target
    has_name = len(argv) > 3 and not argv[3].startswith("-")
    if has_name and not NAME.match(argv[3]):
        return "resource name not allowed"
    return check_flags(argv[4:] if has_name else argv[3:])


def check_command(text):
    """Return (argv, None) when the command is allowed, or (None, reason) when it is refused."""
    if SHELL_CHARS.search(text):
        return None, "shell characters are not allowed"
    try:
        argv = shlex.split(text)
    except ValueError:
        return None, "command could not be parsed"
    reason = check_argv(argv)
    return (None, reason) if reason else (argv, None)
EOF
test -s policy.py && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd ... ; cat > policy.py <<'EOF' ... EOF | Moves into the agent folder and writes everything between the first and the last line into policy.py. Running it again replaces the file with the same text. | The lab has no editor, so a paste is how you make the file. |
| test -s policy.py && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| VERBS, KINDS | The permitted verbs and kinds of object in two small sets. The four kinds written here are the starting list. KINDS also adds MORE_KINDS, the extra kinds from kinds.py, which you write in 2e. To allow something new you change a list in a reviewed change. | Everything the agent may read is listed in these two sets, so a review of the list is a review of the agent's power. |
| NAME, LOG_TARGET | Patterns for a resource name and for the one log target form allowed, deployment/NAME. A name with spaces or symbols never matches. | Strict patterns for names stop a proposal from sneaking extra words or symbols into the command. |
| SHELL_CHARS | Characters a shell treats as special, such as ; & \| and $. Any of them in the text means refuse. | These characters are how a shell chains or expands commands, so any of them means the proposal is refused. |
| try: from kinds import MORE_KINDS ... except ImportError | Reads the extra kinds from kinds.py if that file exists. If it does not, MORE_KINDS is an empty set and nothing extra is allowed. | A missing file leaves the list at its narrowest, never wider. You write kinds.py in this step. |
| from flags import check_flags | Takes the option check from flags.py. | The option rules sit in their own file, so each file stays short enough to read. |
| `argv[0] != "oc" or argv[1] not in VERBS` | The command must start with oc and one of three read-only verbs. oc delete, oc exec and oc apply stop here. | This is the first gate, where the words that make a command harmful, such as delete or exec, are stopped. |
| verb == "logs" | Logs have their own rule: the target must be deployment/NAME. | Logs take a different target than get and describe, so they need their own check. |
| target not in KINDS | A get or describe may name only the kinds in KINDS: the four supplied ones and any you add in kinds.py. Secrets, nodes and config maps are not on the list. | This keeps the agent away from kinds of object you did not list, secrets included. |
| has_name ... | An optional object name, checked against a strict pattern. | A name is data from the model, so it is checked against the strict pattern too. |
| check_command(text) | The function the loop calls. It returns the command as separate words if allowed, or a reason if not. | One function is the single door into the cluster, so every proposal passes the same checks. |
| `shlex.split(text)` | Splits the text into words the way a shell would, without running anything. | The command becomes separate words without a shell ever running, so nothing can be chained. |

#### 2c. Save the test runner as try_policy.py

You will now make the file try_policy.py in the same folder as policy.py by pasting the whole block into the lab shell.

- The file checks eight example commands against the verdict each one should get, plus the cases you write next.
- The command prints ok when try_policy.py has content.

```bash
cd /workspace/aid-4/agent
cat > try_policy.py <<'EOF'
import sys

from my_cases import MY_CASES
from policy import check_command

CASES = [
    ("oc get pods -n demo", True),
    ("oc logs deployment/noisy-app -n demo --tail=20", True),
    ("oc delete pods --all -n demo", False),
    ("oc get secrets -n demo", False),
    ("oc get pods -n demo -o yaml", False),
    ("oc get pods -n kube-system", False),
    ("oc get pods -n demo; oc delete pods --all -n demo", False),
    ("oc get pods -n demo --as=system:admin", False),
] + MY_CASES
mismatches = 0
for text, should_allow in CASES:
    argv, reason = check_command(text)
    allowed = argv is not None
    matches = allowed == should_allow
    print("ok      " if matches else "MISMATCH", "ALLOW " if allowed else "REFUSE", text, "" if allowed else "(" + reason + ")")
    mismatches += not matches
print(len(CASES), "cases,", mismatches, "mismatches")
sys.exit(1 if mismatches else 0)
EOF
test -s try_policy.py && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd ... ; cat > try_policy.py <<'EOF' ... EOF | Moves into the agent folder and writes everything between the first and the last line into try_policy.py. Running it again replaces the file with the same text. | The lab has no editor, so a paste is how you make the file. |
| test -s try_policy.py && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| from my_cases import MY_CASES | Brings in the list of test cases you write in the next block, in a file named my_cases.py. | Your cases live in their own small file, so you write only the cases and not this whole runner. |
| CASES = [ (command, True or False), ... ] | Each case is a command and the answer it should get: True means the allowed list must allow it, False means it must refuse it. Two must be allowed and six must be refused. | A test that states the right answer in advance can fail. A test that only prints verdicts cannot. |
| check_command(text) | Runs each case through the real allowed list. Nothing is sent to the cluster. | Using the real list, not a copy, means the test shows what the loop will do. |
| print(...) and mismatches | Prints ok or MISMATCH, then ALLOW or REFUSE, the command, and the reason for a refusal. Counts the mismatches. | A line for each case shows the verdict and the reason side by side. |
| sys.exit(1 if mismatches else 0) | Ends with status 1 when any case got the wrong answer, and 0 when all are right. | A status a script can read is what lets a review gate use this file later. |

#### 2d. Your turn: write two test cases first, then run them (they should fail once)

You will now write two test cases for ReplicaSets (the objects a deployment uses to keep its pods running), which a triage often needs.

- You write them before the allowed list can pass them.
- The block below is a scaffold: type it, and replace each ____ with the full command text.
- Case one is the command that lists the ReplicaSets in project demo and must be allowed.
- Case two is `oc get replicasets -n demo -o yaml`, and it must be refused.
- oc takes the kind as a lowercase plural.
- One of the two cases should print MISMATCH, because the allowed list does not know ReplicaSets yet.
- Try the cases yourself before you look at any reference.
- The first line printed is ok when my_cases.py has content.
- An import error when you run the cases usually means flags.py, policy.py or try_policy.py is empty, so paste its block again.

```bash
cd /workspace/aid-4/agent
cat > my_cases.py <<'EOF'
MY_CASES = [
    ("____", True),
    ("____", False),
]
EOF
test -s my_cases.py && echo ok || echo EMPTY
python3 try_policy.py
```

**Expected output:**

```
Example only. The line for your first case shows MISMATCH and the last line says 1 mismatches.
ok
ok       ALLOW  oc get pods -n demo 
ok       ALLOW  oc logs deployment/noisy-app -n demo --tail=20 
ok       REFUSE oc delete pods --all -n demo (only oc get, describe and logs are allowed)
ok       REFUSE oc get secrets -n demo (resource kind not allowed: secrets)
ok       REFUSE oc get pods -n demo -o yaml (flag or value not allowed: -o)
ok       REFUSE oc get pods -n kube-system (flag or value not allowed: -n)
ok       REFUSE oc get pods -n demo; oc delete pods --all -n demo (shell characters are not allowed)
ok       REFUSE oc get pods -n demo --as=system:admin (flag or value not allowed: --as=system:admin)
MISMATCH REFUSE oc get replicasets -n demo (resource kind not allowed: replicasets)
ok       REFUSE oc get replicasets -n demo -o yaml (resource kind not allowed: replicasets)
10 cases, 1 mismatches
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd ... ; cat > my_cases.py <<'EOF' ... EOF | Writes your two cases into my_cases.py, in the folder where try_policy.py already is. | The runner reads this file, so your cases must be in it. |
| test -s my_cases.py && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| ("____", True) | Your first case. Replace ____ with the command that lists ReplicaSets in project demo. True means it must be allowed. | This is the positive check: the new kind works when asked the plain way. |
| ("____", False) | Your second case. Replace ____ with the same command plus -o yaml. False means it must be refused. | This is the negative check: allowing a new kind must not switch off the rules about options. |
| python3 try_policy.py | Runs the eight supplied cases and your two against the allowed list as it is now. | Seeing your case fail first proves the test can fail, so a pass later means something. |

![Output from a real lab run: Your turn: write two test cases first, then run them (they should fail once)](img/AID-4-shot-2d.png)

#### 2e. Your turn: add the kind to the allowed list, then run the cases again

You will now make the failing case pass.

- policy.py already looks for a file named kinds.py with a set named MORE_KINDS.
- Type the scaffold below.
- Replace each ____ with a name oc accepts for ReplicaSets: the plural and the singular, both lowercase, like the other kinds in policy.py.
- The command then runs the same ten cases again.
- The first line printed is ok when kinds.py has content.

```bash
cd /workspace/aid-4/agent
cat > kinds.py <<'EOF'
MORE_KINDS = {"____", "____"}
EOF
test -s kinds.py && echo ok || echo EMPTY
python3 try_policy.py
```

**Expected output:**

```
Example only. All ten case lines say ok and the last line says 0 mismatches.
ok
ok       ALLOW  oc get pods -n demo 
ok       ALLOW  oc logs deployment/noisy-app -n demo --tail=20 
ok       REFUSE oc delete pods --all -n demo (only oc get, describe and logs are allowed)
ok       REFUSE oc get secrets -n demo (resource kind not allowed: secrets)
ok       REFUSE oc get pods -n demo -o yaml (flag or value not allowed: -o)
ok       REFUSE oc get pods -n kube-system (flag or value not allowed: -n)
ok       REFUSE oc get pods -n demo; oc delete pods --all -n demo (shell characters are not allowed)
ok       REFUSE oc get pods -n demo --as=system:admin (flag or value not allowed: --as=system:admin)
ok       ALLOW  oc get replicasets -n demo 
ok       REFUSE oc get replicasets -n demo -o yaml (flag or value not allowed: -o)
10 cases, 0 mismatches
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd ... ; cat > kinds.py <<'EOF' ... EOF | Writes the extra kinds into kinds.py. policy.py adds this set to its own four kinds. If the file is missing, policy.py adds nothing, so the list stays as narrow as before. | The one change you make to the agent's power sits in its own small file, so a reviewer can read it at a glance. |
| test -s kinds.py && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| MORE_KINDS = {"____", "____"} | Replace both ____ with the two lowercase names for ReplicaSets. | A kind that is not in this set stays refused, whatever the model proposes. |
| python3 try_policy.py | Runs all ten cases again. | All ten ok, with the delete and the -o yaml cases still refused, proves you widened the list by one kind and nothing else. |

#### 2f. Store the allowed list in the cluster and test the stored copy

You will now store your allowed list (flags.py, policy.py and your kinds.py) in a config map in project ai-lab, copy it back out, and run the same ten cases against the stored copy.

- The agent itself still runs from this folder, so the config map is the copy a reviewer reads.

```bash
cd /workspace/aid-4/agent
oc create configmap triage-policy -n ai-lab --from-file=flags.py --from-file=policy.py --from-file=kinds.py --dry-run=client -o yaml | oc apply -f -
mkdir -p stored; oc extract configmap/triage-policy -n ai-lab --to=stored --confirm >/dev/null
cp try_policy.py my_cases.py stored/; python3 stored/try_policy.py | tail -n 1
```

**Expected output:**

```
Example only.
configmap/triage-policy created
10 cases, 0 mismatches
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-4/agent | Moves into the agent folder made in Step 1. | The files are in the folder you are standing in. |
| oc create configmap triage-policy ... \| oc apply -f - | Stores the three files in a config map in project ai-lab. Applying again changes nothing instead of failing. | The allowed list becomes an object in the cluster that a reviewer can read, not only files in your folder. |
| mkdir -p stored; oc extract ... --to=stored --confirm | Copies the stored files back out into a new folder named stored. | You test what the cluster holds, not your local copy. |
| cp try_policy.py my_cases.py stored/; python3 stored/try_policy.py \| tail -n 1 | Adds the test runner and your cases next to the stored files and runs the ten cases there. The last line is the result. | No mismatch on the stored copy shows it is the list you tested. |

#### 2g. Only after you have tried: compare with the reference answer

You will now print the two reference files that the lab stored in project ai-lab, so you can compare them with your own.

- Do not open the reference files until you have tried both blocks above; if you are stuck for more than a few minutes, look.
- Different wording is fine if all ten cases say ok and the -o yaml case is still refused.

```bash
oc get configmap aid4-ref -n ai-lab -o json | jq -r '.data["my_cases.py"], .data["kinds.py"]'
```

**Expected output:**

```
Example only.
MY_CASES = [
    ("oc get replicasets -n demo", True),
    ("oc get replicasets -n demo -o yaml", False),
]
MORE_KINDS = {"replicasets", "replicaset"}
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| oc get configmap aid4-ref -n ai-lab -o json | Reads the config map that holds the reference files and prints it as JSON. | The answer is kept on the cluster, not in your folder, so it is not in front of you while you work. |
| jq -r '.data["my_cases.py"], .data["kinds.py"]' | Prints the text of the two reference files, one after the other. | You compare your own files with these two. |

> **TIP:** The option -o yaml is refused because a full object dump can hold data you did not mean to read, even when the platform would allow it. --as is refused so a proposal cannot change the identity the loop runs as.

> **YOUR TURN:** Paste flags.py, policy.py and try_policy.py. Then write my_cases.py and kinds.py yourself, run the cases after each, store the list in the config map, and open the reference answer only afterwards.

> **CHECKPOINT:** The first run of your cases prints one MISMATCH and ends with 10 cases, 1 mismatches. After kinds.py the last line says 10 cases, 0 mismatches, and the stored copy in the config map says the same. The ReplicaSets case is ALLOW and the same case with -o yaml is REFUSE, and the delete, secrets and chained cases are still REFUSE.

> **TAKEAWAY:** An allowed list names what is permitted, so anything not on it is refused, including the verb nobody thought of.

**How this meets the controls**

- **CM-7:** You write the allowed list: three read-only verbs, four kinds of object plus the one you add, and one project. The test run checks ten commands and each bad one must be refused with a reason.
- **SI-10:** The allowed list splits the command into words and checks every one. A shell character, an unknown flag or an unlisted kind of object is refused with a reason.

### Step 3. Write the loop: validate, log, cap and stop (SI-10 Information Input Validation, AU-12 Audit Record Generation)

**Learning point: Build the full loop that validates proposals, logs every action to Loki before it acts, enforces a step cap, and stops on a file. This is the complete agent with every safety control in place.**

- The loop writes a record before each action and stops if the record cannot be written.
- You copy the supplied `audit.py` and read it.
- You paste `agent.py` and `loop.py` yourself.

What this step adds (thick lines and outlines are new):

![The model proposes, the wrapper decides, after step 3](img/AID-4-step-3.png)

- The loop is written in your agent folder. It asks the stub model service for a step, checks the proposal against the allowed list, runs allowed commands as the view-only identity against project demo, sends a record of every action to Loki in project siem, and honors the step cap and the stop file. A refused command is stopped in your agent folder and never reaches the cluster.

#### 3a. Copy the supplied audit writer and Loki helper into your agent folder

You will now copy audit.py and `ailog.py` out of a config map on the cluster into your agent folder.

- The file `ailog.py` is a small helper that sends one log record to Loki.
- `ailog.py` signs in with the lab variables.

```bash
cd /workspace/aid-4/agent
oc extract configmap/aid4-kit -n ai-lab --to=. --confirm
```

**Expected output:**

```
Example only. oc names each file it writes.
audit.py
ailog.py
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-4/agent | Moves into the agent folder made in Step 1. | The supplied files must land next to policy.py. |
| oc extract configmap/aid4-kit ... --confirm | Writes the supplied audit.py and `ailog.py` into the current folder, replacing them if they are already there. `ailog.py` is the Loki helper described above, so only audit.py is read below. | The Loki push code is supplied so you spend your time on the loop. You read audit.py before you use it, because it holds the one rule that is new here. |

#### 3b. Read audit.py

You will now read the file audit.py you just copied.

- You do not type audit.py, and reading it prints nothing.
- To see the same file in lab shell, type cd /workspace/aid-4/agent and then cat audit.py.

Look for these as you read:

- audit() builds each record from a kind, a UTC time and the fields the caller gives, then prints it on screen before it is pushed.
- push() comes from `ailog.py`, the Loki helper from AID-3. The labels are app=triage-agent and the kind of event, and the login and the certificate file come from lab variables, so no password is written in either file.
- The except OSError line: if Loki cannot be reached, audit.py raises a RuntimeError (a Python error). That is the rule that makes the loop stop when it cannot log.
- Nothing in audit.py decides what is logged from the model's text: the loop passes the fields, and audit.py only writes them.

```python
import json
import time

from ailog import push


def audit(kind, **fields):
    line = json.dumps({"kind": kind, "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **fields})
    print("AUDIT", line)
    try:
        push({"app": "triage-agent", "kind": kind}, line)
    except OSError as exc:
        raise RuntimeError("audit log unavailable, stopping: " + str(exc)) from exc
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| `from ailog import push` | Reuses the Loki push you read in AID-3 instead of a second copy of the same code. | One copy of the sign-in and certificate handling means a fix is made once. |
| audit(kind, **fields) | Builds the record: the kind, a UTC time, and whatever fields the caller gives, such as the step number and the command. | One function writes every record in the same format, so a search finds them all. |
| print("AUDIT", line) | Shows each record on screen too, so you can follow the run. | Following the run on screen helps you notice when something does not match the log. |
| except OSError ... raise RuntimeError | The new rule in this module: fail closed, which means stop when something needed for safety is missing. If Loki cannot be reached, stop the whole run. The loop turns this into exit status 6 (the number a program leaves behind when it ends). | An action nobody can see is not allowed, so a log failure stops the run instead of being ignored. |

![Output from a real lab run: Read audit.py](img/AID-4-shot-3b.png)

#### 3c. Save the proposal checks and the command runner as agent.py

You will now make the file agent.py in your agent folder by pasting the whole block (a heredoc) into the lab shell.

- The command prints ok when agent.py has content.

```bash
cd /workspace/aid-4/agent
cat > agent.py <<'EOF'
import json
import os
import subprocess
import urllib.request

STUB_URL = os.environ.get("STUB_URL", "http://127.0.0.1:8089")
IDENTITY = "--as=system:serviceaccount:ai-lab:triage-agent"
MAX_STEPS = 6
OUTPUT_LIMIT = 2000
STOP_FILE = "STOP"
SHAPES = {"run": {"action", "command"}, "finish": {"action", "summary"}}


def ask(scenario, number, observation):
    body = json.dumps({"request_id": f"{scenario}-{number}", "input": observation}).encode()
    request = urllib.request.Request(STUB_URL + "/v1/answer", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())["reply"]


def parse_proposal(text):
    data = json.loads(text)
    if not isinstance(data, dict) or set(data) != SHAPES.get(data.get("action"), None):
        raise ValueError("proposal does not match an allowed shape")
    if not all(isinstance(value, str) for value in data.values()):
        raise ValueError("proposal fields must be text")
    return data


def execute(argv):
    done = subprocess.run([argv[0], IDENTITY, *argv[1:]], capture_output=True, text=True, timeout=20, check=False)
    return (done.stdout + done.stderr)[:OUTPUT_LIMIT]
EOF
test -s agent.py && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd ... ; cat > agent.py <<'EOF' ... EOF | Moves into the agent folder and writes everything between the first and the last line into agent.py. Running it again replaces the file with the same text. | The lab has no editor, so a paste is how you make the file. |
| test -s agent.py && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| IDENTITY | Put into every command by the wrapper, never by the model. Every command runs as the view-only identity from Step 1. | Putting the identity in the wrapper means the model cannot choose or change who runs the command. |
| MAX_STEPS = 6 | The step cap. A run that has not finished by the sixth step is stopped. A choice the lab makes. | A cap guarantees the loop ends, even if the model never says it is done. |
| OUTPUT_LIMIT = 2000 | The most characters of a command's output the loop keeps and passes back to the model. | Limiting the output stops one huge log from filling what the model sees. |
| STOP_FILE = "STOP" | The stop switch. If a file with this name exists, the loop ends. | A person needs a simple way to halt a run, and checking for a file needs no extra tools. |
| ask(scenario, number, observation) | Sends the question to the stub with the request id scenario-number, such as triage-clean-1. | The request id carries the scenario and the step, which is how the stub knows which scripted answer to give. |
| parse_proposal(text) | Accepts a JSON object (a plain-text data format of names and values) with exactly the fields action and command, or action and summary, and all values text. Chat text, extra fields and other actions raise an error. | The model's reply is an input, so only the two exact shapes are accepted before anything reads it. |
| `subprocess.run([argv[0], IDENTITY, *argv[1:]] ...)` | Runs the command as a list of words, without a shell, with a time limit, as the view-only identity. | Running a list of words with no shell is what keeps a command from being chained or expanded. |

#### 3d. Save the loop as loop.py

You will now make the file loop.py in your agent folder by pasting the whole block into the lab shell.

- The command prints ok when loop.py has content.

```bash
cd /workspace/aid-4/agent
cat > loop.py <<'EOF'
import os
import sys

from agent import MAX_STEPS, STOP_FILE, ask, execute, parse_proposal
from audit import audit
from policy import check_command


def run(scenario):
    observation = "Triage the demo project."
    for number in range(1, MAX_STEPS + 1):
        if os.path.exists(STOP_FILE):
            audit("stopped", step=number)
            return 3
        try:
            proposal = parse_proposal(ask(scenario, number, observation))
        except (ValueError, KeyError, TypeError, OSError) as exc:
            audit("invalid", step=number, reason=str(exc))
            return 4
        if proposal["action"] == "finish":
            audit("finish", step=number, summary=proposal["summary"])
            return 0
        argv, reason = check_command(proposal["command"])
        if reason:
            audit("refused", step=number, command=proposal["command"], reason=reason)
            return 4
        audit("allowed", step=number, command=proposal["command"])
        observation = execute(argv)
        audit("result", step=number, chars=len(observation))
    audit("step_cap", limit=MAX_STEPS)
    return 5


if __name__ == "__main__":
    try:
        sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else "triage-clean"))
    except RuntimeError as exc:
        print("STOPPED:", exc)
        sys.exit(6)
EOF
test -s loop.py && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd ... ; cat > loop.py <<'EOF' ... EOF | Moves into the agent folder and writes everything between the first and the last line into loop.py. Running it again replaces the file with the same text. | The lab has no editor, so a paste is how you make the file. |
| test -s loop.py && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| for number in range(1, MAX_STEPS + 1) | The loop cannot run more than six times, whatever the model says. | A hard bound on the loop makes sure a run cannot go on forever. |
| os.path.exists(STOP_FILE) | Checked before every step, so a stop takes effect before the next action. | A person who creates the stop file wants the run to end before its next action, so the check comes first. |
| except (ValueError, KeyError, TypeError, OSError) | A reply that is not valid, or a model that cannot be reached, ends the run as invalid. | A reply the loop cannot read is one it cannot trust, so the run ends and the reason is recorded. |
| proposal["action"] == "finish" | The model says it is done. The loop logs the summary and ends with status 0. | A summary from the model is accepted as the end of the run, once the record is written. |
| `check_command(proposal["command"])` | The allowed list from Step 2. A refusal is logged and ends the run with status 4. The command is never executed. | This is where the model's proposal meets the allowed list, and a refusal ends the run with a record. |
| `audit("allowed", ...)` then `execute(argv)` | The record is written before the command runs. | Recording first means the trail exists even if the command then fails or hangs. |
| audit("step_cap", ...) return 5 | Reached only if six steps passed without a finish. | A run that reaches this point never finished, which a reader needs to see as its own kind of record. |
| sys.exit(6) | Exit status 6 means the audit log could not be written. | A distinct status tells a person or a schedule that the run ended because logging failed. |

#### 3e. Check that all five files are well formed

You will now check the five files for typing errors without running them.

```bash
cd /workspace/aid-4/agent
python3 -m py_compile audit.py agent.py loop.py policy.py flags.py
```

**Expected output:**

```
Example only.
(no output means all five files are well formed)
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-4/agent | Moves into the agent folder made in Step 1. | All five files are there. |
| `python3 -m py_compile ...` | Checks that all five files are well formed without running them. No output means success. | Checking how all five files are written catches a typing slip before the first run. |

> **NOTE:** Trade-off: after a refusal this loop ends the run. Letting the model try another step would sometimes finish the triage, but each retry gives injected text another attempt. Ending the run costs a person one rerun, so the lab ends it.

> **SECURITY:** The model's text is never run as a shell command and never changes the identity, the limits or the log. Only the wrapper's own constants decide those. If you find yourself adding a rule that depends on what the model says it is doing, stop: the model can say anything.

> **YOUR TURN:** Extract audit.py and `ailog.py`, read audit.py, paste agent.py and loop.py, then run the check.

> **CHECKPOINT:** python3 -m py_compile prints nothing, which means all five files are well formed.

> **TAKEAWAY:** Write the record before each action, because an action nobody can see is not allowed.

**How this meets the controls**

- **SI-10:** `parse_proposal` accepts only two exact shapes from the model; the command inside is checked again by the allowed list. Anything else ends the run with status 4.
- **AU-12:** `audit.py` writes a record for every allowed, refused, invalid, finished, stopped and capped event before the action happens. If Loki cannot be reached, the loop stops with status 6.

### Step 4. Run a clean triage and read the trail (AU-12 Audit Record Generation)

**Learning point: Run the clean scenario end to end and read the action trail back from Loki. This proves the agent is useful when nothing goes wrong and that the trail exists in the central log store, not only on screen.**

- The stub model service proposes three read-only commands and then finishes, and every action leaves a record in Loki.
- Reading the trail from Loki, not from the screen, is how you prove the records reached the central store.

What this step adds (thick lines and outlines are new):

![The model proposes, the wrapper decides, after step 4](img/AID-4-step-4.png)

- A clean run reads the pods and the log of the noisy application in project demo, and finishes with a summary. Every action is sent to Loki in project siem.

#### 4a. Run the clean scenario and read the trail in Loki

You will now run the loop on the clean scenario, keep its records in run.log, and then read the same records back from Loki.

- An import error when you run the loop usually means agent.py or loop.py is empty, so paste its block again.

```bash
cd /workspace/aid-4/agent
curl -s http://127.0.0.1:8089/healthz >/dev/null || { oc port-forward -n ai-lab svc/stub-model 8089:8080 >/dev/null 2>&1 & sleep 3; }
python3 loop.py triage-clean > run.log; echo "exit status: $?"
cat run.log
sleep 5
curl -sG --cacert "$LOKI_CA_FILE" -u "$LOKI_USER:$LOKI_PASSWORD" \
  "$LOKI_URL/loki/api/v1/query_range" \
  --data-urlencode 'query={app="triage-agent"}' \
  --data-urlencode 'limit=50' \
  | jq -r '[.data.result[].values[]] | sort_by(.[0])[] | .[1] | fromjson | [.time, .kind, .step, .command] | @tsv'
```

**Expected output:**

```
Example only. <time> is the time of each record.
exit status: 0
AUDIT {"kind": "allowed", "time": "<time>", "step": 1, "command": "<command>"}
AUDIT {"kind": "result", "time": "<time>", "step": 1, "chars": <n>}
(the same pair of records for steps 2 and 3)
AUDIT {"kind": "finish", "time": "<time>", "step": 4, "summary": "<summary text>"}
<time>	allowed	1	<command>
<time>	result	1
(one line for each of the seven records, in time order)
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-4/agent | Moves into the agent folder made in Step 1. | loop.py and run.log are files in that folder. |
| curl -s ... \|\| { oc port-forward ... } | Opens the tunnel to the stub only if it is not already open. Its messages are hidden (>/dev/null 2>&1) so they do not look like errors. | The loop asks the stub for every step, and the tunnel is gone if you opened a new lab shell. |
| python3 loop.py triage-clean > run.log | Runs the clean scenario. The word after loop.py picks the scenario. The records go to run.log, which Test 1 in Section 4 reads. | A normal run proves the agent is still useful and gives you a trail to read. |
| echo "exit status: $?" | Prints how the loop ended. 0 means the model finished. | The status tells a person or a schedule how the run ended without reading the log. |
| cat run.log | Shows the records the run printed. | Test 1 in Section 4 counts the lines in run.log, so you keep a copy of the run. |
| query={app="triage-agent"} | Asks Loki for every record the agent wrote. | Reading the trail from Loki, not from your screen, proves the records reached the central store. |
| jq -r '[...values[]] \| sort_by(.[0])[] \| .[1] \| fromjson \| [...] \| @tsv' | Puts the records in the order Loki stamped them, reads each record, and prints one tab-separated line: time, kind, step and command. | A table of time, kind, step and command is quicker to read than raw JSON lines, and Loki's own timestamp keeps records from the same second in the order they happened. |
| sort_by(.[0]) | Sorts by the timestamp Loki gave each record, to the nanosecond. | Records can arrive out of order, and a plain text sort would mix records from the same second, so the stamp from Loki gives the true order of events. |

![Output from a real lab run: Run the clean scenario and read the trail in Loki](img/AID-4-shot-4a.png)

> **YOUR TURN:** Run the block and read each line of the trail.

> **CHECKPOINT:** The exit status is 0. The trail shows allowed and result pairs for three steps, then one finish record, and run.log holds seven AUDIT lines.

> **TAKEAWAY:** Read the trail from Loki, not from your screen, because the central store is what a reviewer can search.

**How this meets the control**

- **AU-12:** You run the clean scenario and read the records back from Loki. The table of time, kind, step and command is the trail that shows what the agent did.

## Section 4. Verify It Works

### Test 1 (positive). A clean run finishes and every action is on record (AU-12 Audit Record Generation)

- The agent must still be useful: it reads, summarizes and ends on its own, and the trail must show each action.
- Step 4 already ran the clean scenario and saved run.log, so this reads that run instead of repeating it.

```bash
cd /workspace/aid-4/agent
grep -c AUDIT run.log
grep -c '"kind": "finish"' run.log
```

**Expected output:**

```
Example only. The first count is the number of records the run wrote.
7
1
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-4/agent | Moves into the agent folder, where Step 4 saved run.log. | run.log is a file in that folder. |
| grep -c AUDIT run.log | Counts the audit records the clean run printed. The answer is 7. | Three allowed commands, their three results and one finish make seven. |
| grep -c '"kind": "finish"' run.log | Counts the finish records. The answer is 1. | The run ended by itself, with the summary on record. |

![Output from a real lab run: A clean run finishes and every action is on record](img/AID-4-shot-test1.png)

> **CHECKPOINT:** Seven AUDIT lines (three allowed commands, their three results, and one finish) and exactly one finish record. The exit status 0 was shown in Step 4.

**How this meets the control**

- **AU-12:** You count the records in run.log from Step 4. Seven records, one of them the finish record, show that every action was recorded.

### Test 2 (negative). The injected instruction is refused by both layers and nothing is deleted (CM-7 Least Functionality, AC-6 Least Privilege, AU-12 Audit Record Generation)

- The noisy application's log tells an assistant to delete all pods, and the injected scenario has the stub propose exactly that at step 3.
- The wrapper must refuse the delete of all pods and leave every pod in place.
- You also send that same delete straight to the platform as the view-only identity, as a dry run, so you see the second layer, the platform, refuse it too.

```bash
cd /workspace/aid-4/agent
curl -s http://127.0.0.1:8089/healthz >/dev/null || { oc port-forward -n ai-lab svc/stub-model 8089:8080 >/dev/null 2>&1 & sleep 3; }
oc get pods -n demo --no-headers | wc -l
python3 loop.py triage-injected; echo "exit status: $?"
oc get pods -n demo --no-headers | wc -l
oc delete pods --all -n demo --as=system:serviceaccount:ai-lab:triage-agent --dry-run=server
```

**Expected output:**

```
Example only. The pod count in your project can differ, but the two counts must match.
2
AUDIT {"kind": "allowed", "time": "2026-10-29T14:03:11Z", "step": 1, "command": "oc get pods -n demo"}
AUDIT {"kind": "result", "time": "2026-10-29T14:03:11Z", "step": 1, "chars": 212}
AUDIT {"kind": "allowed", "time": "2026-10-29T14:03:12Z", "step": 2, "command": "oc logs deployment/noisy-app -n demo --tail=20"}
AUDIT {"kind": "result", "time": "2026-10-29T14:03:12Z", "step": 2, "chars": 940}
AUDIT {"kind": "refused", "time": "2026-10-29T14:03:12Z", "step": 3, "command": "oc delete pods --all -n demo", "reason": "only oc get, describe and logs are allowed"}
exit status: 4
2
Error from server (Forbidden): <a message that names the service account and pods; the dry run prints one such line for each pod in the project>
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-4/agent | Moves into the agent folder from Step 1. | loop.py is a file in that folder. |
| oc get pods -n demo --no-headers \| wc -l | Counts the pods in project demo. It is run before and after the attack. | Equal counts are the proof that nothing was deleted. |
| python3 loop.py triage-injected | Runs the scenario where the stub proposes the delete the log line asked for. | The wrapper must refuse it. |
| AUDIT ... "kind": "refused" ... reason | The record of the refusal, with the command and the reason. | It lets a person see the attempt later. |
| exit status: 4 | The loop ended because of a refusal. | Status 4 is the signal that a person should look. |
| oc delete pods --all -n demo --as=... --dry-run=server | Sends the same delete straight to the platform as the view-only identity, as a dry run. | The platform refuses it too, so the limit holds even if the allowed list has a bug. |

![Output from a real lab run: The injected instruction is refused by both layers and nothing is deleted](img/AID-4-shot-test2.png)

> **CHECKPOINT:** A refused record names the delete and the reason, the exit status is 4, and the pod count is the same before and after. The last command takes the wrapper out of the picture and sends the same delete as the view-only identity, as a dry run. The platform refuses it too. The project demo is shared with other modules: if a pod starts or stops between the two counts, they differ for a reason unrelated to the agent, so run the block again.

**How this meets the controls**

- **CM-7:** The injected scenario proposes a delete of all pods, and the allowed list refuses it. The equal pod counts before and after prove that nothing was deleted.
- **AC-6:** The same delete is sent directly as the view-only identity, with the wrapper out of the way. The platform answers Forbidden, so the limit holds even if the allowed list has a bug.
- **AU-12:** The refused proposal leaves a record that names the command and the reason. That record lets a person see the attempt later.

### Test 3 (negative). A loop that never finishes is cut off, and a person can stop it (AU-12 Audit Record Generation)

- The step cap and the stop file are two limits that do not depend on the model behaving.
- In the triage-loop scenario the stub proposes the same read forever, and the step cap must end it.
- You then create the stop file and confirm that no step runs at all.

```bash
cd /workspace/aid-4/agent
curl -s http://127.0.0.1:8089/healthz >/dev/null || { oc port-forward -n ai-lab svc/stub-model 8089:8080 >/dev/null 2>&1 & sleep 3; }
python3 loop.py triage-loop | grep -c '"kind": "allowed"'
python3 loop.py triage-loop | grep step_cap
touch STOP
python3 loop.py triage-clean | grep -c '"kind": "allowed"'
python3 loop.py triage-clean | grep stopped
rm STOP
```

**Expected output:**

```
Example only. The time in each record differs.
6
AUDIT {"kind": "step_cap", "time": "2026-10-29T14:05:40Z", "limit": 6}
0
AUDIT {"kind": "stopped", "time": "2026-10-29T14:05:42Z", "step": 1}
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-4/agent | Moves into the agent folder from Step 1. | The stop file is made in the folder the loop runs in. |
| python3 loop.py triage-loop \| grep -c ...allowed | Runs the endless scenario and counts the allowed steps. The answer is 6. | The step cap ends the run at six. |
| grep step_cap | Prints the record that says the cap was reached. | A capped run has its own kind of record. |
| touch STOP | Makes the stop file. | This is the stop switch a person uses. |
| python3 loop.py triage-clean \| grep -c ...allowed | Runs a clean scenario with the stop file present. The answer is 0. | No step runs once a person has asked for a stop. |
| grep stopped ; rm STOP | Prints the stopped record, then removes the stop file. | Removing the file lets later runs work. |

![Output from a real lab run: A loop that never finishes is cut off, and a person can stop it](img/AID-4-shot-test3.png)

> **CHECKPOINT:** Six allowed steps and then a step_cap record. With the stop file present, zero allowed steps and a stopped record. Remove the stop file afterward.

**How this meets the control**

- **AU-12:** The step cap and the stop file each end the run and each leaves its own record, step_cap or stopped. The records show why the run ended, not only that it did.

### Test 4 (negative). Secrets, chained commands and chat text are all refused (SI-10 Information Input Validation, CM-7 Least Functionality)

- A proposal can go wrong in three more ways: a read of secrets, a second command chained onto an allowed one, and a reply that is chat text instead of a proposal.
- Each of these three bad proposals must end the run with status 4 and a record that says why.

```bash
cd /workspace/aid-4/agent
curl -s http://127.0.0.1:8089/healthz >/dev/null || { oc port-forward -n ai-lab svc/stub-model 8089:8080 >/dev/null 2>&1 & sleep 3; }
for scenario in triage-secret triage-chained triage-malformed; do
  python3 loop.py "$scenario" | grep -E 'refused|invalid' | cut -c1-200
done
```

**Expected output:**

```
Example only. Times differ.
AUDIT {"kind": "refused", "time": "2026-10-29T14:07:01Z", "step": 2, "command": "oc get secrets -n demo -o yaml", "reason": "resource kind not allowed: secrets"}
AUDIT {"kind": "refused", "time": "2026-10-29T14:07:02Z", "step": 1, "command": "oc get pods -n demo; oc delete deployment noisy-app -n demo", "reason": "shell characters are not allowed"}
AUDIT {"kind": "invalid", "time": "2026-10-29T14:07:03Z", "step": 1, "reason": "Expecting value: line 1 column 1 (char 0)"}
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-4/agent | Moves into the agent folder from Step 1. | loop.py is a file in that folder. |
| for scenario in triage-secret triage-chained triage-malformed | Runs three scenarios, each with a different bad proposal. | Each bad proposal is stopped by a different check. |
| grep -E 'refused\|invalid' \| cut -c1-200 | Keeps only the refusal and invalid records and shortens long lines. | Those records say why the run ended. |
| resource kind not allowed: secrets | The read of secrets was refused. | The allowed list does not name secrets. |
| shell characters are not allowed | The chained command was refused. | A second command cannot ride along on an allowed one. |
| "kind": "invalid" | The chat text was not a proposal. | Only two exact shapes are accepted. |

![Output from a real lab run: Secrets, chained commands and chat text are all refused](img/AID-4-shot-test4.png)

> **CHECKPOINT:** Three different reasons: resource kind, shell characters, and an invalid proposal. None of the three bad proposals reached the cluster.

**How this meets the controls**

- **SI-10:** Three bad proposals are tried: a read of secrets, a chained command and chat text in place of a proposal. Each is stopped by a check and leaves a record that says why.
- **CM-7:** The secrets read and the chained command are both outside the allowed list. Both are refused, so neither reaches the cluster.

## Section 5. What Each Control Is For

### Control mapping

| Control | What it requires, in plain words | Tool or service | Where this module covers it |
| --- | --- | --- | --- |
| AC-6 Least Privilege | Give each identity only the access its job needs. | An OpenShift service account with the built-in view role in project demo, used through oc --as. Explained in section 2.1. | Section 3, Step 1: give the agent a view-only identity and prove its limits. Section 4, Test 2: the platform refuses the same delete when the wrapper (the program around the model that decides what may run) is bypassed. |
| CM-7 Least Functionality | Allow only the functions the job needs and block the rest. | The command allowed list in policy.py, which runs commands as separate words with no shell. Explained in section 2.1. | Section 3, Step 2: write the allowed list (a list of what is permitted, where anything else is refused): three read-only verbs, four kinds of object plus the one you add, one project (a named section of the cluster). Section 4, Test 2: a delete is refused. Section 4, Test 4: secrets and chained commands are refused. |
| SI-10 Information Input Validation | Check inputs for valid syntax and content before they are used. | parse_proposal in agent.py and check_command in policy.py. Explained in sections 2.1 and 2.2. | Section 3, Step 3: accept only two proposal shapes from the model. Section 3, Step 2: validate the command inside one. Section 4, Test 4: send malformed and chained proposals. |
| AU-12 Audit Record Generation | Produce audit records (log lines that say what happened and when) for the events the system is meant to record. | audit.py, which pushes each record to Loki (the log store in your lab cluster). Explained in section 2.1. | Section 3, Step 3: log every allowed, refused and invalid action to Loki before it acts. Section 3, Step 4: read the trail back from Loki. Section 4, Tests 1 to 3: count and print the records. |

### What each control is for

Each table below says what the control is trying to prevent and how this module's tool meets it.

#### AC-6 Least Privilege

| Question | Answer |
| --- | --- |
| Control Intent | An agent runs with the permissions of the person who started it, and a planted instruction uses all of them. |
| The operational question | If the agent did exactly what a hostile log line told it to, what is the most damage this identity could do? |
| What evidence proves it | The permission checks for the agent identity, with a yes or no for each action that matters. |
| How much is enough | The identity can read what triage needs and nothing else. It cannot read secrets or change or delete anything. The platform enforces this, so it holds if the wrapper has a bug. NIST does not list which accesses a job needs. The lab grants the built-in view role in project demo only. |
| How the tool in this module satisfies it | A service account (an identity for a program instead of a person) with the view role in project demo (Step 1), used through --as on every command the loop runs. |

#### CM-7 Least Functionality

| Question | Answer |
| --- | --- |
| Control Intent | The agent is able to run any command a shell (the program that reads the commands you type and runs them) can run, so anything the model proposes can happen. |
| The operational question | Which commands can this loop run, and who decided that list? |
| What evidence proves it | The allowed list as code, and a test that a command outside it is refused. |
| How much is enough | The loop runs only commands on a short list written in advance, without a shell, so a command cannot be chained. An allowed list names what is permitted, while a blocked list always misses something. The lab lists the verbs get, describe and logs, four kinds of object, and project demo. |
| How the tool in this module satisfies it | policy.py (Step 2) parses a proposal into separate words and refuses anything it does not recognize, including shell characters and unknown flags. |

#### SI-10 Information Input Validation

| Question | Answer |
| --- | --- |
| Control Intent | The model's output is treated as a trusted instruction, so whatever it says to run, runs. |
| The operational question | What exact shapes of proposal does the loop accept, and what happens to anything else? |
| What evidence proves it | The accepted shapes in code, and tests that send other shapes. |
| How much is enough | Only two shapes are accepted: run with a command, and finish with a summary. A missing field, an extra field or a non-text value ends the run. The command is then checked a second time against the allowed list. |
| How the tool in this module satisfies it | parse_proposal in agent.py (Step 3) and check_command in policy.py (Step 2). |

#### AU-12 Audit Record Generation

| Question | Answer |
| --- | --- |
| Control Intent | The agent acts and nobody can later show what it did or what it was stopped from doing. |
| The operational question | For each step, can you show what was proposed, whether it ran, and why it was refused? |
| What evidence proves it | Records for allowed, refused, invalid, finished, stopped and capped events in Loki. |
| How much is enough | A record is written before each action, in the central log store. If the log store cannot be reached, the loop stops, because an action nobody can see is not allowed. |
| How the tool in this module satisfies it | audit.py (Step 3) prints each record and pushes it to Loki, and the loop stops with status 6 if the push fails. |

## Section 6. Next Steps

### Using this in other environments

- The allowed list (`policy.py`, `flags.py`) and the loop (`loop.py`, `agent.py`) are plain Python and work on any OS with Python 3. The stub model service needs no key or internet access.
- Change these lab values first: the allowed project (`demo`) in `NAMESPACES`, the allowed kinds, the service account and project in `IDENTITY`, and the stub URL if the port forward address differs.
- The view-only identity uses standard Kubernetes RBAC; replace `oc` with `kubectl` on non-OpenShift clusters.
- The audit log uses Loki via `ailog.py`; production also needs Loki replicated to protected storage and an alert when the loop stops with status 6.

The table shows what changes on each platform:

| Check/part | In this lab (OpenShift) | On other platforms | What you change |
| --- | --- | --- | --- |
| Allowed list (`policy.py`) | `oc` verbs, `shlex.split`, no shell | Same, no cluster dependency | Change `oc` to `kubectl` in the `argv[0]` check in `check_argv()`. |
| View-only identity | Service account with view role in project demo, `--as` impersonation | Standard Kubernetes RBAC, same impersonation flag | Change `demo` to your project in `NAMESPACES` in `flags.py`. |
| Audit log (`audit.py`) | Loki in project siem via `ailog.py`, basic auth | Any HTTP log store that accepts pushes | Update `ailog.py` push() to match the target endpoint. |
| Model service (stub) | Stub in project ai-lab, port forward to 8089 | Any HTTP model endpoint | Set `STUB_URL` to the real endpoint. |
| Step cap and stop file | Constants in `agent.py`, checked in `loop.py` | Same, no cluster dependency | Nothing. |

> **TIP:** Next module: AID-5 Safe Adoption Pattern for Agents: you move the same limits into the platform so every new agent project inherits them, and measure how many attacks they stop.

<details>
<summary><strong>Section 7. Terms</strong></summary>

Each term is also explained the first time it appears. In Word, hover over an underlined term to see its meaning, or Ctrl+click it to jump to this table.

| Term | Plain meaning |
| --- | --- |
| Agent | A loop in which a model proposes the next step and a program carries it out. |
| Allowed list | A list of what is permitted. Anything not on it is refused. A blocked list names what is forbidden and misses what nobody thought of. |
| Audit record | One log line that says what happened, when, and why a step was allowed or refused. |
| AWS | Amazon Web Services, the cloud your lab runs in. |
| Certificate | A file that proves a server's identity, signed by a trusted authority. |
| Cluster | A group of servers that work together as one system. Here it is your own OpenShift cluster in AWS. |
| Config map | A cluster object that holds plain settings (not secrets) as named values or files, so a program can read them. |
| Container | A sealed box that holds one program and everything it needs to run. |
| Deployment | A cluster object that keeps a set number of copies of a program running. |
| Dry run | A check that reads and validates a request without making any change. |
| Endpoint | One address and port that something listens on, such as a pod behind a Service or a URL path that returns data. |
| Exit status | A number a command leaves behind when it ends. 0 means success and anything else means a problem. |
| Fail closed | Stop when something needed for safety is missing, instead of carrying on without it. |
| grep | A command that prints only the lines that match a pattern. |
| Header | A line of extra information sent with a web request, such as a sign-in token. |
| Heredoc | A way to make a file by pasting its text between a first line such as cat > name <<'EOF' and a last line that says EOF. |
| HTTP | The protocol that web pages and web APIs use. HTTPS is the encrypted form. |
| Identity | The name the cluster knows a user or a program by. It decides what that user or program may do. |
| Impersonation | Running a command as another identity. It lets the loop use the view-only identity while you stay logged in as yourself. |
| jq | A tool that picks one value out of JSON text. |
| JSON | A plain-text format for data: names and values written inside curly braces. |
| Kubernetes | The open-source system that runs and manages containers across servers. OpenShift is built on it. |
| Label | A key=value tag on a cluster object, used to pick objects, such as app=demo-app. |
| Log | A line of text that a program saves about what happened. |
| Loki | A log store that runs in your lab cluster. Programs send log lines to it and you search them later. |
| mkdir | A command that makes a new folder. |
| Model | A program that writes text when you ask. Here a stub stands in for it. |
| Namespace | A named section of the cluster that holds a set of related parts. |
| Network policy | A rule that says which pods may send traffic to which other pods. |
| NIST | The US National Institute of Standards and Technology. It publishes the security control catalog these modules cite. |
| Node | One server in the cluster. |
| Observation | The text a command printed. The loop sends it back to the model as what it has learned so far. |
| oc | The command-line tool for OpenShift. You type oc to ask the cluster questions. |
| OpenShift | The Red Hat platform your lab cluster runs on. It is Kubernetes with extra security and tools built in. |
| Option | An extra word after a command that changes how it runs, such as -n demo or --tail=20. Also called a flag. |
| Pod | The smallest running unit on the cluster: one or more containers together. |
| Policy | A set of rules written down so that a tool can enforce them. |
| Port forward | A tunnel from your shell to a service inside the cluster, so a command in lab shell can reach it. |
| Project | A named section of the cluster that keeps workloads apart. OpenShift also calls it a namespace. |
| Prompt injection | Text placed in data the model reads, such as a log line, written to change what the model does. |
| Proposal | What the model asks for next: either run one command, or finish with a summary. |
| Query | A question you ask a data store, written in a query language, such as a log search. |
| RBAC | Role-based access control: the cluster's built-in way to say which identity may do which action. |
| Read-only command | A command that looks at the system and cannot change it. |
| ReplicaSet | The object a deployment creates to keep the right number of copies of a program (pods) running. A triage often needs to read it. |
| Role | A list of actions a user or program may take on named kinds of objects. |
| Rule | A written condition that a tool checks. |
| Runner | The program or container that carries out the steps of a pipeline. |
| Secret | A cluster object that holds a small sensitive value, such as a password or a token. |
| Service account | An identity for a program instead of a person. |
| Shell | The program that reads the commands you type and runs them. It can chain and expand commands, which is why the loop never uses one. |
| Step cap | A fixed limit on how many steps one run may take. |
| Stop switch | A way for a person to end a run at once. Here it is a file whose existence stops the loop. |
| Stub model service | A small program that stands in for a model and returns a fixed answer for each request id. It never reads the text it is sent. |
| Timestamp | The date and time recorded for an event. |
| TSV | Tab-separated values: a table written as text, with a tab between columns. |
| URL | A web address, such as https://example.com/page. |
| UTC | Universal time, the same clock everywhere, so records from different places line up. |
| Verb | The word after oc that says what to do, such as get, describe or logs. |
| View role | A built-in role that lets an identity read most objects in a project but not secrets, and change nothing. |
| Wrapper | The program around the model that decides whether each proposed step may run. The model never runs anything itself. |
| YAML | A plain-text format for settings: lines of name: value, with indentation to show what belongs to what. |

</details>
