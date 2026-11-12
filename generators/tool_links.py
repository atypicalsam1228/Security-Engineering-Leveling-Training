"""Official overview links and lab-use blurbs for the tools each module uses.

Links were fetched and confirmed when written. Red Hat links point at the OpenShift 4.22 docs.
"""

import re

B = "https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/"
TOOLS = {
    "OpenShift Container Platform": (B + "overview/ocp-overview", "A Kubernetes container platform for running and managing containerized applications."),
    "oc": (B + "cli_tools/openshift-cli-oc", "The OpenShift command-line tool for creating and managing applications and projects from a terminal."),
    "NetworkPolicy": (B + "network_security/network-policy", "Rules for which pods may talk to which. Once a policy selects a pod, it accepts only what the policies allow."),
    "Service Mesh 3": ("https://docs.redhat.com/en/documentation/red_hat_openshift_service_mesh/3.4/html/about/ossm-about-openshift-service-mesh", "An Istio-based layer that adds encrypted service identity, traffic policy and telemetry between components without code changes."),
    "Compliance Operator": (B + "security_and_compliance/compliance-operator", "Checks cluster configuration against standards and benchmarks. It is not an auditor."),
    "OpenShift Pipelines (Tekton)": (B + "pipelines/index", "Kubernetes-native CI/CD built on Tekton."),
    "tkn": (B + "cli_tools/pipelines-cli-tkn", "Command-line tool for managing pipelines, runs and tasks."),
    "AWS CLI": ("https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html", "Runs AWS actions from a shell instead of the browser console."),
    "Grafana Loki": ("https://grafana.com/docs/loki/latest/", "Log storage that indexes only labels and keeps compressed log data in object storage."),
    "Grafana": ("https://grafana.com/docs/grafana/latest/", "Dashboards, log browsing and alerting."),
    "Grafana Alloy": ("https://grafana.com/docs/alloy/latest/", "A collector that gathers, processes and ships logs and metrics."),
    "LogQL": ("https://grafana.com/docs/loki/latest/query/", "Loki's query language for searching and filtering logs."),
    "Kyverno": ("https://kyverno.io/docs/", "A policy engine that checks and enforces rules on Kubernetes resources."),
    "Trivy": ("https://trivy.dev/", "Scans images, code and clusters for known flaws and misconfigurations."),
    "Cosign": ("https://docs.sigstore.dev/cosign/signing/overview/", "Signs container images and verifies the signature."),
    "Gitea": ("https://docs.gitea.com/", "A lightweight self-hosted git server."),
    "Falco": ("https://falco.org/docs/", "Watches system calls and alerts in real time when a rule detects suspicious behavior."),
    "Mattermost": ("https://docs.mattermost.com/developers/integrate/webhooks/incoming", "Open-source team chat. Incoming webhooks let tools post messages into a channel."),
    "jq": ("https://jqlang.org/", "Command-line JSON processor."),
    "curl": ("https://curl.se/docs/manpage.html", "Command-line tool for transferring data over URLs, used here to call web endpoints."),
    "OpenSSL": ("https://docs.openssl.org/master/man1/openssl/", "Command-line tool for keys, certificates and testing TLS connections."),
    "Git": ("https://git-scm.com/about", "Version control that stores repository history."),
    "Python 3": ("https://docs.python.org/3/tutorial/introduction.html", "General-purpose language, used here for small helper scripts."),
    "lab shell": ("https://docs.podman.io/en/latest/markdown/podman-run.1.html", "The lab's prebuilt tools container, started with the lab shell command. It has oc, git, jq, curl and the other tools installed, so commands behave the same on every laptop. (No vendor page exists for it; the link is the Podman run reference.)"),
    "bash": ("https://www.gnu.org/software/bash/manual/bash.html", "The command shell that reads what you type and runs scripts."),
    "grep": ("https://www.gnu.org/software/grep/manual/grep.html", "Searches text or files for lines that match a pattern."),
    "Stub model service": ("https://kubernetes.io/docs/concepts/services-networking/service/", "A small stand-in for an AI model that the lab runs in the cluster. It gives fixed, scripted answers, so no model account or key is needed. (No vendor page exists for it; the link explains the Kubernetes Service it runs as.)"),
    "Kubernetes RBAC": ("https://kubernetes.io/docs/reference/access-authn-authz/rbac/", "Roles list what an identity may do, and bindings give those roles to users or service accounts."),
    "Pod security admission": ("https://kubernetes.io/docs/concepts/security/pod-security-admission/", "A built-in check that refuses or warns about new pods that break a chosen security level."),
    "Kubernetes Secrets": ("https://kubernetes.io/docs/concepts/configuration/secret/", "Objects that hold small sensitive values, such as a password, apart from the workload's settings."),
    "Kyverno policy reports": ("https://kyverno.io/docs/policy-reports/", "Kyverno records pass and fail results for existing resources as report objects in the cluster."),
    "Grafana alerting": ("https://grafana.com/docs/grafana/latest/alerting/fundamentals/", "Rules that run a query on a schedule and send a notification when the result crosses a threshold."),
    "Terraform": ("https://developer.hashicorp.com/terraform/intro", "Builds and changes infrastructure from files, and compares the files with what exists."),
    "Ansible": ("https://docs.ansible.com/ansible/latest/getting_started/introduction.html", "Runs playbooks, which are lists of tasks that put a system into a stated state."),
    "ansible-lint": ("https://ansible.readthedocs.io/projects/lint/", "Checks Ansible playbooks for style problems and risky patterns."),
    "Project request template": (B + "building_applications/projects", "The template OpenShift uses to build every new project, so it can include a quota and other defaults."),
}
_MODULES: list = []

_CURATED = {mid: dict(items) for mid, _title, items in _MODULES}

OCP, KY, TR, TK, LK, GR, MM, GT, NP, PY, OC = (
    "OpenShift Container Platform", "Kyverno", "Trivy", "OpenShift Pipelines (Tekton)", "Grafana Loki", "Grafana",
    "Mattermost", "Gitea", "NetworkPolicy", "Python 3", "oc",
)

# Module-specific "Used in this lab" text, keyed by module id then tool key. These win over _CURATED and _SHARED.
_USE = {
    "ENG-0": {
        "lab shell": "You open it, make a folder, read and write small files, and run every other command in this module from it.",
        OC: "You run read-only oc commands, read the YAML they return and read an error message.",
        "Git": "You clone the sandbox repository, edit a file, commit and push the change.",
        GT: "The in-lab git server that holds the sandbox repository you clone and push to.",
        "curl": "Calls the Gitea web interface to read the latest commit and confirm your push arrived.",
        "jq": "Filters JSON replies so you read one field instead of a long reply.",
    },
    "ENG-1": {
        "lab shell": "You run every command from it, and use oc exec to run curl inside a pod from it.",
        OC: "You read pod and Service addresses, read the cluster address ranges, create a Route and run commands inside the client pod.",
        "curl": "Makes every call, from inside the client pod, and its exit code names the kind of failure.",
        "OpenSSL": "Connects to the router like a browser and prints the subject, issuer and dates of the certificate.",
        PY: "Checks with a few lines whether an address falls inside an address range.",
        "jq": "Picks single fields, such as the target port, out of long replies.",
        NP: "A deny policy and an allow policy that you read to find why the call fails, then fix.",
    },
    "GRC-2": {
        OCP: "The cluster the evidence collector asks questions of, using only read commands.",
        TK: "Runs the same collector as a pipeline with no person at the keyboard.",
        KY: "One check in the collector lists the Kyverno cluster policies.",
        OC: "The collector is a set of oc get commands. You also use oc to fetch it from its config map.",
        "tkn": "Starts the evidence pipeline and follows its run.",
        "jq": "Reads the evidence file the collector writes and picks out single checks.",
        PY: "Runs collect_facts.py, the collector, and saves its output in a file.",
    },
    "VM-2": {
        OCP: "The cluster that holds the hand-off script and the live legacy-web workload you scan.",
        TR: "Runs the four scans: an image, a repository checkout, the cluster configuration and an SBOM.",
        GT: "Holds the vm-app repository that you clone and scan.",
        OC: "Fetches the supplied files and exports the live legacy-web Deployment as YAML for scanning.",
        "Git": "Clones the vm-app repository from Gitea.",
        "jq": "Counts findings in the scan reports to check the hand-off numbers.",
    },
    "SDR-2": {
        GR: "Where the alerts the runbook covers are shown.",
        LK: "Holds the audit and runtime records the supplied search commands read.",
        MM: "Where the alerts arrive and where your triage is reported.",
        OCP: "The cluster whose audit records and pods the four alerts describe.",
        OC: "Extracts the runbook from its ConfigMap and checks the pods involved.",
        "curl": "Calls the Loki and Mattermost web interfaces from the shell.",
        "jq": "Picks fields out of log records and the triage output.",
        "Python 3": "Runs triage.py for each alert type (privilege, signin, shell, path, gaps).",
    },
    "CPS-2": {
        OCP: "The cluster and the workload you harden with a supplied baseline.",
        "Compliance Operator": "Runs the supplied scan profile and reports a status for each rule.",
        "Pod security admission": "You label the namespace so a new pod that breaks the restricted level is refused, then try a bad pod.",
        OC: "Applies the labels, patch, quota and default-deny rule, then reads the scan results.",
        "jq": "Reads workload settings and picks fields out of the scan results.",
    },
    "AID-2": {
        "bash": "Checks each script's syntax and runs the safe one in the sandbox project.",
        "grep": "Searches each script for risky lines before you read it.",
        OC: "Opens the port forward to the stub model service and runs the safe script against the sandbox project.",
        "curl": "Fetches the three scripts from the stub model service through the port forward.",
        "jq": "Reads the JSON the stub model service returns.",
        "Stub model service": "Holds the three scripts, one safe and two unsafe, that you review before running.",
    },
    "ARC-2": {
        OCP: "The cluster the map script reads.",
        NP: "One of the parts the map shows: which pods may talk to which. You test the claim with real traffic.",
        KY: "Its rules are mapped as enforced or only logged, and two test pods show the difference.",
        OC: "Lists the parts by hand first, then runs the checks that test the map's claims.",
        "jq": "Reads the map and picks sections out of cluster JSON.",
        "Python 3": "Runs the supplied map script and keeps its output in a file.",
    },
    "GRC-3": {
        OCP: "The cluster the evidence script asks about (CM-6, CM-7, CM-8).",
        TK: "Runs the review gate that must pass before a pull request can merge.",
        GT: "Holds the repository and the branch protection that makes the gate a condition for merging.",
        OC: "Fetches the gate and runs the checks the evidence script performs.",
        "Git": "You branch, commit and push the script, then merge through a pull request.",
        "curl": "Calls the Gitea API for branch protection and merge status.",
        "jq": "Reads fields from Gitea replies and the evidence text.",
        "OpenSSL": "Hashes the evidence text so you can compare it with the hash in the log.",
        "Python 3": "You write collect_evidence.py, with a check per control, a UTC time stamp and a hash.",
    },
    "VM-3": {
        OCP: "The cluster that holds the supplied gate and fixtures.",
        TR: "Scans the main branch and the deps-updated branch of vm-app.",
        GT: "Holds vm-app and the tracking items that the script opens and closes through the Gitea API.",
        "Python 3": "You write rank.py and the Gitea code, then run triage.py to plan, open and close items.",
        OC: "Fetches the supplied files from their ConfigMap.",
        "Git": "Clones the repository and the fixed branch.",
        "curl": "Checks Gitea directly, with a token, against what the script created.",
        "jq": "Counts findings in the scan reports to check the ranking.",
    },
    "SDR-3": {
        "LogQL": "The query language you use to count failed sign-ins by source in Loki.",
        "Grafana alerting": "Holds the alert rule and the dashboard panel; you set the same threshold in both.",
        OCP: "The cluster whose sign-in records you analyze.",
        OC: "Applies the changed rule and panel and fetches the review gate.",
        "curl": "Sends the log queries to Loki.",
        "jq": "Counts and groups the query results.",
        "Python 3": "Runs review_gate.py, which recomputes the facts and checks your threshold.",
    },
    "CPS-3": {
        OCP: "The cluster where you measure, then restrict, one workload.",
        "Kubernetes RBAC": "You write a minimal role and binding for the report app's service account and remove the broad one.",
        NP: "You write a default-deny policy that blocks all traffic, then show a call is blocked.",
        OC: "Measures what the service account can do and applies the role, binding, policy and patch.",
        "jq": "Reads Role, binding and Deployment JSON for the gate.",
        "Python 3": "Runs review_gate.py, which refuses wildcards and cluster-admin grants.",
    },
    "AID-3": {
        "Python 3": "You write the shape check, its tests and summarize.py, which asks the model and logs every exchange.",
        "Git": "You branch, commit and push your work, then open a pull request.",
        GT: "Holds the repository and merges your pull request only when the commit status is success.",
        TK: "Runs the review gate pipeline in project build that clones your branch and checks it.",
        LK: "Stores the log of every prompt and reply so you can search it.",
        "Stub model service": "Returns the scan findings and the scripted replies, including bad ones your check must refuse.",
        OC: "Opens a port forward to the model service and checks the pipeline.",
        "tkn": "Starts and follows the review gate run.",
        "curl": "Calls the lab services' web interfaces to check results.",
        "jq": "Checks the model's JSON replies and reads the log records.",
    },
    "ARC-3": {
        OCP: "The cluster where the same Kyverno rules run in three conditions.",
        KY: "Its rules run in Audit and in Enforce mode; you send the same test requests under each.",
        OC: "Sends the test requests as dry runs and switches the policy between conditions.",
        "jq": "Reads the result files the comparison prints.",
        "Python 3": "Runs the test script and the comparison table.",
    },
    "GRC-4": {
        TK: "Runs the pipeline of three tasks: scan, policy check and signed bundle.",
        TR: "Scans the image; a serious finding stops the pipeline.",
        KY: "The policy check asks the cluster whether a candidate Deployment would be admitted.",
        "Cosign": "Signs the evidence bundle with a new key and verifies it with the public key.",
        "OpenSSL": "Makes the random password for the signing key.",
        OC: "Applies the tasks and pipeline and asks the cluster the admission question as a dry run.",
        "tkn": "Starts the pipeline run and follows it.",
        "jq": "Reads the JSON bundle and counts blocking findings.",
    },
    "VM-4": {
        OCP: "The cluster whose workloads' exposure and scale the script reads.",
        TR: "Scans the two images the workloads use and keeps every severity.",
        GT: "Holds the repository where the fix goes through a branch and pull request.",
        "Python 3": "Runs collect_facts.py and prioritize.py, which turn facts and scans into a plan.",
        OC: "Reads the facts about each workload.",
        "Git": "Branch and commit the Dockerfile fix.",
        "curl": "Calls the Gitea web interface, with a token, for the pull request.",
        "jq": "Picks fields out of the facts and the plan.",
    },
    "SDR-4": {
        "LogQL": "You write three detection queries (privilege escalation, secret read, pod exec) and test them on recorded scenarios.",
        "Grafana Alloy": "The collector pipeline in which you write the stage that adds the audit_resource label.",
        OCP: "The cluster whose audit records the detections watch.",
        NP: "The quarantine policy that denies all traffic to the pod you isolate.",
        OC: "Opens the tunnel to the pipeline intake, applies the Alloy configuration, and applies the policy and swaps the labels that isolate the pod.",
        "curl": "Sends the queries to Loki and calls the isolated pod from a helper pod.",
        "jq": "Picks fields out of Loki replies to build the timeline.",
        "Python 3": "Runs detect_test.py and timeline_check.py.",
    },
    "CPS-4": {
        OCP: "The cluster and the workload you secure end to end.",
        "Kubernetes Secrets": "Hold the password that you move out of the workload's settings.",
        "Kubernetes RBAC": "Gives the workload its own service account with no role.",
        NP: "Default-deny plus one rule that accepts the approved caller.",
        "Falco": "A rule you add alerts when a shell is started in the workload's container.",
        "AWS CLI": "Read-only calls that show the cloud identity of the lab shell.",
        OC: "Collects the evidence and applies the identity, secret, policies and container settings.",
        "jq": "Reads the live settings for the check.",
        "Python 3": "Runs check_workload.py, which fails if any of seven things drift.",
    },
    "AID-4": {
        "Python 3": "You write the allowed list and loop.py, which validates, logs, caps and stops the agent.",
        OC: "Runs the agent's commands as a view-only identity and sets that identity up.",
        LK: "Holds the agent's action trail, which you search.",
        "Stub model service": "Proposes the next step for each run, including one with an injected instruction.",
        "curl": "Sends queries to Loki to read the trail.",
        "jq": "Checks the shape of model replies and reads the trail.",
    },
    "ARC-4": {
        OCP: "The cluster with two projects that hold the same workloads.",
        NP: "Design A: network policies limit who may reach the database.",
        "Service Mesh 3": "Design B: mutual TLS and an identity rule limit who may reach the database.",
        OC: "Builds both designs, runs each attack case inside a pod and applies the failure steps.",
        "jq": "Reads the result file.",
        "Python 3": "Runs the harness that sends each attack case and records the code.",
    },
    "GRC-5": {
        "Kyverno policy reports": "The machine-made results that convert.py turns into standard assessment JSON.",
        "Python 3": "Runs convert.py, drift.py and measure.py.",
        "jq": "Reads the converted results.",
        OC: "Reads the policy reports and runs the monitor as a scheduled job.",
    },
    "VM-5": {
        OCP: "The cluster that runs the shared gate and holds the application scanned.",
        TK: "Runs the gate as shared tasks: risk-scan and the gate task.",
        TR: "Finds the base image and scans it.",
        GT: "Holds the application repository.",
        "Python 3": "You write gate_rules.py, gate_exceptions.py and gate.py, and run the gate.",
        "tkn": "Starts and follows gate runs.",
        OC: "Applies the ConfigMap and tasks.",
        "jq": "Reads the scan and result files.",
    },
    "SDR-5": {
        GT: "Holds the detections repository and the push to main that starts the pipeline.",
        TK: "Runs the pipeline that tests the rules and then deploys them.",
        "Grafana alerting": "Receives the rules your deploy script creates or updates.",
        LK: "Has the recorded cases replayed into it to test each rule.",
        MM: "Where the proof script looks for the alert.",
        OCP: "The cluster where the pipeline runs.",
        OC: "Applies the pipeline and starts the work.",
        "tkn": "Starts and follows the pipeline.",
        "Git": "Clone, commit and push to main.",
        "curl": "Calls the web interfaces of Gitea, Loki and Grafana.",
        "jq": "Reads JSON from those calls.",
        "Python 3": "Runs ci/run_tests.py, the deploy script and ci/prove_alert.py.",
    },
    "IAC-1": {
        "Terraform": "Builds the namespace, quota, network policy and role from files, and shows a plan before any change.",
        "Ansible": "Adds the service account and the settings record by running a playbook.",
        OC: "Reads and edits the cluster, so you can see what the tools built and make a change by hand.",
        "jq": "Picks values out of the saved plan.",
    },
    "IAC-2": {
        "Terraform": "Writes, plans and applies the baseline through the hashicorp/kubernetes provider.",
        GT: "Holds the repository and enforces branch protection, so a change needs a pull request.",
        TK: "Runs the plan gate as a pipeline task.",
        "tkn": "Starts the pipeline run and follows it.",
        "Git": "Records the Terraform files and the branch you push.",
        "Python 3": "Runs the plan gate that reads the plan and refuses an unsafe change.",
        OC: "Reads and patches objects on the cluster, for example to cause drift.",
        "jq": "Reads the plan and the Gitea replies as JSON.",
    },
    "IAC-3": {
        "Terraform": "Compares the Terraform files and state with the live namespace and reports drift with an exit code.",
        "Ansible": "Tests the playbook against the namespace without changing it.",
        "ansible-lint": "Checks the playbook for style problems and risky patterns.",
        OC: "Makes the hand changes and reads the live objects.",
        "Python 3": "Runs the timing script and the conformance check that compares live objects with the playbook.",
    },
    "CPS-5": {
        OCP: "The cluster where you build the guardrails and test them on twelve workloads.",
        "Project request template": "You add a quota so every new project starts with limits.",
        KY: "Generates default-deny and a fallback quota, adds safe defaults and refuses unsafe settings.",
        OC: "Applies the template and policies and creates the test projects.",
        "jq": "Reads results.",
        "Python 3": "Runs score.py, which counts what is admitted before and after.",
    },
    "AID-5": {
        KY: "Generates default objects when a labelled project is created and refuses agent workloads that carry write power or secrets.",
        NP: "Limits an agent to reaching the model service and nothing else.",
        "Grafana alerting": "Alerts when the agent identity acts outside its list.",
        LK: "Holds the records the alert reads.",
        "Stub model service": "Holds the attempts that should be blocked and the actions that must still work.",
        "Python 3": "Runs report.py, which measures the block rate.",
        OC: "Applies the policies and runs the probe.",
        "curl": "Makes web calls to lab services to check results.",
        "jq": "Reads results.",
    },
    "ARC-5": {
        OCP: "The cluster whose four components you check against the list.",
        NP: "Generated from the flows file: default-deny plus one allow policy per entry.",
        KY: "The generated admission check refuses a pod the list does not name.",
        OC: "Applies the generated objects and checks live state.",
        "jq": "Reads results.",
        "Python 3": "Runs gen_netpol.py, gen_admission.py, conformance.py and drift_timer.py.",
    },
}

# Each rule maps a tools-list string (lowercase, matched from the start) to the TOOLS keys that get a row.
# Specific rules come before general ones; the first match wins.
_KEYS = [
    (r"lab shell", ["lab shell"]),
    (r"aws command-line|aws cli|aws$", ["AWS CLI"]),
    (r"openshift container platform \(project request template\)", ["OpenShift Container Platform", "Project request template"]),
    (r"openshift container platform", ["OpenShift Container Platform"]),
    (r"(red hat )?openshift service mesh", ["Service Mesh 3"]),
    (r"openshift compliance operator|compliance operator", ["Compliance Operator"]),
    (r"openshift pipelines|tekton", ["OpenShift Pipelines (Tekton)"]),
    (r"^tkn", ["tkn"]),
    (r"cosign", ["Cosign"]),
    (r"trivy and trivy operator", ["Trivy"]),
    (r"trivy", ["Trivy"]),
    (r"kyverno policy reports", ["Kyverno policy reports"]),
    (r"kyverno", ["Kyverno"]),
    (r"kubernetes secrets, rbac and networkpolicy", ["Kubernetes Secrets", "Kubernetes RBAC", "NetworkPolicy"]),
    (r"kubernetes rbac and networkpolicy", ["Kubernetes RBAC", "NetworkPolicy"]),
    (r"(kubernetes )?networkpolicy", ["NetworkPolicy"]),
    (r"pod security admission", ["Pod security admission"]),
    (r"loki logql", ["LogQL"]),
    (r"grafana loki", ["Grafana Loki"]),
    (r"loki and grafana", ["Grafana Loki", "Grafana"]),
    (r"loki", ["Grafana Loki"]),
    (r"grafana alloy", ["Grafana Alloy"]),
    (r"grafana alerting", ["Grafana alerting"]),
    (r"grafana", ["Grafana"]),
    (r"mattermost", ["Mattermost"]),
    (r"gitea", ["Gitea"]),
    (r"falco", ["Falco"]),
    (r"ansible with .*ansible-lint", ["Ansible", "ansible-lint"]),
    (r"ansible-lint", ["ansible-lint"]),
    (r"ansible", ["Ansible"]),
    (r"terraform", ["Terraform"]),
    (r"openssl", ["OpenSSL"]),
    (r"python", ["Python 3"]),
    (r"stub model service", ["Stub model service"]),
    (r"bash", ["bash"]),
    (r"grep", ["grep"]),
    (r"git$", ["Git"]),
    (r"oc$", ["oc"]),
    (r"jq$", ["jq"]),
    (r"curl$", ["curl"]),
]
_KEY_RULES = [(re.compile(p), keys) for p, keys in _KEYS]

# Generic fallback text for tools whose module has no specific entry; only used for these shared command-line tools.
_SHARED = {
    "OpenShift Container Platform": "The cluster every command in this module runs against.",
    "oc": "Runs the cluster commands in each step.",
    "AWS CLI": "Reads and checks AWS resources from the shell.",
    "jq": "Picks fields out of JSON output.",
    "curl": "Calls web endpoints to test behavior.",
    "Git": "Tracks and reviews file changes.",
}


# A tools-list entry may resolve to a more specific key than the older curated row used.
_ALIAS = {"Grafana alerting": "Grafana"}


# "Why this tool": why the lab uses this tool and not another way of doing the same job. Shown in a module's
# tool table when the module sets "tool_why": True.
_WHY = {
    "lab shell": "Every command in every module runs inside it, so the instructions are identical on Mac and Windows and you install nothing on your laptop.",
    "oc": "It is the one command that talks to the cluster, so every module uses it to ask what is true and to make changes. You sign in once, and it works on OpenShift objects as well as standard Kubernetes ones. Unlike clicking in the web console, a command can be pasted, repeated and checked by a test.",
    "Git": "It keeps scripts and settings with a history, so every change has a record of who made it and when, and a mistake can be undone.",
    "Gitea": "It gives the lab a git server of its own, so you can push and review changes without an outside account.",
    "curl": "It calls a web address from the terminal, so you can check what a service really returns instead of trusting a screen.",
    "jq": "It picks one field out of a long JSON reply, so a test can read a single value.",
    "OpenShift Container Platform": "It is the platform the whole lab runs on, so every module works on the same real cluster, with the same kinds of objects a production OpenShift system has.",
    "OpenShift Pipelines (Tekton)": "It runs automated tasks inside the cluster, so you can see a check run with no person at the keyboard and under its own limited identity. A script run from a laptop could not show that.",
    "Kyverno": "It is the policy engine the lab already uses to check and enforce rules on cluster objects, so there are real policies to count and read as evidence. It is free and open source.",
    "tkn": "It starts and reads pipeline runs from the terminal, so the same shell you use for everything else drives the pipeline. The other way is the web console, which cannot be pasted into a step.",
    "Python 3": "Python reads and writes JSON easily and is already in the lab shell, so a small script needs nothing installed.",
    "bash": "It is the shell the lab shell opens, so every command in the modules behaves the same on every laptop and can be pasted as written.",
    "grep": "It finds the lines you care about in long output or files, so a step or a test can look for one word without you reading everything.",
    "Stub model service": "A real model needs an account, a key and money. A scripted stand-in gives the same answers every time, so every learner sees the same behavior and a test can check it.",
    "Grafana Loki": "It stores logs cheaply and is free and open source, so the lab can keep the logs that detections and investigations need without a paid logging product.",
    "NetworkPolicy": "It is the built-in way to limit which pods can talk to which, so you need no extra product to show what a blocked connection looks like.",
    "Grafana alerting": "It runs a log query on a schedule and notifies when the result crosses a limit, so a detection becomes an alert without writing a separate program.",
    "Terraform": "It states the wanted infrastructure in files and shows a plan before changing anything, so a change can be reviewed and drift can be detected by comparing the files with the live system.",
    "Ansible": "It runs a list of tasks that put a system into a stated state and can test them without changing anything, so the same baseline can be applied repeatedly.",
    "ansible-lint": "It catches style problems and risky patterns in a playbook before it runs, so review starts from a clean file.",
    "Service Mesh 3": "It gives pods encrypted, identified connections without changing the application code, so you can see mesh policy do work that a NetworkPolicy alone cannot.",
    "Compliance Operator": "It scans the cluster against a published checklist inside the cluster, so you get repeatable results instead of checking each setting by hand.",
    "Pod security admission": "It is built into OpenShift, so the lab can show a pod being refused for breaking a security level without installing anything.",
    "Kubernetes RBAC": "It is the built-in way to say who may do what in the cluster, so the lab uses the same permission model a real OpenShift system uses.",
    "Kubernetes Secrets": "It is the built-in place for small sensitive values, so you see how a cluster keeps a password apart from the workload that uses it.",
    "Falco": "It watches what a running container actually does, which the cluster's own settings cannot show, so you can detect behavior and not only configuration. It is free and open source.",
    "AWS CLI": "It reads the cloud account's settings from a terminal, so a check can be pasted, repeated and tested instead of clicked through in the console.",
    "Project request template": "It is how OpenShift builds every new project, so a default set here reaches every future project without anyone remembering to add it.",
    "OpenSSL": "It is the standard tool for looking at keys and certificates, so you can see for yourself what a certificate says and whether a connection is encrypted.",
    "Trivy": "It scans images and clusters for known flaws and bad settings from the command line and is free and open source, so the same scan can run by hand and in a pipeline.",
    "Cosign": "It signs an image and checks the signature, so the cluster can refuse an image nobody vouched for. It is free and open source.",
    "Kyverno policy reports": "Kyverno saves pass and fail results as objects in the cluster, so a policy check leaves evidence you can read later, not only a message at the time.",
    "Grafana": "It is where you browse logs and build dashboards, so the data Loki stores becomes something you can look at and share. It is free and open source.",
    "Mattermost": "It is chat you run yourself and can send messages to from a script, so an alert reaches a person without an outside chat account.",
    "LogQL": "It is the query language Loki uses, so you need it to ask the stored logs a question and to write a detection.",
    "Grafana Alloy": "It collects logs and sends them to Loki, so you can see how data reaches the place you search it. It is free and open source.",
}


def resolve_keys(tool: str) -> list[str]:
    """TOOLS keys for one entry of a module's `tools` list (empty when nothing matches)."""
    text = tool.strip().lower()
    for rule, keys in _KEY_RULES:
        if rule.match(text):
            return keys
    return []


def tool_rows(module: dict) -> list[tuple]:
    """Rows (name, url, what it is, used here) for every entry of the module's `tools` list, without duplicates.

    When the module sets "tool_why": True, each row gains a fifth item: why the lab uses this tool.
    """
    mid = module["id"]
    curated, specific = _CURATED.get(mid, {}), _USE.get(mid, {})
    rows, seen = [], set()
    for tool in module["tools"]:
        for key in resolve_keys(tool):
            if key in seen or key not in TOOLS:
                continue
            use = specific.get(key) or curated.get(key) or curated.get(_ALIAS.get(key, "")) or _SHARED.get(key)
            if not use:
                continue
            seen.add(key)
            url, what = TOOLS[key]
            rows.append((key, url, what, use))
    for key, use in curated.items():
        if key not in seen:
            seen.add(key)
            url, what = TOOLS[key]
            rows.append((key, url, what, specific.get(key) or use))
    if module.get("tool_why"):
        rows = [(*r, _WHY.get(r[0], "")) for r in rows]
    return rows


def missing_tools(module: dict) -> list[str]:
    """Entries of the module's `tools` list for which tool_rows has no row (used by accuracy check C9)."""
    have = {r[0] for r in tool_rows(module)}
    return [t for t in module["tools"] if not resolve_keys(t) or not all(k in have for k in resolve_keys(t))]
