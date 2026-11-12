"""SDR-2: Triage an alert by runbook. Security data and incident response, levels 1 and 2."""

NIST = "nist-sp-800-53r5-full.md"

MODULE = {
    "intent_at_end": True,
    "id": "SDR-2",
    "slug": "Triage",
    "title": "Triage an Alert by Runbook",
    "draft": (
        "Nothing here has run on a live cluster. The supplied triage.py was tested against a local stand-in for Loki, not a real one. "
        "The exercise records are pushed to Loki with an extra label, lab_seed, so they never mix with real records, and every triage search adds that label and the seed_run label (the start time of this lab start), so records left from an earlier lab start are ignored. "
        "Assumptions to confirm live: Loki accepts pushes with timestamps up to three hours old; the Falco record shape (rule Terminal shell in container, with output_fields); "
        "the Keycloak event lines (type LOGIN_ERROR and LOGIN, ipAddress, username) and that Keycloak logs successful sign-ins; the audit field names under the json parser; "
        "the collector pod label app.kubernetes.io/component=collector (the start state's forwarder uses the platform's log operator, which sets this label); Grafana answering on /api/health and Mattermost on /api/v4/system/ping. "
        "Also unconfirmed: that the real audit log carries the role binding request body that the exercise records show (the OpenShift Default audit profile logs metadata only; the WriteRequestBodies profile logs the body of write requests, so a real cluster needs that profile for the roleRef check); that the real Falco output_fields hold k8s.ns.name and k8s.pod.name (create a shell in a pod and read the record in Loki); that Keycloak logs successful sign-ins (its event log listener logs successes at debug level by default, so set the success level to info in the Keycloak configuration); and whether the collector stores an application line as plain text or as a JSON record with a message field (read one real Keycloak line from Loki with a query_range call and compare). "
        "The lab chooses the 5 minute late limit and the 10 minute gap limit; NIST and FedRAMP leave the AU-5 alert time period and recipients organization-defined; FedRAMP sets the AU-6 review frequency at least weekly."
    ),
    "controls": ["AU-6", "IR-4", "AU-5"],
    "mentions": ["SI-4", "IR-5", "IR-6", "AU-8", "AU-12"],
    "unit_values_ok": [
        "5 minute", "10 minute", "5 minutes", "10 minutes", "15 minutes", "20 minutes", "24 minutes", "25 minutes", "28 minutes", "30 minutes",
        "3 hours", "1 hour", "1 minute", "2 minutes", "60 seconds",
    ],
    "minutes": {"hands_on": 38, "verify": 18},
    "tools": ["Loki and Grafana (free, open source)", "Mattermost (free, open source)", "OpenShift Container Platform", "oc", "curl", "jq", "python3"],
    "tool_why": True,
    "hide_draft": True,
    "hover": True,
    "terms_at_end": True,
    "diagrams": [
        {
            "id": "path",
            "title": "The path a log takes, and where the triage commands look",
            "caption": "Logs (lines of text that programs save about what happened) travel from the sources to the log collector (a program that reads them and sends them on), then to Loki (the log store). An alert (a message that says a rule matched) travels from Grafana (the tool that runs the rules) to the alert channel (a named chat room) in Mattermost (team chat). The triage script in your lab shell searches Loki, and you post each decision to the same channel. This diagram shows the lab (test) setup. In production the runbook is kept under change control and alerts also reach the people on call. Each step below adds one part, drawn with thick lines.",
            "per_step": True,
            "rankdir": "LR",
            "step_notes": {
                1: "You copy the runbook from the cluster into your lab shell with oc, and print the four alerts that were posted to the alert channel in Mattermost.",
                2: "The first triage command searches Loki for the audit record behind a privilege-change alert, and you post your decision to the alert channel.",
                3: "The second command searches the sign-in records in Loki and compares failures with later successes, and you post your decision to the alert channel.",
                4: "The third command pairs a runtime shell record in Loki with the audit record that names the person. Later, in Verify, the path check walks every hop from the log collector to the alert channel and reads how old the newest record of each type is.",
            },
            "zones": [
                {"id": "cluster", "icon": "aws/group-AWS-Cloud", "label": "Your cluster (your OpenShift cluster, in AWS)", "kind": "boundary"},
                {"id": "node", "icon": "k8s/node", "label": "On the node", "parent": "cluster", "kind": "group"},
                {"id": "logging", "icon": "brands/openshift", "label": "Project openshift-logging", "parent": "cluster", "kind": "group"},
                {"id": "siem", "icon": "brands/openshift", "label": "Project siem", "parent": "cluster", "kind": "group"},
                {"id": "chat", "icon": "brands/openshift", "label": "Project chat", "parent": "cluster", "kind": "group"},
                {"id": "shell", "label": "Lab shell (on your computer)", "kind": "boundary", "labeljust": "r"},
            ],
            "key": {"aws/group-AWS-Cloud": "AWS Cloud", "k8s/node": "Kubernetes node", "brands/openshift": "OpenShift project", "k8s/pod": "Kubernetes pods", "brands/loki": "Loki", "brands/grafana": "Grafana", "k8s/cm": "Kubernetes config map", "brands/mattermost": "Mattermost", "brands/python": "Python script"},
            "nodes": [
                {"id": "src", "title": "Log sources", "sub": "Audit, infrastructure, application", "zone": "node"},
                {"id": "col", "icon": "k8s/pod", "title": "Log collector", "sub": "Pods that read logs and forward them", "zone": "logging"},
                {"id": "loki", "icon": "brands/loki", "title": "Loki (the log store)", "sub": "Stores the records", "zone": "siem"},
                {"id": "graf", "icon": "brands/grafana", "title": "Grafana (alert rules)", "sub": "Raises the alerts", "zone": "siem"},
                {"id": "book", "icon": "k8s/cm", "title": "Runbook (ConfigMap)", "sub": "Kubernetes config map sdr-runbook", "zone": "siem", "kind": "warn", "s": 1},
                {"id": "chan", "icon": "brands/mattermost", "title": "Alert channel (Mattermost)", "sub": "Channel siem-alerts", "zone": "chat", "kind": "ok"},
                {"id": "tri", "icon": "brands/python", "title": "Triage script", "sub": "Python script triage.py", "zone": "shell", "kind": "warn", "s": 1},
            ],
            "edges": [
                {"a": "src", "b": "col", "label": "Read by"},
                {"a": "col", "b": "loki", "label": "Forwarded to"},
                {"a": "loki", "b": "graf", "label": "Queried by"},
                {"a": "graf", "b": "chan", "label": "Alert posted to", "kind": "ok"},
                {"a": "book", "b": "tri", "label": "Copied into", "kind": "warn", "s": 1},
                {"a": "tri", "b": "loki", "label": "Searches", "kind": "warn", "s": 2},
                {"a": "tri", "b": "chan", "label": "Decision posted to", "kind": "ok", "s": 2},
                {"a": "tri", "b": "col", "label": "Path check reads pods of", "kind": "warn", "flat": True, "beside": True, "s": 4},
            ],
            "why_built": (
                "You work in lab shell on your computer, the same tools container you opened in the foundation module, and everything you search runs inside your cluster (a group of servers that work together as one system). "
                "Logs are written on a node (one server in the cluster), a collector in the project openshift-logging sends them to Loki in the project siem, and Grafana, also in siem, runs alert rules over what Loki holds and posts each alert to Mattermost in the project chat (a project is a named section of the cluster, also called a namespace). "
                "This module adds that logging path and the alert channel to the lab layout the foundation module showed, because triage only makes sense when you can see where a record comes from. "
                "This module also adds the script triage.py, which you run in lab shell: it searches Loki over the network, and you post each decision to the alert channel with curl. "
                "The runbook is stored in the cluster as a ConfigMap (a named bundle of small files) so every learner gets the same copy, and you copy it into lab shell with oc. "
                "The path is split into separate stops on purpose, so when a search comes back empty you can test each stop in turn and find the one that failed."
            ),
            "setup": [
                ("Log collector", "Pods in the project openshift-logging (a pod is the smallest running unit on the cluster)", "It reads logs where they are written, so no log source has to know about Loki."),
                ("Loki", "The project siem", "One store for every log type, so a single search can look across sources."),
                ("Grafana", "The project siem, next to Loki", "It queries Loki directly and posts the alerts that start your triage."),
                ("Alert channel", "Mattermost in the project chat", "People already read chat, so alerts and your decisions sit together in one place."),
                ("Runbook", "A ConfigMap in the project siem", "Every learner gets the same copy, and you copy it into lab shell with oc."),
                ("Triage script", "Your lab shell", "It reaches Loki over the network with the lab variables (named values the lab sets for you), so no password is typed."),
            ],
            "reading": [
                "1. Log sources: where logs are first written on a node. Audit, infrastructure and application logs start here.",
                "2. Log collector: pods in the project openshift-logging that read the logs and forward them to Loki.",
                "3. Loki (the log store): keeps every record so it can be searched. Triage searches here.",
                "4. Grafana (alert rules): queries Loki on a schedule and raises an alert when a rule matches.",
                "5. Runbook (ConfigMap): the ConfigMap sdr-runbook, which you copy into your lab shell with oc.",
                "6. Alert channel (Mattermost): the channel siem-alerts, where Grafana posts alerts and you post each decision.",
                "7. Triage script: triage.py in your lab shell. It searches Loki, and its path check also reads the pods of the log collector, so a gap can be located one hop (one stop on the path) at a time.",
            ],
        },
    ],
    "prereq": ["ENG-0 Terminal, Git and Your Lab (you can open lab shell, type oc and jq commands, and read their output)"],
    "lab_needs": [],
    "lab": {
        "start": "lab start sdr-2",
        "env": ["LOKI_URL", "LOKI_CA_FILE", "LOKI_USER", "LOKI_PASSWORD", "GRAFANA_URL", "MM_URL", "MM_WEBHOOK_URL"],
    },
    "objectives": [
        {"label": "Skill", "text": "Run supplied commands that gather the evidence behind four alerts, decide to close or escalate each one, post the decision, and check that the logs behind an empty search were really there."},
        {"label": "Tools", "text": "`python3 triage.py` (the supplied commands) searches Loki and prints the evidence and the checks. `oc` copies the runbook out of the cluster. `curl` and `jq` post each decision to the Mattermost alert channel. Loki stores the logs, Grafana raises the alerts and Mattermost holds the alert channel."},
        {"label": "Security Function", "text": "Detects whether an alert is expected or needs escalation, and detects missing or late logs, so an empty search is not read as proof that nothing happened."},
        {"label": "NIST AU-6 Audit Record Review, Analysis, and Reporting", "text": "`triage.py` prints the audit records behind each alert, and the decision you post to the Mattermost alert channel is the report."},
        {"label": "NIST IR-4 Incident Handling", "text": "The runbook (`triage.py` and its decision table) gives every analyst the same checks and the same outcomes for the detection and analysis phase."},
        {"label": "NIST AU-5 Response to Audit Logging Process Failures", "text": "`triage.py path` and `triage.py gaps` find a late log type and a span with no records, and you tell the platform team in the alert channel."},
    ],
    "requirement_bullets": [
        "Purpose: make sure people review what monitoring raises, decide quickly whether it is real, and notice when logs are missing or late (AU-6, IR-4, AU-5).",
        "You use a runbook and supplied triage.py commands for three alert types: a privilege change, a burst of failed sign-ins and a shell opened in a pod.",
        "You run the commands, read the evidence, decide to close or escalate, post each decision to the alert channel, and then run the path and gap checks.",
    ],
    "requirement": (
        "A regulated system must have people who look at what the monitoring tools raise (an alert is a message that a rule matched), work out quickly whether it is a real problem, "
        "and report what they find. They must also notice when the logs (lines of text that programs save about what happened) they depend on are missing or late, because an empty search "
        "result does not mean nothing happened. This module gives you a runbook (a written list of exact steps for one kind of alert) "
        "and supplied commands for three alert types: a privilege change (giving someone more permissions), a burst of failed sign-ins, and a shell opened in a pod (a window for typing commands, opened inside a running program). "
        "You run the commands, read the evidence, decide whether to close or escalate (hand the alert to someone with more authority), "
        "and record the decision in the alert channel. You build nothing and write no document."
    ),
    "mapping": [
        {
            "control": "AU-6 Audit Record Review, Analysis, and Reporting",
            "plain": "Review audit records for unusual activity, work out its impact, and report the findings to named people.",
            "source": "NIST",
            "tool": "The supplied triage.py commands and the Mattermost alert channel. Explained in section 2.1.",
            "covered": "Section 3, Steps 2 to 4: you review the records behind three alerts and post a finding for each in the alert channel.",
            "cite": [
                {"file": NIST, "quote": "Review and analyze system audit records [Assignment: organization-defined frequency] for"},
                {"file": NIST, "quote": "Report findings to [Assignment: organization-defined personnel or roles]"},
            ],
        },
        {
            "control": "IR-4 Incident Handling",
            "plain": "Handle an incident through preparation, detection and analysis, containment, eradication and recovery, and keep the handling comparable and predictable.",
            "source": "NIST",
            "tool": "The runbook, kept in the ConfigMap sdr-runbook, with its decision table. Explained in section 2.1.",
            "covered": "Section 3, Steps 2 to 4: the detection and analysis phase, with a fixed set of checks and a fixed rule for what to do next.",
            "cite": [
                {"file": NIST, "quote": "includes preparation, detection and analysis, containment, eradication, and recovery"},
                {"file": NIST, "quote": "Ensure the rigor, intensity, scope, and results of incident handling activities are comparable"},
            ],
        },
        {
            "control": "AU-5 Response to Audit Logging Process Failures",
            "plain": "When the logging process itself fails, alert named people within a set time.",
            "source": "NIST",
            "tool": "The path check and the gap check in triage.py, which read Loki, Grafana and Mattermost. Explained in section 2.3.",
            "covered": "Section 4, Tests 1 and 2: what a late log type and a gap in a log type look like, and the rule to escalate.",
            "cite": [
                {"file": NIST, "quote": "Alert [Assignment: organization-defined personnel or roles] within [Assignment: organization-defined time period] in the event of an audit logging process failure"},
            ],
        },
    ],
    "intent": [
        {
            "control": "AU-6 Audit Record Review, Analysis, and Reporting",
            "feared": "Alerts pile up in a channel, nobody can say which were real, and findings never reach the people who must act.",
            "scope": "Alerts and audit records for the components the team operates.",
            "question": "Take the last alert. Who looked at the records behind it, what did they find, and where is that written down?",
            "evidence": "The alert, the search that was run, the finding, and a time-stamped decision posted where the named recipients read.",
            "sufficient": "Every alert gets the same checks and a recorded outcome. NIST leaves the review frequency and the recipients organization-defined; FedRAMP sets the review frequency at least weekly. The lab reviews each alert as it arrives.",
            "tieoff": "Someone checks that no alert stays without a recorded decision.",
            "tool": "The supplied commands print the evidence and the checks. You post one decision line per alert.",
        },
        {
            "control": "IR-4 Incident Handling",
            "feared": "Each person triages a different way, so two people reach different answers from the same evidence, and real incidents are closed as noise.",
            "scope": "Alerts that may turn into incidents on the components the team operates.",
            "question": "Given the same alert, would any trained person on the team run the same checks and reach the same decision?",
            "evidence": "The runbook, the decision table, and decisions that match what the evidence shows.",
            "sufficient": "Handling is comparable and predictable: fixed checks, fixed rules, recorded results. This module covers only detection and analysis.",
            "tieoff": "Someone reviews closed alerts against the evidence now and then and corrects the runbook.",
            "tool": "triage.py prints the same checks every time; the decision table turns the checks into close or escalate.",
        },
        {
            "control": "AU-5 Response to Audit Logging Process Failures",
            "feared": "A log source goes quiet, every search comes back empty, and the empty result is read as proof that nothing happened.",
            "scope": "The logging path from the log sources to the searchable store.",
            "question": "If a search finds nothing, how do you know the logs were there to be searched?",
            "evidence": "A check of each hop of the path, the age of the newest record of each log type, and a search for spans with no records.",
            "sufficient": "Failures are noticed and named people are told within a time period. NIST leaves both organization-defined. The lab treats more than 5 minutes without a record as late and a span of more than 10 minutes as a gap.",
            "tieoff": "An alert exists for the failure itself, and someone owns the response.",
            "tool": "triage.py path reads each hop and the age of each log type; triage.py gaps lists spans with no records.",
        },
    ],
    "terms": [
        ("Triage", "A quick first look at an alert to decide whether it is real, how urgent it is, and what happens next."),
        ("Runbook", "A written list of exact steps, with the decision each result leads to. Here it is a set of commands plus a decision table."),
        ("Escalate", "Hand the alert to someone with more authority or more access, with the evidence you found."),
        ("Telemetry path", "The route a log takes from where it is written to where you search it: source, collector, Loki, Grafana, Mattermost."),
        ("Missing log", "A span of time in which a log type should have records and has none."),
        ("Late log", "A log type whose newest record is older than it should be, so recent events have not arrived yet."),
        ("Approved list", "The short list of changes and people the lab treats as expected. An alert that matches it can be closed."),
        ("Audit record", "One saved entry describing a request made to the cluster, with who asked, what, where and the result."),
        ("Falco", "A free runtime detector that watches what programs do inside containers and writes a record when a rule matches."),
        ("Alert", "A message a monitoring tool sends when one of its rules matches. It tells a person to take a look."),
        ("Log", "A line of text a program saves about something that happened, such as a sign-in or a request to the cluster."),
        ("Collector", "A small program that reads the logs on each node and sends them on to Loki."),
        ("Loki", "A free log store. It keeps log lines and lets you search them."),
        ("Grafana", "A free tool that draws charts and runs alert rules. A rule is a search that runs on a schedule and raises an alert when the result passes a limit."),
        ("Mattermost", "A free team chat tool. In this lab it holds the alert channel, where alerts arrive and decisions are posted."),
        ("Channel", "A named chat room in Mattermost. The alert channel is called siem-alerts."),
        ("ConfigMap", "A named bundle of small files stored in the cluster. The runbook is kept in one."),
        ("LogQL", "Loki's search language. A search names a label such as log_type and can then filter the lines."),
        ("Privilege change", "Giving a person or program more permissions than before, such as granting a powerful role to an account."),
        ("Role", "A named list of permissions. A role binding gives that list to an account."),
        ("Node", "One server in the cluster. Logs are first written on a node."),
        ("Namespace", "A named section of the cluster that keeps workloads apart. OpenShift also calls it a project, as in project siem."),
        ("Pod", "The smallest running unit on the cluster: one or more containers together."),
        ("Shell opened in a pod", "A window for typing commands that someone opens inside a running pod. It lets a person run any command there."),
        ("Keycloak", "The sign-in service in the lab. It writes a log line for every failed and every successful sign-in."),
        ("Exit code", "A number a command leaves behind when it ends. 0 means success; anything else means a problem."),
        ("Variable", "A named value the lab sets for you, such as MM_URL. A dollar sign before the name means use its value."),
        ("Hop", "One stop on the path a log takes, such as the collector or Loki. Each hop can fail on its own."),
        ("Cluster", "A group of servers that work together as one system. Here it is your own OpenShift cluster."),
        ("API", "The front door of a service, where programs send their requests. Every request to the cluster goes through its API."),
        ("Source address", "The network address a request or sign-in came from."),
        ("Webhook", "An address that accepts a message sent to it. The lab gives you one for the alert channel in the variable MM_WEBHOOK_URL; anyone who holds it can post to the channel, so never print it."),
        ("oc", "The command-line tool for OpenShift. You type oc to ask the cluster questions."),
        ("jq", "A tool that builds or picks values in JSON text. Here it builds the message you post."),
    ],
    "concepts": [
        {
            "heading": "2.1 What triage decides",
            "controls": [
                {"id": "AU-6 Audit Record Review, Analysis, and Reporting"},
                {"id": "IR-4 Incident Handling"},
            ],
            "paras": [
                {"bullets": [
                    "Triage is the first look at an alert: you fix nothing, and you collect the same facts every time.",
                    "The outcome is one of two: close the alert as expected, or escalate it (hand it to someone with more authority, with the evidence).",
                    "Without a fixed rule, real attacks get closed as noise and noise gets escalated until nobody trusts the channel.",
                    "The commands print facts and the table below turns the facts into the outcome. The table is the lab's choice; a real team's runbook sets its own.",
                ]},
                {
                    "control": "AU-6: Audit Record Review, Analysis, and Reporting",
                    "text": "The control asks the organization to review and analyze audit records at an organization-defined frequency for organization-defined inappropriate or unusual activity and its potential impact, to report findings to organization-defined personnel or roles, and to adjust the level of review when risk changes. This is done using:",
                },
                {"bullets": [
                    "triage.py: prints the audit records behind each alert and the checks to apply to them.",
                    "The Mattermost alert channel: where each alert arrives and where you post one finding for it, which is the report.",
                ]},
                {
                    "control": "IR-4: Incident Handling",
                    "text": "The control asks the organization to implement an incident handling capability that includes preparation, detection and analysis, containment, eradication, and recovery, and to make the rigor, intensity, scope and results of handling comparable and predictable. This module covers only detection and analysis. This is done using:",
                },
                {"bullets": [
                    "The runbook in the ConfigMap sdr-runbook: holds triage.py, which prints the same checks every time for an alert of the same type.",
                    "The decision table: turns the checks into close or escalate, so two analysts reach the same outcome from the same evidence.",
                ]},
                "The table below shows how each finding leads to an outcome:",
            ],
            "table": {
                "headers": ["Finding", "Outcome", "Why"],
                "rows": [
                    ("The change or person matches the approved list and the role (a named list of permissions) is not admin-level (full control)","Close and record", "It was planned and low risk."),
                    ("A source failed sign-in several times and then succeeded", "Escalate now", "The account may be taken over."),
                    ("The actor is not on the approved list", "Escalate", "An unplanned action by a person."),
                    ("The expected record is missing", "Do not close. Check the path. Escalate as a logging gap if the path shows one", "An empty search may mean the logs were not there."),
                ],
            },
        },
        {
            "heading": "2.2 The path a log takes",
            "paras": [
                {"bullets": [
                    "A log is written on a node (a server in the cluster) and read by a collector (a small program that sends logs onward). It is then stored in Loki, watched by Grafana and announced in Mattermost.",
                    "Each stop on the path (node, collector, Loki, Grafana, Mattermost) is a hop, and each hop can fail on its own.",
                    "When a search is empty, find which hop failed before you decide anything. The path check prints one line per hop.",
                ]},
                "The table below lists each hop, what it does and what its failure looks like:",
            ],
            "table": {
                "headers": ["Hop", "What it does", "What a failure looks like"],
                "rows": [
                    ("Collector", "Reads logs on each node and sends them to Loki", "Fewer collector pods Running than nodes; every log type stops together"),
                    ("Loki", "Stores and indexes the records", "The ready check does not answer"),
                    ("Records in Loki", "Hold the events you search for", "A log type whose newest record is old (late), or a span with none (gap)"),
                    ("Grafana", "Runs the alert rules", "The health check does not answer; alerts stop without a sound"),
                    ("Mattermost", "Shows the alert to people", "The ping does not answer; alerts fire but nobody sees them"),
                ],
            },
        },
        {
            "heading": "2.3 Missing and late are different",
            "controls": [
                {"id": "AU-5 Response to Audit Logging Process Failures"},
            ],
            "paras": [
                {"bullets": [
                    "A late log arrives eventually, so evidence for recent events is incomplete for now. A missing log never arrives, so a span of time has no evidence at all. Either way, do not trust an empty search.",
                    "The lab chooses its own limits, not framework values: a log type is late when its newest record is more than 5 minutes old, and a gap is a span of more than 10 minutes with no record.",
                    "The exercise records carry the labels lab_seed and seed_run so they do not mix with the real records of your cluster or with a copy left from an earlier lab start. A real search would not have these labels.",
                    "The exercise records are fixed in time, so the path check measures their age from the moment the exercise started. On a real system the age is measured from now.",
                ]},
                {
                    "control": "AU-5: Response to Audit Logging Process Failures",
                    "text": "The control asks the organization to alert organization-defined personnel or roles within an organization-defined time period when the audit logging process fails, and to take organization-defined additional actions. This is done using:",
                },
                {"bullets": [
                    "triage.py path: reads each hop of the log path and the age of the newest record of each log type, which finds a late log type.",
                    "triage.py gaps: lists the spans with no records, using the lab limit of 10 minutes.",
                    "The Mattermost alert channel: where you tell the platform team about the failure.",
                ]},
            ],
        },
    ],
    "steps": [
        {
            "title": "Fetch the runbook and read the four alerts",
            "learn": "Copying the runbook out of the cluster and printing the four alerts gives you the commands, the approved list and the alerts to triage.",
            "takeaway": "Triage starts from the same runbook and the same alert list for everyone.",
            "why": "The runbook files live in the cluster as a ConfigMap (a named bundle of small files). You extract them into your lab shell and read the four alerts that the start command posted to the alert channel in Mattermost. Each alert has an identifier such as A-101, a type and the time it was raised.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p /workspace/sdr-2 && cd /workspace/sdr-2\n"
                        "oc extract configmap/sdr-runbook -n siem --to=. --confirm > /dev/null\n"
                        "ls\n"
                        "cat approved.json\n"
                        "python3 triage.py alerts"
                    ),
                    "label": 'Fetch the runbook and look at it',
                    "intro": 'You will now copy the runbook files from the cluster into a folder of your own, read the approved list and print the four alerts. You can run this block again; it overwrites the same files.',
                    "expect": 'Example only. The order of the lines may differ.\nanchor.txt  approved.json  lokilib.py  triage.py\n{ ...the approved list: one privilege change and one person... }\nALERT   A-101  privilege-change     raised <time>  namespace=demo a role binding was created\n(three more ALERT lines: A-102, A-103, A-104)',
                    "lines": [
                        ("mkdir -p ... && cd ...", "Makes a folder for this module and moves into it, so files from other modules cannot collide with yours. The folder persists between lab sessions.", "You run triage.py from this folder in every later step, so one known folder saves you hunting for the files."),
                        ("oc extract configmap/sdr-runbook ... > /dev/null","Copies each file in the ConfigMap into the current folder and hides the list of file names it would print. --confirm lets it overwrite files from an earlier run.", "The runbook is stored on the cluster so every learner gets the same copy. Copying it into lab shell is what lets you run it."),
                        ("ls", "Lists the files: triage.py is the supplied commands, approved.json the approved list, anchor.txt the exercise start time, `lokilib.py` the helper that searches Loki.", "Check that all four files arrived before you try to run one of them."),
                        ("cat approved.json", "Prints the approved list: one privilege change (a grant of more permissions) and one person allowed to open a shell in the demo project.", "Every alert is compared with this list, so read it now to know what counts as expected."),
                        ("python3 triage.py alerts", "Prints the four alerts that the start command posted to the alert channel: identifier, type, the time it was raised and the text of the alert.", "You read the alerts here, so no Mattermost login is needed. Later steps call the same program, triage.py, for each alert."),
                    ],
                }
            ],
            "action": "Run the commands and read the four alerts, A-101 to A-104.",
            "checkpoint": "You have triage.py and approved.json in your folder, and the alerts command lists four alerts with their types.",
        },
        {
            "title": "Triage the privilege-change alert (A-101)",
            "learn": "Running the privilege-change check prints the role binding behind A-101 and compares it with the approved list, so your decision rests on records and not on the alert text.",
            "takeaway": "Compare the alert with the approved list before you decide, and post the decision.",
            "controls": [
                {"id": 'AU-6 Audit Record Review, Analysis, and Reporting', "how": 'You run the search for the role binding behind alert A-101, read who made it, and post a finding to the alert channel. The posted line is the report.'},
                {"id": 'IR-4 Incident Handling', "how": 'The command prints the same checks for every privilege-change alert, and the decision table turns them into close or escalate. Your posted outcome lets another analyst check it.'},
            ],
            "why": "A privilege change is a grant of more permissions to someone. The supplied command searches the audit records (the cluster's record of every request) for role bindings created around the alert, prints who made them and compares the result with the approved list. The command also prints each search it runs, so you can see the LogQL (Loki's search language) used.",
            "blocks": [
                {
                    "code": (
                        "cd /workspace/sdr-2\n"
                        "python3 triage.py privilege A-101"
                    ),
                    "label": 'Run the privilege-change checks for A-101',
                    "intro": 'You will now run the supplied triage command for the first alert. The command only reads from Loki and prints facts.',
                    "expect": 'Example only. Times and names differ in your lab.\nALERT   A-101  type <alert type>  raised <time>\nSEARCH  <the LogQL search it ran>\nEVENT   <time>  <the role binding that was created, and who created it>\nCHECK   <namespace>/<name> matches an approved change (actor, name, role, subject)   <yes or no>\nCHECK   role is admin-level (admin or cluster-admin)   <yes or no>',
                    "lines": [
                        ("cd /workspace/sdr-2", "Moves into the module folder from step 1.", "triage.py and its files are in that folder, so every block starts there."),
                        ("python3 triage.py", "Runs the supplied triage program.", "This is the one program every triage step calls, so you meet its name before its options."),
                        ("privilege A-101", "Tells it to triage a privilege-change alert with this identifier.", "The word after the program name picks the kind of checks. The identifier names the alert, so the search is centered on the time it was raised."),
                    ],
                },
                {
                    "code": (
                        "jq -n --arg t \"A-101 CLOSE: matches the approved list; role is view, not admin-level\" '{text:$t}' | curl -s -o /dev/null -w 'posted, HTTP %{http_code}\\n' -H 'Content-Type: application/json' -d @- \"$MM_WEBHOOK_URL\""
                    ),
                    "label": 'Post your decision for A-101',
                    "intro": 'You will now write your decision as one line in the alert channel.',
                    'expect': 'Example only.\nposted, HTTP 200',
                    "screenshot": {"file": "SDR-2-shot-4b-mattermost.png", "alt": "The Mattermost SIEM alerts channel showing the posted decision", "width": 6.0},
                    "lines": [
                        ("jq -n --arg t ... '{text:$t}'", "Builds the small message body that Mattermost expects, with your decision as the text.", "Your decision has to be a short sentence in the shape the chat tool accepts. jq builds it safely, so a quote in your words cannot break the message."),
                        ("curl -s -o /dev/null -w ... -d @-", "Posts it and prints only the status code Mattermost answers with. 200 means the message was accepted into the channel. The address comes from the variable MM_WEBHOOK_URL (a webhook is an address that accepts messages), so no secret is typed.", "Posting the decision is the record of your triage. Without it the alert has no outcome that anyone can check later."),
                    ],
                },
            ],
            "note": "If you decide on a different outcome, change the words after the identifier.",
            "action": "Run the first command and read every line. Decide using the table in 2.1. Then post your decision with the second command and check that it prints HTTP 200.",
            "checkpoint": "The CHECK lines show a match with the approved list and a role that is not admin-level, and the post prints HTTP 200.",
        },
        {
            "title": "Triage the failed sign-in burst (A-102)",
            "learn": "Grouping the sign-in records by account and source address shows whether failures from one source were followed by a success, which a single line cannot show.",
            "takeaway": "A success after repeated failures from one source is escalated.",
            "controls": [
                {"id": 'AU-6 Audit Record Review, Analysis, and Reporting', "how": 'You read the sign-in records grouped by account and address, find the source whose failures were followed by a success, and post that finding to the alert channel.'},
                {"id": 'IR-4 Incident Handling', "how": 'The grouped rows and the last CHECK line apply a fixed rule: a success after repeated failures from one source is escalated. Your posted line gives the outcome and its reason.'},
            ],
            "why": "A burst of failed sign-ins is many wrong passwords from one place in a short time, recorded by Keycloak, the lab's sign-in service. One burst of failures may be a mistyped password. A burst matters most when a success follows from the same source address (the network address the sign-in came from), because the guesser may have got in. The command groups the sign-in records by account and source address and shows whether a success came after the last failure.",
            "blocks": [
                {
                    "code": (
                        "cd /workspace/sdr-2\n"
                        "python3 triage.py signin A-102"
                    ),
                    "label": 'Run the failed sign-in checks for A-102',
                    "intro": 'You will now run the supplied triage command for the second alert. The command reads the sign-in records in Loki and prints one row per account and source address.',
                    "expect": 'Example only. Accounts, addresses and times differ in your lab.\nALERT   A-102  type <alert type>  raised <time>\nSEARCH  <the LogQL search it ran>\n<row 1: an account and address with 7 failures, LATER_SUCCESS <time>>\n<row 2: an account and address with 3 failures, LATER_SUCCESS none>\nCHECK   <last check line>   yes',
                    "lines": [
                        ("cd /workspace/sdr-2", "Moves into the module folder from step 1.", "triage.py is in that folder."),
                        ("signin A-102", "Searches the sign-in records around the alert and prints one row per account and source address.", "One failed sign-in and a break-in can look alike in a single line. Grouping by account and address is what tells them apart."),
                    ],
                },
                {
                    "code": (
                        "jq -n --arg t \"A-102 ESCALATE: a source with repeated failures was followed by a success; account may be taken over\" '{text:$t}' | curl -s -o /dev/null -w 'posted, HTTP %{http_code}\\n' -H 'Content-Type: application/json' -d @- \"$MM_WEBHOOK_URL\""
                    ),
                    "label": 'Post your decision for A-102',
                    "intro": 'You will now write your escalation, with its reason, as one line in the alert channel.',
                    'expect': 'Example only.\nposted, HTTP 200',
                    "lines": [
                        ("--arg t \"A-102 ESCALATE ...\"", "The decision line. It names the alert, the outcome and the reason.", "An escalation must carry its reason, so the person who receives it does not have to repeat your search."),
                    ],
                },
            ],
            "security": "Do not copy account names or addresses from an alert into places outside the alert channel. Say which row you mean by its position in the table.",
            "action": "Run the first command. Look at both rows: one source has a time under LATER_SUCCESS, the other says none. Post your decision.",
            "checkpoint": "One row shows seven failures followed by a success from the same address, the other shows three failures and none, and the last CHECK line says yes.",
        },
        {
            "title": "Triage the shell opened in a pod (A-103)",
            "learn": "Pairing the Falco record with the audit record names the person who opened the shell, which neither record can do alone.",
            "takeaway": "Do not close a shell alert until an audit record names the person.",
            "controls": [
                {"id": 'AU-6 Audit Record Review, Analysis, and Reporting', "how": 'You pair the Falco record with the audit record that names the person, compare the person with the approved list, and post a finding to the alert channel.'},
                {"id": 'IR-4 Incident Handling', "how": 'The command always pairs the two sources and checks the approved list, so a close decision rests on named evidence. If no audit record names the person, the runbook rule is not to close the alert.'},
            ],
            "why": "A shell opened inside a running pod lets a person run any command there. Two sources help: the runtime detector Falco says a shell was opened and in which pod, and the audit records say which person asked the cluster's API (the front door for requests to the cluster) to do it. The command pairs the Falco and audit records; if no audit record names the person, you cannot say who did it.",
            "blocks": [
                {
                    "code": (
                        "cd /workspace/sdr-2\n"
                        "python3 triage.py shell A-103"
                    ),
                    "label": 'Run the shell-in-a-pod checks for A-103',
                    "intro": 'You will now run the supplied triage command for the third alert. The command pairs the Falco record with the audit record.',
                    "expect": 'Example only. Times and the pod name differ in your lab.\nALERT   A-103  type shell-in-pod  raised <time>\nSEARCH  <the search for the Falco record>\nEVENT   <time>  shell in <namespace>/<pod> as <user>\nSEARCH  <the search for the audit record>\nCHECK   an API audit record names who opened the shell             yes\nEVENT   <time>  <the person> ran exec on <pod>\nCHECK   actor is on the approved shell list for <namespace>   <yes or no>',
                    "lines": [
                        ("cd /workspace/sdr-2", "Moves into the module folder from step 1.", "triage.py is in that folder."),
                        ("shell A-103", "Finds the Falco record, then the audit record for the same pod, and checks the person against the approved list.", "Falco alone cannot say who opened the shell, and the audit record alone cannot say what ran. Pairing them is how you name the person."),
                    ],
                },
                {
                    "code": (
                        "jq -n --arg t \"A-103 CLOSE: shell opened by an approved person in the demo project; audit record found\" '{text:$t}' | curl -s -o /dev/null -w 'posted, HTTP %{http_code}\\n' -H 'Content-Type: application/json' -d @- \"$MM_WEBHOOK_URL\""
                    ),
                    "label": 'Post your decision for A-103',
                    "intro": 'You will now write your decision as one line in the alert channel.',
                    'expect': 'Example only.\nposted, HTTP 200',
                    "lines": [
                        ("A-103 CLOSE", "The decision line for an expected shell with a named, approved person.", "You may close only because an approved person and an audit record were both found. The line says so, so a reviewer can check it."),
                    ],
                },
            ],
            "action": "Run the first command and read both searches it prints. Decide and post.",
            "checkpoint": "Both an audit record and a Falco record are found, the person is on the approved list, and the post prints HTTP 200.",
        },
    ],
    "verify": [
        {
            "kind": "positive",
            "title": "The path check names the late log type",
            "controls": [
                {"id": 'AU-5 Response to Audit Logging Process Failures', "how": 'The path check reads each hop and the age of the newest record of each log type, and it marks the late one. Finding the late infrastructure log is the detection that must come before anyone can be alerted.'},
            ],
            "why": "Before you trust any empty result you must know the logs were there and the telemetry path (the route a log takes to where you search it) was healthy. You checked your three decisions against the CHECK lines in Steps 2 to 4. A healthy path would print no LATE line. This exercise has one late log type, and finding it is the point. The rule for a late log is to carry on with the triage, note the lateness in your decision line, and tell the platform team.",
            "code": (
                "cd /workspace/sdr-2\n"
                "python3 triage.py path"
            ),
            "expect": (
                "Example only. The collector line depends on your cluster.\n"
                "HOP 1 collector  1 of 1 pods Running\n"
                "HOP 2 Loki       ready\n"
                "HOP 3 audit          newest record 2 minutes old  ok\n"
                "HOP 3 infrastructure newest record 24 minutes old  LATE\n"
                "HOP 3 application    newest record 2 minutes old  ok\n"
                "HOP 4 Grafana    answers\n"
                "HOP 4 Mattermost answers\n"
                "SUMMARY 1 hop(s) need attention"
            ),
            "lines": [
                ("cd /workspace/sdr-2 and python3 triage.py path", "Moves into the module folder, then checks each hop in order: the collector pods, Loki, the newest record of each log type, then Grafana and Mattermost.", "An empty search only means something if every hop works, so you check them before you trust it."),
                ("HOP 3 ... newest record N minutes old", "How old the newest record of that log type is. More than 5 minutes (the lab limit) is marked LATE.", "A late log type means recent events may not have arrived yet."),
                ("HOP 3 infrastructure ... LATE", "The one late log type in this exercise.", "Finding it is the point of the test."),
                ("SUMMARY 1 hop(s) need attention", "The count of hops that failed or are late.", "One is the expected answer here; a healthy path prints 0."),
            ],
            "checkpoint": "Only the infrastructure line says LATE, and the summary counts one hop needing attention.",
        },
        {
            "kind": "negative",
            "title": "A missing log: the shell alert with no audit record (A-104)",
            "controls": [
                {"id": 'AU-5 Response to Audit Logging Process Failures', "how": 'The shell command stops with a non-zero exit code instead of guessing, and the gap check shows the span with no audit records. You escalate it as a logging gap rather than closing the alert.'},
                {"id": 'IR-4 Incident Handling', "how": 'The runbook rule for a missing record is the same every time: do not close, check the path, and escalate. The exit code makes that rule hard to skip.'},
            ],
            "why": "You will now triage alert A-104, which is also a shell opened in a pod. For alert A-104 the audit record is missing, so the command stops with a non-zero exit code (a number a command leaves behind when it ends; 0 means success) instead of guessing. A good runbook step stops when evidence is missing, and the gap check then shows why. After the gap check, post an escalation with the same jq and curl command as in Step 3, with your words changed to say the person is unknown because the audit log has a gap.",
            "code": (
                "cd /workspace/sdr-2\n"
                "python3 triage.py shell A-104; echo \"exit code $?\"\n"
                "python3 triage.py gaps | head -n 1"
            ),
            "expect": (
                "Example only. Times and the pod name differ in your lab.\n"
                "ALERT   A-104  type shell-in-pod  raised <time>\n"
                "SEARCH  {log_type=\"application\", kubernetes_namespace_name=\"security-tools\", lab_seed=\"sdr-2\", seed_run=\"<run number>\"} |= \"Terminal shell\"\n"
                "EVENT   <time>  shell in demo/demo-batch-7f9c4d5b6-k2m8n as root\n"
                "SEARCH  {log_type=\"audit\", lab_seed=\"sdr-2\", seed_run=\"<run number>\"} |= \"demo-batch-7f9c4d5b6-k2m8n\" |= \"exec\"\n"
                "CHECK   an API audit record names who opened the shell             NO\n"
                "RESULT  no audit record. The person cannot be named. Run: python3 triage.py gaps\n"
                "exit code 2\n"
                "GAP     audit          <start> to <end>  (28 minutes with no record)"
            ),
            "lines": [
                ("python3 triage.py shell A-104; echo \"exit code $?\"", "Runs the shell checks for the fourth alert, then prints the exit code.", "The exit code shows that the command stopped instead of guessing."),
                ("CHECK ... NO", "No audit record names who opened the shell.", "Without it you cannot say who did it, so you must not close the alert."),
                ("exit code 2", "A non-zero number: evidence was missing.", "A runbook step that stops with a non-zero code cannot be skipped by accident."),
                ("python3 triage.py gaps | head -n 1", "Prints the first gap found, which is in the audit log.", "It explains why the audit record is missing."),
                ("GAP audit ... (28 minutes with no record)", "A span of 28 minutes with no audit record, which covers the time of the shell.", "A logging gap, not a quiet night, is the reason; you escalate it."),
            ],
            "checkpoint": "The shell was seen by Falco but no audit record names the person, and the gap check shows an audit span with no records that covers the time of the shell. Do not close it.",
        },
    ],
    "glossary": [
        ("Triage", "A quick first look to decide whether an alert is real and what to do next."),
        ("Runbook", "A written list of exact steps with the decision each result leads to."),
        ("Escalate", "Hand the alert to someone with more authority, with the evidence."),
        ("Telemetry path", "The route a log takes from the source to where you search it."),
        ("LogQL", "Loki's search language."),
        ("Collector", "A small program on each node that reads logs and sends them onward."),
        ("ConfigMap", "A named bundle of small files stored in the cluster."),
        ("Falco", "A free runtime detector that writes a record when a rule matches what a program does inside a container."),
    ],
    "design": [
        {
            "decision": "Commands print facts and a table decides",
            "how": "The supplied commands print the same CHECK lines for each alert type, and a decision table in the runbook turns those checks into close or escalate. The analyst posts one decision line per alert to the alert channel.",
            "why": "Comparable handling means two analysts reach the same outcome from the same evidence, and the decision stays with a person while the command only gathers facts.",
            "alternatives": "The advantage of letting the command close alerts by itself is that it is faster and fully consistent. The drawback is that one wrong rule would silently close a real attack, and nobody practices judgment.",
        },
        {
            "decision": "Check the path before trusting an empty result",
            "how": "The path check tests each hop from the collector to the chat channel and reads the age of the newest record per log type, and the gap check lists spans with no records. When the audit record is missing, the shell command exits with a non-zero code instead of guessing.",
            "why": "An empty search may only mean the logs were not there, and a late log and a missing log call for different responses.",
            "alternatives": "The advantage of treating no record as no event is that it is simple and fast. The drawback is that a logging failure then looks like a quiet night, which is the worst case for an audit trail.",
        },
    ],
    "next": "Next module: SDR-3 Investigate and Tune: investigate an alert in Loki yourself and tune the alert rule so it fires on real problems, not noise.",
}

MODULE["portability"] = {
    "bullets": [
        "The triage script, the runbook files and the decision table are plain Python, curl and jq against the Loki, Grafana and Mattermost HTTP APIs, so they run anywhere those three answer.",
        "Change these lab values first: the LOKI_URL, LOKI_CA_FILE, LOKI_USER and LOKI_PASSWORD variables, GRAFANA_URL, MM_URL and MM_WEBHOOK_URL, and the channel name siem-alerts.",
        "The lab labels (kubernetes_namespace_name=security-tools, the lab_seed label) and the namespaces siem, openshift-logging and chat are lab choices. Your log store may use other label names and namespaces.",
        "The oc extract of the sdr-runbook ConfigMap and the collector pod check are cluster-specific. On other Kubernetes use kubectl, or keep the runbook files in git.",
    ],
    "headers": ["Check", "In this lab (OpenShift)", "On other platforms", "What you change"],
    "rows": [
        ("Fetch the runbook", "oc extract configmap/sdr-runbook -n siem", "kubectl get configmap sdr-runbook -n <namespace> -o json, or read the files from git", "The tool name and the namespace."),
        ("Searches in Loki", "LogQL over the labels log_type, kubernetes_namespace_name, lab_seed and seed_run", "The same LogQL if you run Loki. Another log store needs its own query language", "The label names, and drop lab_seed and seed_run."),
        ("Collector hop in the path check", "Pods in openshift-logging labeled app.kubernetes.io/component=collector", "Your log shipper's pods or agent status", "The namespace and the pod label."),
        ("Keycloak sign-in records", "Application logs from the keycloak namespace, LOGIN_ERROR and LOGIN lines", "The same lines if you run Keycloak. Another identity provider logs its own event names", "The namespace and the event names."),
        ("Audit records", "OpenShift API audit log in Loki", "The provider's Kubernetes audit log, if it is collected", "The label and field names. Replace the check if the audit log is not collected."),
        ("Falco shell record", "Falco lines in Loki from the security-tools namespace", "The same, if Falco ships to your log store", "The namespace."),
        ("Alert channel", "Mattermost webhook in MM_WEBHOOK_URL", "Any chat tool with an incoming webhook", "The URL variable and the JSON field the tool expects."),
    ],
}
