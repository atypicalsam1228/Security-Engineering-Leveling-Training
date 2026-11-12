"""Build the "Tool Walkthrough" guide (.docx + .md) from one content list.

Usage: python build_tool_walkthrough.py
Writes into ../modules/: Tool-Walkthrough.docx and Tool-Walkthrough.md. Screenshots come from ../modules/img/WALK-*.png
(real lab pages, redacted; unredacted originals stay outside the project).
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt

HERE = Path(__file__).resolve().parent
MODULES = HERE.parent / "modules"
IMG = MODULES / "img"
STEM = "Tool-Walkthrough"

TITLE = "Tool Walkthrough: finding your way around the lab"
INTRO = (
    "This guide shows each tool you will open during the training, what it is for, and the few pages a security engineer "
    "comes back to most. Every picture is a real page from the lab. The lab prints the web address and the sign-in name for "
    "each tool when it starts; the sign-in values are saved as lab variables, so you never copy a password into a file."
)
HOW_TO_READ = [
    "Each tool has a short 'what it is for' line, then the pages to learn, in the order you will meet them.",
    "Under each picture, 'Look at' says what to read on the page, and 'Why it matters' says what a security engineer does with it.",
    "The modules that use the tool are listed so you know where to practise.",
]

# Each tool: name, role, modules, pages = [(heading, image, look_at list, why)]
TOOLS = [
    {
        "name": "OpenShift web console",
        "role": "The control panel for the cluster. You use it to see what is running, what failed, and what the platform is warning about.",
        "modules": "Almost every module points at it",
        "pages": [
            ("Overview", "WALK-console-overview.png",
             ["The Status box: Cluster, Control Plane, Operators. Green ticks mean healthy.",
              "The left menu: Workloads, Networking, Observe and Administration hold most of what you need."],
             "Start here. A red item on the Overview tells you where to look before you run any command."),
            ("Nodes", "WALK-console-nodes.png",
             ["Status says Ready when the machine is healthy.", "Pods, Memory and CPU show how full the machine is."],
             "A full node is the first thing to rule out when pods are slow or fail to start."),
            ("Pods in a project", "WALK-console-pods.png",
             ["The project picker at the top (here: siem). Pods only show for the project you chose.",
              "Status and Restarts. Running with many restarts means something keeps crashing.",
              "Memory and CPU per pod."],
             "Pods are where your workloads live. Restarts and status are the quickest health check, and they match what the oc get pods command prints."),
            ("Events", "WALK-console-events.png",
             ["Newest first. Yellow rows are warnings.", "Each row names the object and the project it belongs to."],
             "Events say why something failed, for example a task that exited with an error. They are the first thing to read when a pipeline run fails."),
            ("Pipelines and runs", "WALK-console-pipelines.png",
             ["Pipelines are the definitions. Open Pipelines, then PipelineRuns to see each run."],
             "This is where a build or a security gate runs. Modules on scanning, signing and evidence use it."),
            ("PipelineRuns", "WALK-console-pipelineruns.png",
             ["Succeeded True or False, and the Reason. Failed means a task stopped the run.",
              "Open one run to see its tasks and logs."],
             "A failed gate is a result, not a mistake. Read which task failed and why before you rerun."),
            ("Kyverno policies", "WALK-console-clusterpolicies.png",
             ["READY True means the policy is loaded.", "ADMISSION true means it can refuse a new object. BACKGROUND true means it also checks what already exists."],
             "Policies are the guardrails. This page shows which rules are on, and whether they refuse or only record."),
            ("Alerting", "WALK-console-alerting.png",
             ["Filters at the top: state and source. Platform alerts come from the cluster itself.",
              "Firing means the condition is true right now."],
             "Alerts tell you something needs attention. Watchdog firing is normal: it proves alerting works."),
        ],
    },
    {
        "name": "Grafana (with Loki)",
        "role": "Search logs and set up alerts. Loki stores the logs; Grafana is how you search them and turn a search into an alert.",
        "modules": "SDR-2 to SDR-5, AID-3 to AID-5, ENG-0",
        "pages": [
            ("Explore", "WALK-grafana-explore.png",
             ["The data source at the top says Loki.", "Pick a label, then a value, to narrow the logs. Use Code to type a query yourself.",
              "Set the time range with the clock button."],
             "This is the search box for every log. Investigations start here: who did what, and when."),
            ("Alert rules", "WALK-grafana-alert-rules.png",
             ["Rules are grouped in a folder (here siem-detect).", "State filters: Firing, Normal, Pending."],
             "Each rule is a saved search with a threshold. This is where detections live and where you check that they are healthy."),
            ("Contact points", "WALK-grafana-contact-points.png",
             ["A contact point is where an alert goes. Here, mattermost.", "Last delivery attempt shows whether the message was sent."],
             "An alert nobody receives is the same as no alert. Check delivery here first when a message does not arrive."),
        ],
    },
    {
        "name": "Mattermost",
        "role": "Team chat. Alerts from Grafana arrive in a channel, the way a real security team receives them.",
        "modules": "SDR-2, SDR-5, AID-2, ENG-0",
        "pages": [
            ("The alert channel", "WALK-mattermost-alert.png",
             ["The title shows FIRING, the rule name and the severity.", "Labels name the control, the folder and where the rule came from.",
              "Source opens the rule. Silence mutes it for a while."],
             "This is what you triage. Read the labels first: they tell you what fired and who owns the rule."),
        ],
    },
    {
        "name": "Gitea",
        "role": "The lab's git server. Detections, pipelines and infrastructure files live here as code, and changes go through pull requests.",
        "modules": "ENG-0, GRC-3, SDR-5, AID-3, IAC-2, VM-2 to VM-5",
        "pages": [
            ("Dashboard", "WALK-gitea-dashboard.png",
             ["Repositories on the right. The feed on the left shows recent pushes and pull requests."],
             "The feed is an audit trail of who changed what, and when."),
            ("Pull requests", "WALK-gitea-pullrequests.png",
             ["Open and Closed counts. A green tick means checks passed; a red cross means they failed.", "main on the left, the branch on the right."],
             "A pull request is where a change is reviewed and gated before it reaches main. A closed, failed one is a gate doing its job."),
        ],
    },
    {
        "name": "Keycloak",
        "role": "Sign-in and identity. It decides who users are and which applications they may use.",
        "modules": "SDR-2 to SDR-4",
        "pages": [
            ("Home and sign-in", "WALK-keycloak-home.png",
             ["The realm name at the top left. A realm is one separate set of users and clients.", "The menu: Clients, Users, Sessions, Events."],
             "Check which realm you are in before you read or change anything."),
            ("Clients", "WALK-keycloak-clients.png",
             ["A client is an application that asks Keycloak to sign users in."],
             "Every client is a door into the system. Know which ones exist and which you did not expect."),
            ("Users", "WALK-keycloak-users.png",
             ["The user list and the Add user button."],
             "Accounts are what an attacker wants. Review who exists, and look for accounts nobody can explain."),
            ("Events", "WALK-keycloak-events.png",
             ["The banner says saving user events is turned off. No events are kept until you turn it on."],
             "Sign-in events are the raw material for detections. Turn them on, or you cannot investigate a bad sign-in."),
        ],
    },
    {
        "name": "Argo CD",
        "role": "Keeps the cluster matching what is in git. If someone changes the cluster by hand, Argo CD shows the difference.",
        "modules": "GRC-5",
        "pages": [
            ("Applications", "WALK-argocd-applications.png",
             ["The page is empty until an application is added in GRC-5. Once there are applications, each tile shows its sync state and health.", "Sync apps and Refresh apps compare git with the cluster."],
             "Out of sync means the cluster no longer matches git. That is drift, and it is evidence a change happened."),
        ],
    },
    {
        "name": "AWS console",
        "role": "The cloud account the lab runs in. You mostly use the command line, but the console is the quickest way to see what exists.",
        "modules": "ENG-0 setup, CPS-4",
        "pages": [
            ("EC2 instances", "WALK-aws-ec2-instances.png",
             ["Instance state: Running costs money. The cluster machine and the bastion are listed.", "Instance type shows the size."],
             "Anything running is billed. Check here that nothing is left on after the lab is shut down."),
            ("S3 buckets", "WALK-aws-s3-buckets.png",
             ["Names starting eng-sam are the lab's logs, artifacts and state."],
             "Buckets hold logs and evidence. Know which hold what, and who can read them."),
            ("KMS keys", "WALK-aws-kms-keys.png",
             ["Status Enabled or Pending deletion.", "Key usage says what a key is for."],
             "Encryption keys protect the data. A key pending deletion is a key you can no longer use."),
        ],
    },
    {
        "name": "Trivy (command line)",
        "role": "Scans a container image for known vulnerabilities. It has no web page: you run it in the lab shell, and the Trivy operator also scans what runs in the cluster and saves the results as reports.",
        "modules": "ENG-0, GRC-4, VM-2 to VM-5",
        "pages": [
            ("Scan an image", "WALK-trivy1.png",
             ["Total at the bottom: how many findings, split by severity.", "--severity HIGH,CRITICAL hides the low and medium noise."],
             "A scan gives a count to act on. A gate in a pipeline blocks a release when the count is not zero."),
            ("Count by severity, and fixable only", "WALK-trivy2.png",
             ["The first block groups findings by severity.", "The last number counts only findings that have a fix, using --ignore-unfixed."],
             "Fixable findings are the ones you can act on today. Unfixable ones need a decision, not a patch."),
            ("What the operator found in the cluster", "WALK-trivy3.png",
             ["One report per running workload, with Critical, High and Medium counts.", "A row of 0 0 0 is a clean image."],
             "Reports show what is vulnerable right now in the cluster, without scanning anything by hand."),
        ],
    },
]

HABITS = [
    "Start from the question, not the tool. 'Did anything change?' goes to Gitea and Argo CD. 'Who did this?' goes to Grafana Explore. 'Is it healthy?' goes to the console.",
    "Pick the project or realm first. Most empty pages are the wrong project, not missing data.",
    "Read Events and logs before you retry a failed run.",
    "Use the web page to look, and the command line to prove it. Both should show the same thing.",
    "Never paste a password into a note or a message. Read it from the lab variable and type it where it is asked.",
]


def md_text() -> str:
    lines = [f"# {TITLE}", "", INTRO, "", "## How to read this guide", ""]
    lines += [f"- {x}" for x in HOW_TO_READ] + [""]
    for tool in TOOLS:
        lines += [f"## {tool['name']}", "", f"**What it is for.** {tool['role']}", "", f"**Used in:** {tool['modules']}", ""]
        for heading, image, look, why in tool["pages"]:
            lines += [f"### {heading}", "", f"![{heading}](img/{image})", "", "**Look at:**", ""]
            lines += [f"- {x}" for x in look] + ["", f"**Why it matters.** {why}", ""]
    lines += ["## Habits that carry across every tool", ""] + [f"- {x}" for x in HABITS] + [""]
    return "\n".join(lines)


def build_docx(path: Path) -> None:
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    doc.add_heading(TITLE, 0)
    doc.add_paragraph(INTRO)
    doc.add_heading("How to read this guide", 1)
    for item in HOW_TO_READ:
        doc.add_paragraph(item, style="List Bullet")
    for tool in TOOLS:
        doc.add_heading(tool["name"], 1)
        para = doc.add_paragraph()
        para.add_run("What it is for. ").bold = True
        para.add_run(tool["role"])
        para = doc.add_paragraph()
        para.add_run("Used in: ").bold = True
        para.add_run(tool["modules"])
        for heading, image, look, why in tool["pages"]:
            doc.add_heading(heading, 2)
            picture = doc.add_picture(str(IMG / image), width=Inches(6.0))
            picture._inline.docPr.set("descr", f"{tool['name']}: {heading}")
            doc.paragraphs[-1].paragraph_format.keep_with_next = True
            para = doc.add_paragraph()
            para.paragraph_format.keep_with_next = True
            para.add_run("Look at:").bold = True
            for item in look:
                doc.add_paragraph(item, style="List Bullet")
            para = doc.add_paragraph()
            para.add_run("Why it matters. ").bold = True
            para.add_run(why)
    doc.add_heading("Habits that carry across every tool", 1)
    for item in HABITS:
        doc.add_paragraph(item, style="List Bullet")
    doc.save(str(path))


def main() -> None:
    missing = [p[1] for t in TOOLS for p in t["pages"] if not (IMG / p[1]).exists()]
    if missing:
        raise SystemExit(f"missing images: {missing}")
    (MODULES / f"{STEM}.md").write_text(md_text(), encoding="utf-8", newline="\n")
    build_docx(MODULES / f"{STEM}.docx")
    print(f"{STEM}.docx, {STEM}.md")


if __name__ == "__main__":
    main()
