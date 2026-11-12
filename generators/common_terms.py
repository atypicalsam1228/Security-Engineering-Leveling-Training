"""Plain meanings for common technical words, so the Why This Matters text always has hover help.

A module lists its own terms in MODULE["terms"]. A word here is added to a module's term table only when the
module's requirement text uses it, the module does not define it, and the text does not define it in brackets.
"""
from __future__ import annotations

import re

# term -> (plain meaning, other spellings that link to the same entry)
COMMON: dict[str, tuple[str, list[str]]] = {
    "pod": ("The smallest thing the cluster runs: one or more containers that run together and share one network address.", []),
    "cluster": ("The group of servers that runs your lab and the programs in it.", []),
    "container": ("A sealed box that holds one program and everything it needs to run.", []),
    "workload": ("A program the cluster runs.", []),
    "namespace": ("A named section of the cluster that holds a set of related parts.", []),
    "node": ("One server in the cluster.", []),
    "image": ("A packaged copy of a program and everything it needs to run. A container starts from an image.", []),
    "script": ("A text file of commands that a computer runs in order.", []),
    "scan": ("A check of software or settings against a list of known problems. The scan reports what it finds.", ["scanner", "scanning"]),
    "log": ("A line of text that a program saves about what happened.", []),
    "alert": ("A message sent when a rule matches something in the logs.", []),
    "rule": ("A written condition that a tool checks.", []),
    "policy": ("A set of rules written down so that a tool can enforce them.", ["policies"]),
    "identity": ("The name a person or program is known by when it asks for something.", []),
    "key": ("A secret value that locks or unlocks encrypted data, or proves who you are.", []),
    "encryption": ("Scrambling data so that only someone with the right key can read it.", ["encrypted"]),
    "database": ("An organized store of data that programs read and write.", []),
    "api": ("The set of requests a program accepts from other programs.", []),
    "gate": ("A pipeline step that stops the run when a rule is broken.", []),
    "admission": ("The check the cluster makes on a request to create or change something, before it allows the request.", []),
    "sandbox": ("A fenced-off place where a program runs, so a mistake cannot reach anything else.", []),
    "prompt": ("The text you give a model to tell it what to do.", []),
    "privilege": ("The permission to do something powerful.", ["privileged"]),
    "escalation": ("Gaining more permission than you were given.", []),
    "shell": ("A window where a person types commands.", []),
    "deploy": ("Put a new version of a program into the running system.", ["deployment"]),
    "repository": ("A folder whose history git records.", []),
    "git": ("A tool that records the history of a folder of files.", []),
    "evidence": ("Saved records that show a system is set up and behaving as claimed.", []),
    "signed": ("Marked with a digital signature, which shows who made it and that it was not changed.", []),
    "audit": ("A record of who did what and when, kept so it can be checked later.", []),
    "vulnerability": ("A flaw in software that an attacker could use.", ["vulnerabilities"]),
    "fips": ("A set of US federal standards. In FIPS mode a system uses only cryptography validated against the federal standard.", []),
    "siem": ("A system that collects logs from many sources so they can be searched and raise alerts.", []),
    "openshift": ("The Red Hat platform your lab cluster runs on. It is Kubernetes with extra security and tools built in.", []),
    "kubernetes": ("The open-source system that runs and manages containers across servers. OpenShift is built on it.", []),
    "nist": ("The US National Institute of Standards and Technology. It publishes the security control catalog these modules cite.", []),
    "fedramp": ("The US program that sets security requirements for cloud services used by the federal government.", []),
    "aws": ("Amazon Web Services, the cloud your lab runs in.", []),
    "oc": ("The command-line tool for OpenShift. You type oc to ask the cluster questions.", []),
    "jq": ("A tool that picks values out of JSON text.", []),
    "json": ("A text format for data, made of names and values in braces.", []),
    "yaml": ("A plain-text format for settings: lines of name: value, with indentation to show what belongs to what.", []),
    "config map": ("A cluster object that holds plain settings (not secrets) as named values or files, so a program can read them.", ["configmap"]),
    "secret": ("A cluster object that holds a sensitive value such as a password or token, kept apart from ordinary settings.", []),
    "token": ("A long secret string that works like a password for one program. Anyone who holds it can act as you, so never print it or commit it.", []),
    "credential": ("A secret that proves who you are, such as a password, token or key.", []),
    "baseline": ("The agreed starting configuration that the system is expected to match.", []),
    "drift": ("When the real system no longer matches what the files say it should be.", []),
    "query": ("A question you ask a data store, written in a query language, such as a log search.", ["queries"]),
    "branch": ("A separate line of changes in git. The main branch is the agreed version.", []),
    "commit": ("One saved snapshot in git, with a short message.", []),
    "merge": ("Combine the changes from one git branch into another.", []),
    "pull request": ("A request to merge one branch into another, where others can review the change first.", []),
    "label": ("A key=value tag on a cluster object, used to pick objects, such as app=demo-app.", []),
    "selector": ("A rule that picks objects by their labels.", []),
    "annotation": ("A note attached to a cluster object that tools can read. Unlike a label, it is not used to pick objects.", []),
    "pipeline": ("A set of automated steps that run in order, such as scan, check and sign.", []),
    "tekton": ("The pipeline engine in OpenShift Pipelines. It runs each pipeline step in a container.", []),
    "registry": ("A server that stores container images.", ["registries"]),
    "rbac": ("Role-based access control: permissions are given to roles, and roles are given to users or programs.", []),
    "role": ("A list of actions a user or program may take on named kinds of objects.", []),
    "role binding": ("Gives a role to a user, group or service account.", ["rolebinding", "clusterrolebinding", "cluster role binding"]),
    "service account": ("An identity that a program (not a person) uses to talk to the cluster.", ["serviceaccount"]),
    "network policy": ("A rule that says which pods may send traffic to which other pods.", ["networkpolicy", "networkpolicies"]),
    "resource quota": ("A limit on the total resources a namespace may use.", ["resourcequota"]),
    "ingress": ("The way traffic from outside the cluster reaches a program inside it.", []),
    "route": ("An OpenShift object that gives a program inside the cluster an address reachable from outside.", []),
    "endpoint": ("One address and port that something listens on, such as a pod behind a Service or a URL path that returns data.", []),
    "certificate": ("A file that proves a server's identity, signed by a trusted authority.", []),
    "webhook": ("An address that another program calls to send it a message when something happens.", []),
    "runner": ("The program or container that carries out the steps of a pipeline.", []),
    "severity": ("How serious a finding is, such as low, medium, high or critical.", ["severities"]),
    "schema": ("The expected shape of data: which fields it has and what type each one is.", []),
    "header": ("A line of extra information sent with a web request, such as a sign-in token.", []),
    "timestamp": ("The date and time recorded for an event.", []),
    "hash": ("A short fixed-length fingerprint of data. If the data changes, the hash changes.", ["checksum"]),
    "controller": ("A program in the cluster that keeps the real state matching what you asked for.", []),
    "replica": ("One running copy of a program.", []),
    "operator": ("A program that installs and looks after another tool inside the cluster.", []),
    "provider": ("The company or plug-in that supplies a platform, such as a cloud provider or a Terraform provider.", []),
    "terraform": ("A tool that builds infrastructure from files that describe it.", []),
    "ansible": ("A tool that changes systems by running a playbook, a list of tasks.", []),
    "playbook": ("An Ansible file that lists the tasks to run.", []),
    "loki": ("The log store in the lab. You search it with LogQL.", []),
    "logql": ("The search language for Loki.", []),
    "grafana": ("The dashboard and alerting tool in the lab. It reads logs from Loki.", []),
    "trivy": ("A scanner that finds known vulnerabilities and bad settings in code, images and files.", []),
    "falco": ("A tool that watches what programs do on a node and raises an alert when the behavior looks wrong.", []),
    "kyverno": ("A policy engine for the cluster. It checks, changes or blocks objects against rules you write.", []),
    "mattermost": ("The chat tool in the lab, where alerts and messages go.", []),
    "gitea": ("A git server that runs in your lab.", []),
    "keycloak": ("The sign-in service (identity provider) in the lab.", []),
    "inventory": ("A list of the parts of a system; in Ansible, the machines a playbook runs against.", []),
    "runtime": ("The time when a program is running, as opposed to when it is written or built.", []),
    "exploit": ("Code or a method that takes advantage of a vulnerability.", ["exploits", "exploitable"]),
    "remediate": ("Fix a finding, for example by upgrading a package or changing a setting.", ["remediation", "remediated"]),
    "digest": ("A hash computed from content. The same content always gives the same digest; for a container image it names that exact image, written like sha256:...", ["digests"]),
    "signature": ("A value made with a private key that shows who made something and that it was not changed.", ["signatures", "signed"]),
    "manifest": ("A YAML file that describes the objects to create in the cluster.", ["manifests"]),
    "runbook": ("Step-by-step instructions for handling a known situation.", ["runbooks"]),
    "artifact": ("A file produced by a build or a step, such as an image, a report or a log.", ["artifacts"]),
    "template": ("A file with blanks that are filled in when it is used.", ["templates"]),
    "payload": ("The data carried inside a message or request.", ["payloads"]),
    "state file": ("The file where Terraform records what it has built. Also called tfstate.", ["tfstate", "terraform state"]),
    "stig": ("Security Technical Implementation Guide: a DoD checklist of settings for one product.", ["stigs"]),
    "pipelinerun": ("One execution of a Tekton pipeline.", ["pipelineruns", "pipeline run"]),
    "taskrun": ("One execution of a single Tekton task.", ["taskruns"]),
    "cluster policy": ("A Kyverno policy that applies to the whole cluster.", ["clusterpolicy", "clusterpolicies"]),
    "crd": ("Custom resource definition: adds a new kind of object to the cluster.", ["crds"]),
    "etcd": ("The database where the cluster stores all of its objects.", []),
    "cosign": ("A tool that signs container images and checks their signatures.", []),
    "dns": ("The system that turns names into network addresses.", []),
    "tcp": ("The standard way programs send data reliably over a network.", []),
    "http": ("The protocol that web pages and web APIs use. HTTPS is the encrypted form.", ["https"]),
    "url": ("A web address, such as https://example.com/page.", ["urls"]),
    "cli": ("Command-line interface: a program you use by typing commands.", []),
    "sso": ("Single sign-on: one sign-in that works for many tools.", ["single sign-on"]),
    "uid": ("The number that identifies the user a process runs as.", ["uids"]),
    "jsonl": ("A text file with one JSON object on each line.", []),
    "tsv": ("Tab-separated values: a table written as text, with a tab between columns.", []),
    "heredoc": ("A shell way to write a multi-line file: type text until a marker line such as EOF.", ["here-document"]),
    "threshold": ("The limit at which something is counted or an alert fires.", ["thresholds"]),
    "ec2": ("An AWS virtual server.", []),
    "grep": ("A command that prints only the lines that match a pattern.", []),
    "sed": ("A command that edits text as it passes through, often to replace one string with another.", []),
    "diff": ("A command that shows the differences between two files.", []),
    "mkdir": ("A command that makes a new folder.", []),
    "pwd": ("A command that prints the folder you are in.", []),
    "printf": ("A command that prints text in a set format.", []),
    "uniq": ("A command that removes repeated neighbouring lines.", []),
    "chmod": ("A command that changes who may read, write or run a file.", []),
}

DISPLAY = {
    "api": "API", "fips": "FIPS", "siem": "SIEM", "json": "JSON", "yaml": "YAML", "rbac": "RBAC", "nist": "NIST",
    "fedramp": "FedRAMP", "aws": "AWS", "openshift": "OpenShift", "kubernetes": "Kubernetes", "oc": "oc", "jq": "jq",
    "logql": "LogQL", "kyverno": "Kyverno", "tekton": "Tekton", "trivy": "Trivy", "falco": "Falco", "grafana": "Grafana",
    "loki": "Loki", "gitea": "Gitea", "mattermost": "Mattermost", "keycloak": "Keycloak", "terraform": "Terraform",
    "ansible": "Ansible", "config map": "Config map", "etcd": "etcd", "dns": "DNS", "tcp": "TCP", "http": "HTTP",
    "url": "URL", "cli": "CLI", "sso": "SSO", "uid": "UID", "jsonl": "JSONL", "tsv": "TSV", "ec2": "EC2", "crd": "CRD",
    "stig": "STIG", "cosign": "Cosign", "pipelinerun": "PipelineRun", "taskrun": "TaskRun", "cluster policy": "Cluster policy",
    "state file": "State file", "grep": "grep", "sed": "sed", "diff": "diff", "mkdir": "mkdir", "pwd": "pwd", "printf": "printf",
    "uniq": "uniq", "chmod": "chmod",
}

# Words that mean something else in one module's text.
SKIP = {
    "ARC-3": {"audit"},
    "ARC-4": {"key", "api"},
    "AID-3": {"log"},
    "CPS-4": {"script"},
    "CPS-5": {"gate"},
    "GRC-3": {"gate"},
    "CAP": {"privilege"},
}


TEXT_SKIP_KEYS = {
    "code", "lang", "terms", "glossary", "cite", "quote", "file", "id", "slug", "controls", "mentions", "env", "start", "expect",
    "dot", "a", "b", "zone", "parent", "kind", "rankdir", "unit_values_ok", "lab_needs", "lab", "break_code", "restore_code",
}


def module_text(m: dict) -> str:
    """All prose of a module (not code, not its own terms or glossary), so a common word is defined wherever it is used."""
    parts: list[str] = []

    def walk(node) -> None:
        if isinstance(node, str):
            parts.append(node)
        elif isinstance(node, dict):
            for k, v in node.items():
                if k not in TEXT_SKIP_KEYS:
                    walk(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v)

    walk({k: v for k, v in m.items() if k not in ("terms", "glossary")})
    return "\n".join(parts)


def _spellings(term: str) -> list[str]:
    return [term, *COMMON[term][1]]


# Terms added after the first group: these are found anywhere in a module's text. The first group
# (pod ... siem) is only looked for in the requirement text, as before.
TEXT_WIDE_FROM = "openshift"
# term -> (regex that must not end just before the hit, regex that must not follow it)
AVOID = {"route": (None, r"\s*53"), "provider": (r"identity\s+$", None)}


def _squash(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _hit(text: str, term: str) -> str | None:
    """The spelling of `term` that appears in `text` as a term (not followed by an opening bracket), or None."""
    before, after = AVOID.get(term, (None, None))
    for spelling in _spellings(term):
        pattern = r"(?<![A-Za-z0-9])" + re.escape(spelling) + r"(?:s|es)?(?![A-Za-z0-9])(\s*\()?"
        for hit in re.finditer(pattern, text, flags=re.I):
            if hit.group(1):
                continue
            if before and re.search(before, text[: hit.start()], flags=re.I):
                continue
            if after and re.match(after, text[hit.end():]):
                continue
            return spelling
    return None


WIDE_EARLY = {"policy", "rule", "scan", "evidence", "pod", "container", "image", "namespace", "node", "cluster"}  # older entries that are also found in all prose


def extras(m: dict) -> tuple[list[tuple[str, str]], dict[str, str]]:
    """Return (term rows to append, spelling -> term aliases) for the common words this module uses but does not define."""
    own = {_squash(t[0]) for t in m["terms"]}
    keys = list(COMMON)
    wide_from = keys.index(TEXT_WIDE_FROM)
    texts = {}
    for scope, text in (("requirement", m["requirement"]), ("wide", module_text(m))):
        for name in sorted((t[0].lower() for t in m["terms"]), key=len, reverse=True):
            text = re.sub(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?:s|es)?(?![A-Za-z0-9])", " ", text, flags=re.I)
        texts[scope] = text
    rows, aliases = [], {}
    for index, (term, (meaning, others)) in enumerate(COMMON.items()):
        if {_squash(term), *(_squash(o) for o in others)} & own or term in SKIP.get(m["id"], ()):
            continue
        if _hit(texts["wide" if index >= wide_from or term in WIDE_EARLY else "requirement"], term):
            rows.append((DISPLAY.get(term, term.capitalize()), meaning))
            aliases.update({o: term for o in others})
    return rows, aliases
