"""Build the aside "How to Read the Tools": one page per tool, each with a diagram.

Usage: python read_guides.py   ->  modules/Reading-Guides.docx and .md (diagrams in modules/img/)
Not part of any module. The pages teach reading, not writing.
"""

from __future__ import annotations

from docx.enum.text import WD_BREAK
from docx.shared import Inches, Pt

import module_diagrams as md
from doc_builder import DocBuilder

OUT_DIR = md.IMG_DIR.parent
STEM = "Reading-Guides"
MAX_IMG_WIDTH = 4.0
LANG = {"terraform": "hcl", "yaml": "yaml", "ansible": "yaml", "jq": "bash"}


def _zone(zid: str, label: str, kind: str = "group") -> dict:
    return {"id": zid, "label": label, "kind": kind}


def _node(nid: str, title: str, sub: str, zone: str, kind: str = "neutral", icon: str | None = None) -> dict:
    node = {"id": nid, "title": title, "sub": sub, "zone": zone, "kind": kind}
    if icon:
        node["icon"] = icon
    return node


def _edge(a: str, b: str, label: str, n: int | None = None, kind: str = "neutral") -> dict:
    edge = {"a": a, "b": b, "label": label, "kind": kind}
    if n:
        edge["n"] = n
    return edge


def _diagram(did: str, title: str, zones: list, nodes: list, edges: list, rankdir: str = "LR") -> dict:
    return {"id": did, "title": title, "caption": "", "reading": [], "rankdir": rankdir, "zones": zones, "nodes": nodes, "edges": edges}


GUIDES = [
    {
        "name": "Terraform",
        "file": "terraform",
        "intro": "Terraform files describe the objects you want. Terraform compares the files with what exists and changes only the difference.",
        "moves": [
            "Find the blocks: each block starts with a word such as resource, variable, output or data, then names in quotes, then braces.",
            "Read a resource block as 'make one object of this type, with these settings'. The first quoted name is the type; the second is your label for it.",
            "Follow the references: var.name is an input, and type.label.attribute is a setting taken from another object.",
            "Read a plan before anything else. A plus means create, a minus means destroy, a tilde means change in place, and minus-plus means replace.",
            "Remember the state file: it records what Terraform built, so a plan is a comparison of your files, the state and the real objects.",
        ],
        "code": 'variable "name" {\n  type = string\n}\n\nresource "kubernetes_namespace_v1" "lab" {\n  metadata {\n    name = var.name\n  }\n}',
        "notes": [
            "variable: an input with a type; a value comes from a file, the command line or a default.",
            "resource: one object; the settings inside the braces are what Terraform makes true.",
            "var.name: the input is used as the namespace name.",
        ],
        "commands": "terraform init: downloads the providers the files need. terraform plan: shows the difference and changes nothing. terraform apply: makes the difference real and updates the state.",
        "seen": "IAC-1, IAC-2 and IAC-3 run and review Terraform.",
        "diagram": _diagram(
            "terraform",
            "Terraform compares three things before it changes anything",
            [_zone("you", "Your files"), _zone("tf", "Terraform"), _zone("world", "The real system")],
            [
                _node("files", "Terraform files", "The .tf files you read", "you", icon="brands/terraform"),
                _node("state", "State file", "What Terraform built last time", "tf"),
                _node("plan", "Plan", "The difference, nothing changed yet", "tf", "warn"),
                _node("apply", "Apply", "Makes the difference real", "tf", "ok"),
                _node("real", "Real objects", "Namespaces, quotas, policies", "world"),
            ],
            [
                _edge("files", "plan", "Wanted", 1),
                _edge("state", "plan", "Known", 2),
                _edge("real", "plan", "Actual", 3),
                _edge("plan", "apply", "You approve", 4),
                _edge("apply", "real", "Changes", 5, "ok"),
            ],
        ),
    },
    {
        "name": "Ansible",
        "file": "ansible",
        "intro": "An Ansible playbook is a list of tasks run in order. Each task asks a module to make one thing true and reports whether it had to change anything.",
        "moves": [
            "Read the play first: hosts says where it runs, and tasks lists what it does, top to bottom.",
            "Read each task as its name, then its module, then the module's settings. The name says the intent in plain words.",
            "Look for conditions and variables: when skips a task, and double braces mark a value filled in at run time.",
            "Read the recap: ok means already true, changed means Ansible made it true, and failed means stop and read the message.",
            "Use check mode to preview: --check shows what would change without changing it, and ansible-lint reads the file for risky or sloppy tasks.",
        ],
        "code": "- name: Baseline for the lab project\n  hosts: localhost\n  tasks:\n    - name: Ensure the service account exists\n      kubernetes.core.k8s:\n        state: present\n        kind: ServiceAccount\n        name: lab-runner\n        namespace: iac-lab\n      when: create_account | default(true)",
        "notes": [
            "name (play): what the whole play is for.",
            "hosts: where the tasks run; localhost means the machine running the playbook.",
            "kubernetes.core.k8s: the module; it does the work and reports ok or changed.",
            "state, kind, name, namespace: the settings that describe the wanted result.",
            "when: the task runs only if this is true.",
        ],
        "commands": "ansible-playbook file.yml runs the playbook. Add --check to preview. ansible-lint file.yml reviews it without running it.",
        "seen": "IAC-1 and IAC-3 run an Ansible playbook, and IAC-3 lints it.",
        "diagram": _diagram(
            "ansible",
            "A playbook runs tasks in order and reports each result",
            [_zone("file", "Your playbook"), _zone("run", "When it runs"), _zone("target", "The target")],
            [
                _node("play", "Play", "Where it runs and the task list", "file", icon="brands/ansible"),
                _node("task", "Task", "A name and one module", "file"),
                _node("module", "Module", "Checks, then changes only if needed", "run"),
                _node("target", "Target system", "A cluster, a server or a file", "target"),
                _node("ok", "ok", "Already true, nothing changed", "run", "ok"),
                _node("changed", "changed", "Made it true", "run", "warn"),
            ],
            [
                _edge("play", "task", "Each in order", 1),
                _edge("task", "module", "Calls", 2),
                _edge("module", "target", "Asks", 3),
                _edge("target", "ok", "Matches", 4, "ok"),
                _edge("target", "changed", "Differs", 5, "warn"),
            ],
        ),
    },
    {
        "name": "Kubernetes and OpenShift YAML",
        "file": "yaml",
        "intro": "A manifest states what should exist. The cluster keeps comparing the file's spec with what is running and works to make them match.",
        "moves": [
            "Read the first two lines: apiVersion and kind tell you what type of object it is.",
            "Read metadata next: name, namespace and labels say which object it is and where it lives.",
            "Read spec as the wanted state. Everything the cluster should make true is under it.",
            "Follow the indentation: two spaces deeper means 'belongs to the line above', and a dash starts one item in a list.",
            "Read status, if you see it, as the cluster's own report. You never write status; the cluster fills it in.",
        ],
        "code": "apiVersion: v1\nkind: ResourceQuota\nmetadata:\n  name: lab-quota\n  namespace: iac-lab\nspec:\n  hard:\n    pods: \"10\"\n    requests.cpu: \"2\"",
        "notes": [
            "apiVersion and kind: the object type, here a resource quota.",
            "metadata: the name and the project it belongs to.",
            "spec.hard: the wanted limits; the cluster refuses anything above them.",
        ],
        "commands": "oc apply -f file.yaml sends the file. oc get <kind> <name> -o yaml shows the live object, including status.",
        "seen": "Nearly every module applies or reads a manifest.",
        "diagram": _diagram(
            "yaml",
            "The cluster keeps making the real object match your spec",
            [_zone("file", "Your file"), _zone("cluster", "The cluster")],
            [
                _node("manifest", "Manifest", "kind, metadata and spec", "file", icon="brands/kubernetes"),
                _node("api", "API server", "Stores the wanted state", "cluster"),
                _node("ctl", "Controller", "Compares wanted with running", "cluster"),
                _node("obj", "Running object", "Pods, policies, quotas", "cluster", "ok"),
                _node("status", "Status", "The cluster's own report", "cluster", "warn"),
            ],
            [
                _edge("manifest", "api", "oc apply", 1),
                _edge("api", "ctl", "Spec", 2),
                _edge("ctl", "obj", "Makes match", 3, "ok"),
                _edge("obj", "status", "Reports", 4, "warn"),
            ],
        ),
    },
    {
        "name": "Python",
        "file": "python",
        "intro": "A Python script runs from the top. Reading it is following where data comes in, what each function does to it and what comes out.",
        "moves": [
            "Start at the bottom: the last lines, often under if __name__ == \"__main__\":, show what runs first.",
            "Read the imports at the top: they list the tools the script uses, such as json, subprocess or yaml.",
            "Read each def line as a name and its inputs; the first string inside, if any, says what it is for.",
            "Follow indentation: everything indented under if, for, try or def belongs to that line.",
            "Read try and except as 'attempt this, and say what to do if it fails'; a good script reports the failure instead of hiding it.",
        ],
        "code": "import json\nimport subprocess\n\ndef get_quota(namespace):\n    out = subprocess.run([\"oc\", \"get\", \"quota\", \"-n\", namespace, \"-o\", \"json\"],\n                         capture_output=True, text=True, check=True)\n    return json.loads(out.stdout)\n\nif __name__ == \"__main__\":\n    print(get_quota(\"iac-lab\")[\"items\"][0][\"metadata\"][\"name\"])",
        "notes": [
            "import: the script uses JSON parsing and can run other commands.",
            "def get_quota(namespace): a function; the namespace is its input.",
            "subprocess.run: runs the oc command and captures its output; check=True raises an error if the command fails.",
            "json.loads: turns the text output into data the script can index.",
            "if __name__ == \"__main__\": the script starts here when run directly.",
        ],
        "commands": "python3 script.py runs the script. python3 -m py_compile script.py checks the syntax without running it.",
        "seen": "Short Python scripts appear in GRC, SDR, VM, CPS, AID and IAC modules.",
        "diagram": _diagram(
            "python",
            "Data goes in, functions change it, a result comes out",
            [_zone("script", "The script"), _zone("outside", "Outside the script")],
            [
                _node("input", "Input", "A file, a command or an argument", "outside"),
                _node("main", "Main section", "The bottom lines that start the run", "script", icon="brands/python"),
                _node("func", "Functions", "Each def does one job", "script"),
                _node("check", "try and except", "Reports a failure", "script", "warn"),
                _node("output", "Output", "A printed line or a file", "outside", "ok"),
            ],
            [
                _edge("input", "main", "Read", 1),
                _edge("main", "func", "Calls", 2),
                _edge("func", "check", "May fail", 3, "warn"),
                _edge("func", "output", "Returns", 4, "ok"),
            ],
        ),
    },
    {
        "name": "jq",
        "file": "jq",
        "intro": "jq reads JSON and keeps only the parts you ask for. A jq filter is a chain of small steps separated by pipes.",
        "moves": [
            "Read left to right: each | hands the result of one step to the next.",
            "Read .name as 'the field called name', and .items[] as 'every entry in the list called items'.",
            "Read select(condition) as 'keep the entries where the condition is true, drop the others'.",
            "Read braces as a new, smaller object: {name: .metadata.name} builds one with only that field.",
            "Check the flags: -r prints plain text without quotes, -c prints each result on one line, and -e makes jq exit with an error when the last result is false or null.",
        ],
        "code": "oc get pods -o json | jq -r '.items[] | select(.status.phase != \"Running\") | .metadata.name'",
        "notes": [
            ".items[]: take each pod from the list.",
            "select(.status.phase != \"Running\"): keep only pods whose phase is not Running.",
            ".metadata.name: print only the pod's name.",
            "-r: print the names as plain text.",
        ],
        "commands": "jq . file.json pretty-prints a file. Add a filter in single quotes to narrow it, and build it one pipe at a time.",
        "seen": "Evidence, scan and policy checks in most modules use jq.",
        "diagram": _diagram(
            "jq",
            "A jq filter narrows the JSON one pipe at a time",
            [_zone("data", "The data"), _zone("filter", "The jq filter")],
            [
                _node("json", "JSON", "All pods with every field", "data", icon="brands/json"),
                _node("each", ".items[]", "One entry at a time", "filter"),
                _node("keep", "select(...)", "Keep entries that match", "filter", "warn"),
                _node("field", ".metadata.name", "Pick one field", "filter"),
                _node("out", "Result", "Only the names you asked for", "data", "ok"),
            ],
            [
                _edge("json", "each", "Input", 1),
                _edge("each", "keep", "Pipe", 2),
                _edge("keep", "field", "Pipe", 3),
                _edge("field", "out", "Print", 4, "ok"),
            ],
        ),
    },
    {
        "name": "Bash",
        "file": "bash",
        "intro": "A shell command is a program name followed by its options. Reading a line means splitting it into commands and following where the output goes.",
        "moves": [
            "Find the command: the first word is the program, and the words after it are its arguments.",
            "Split on | : each side is a separate command, and the left side's output feeds the right side.",
            "Spot redirects: > writes output to a file, >> adds to a file, and 2>&1 sends error messages along with normal output.",
            "Read $VARIABLE as a value saved earlier and $(command) as the output of another command, inserted here.",
            "Watch the joiners: && runs the next command only if this one succeeds, and a backslash at the end of a line continues the command on the next line.",
        ],
        "code": "NS=iac-lab\noc get pods -n \"$NS\" -o name \\\n  | sort \\\n  | tee pods.txt\necho \"exit status: $?\"",
        "notes": [
            "NS=iac-lab: saves a value; later lines read it as $NS.",
            "oc get pods ... -o name: the first command, listing pod names.",
            "| sort: the left output is sorted.",
            "| tee pods.txt: shows the result and saves it in the file.",
            "$?: the exit status of the last command in the pipeline, here tee and not oc; 0 means success.",
        ],
        "commands": "bash -n script.sh checks the syntax without running it. echo $? right after a command shows whether it succeeded.",
        "seen": "Every module's steps run Bash commands in the lab shell.",
        "diagram": _diagram(
            "bash",
            "A pipeline passes output along and may save it",
            [_zone("line", "One command line"), _zone("out", "Where results go")],
            [
                _node("var", "Variable", "NS holds a saved value", "line", icon="brands/gnubash"),
                _node("cmd1", "First command", "Produces text", "line"),
                _node("cmd2", "Next command", "Reads that text through |", "line"),
                _node("screen", "Screen", "What you see", "out", "ok"),
                _node("file", "File", "Saved with > or tee", "out", "ok"),
            ],
            [
                _edge("var", "cmd1", "Fills in", 1),
                _edge("cmd1", "cmd2", "Pipe", 2),
                _edge("cmd2", "screen", "Prints", 3, "ok"),
                _edge("cmd2", "file", "Redirects", 4, "ok"),
            ],
        ),
    },
]


def _page_break(b: DocBuilder) -> None:
    b.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    b._md("---\n")


def build() -> None:
    b = DocBuilder()
    for section in b.doc.sections:
        section.top_margin = section.bottom_margin = Inches(0.5)
        section.left_margin = section.right_margin = Inches(0.8)
    b.doc.styles["Normal"].font.size = Pt(10)
    b.doc.styles["List Bullet"].font.size = Pt(10)
    b.title("How to Read the Tools")
    b.para("An aside for the training, not a module. Each page covers one tool: how to read a file, and how it works. You will not write these tools here; you will recognize them.")
    b.bullet("Terraform, Ansible, Kubernetes YAML, Python, jq and Bash each get one page.")
    b.bullet("Each page has five moves for reading, a small example with the lines explained, the commands that run it, and a picture of how it works.")
    for guide in GUIDES:
        b.h1(guide["name"])
        b.doc.paragraphs[-1].paragraph_format.page_break_before = True
        b._md("---")
        b.para(guide["intro"])
        b.h3("How to read it")
        for move in guide["moves"]:
            b.bullet(move)
        b.h3("A small example")
        b.code(guide["code"], LANG.get(guide["file"], guide["file"]))
        for note in guide["notes"]:
            b.lead_bullet(note)
        b.h3("How it works")
        diagram = guide["diagram"]
        png = md.IMG_DIR / f"READ-{guide['file']}.png"
        md._draw(diagram, None, png, f"READ {guide['file']}")
        b.image(png, diagram["title"], "", width_in=min(md._width_for(png), MAX_IMG_WIDTH))
        b.para(f"{guide['commands']} Where you meet it: {guide['seen']}")
    b.save(OUT_DIR, STEM)
    print(f"{STEM}.docx, {STEM}.md")


if __name__ == "__main__":
    build()
