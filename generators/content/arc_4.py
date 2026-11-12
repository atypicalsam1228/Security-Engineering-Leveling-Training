"""ARC-4: Test Two Designs (security architecture, level 4)."""

NIST = "nist-sp-800-53r5-full.md"
FEDRAMP_MOD = "fedramp-moderate-baseline.md"
FEDRAMP_HIGH = "fedramp-high-baseline.md"

HARNESS_PY = (
    "import json\n"
    "import subprocess\n"
    "import sys\n"
    "\n"
    "PROBE = (\n"
    "    \"import urllib.request as u\\n\"\n"
    "    \"try:\\n\"\n"
    "    \"    print(u.urlopen('http://db:8080', timeout=5).status)\\n\"\n"
    "    \"except Exception as e:\\n\"\n"
    "    \"    print(getattr(e, 'code', 'fail'))\"\n"
    ")\n"
    "\n"
    "\n"
    "def probe(ns, source):\n"
    "    cmd = [\"oc\", \"exec\", source, \"-n\", ns, \"-c\", \"app\", \"--\", \"python3\", \"-c\", PROBE]\n"
    "    done = subprocess.run(cmd, capture_output=True, text=True, timeout=60)\n"
    "    return done.stdout.strip() or \"error\"\n"
    "\n"
    "\n"
    "def run(ns, cases):\n"
    "    codes = {c[\"name\"]: probe(ns, c[\"from\"]) for c in cases}\n"
    "    leaks = [c[\"name\"] for c in cases if c[\"attack\"] and codes[c[\"name\"]] == \"200\"]\n"
    "    legit = all(codes[c[\"name\"]] == \"200\" for c in cases if not c[\"attack\"])\n"
    "    return {\"codes\": codes, \"leaks\": leaks, \"legit_ok\": legit}\n"
    "\n"
    "\n"
    "cases = json.load(open(sys.argv[1]))\n"
    "print(json.dumps({ns: run(ns, cases) for ns in sys.argv[2:]}, indent=2))"
)

CASES_JSON = (
    "[\n"
    "  {\"name\": \"api-to-db\", \"from\": \"deploy/api\", \"attack\": false},\n"
    "  {\"name\": \"web-to-db\", \"from\": \"deploy/web\", \"attack\": true},\n"
    "  {\"name\": \"stranger\", \"from\": \"pod/atk-stranger\", \"attack\": true},\n"
    "  {\"name\": \"copied-label-plain\", \"from\": \"pod/atk-copied-plain\", \"attack\": true},\n"
    "  {\"name\": \"copied-label-mesh\", \"from\": \"pod/atk-copied-mesh\", \"attack\": true}\n"
    "]"
)

MESH_YAML = (
    "apiVersion: security.istio.io/v1\n"
    "kind: PeerAuthentication\n"
    "metadata: {name: default, namespace: arc-b}\n"
    "spec:\n"
    "  mtls:\n"
    "    mode: STRICT\n"
    "---\n"
    "apiVersion: security.istio.io/v1\n"
    "kind: AuthorizationPolicy\n"
    "metadata: {name: db-from-api, namespace: arc-b}\n"
    "spec:\n"
    "  selector: {matchLabels: {app: db}}\n"
    "  action: ALLOW\n"
    "  rules:\n"
    "    - from:\n"
    "        - source:\n"
    "            principals: [\"cluster.local/ns/arc-b/sa/api\"]"
)

ARC = "\"$HOME/arc"
HARNESS_RUN = f"python3 {ARC}/harness.py\" {ARC}/cases.json\""

MODULE = {
    "intent_at_end": True,
    "id": "ARC-4",
    "slug": "TwoDesigns",
    "title": "Test Two Designs",
    "draft": (
        "Run live on 2026-11-10 and again on 2026-11-11 with the Step 4b change; every step and test passed (see live-run/findings-ARC-4.md). The mesh uses sailoperator.io/v1, istiod in istio-system and security.istio.io/v1 policies, all confirmed by server dry run. "
        "A pod with a sidecar and the wrong service account gets HTTP 403, and a pod without a sidecar is refused under STRICT mutual TLS. With the control plane scaled to zero, existing sidecars keep enforcing and no new database pod appears in arc-b; the Sail operator did not restore istiod while it was at zero. "
        "After istiod returns, the database ReplicaSet can stay in backoff, so Step 4b restarts the deployment; the step takes about 8 minutes. Re-running Step 1b prints unchanged instead of created. Istio 1.31.1 lists istio-proxy under initContainers (native sidecars). "
        "Several arc modules share one folder; run lab start arc-4 right before this module."
    ),
    "controls": ["SC-7", "SC-8", "SC-24", "SA-8"],
    "mentions": [],
    "unit_values_ok": ["15 seconds", "60 seconds", "8 minutes"],
    "minutes": {"hands_on": 39, "verify": 12},
    "terms_at_end": True,
    "tools": ["OpenShift Container Platform", "Kubernetes NetworkPolicy", "Red Hat OpenShift Service Mesh 3 (Istio based)", "oc", "jq", "python3"],
    "tool_why": True,
    "hide_draft": True,
    "hover": True,
    "diagrams": [
        {
            "id": "designs",
            "title": "Same attacks, two designs",
            "caption": "This is the lab (test) setup: project arc-a (Design A) uses network policies alone, project arc-b (Design B) adds the service mesh with mutual TLS and an identity rule on the database, and one harness sends the same attack cases to both. In production there are no deliberate attack pods, and the harness would run on a schedule from a pipeline.",
            "skip_steps": [4],
            "per_step": True,
            "rankdir": "LR",
            "step_notes": {
                1: "You apply the network policies to both projects in the cluster, and the mesh policies to arc-b only. The api may call the database in each.",
                2: "You write the harness and the cases file in your arc folder in lab shell. Later the harness sends the same cases to both projects.",
                3: "The harness runs each case with oc exec, from inside the sender in the cluster, and the sender tries the database in the same project. Design A lets the copied-label pods in. Design B blocks them.",
            },
            "zones": [
                {"id": "shell", "label": "Your lab shell", "kind": "boundary"},
                {"id": "cluster", "icon": "aws/group-AWS-Cloud", "label": "Your cluster (your OpenShift cluster, in AWS)", "kind": "boundary"},
                {"id": "pa", "icon": "brands/openshift", "label": "Project arc-a: policies only", "parent": "cluster", "kind": "group"},
                {"id": "pb", "icon": "brands/openshift", "label": "Project arc-b: policies and mesh", "parent": "cluster", "kind": "group", "labeljust": "r"},
                {"id": "ctl", "icon": "brands/openshift", "label": "Project istio-system: mesh control plane", "parent": "cluster", "kind": "group"},
            ],
            "key": {"k8s/deploy": "Kubernetes deployment", "k8s/pod": "Kubernetes pod", "brands/python": "Python script", "brands/openshift": "OpenShift project", "aws/group-AWS-Cloud": "AWS Cloud"},
            "nodes": [
                {"id": "harness", "title": "Harness", "icon": "brands/python", "sub": "Python script harness.py", "zone": "shell", "s": 2},
                {"id": "aapi", "title": "Api in Design A", "icon": "k8s/deploy", "sub": "Kubernetes deployment api", "zone": "pa"},
                {"id": "adb", "title": "Database in Design A", "icon": "k8s/deploy", "sub": "Kubernetes deployment db, network policy only", "zone": "pa"},
                {"id": "aatk", "title": "Copied-label pods in Design A", "icon": "k8s/pod", "sub": "Kubernetes attack pods", "zone": "pa", "kind": "warn", "s": 3},
                {"id": "bapi", "title": "Api in Design B", "icon": "k8s/deploy", "sub": "Kubernetes deployment api", "zone": "pb"},
                {"id": "bdb", "title": "Database in Design B", "icon": "k8s/deploy", "sub": "Kubernetes deployment db, policy, mTLS, identity", "zone": "pb"},
                {"id": "batk", "title": "Copied-label pods in Design B", "icon": "k8s/pod", "sub": "Kubernetes attack pods", "zone": "pb", "kind": "bad", "s": 3},
                {"id": "istiod", "title": "Mesh control program", "icon": "k8s/deploy", "sub": "Kubernetes deployment, the mesh control plane", "zone": "ctl"},
            ],
            "edges": [
                {"a": "aapi", "b": "adb", "label": "Allowed", "kind": "ok"},
                {"a": "bapi", "b": "bdb", "label": "Allowed", "kind": "ok"},
                {"a": "harness", "b": "aatk", "label": "Runs cases", "s": 3},
                {"a": "harness", "b": "batk", "label": "Runs cases", "s": 3},
                {"a": "aatk", "b": "adb", "label": "Gets in", "kind": "warn", "s": 3},
                {"a": "batk", "b": "bdb", "label": "Blocked", "kind": "bad", "s": 3},
                {"a": "istiod", "b": "bdb", "label": "Certificate"},
            ],
            "why_built": (
                "You work in lab shell on your laptop, and both designs run on your own cluster. "
                "This module adds two projects, arc-a and arc-b, that hold the same three parts, so the only thing that differs is the protection around the database. "
                "Design B also adds the service mesh to the cluster, which puts a sidecar in each pod in arc-b and a control plane in its own project, istio-system, so you can see what the extra layer blocks. "
                "The harness runs in lab shell and reaches into each sender with oc exec, because an attack only counts if it starts from inside the project, as a compromised pod would. "
                "Both projects get the same network policies, so any difference in the results comes from the mesh and not from the policies. "
                "The control plane sits outside both projects because it serves every project that uses the mesh, which is why stopping it is a shared failure."
            ),
            "setup": [
                ("Lab shell", "A container on your laptop", "The harness and the cases file live here, and it reaches the cluster only with oc, so the same test code runs against both designs."),
                ("Project arc-a", "On your cluster", "Design A: the three parts protected by network policies alone, so the baseline is clear."),
                ("Project arc-b", "On your cluster", "Design B: the same three parts with the same network policies plus mutual TLS and an identity rule, so only the mesh differs."),
                ("Sidecars", "Inside each pod in arc-b", "They do the encryption and the identity check next to the program, so the program does not change."),
                ("Mesh control plane", "Project istio-system on your cluster", "It issues certificates and adds sidecars for every mesh project, so it is a shared part that can fail."),
                ("Attack pods", "In both projects", "They start from inside the project, which is where a compromised part would be."),
            ],
            "reading": [
                "1. Harness: the Python script harness.py in your lab shell. It sends the same five cases to both projects.",
                "2. Api in Design A: the api part in arc-a. It is the only part the network policy lets call the database.",
                "3. Database in Design A: the data store in arc-a, guarded by a network policy only.",
                "4. Copied-label pods in Design A: attack pods that carry the api label but are not the api. The label match lets them in.",
                "5. Api in Design B: the api part in arc-b, with a sidecar and the service account the database accepts.",
                "6. Database in Design B: the data store in arc-b. It needs the network policy, mutual TLS and the api identity.",
                "7. Copied-label pods in Design B: attack pods with the api label. One has no sidecar and one has a sidecar with the wrong service account. Both are blocked.",
                "8. Mesh control program: the mesh control plane in istio-system. It issues the certificates and adds the sidecars that arc-b depends on.",
            ],
        },
    ],
    "prereq": [
        "ENG-0 Terminal, Git and Your Lab (typing commands in lab shell, making a file with a heredoc, reading oc output)",
    ],
    "lab_needs": [],
    "lab": {
        "start": "lab start arc-4",
        "env": [],
    },
    "requirement": (
        "A regulated system needs more than a rule that says who may talk to whom. It needs to know whether the rule survives an attacker who copies what the rule looks at. "
        "This module compares two ways to isolate the same three workloads (programs the cluster runs, which is your lab's group of servers). Design A uses network policies alone (rules for which pods may talk to which): the cluster decides by pod label, where a pod is one running copy of a program and a label is a key=value tag on it. Design B adds the service mesh (helper programs that add identity and encryption to the traffic between pods): "
        "each pod proves its identity with a certificate (a digital document that proves who a program is), the traffic is encrypted, and the database accepts only the identity of the api. You build both, send the same five cases (test requests) at "
        "each, and compare what each blocks and how it behaves when a part of it fails."
    ),
    "requirement_bullets": [
        "Purpose: find out whether a rule that looks at a pod label still protects the database when an attacker copies that label (SC-7, SC-8, SC-24, SA-8).",
        "You build two designs of the same three workloads: Design A with network policies alone, and Design B with the same policies plus the service mesh.",
        "You write a harness that sends the same five test requests to both designs, then break each design on purpose to see what happens when a protection fails.",
        "You run everything with `oc` and `jq` in the lab shell and choose a design from the results, not from opinion.",
    ],
    "objectives": [
        {"label": "Skill", "text": "Build two designs that isolate the same three workloads. Send the same five test cases to both with a harness, then read what each design blocks and how it behaves when a protection fails."},
        {"label": "Tools", "text": "Kubernetes network policies filter traffic by pod label and port. Red Hat OpenShift Service Mesh 3 (Istio) adds mutual TLS and a rule on who may call the database. `oc` applies the files and runs each test request inside a pod. `jq` queries the results. Python 3 runs the harness that sends each test case. OpenShift is the platform that runs both designs."},
        {"label": "Security Function", "text": "Proves what each design blocks. The same test cases run against both designs. A pod that only copies the api label gets past network policies alone but is blocked by the mesh. Each failure test shows whether a design ends open or closed."},
        {"label": "NIST SC-7 Boundary Protection", "text": "Network policies and the Istio AuthorizationPolicy control which pods may call the database. The harness sends the allowed flow and four attacks and lists every attack that reached the database."},
        {"label": "NIST SC-8 Transmission Confidentiality and Integrity", "text": "The Istio PeerAuthentication in STRICT mode makes the sidecars accept only encrypted mutual TLS connections, so a sender with no sidecar is refused. Test 3 in Section 4 shows what gets in when STRICT mode is relaxed."},
        {"label": "NIST SC-24 Fail in Known State", "text": "`oc` deletes the network policies and stops the mesh control plane, and the harness shows whether each design ends open or closed. You then undo both failures."},
        {"label": "NIST SA-8 Security and Privacy Engineering Principles", "text": "The harness results and a `jq` query turn the design choice into a test that can be rerun: no leaks and a working allowed flow."},
    ],
    "mapping": [
        {
            "control": "SC-7 Boundary Protection",
            "plain": "Communications between key internal parts are monitored and controlled, with only the allowed flows permitted.",
            "source": "NIST",
            "tool": "Kubernetes NetworkPolicy and the Istio AuthorizationPolicy of Red Hat OpenShift Service Mesh 3. Explained in sections 2.1 and 2.2.",
            "covered": "Section 3, Steps 1 to 3: build both designs and test what each lets through. Section 4, Tests 1 and 3: cases that get past a weakened design.",
            "cite": [
                {"file": NIST, "quote": "Monitor and control communications at the external managed interfaces to the system and at key internal managed interfaces within the system"},
                {"file": NIST, "quote": "Deny network communications traffic by default and allow network communications traffic by exception"},
            ],
        },
        {
            "control": "SC-8 Transmission Confidentiality and Integrity",
            "plain": "Information moving between components is protected against being read or changed on the way. FedRAMP assigns both confidentiality and integrity.",
            "source": "NIST; FedRAMP",
            "tool": "Mutual TLS set to STRICT by an Istio PeerAuthentication, enforced by the mesh sidecars. Explained in section 2.1.",
            "covered": "Section 3, Step 1: apply the mesh policies to Design B. Section 3, Step 3: a plain-text sender is refused. Section 4, Test 3: it is admitted when mutual TLS is relaxed.",
            "cite": [
                {"file": NIST, "quote": "Unprotected communication paths are exposed to the possibility of interception and modification."},
                {"file": FEDRAMP_MOD, "quote": "SC-8 [confidentiality AND integrity]"},
                {"file": FEDRAMP_HIGH, "quote": "SC-8 [confidentiality AND integrity]"},
            ],
        },
        {
            "control": "SC-24 Fail in Known State",
            "plain": "When a part of the protection fails, the system ends up in a state chosen in advance.",
            "source": "NIST",
            "tool": "The two failure tests run with oc: deleting the network policies and scaling the mesh control plane to zero. Explained in section 2.1.",
            "covered": "Section 3, Step 4: remove the network policies, then stop the mesh control plane, and read the state each design ends in. Section 4, Test 2: both protections are back.",
            "cite": [
                {"file": NIST, "quote": "Failure in a known state prevents the loss of confidentiality, integrity, or availability of information in the event of failures of organizational systems or system components."},
            ],
        },
        {
            "control": "SA-8 Security and Privacy Engineering Principles",
            "plain": "Design choices follow stated engineering principles and are weighed before they are built.",
            "source": "NIST",
            "tool": "The harness and the jq queries over its result file. Explained in section 2.2.",
            "covered": "Section 3, Step 3: write the choice as a query over the harness results. Section 3, Step 4: read how each design behaves when a protection fails.",
            "cite": [
                {"file": NIST, "quote": "Apply the following systems security and privacy engineering principles in the specification, design, development, implementation, and modification of the system and system components"},
            ],
        },
    ],
    "intent": [
        {
            "control": "SC-7 Boundary Protection",
            "feared": "One compromised part copies what the rule looks at and walks through a boundary that looked closed.",
            "scope": "Flows between the web, api and database parts of one project.",
            "question": "Which of these attacks does the rule stop, and which does it only appear to stop?",
            "evidence": "A result for every attack case under each design, from the same harness, with the allowed flow also tested.",
            "sufficient": "Every attack case is blocked and the allowed flow works. The lab chose the cases: a stranger, a part with no right to call, and two pods that copy the api label.",
            "tieoff": "A leak is a defect to fix or a risk to accept in writing by the owner. It is never ignored.",
            "tool": "The harness (Step 2) and the leak list per design (Step 3).",
        },
        {
            "control": "SC-8 Transmission Confidentiality and Integrity",
            "feared": "Traffic between internal parts crosses the network readable, so a part that is compromised can read or change it.",
            "scope": "Traffic between pods in the project.",
            "question": "If something could watch the wire between api and database, what would it see?",
            "evidence": "A plain-text sender refused by the receiving sidecar, and the same sender admitted once mutual TLS is relaxed.",
            "sufficient": "The receiving side accepts only encrypted connections. The lab protects both confidentiality and integrity, as FedRAMP assigns. For SC-8(1), FedRAMP guidance asks for FIPS validated or NSA approved cryptography; whether the mesh cryptography meets that is outside this module.",
            "tieoff": "Something would notice a part that sends plain text. Detection of a sender of plain text is outside this module; ARC-5 shows how to make a test fail when the cluster drifts.",
            "tool": "PeerAuthentication in STRICT mode (Step 1) and the copied-label-plain case (Step 3 and Test 3).",
        },
        {
            "control": "SC-24 Fail in Known State",
            "feared": "A protective part fails and the system opens up, or it fails shut and stops the mission, and nobody chose which.",
            "scope": "The protective parts of each design: the network policies, the sidecars and the mesh control plane.",
            "question": "When this protective part fails, does traffic flow or stop, and was that the intended outcome?",
            "evidence": "The harness result and the state of the pods after each failure is applied and then undone.",
            "sufficient": "Each failure ends in a state the team chose. NIST leaves the known state and the failures to the organization, so the lab chooses its own. The lab tests two failures of its own choosing: all network policies deleted, and the mesh control plane stopped.",
            "tieoff": "Someone owns the decision of which state each failure should end in and rechecks it after upgrades.",
            "tool": "The two failure tests in Step 4.",
        },
        {
            "control": "SA-8 Security and Privacy Engineering Principles",
            "feared": "The more complex design is chosen because it sounds stronger, and nobody tests what it blocks or how it fails.",
            "scope": "One design choice: how to isolate three workloads.",
            "question": "What does the extra mechanism block that the simpler one does not?",
            "evidence": "Blocking results for both designs under the same cases.",
            "sufficient": "The choice is made from evidence under the same conditions and the criteria are written as a query that can be rerun.",
            "tieoff": "The choice is revisited when the workloads or the mesh change.",
            "tool": "The leak query in Step 3 and the failure tests in Step 4.",
        },
    ],
    "terms": [
        ("Label spoofing", "Giving a pod the same label as a trusted part. A network policy that selects by label cannot tell the copy from the original."),
        ("Network policy", "A cluster rule that lists which pods may send traffic to which other pods, chosen by pod label and port. Anything not listed is blocked once a pod is selected."),
        ("Mutual TLS", "An encrypted connection in which both ends present a certificate. The certificate names who is calling."),
        ("mTLS", "Short for mutual TLS, an encrypted connection in which both ends present a certificate."),
        ("Network plugin", "The cluster part that carries traffic between pods and enforces network policies."),
        ("IstioCNI", "An OpenShift mesh resource that sets up each pod's network so its traffic passes through the sidecar."),
        ("FIPS 140", "The US government standard that encryption software must pass to be called validated."),
        ("Cluster", "A group of servers that work together as one system. Here it is your own OpenShift cluster."),
        ("Project", "A named section of the cluster that keeps one set of work apart from others. Here they are arc-a and arc-b. OpenShift also calls it a namespace."),
        ("Pod", "One running copy of a program in the cluster."),
        ("Deployment", "A cluster object that keeps a set of identical pods running. Web, api and db are each a deployment."),
        ("Workload", "A program that runs on the cluster. Here the web, api and database parts."),
        ("Label", "A key=value tag on a cluster object, such as app=api. Network policies pick pods by label."),
        ("Port", "A number that picks which program on a pod receives a request, such as 8080."),
        ("Service mesh", "Helper programs, plus one control program, that add identity and encryption to the traffic between pods without changing the programs. Here it is Red Hat OpenShift Service Mesh, built on Istio."),
        ("Control plane", "The part of the mesh that issues certificates and adds sidecars to new pods. Here it is the control program that runs in the project istio-system."),
        ("Certificate", "A digital document that proves who a program is. The mesh issues one to each pod's service account."),
        ("Harness", "A script that sends the same test cases to each design and writes the results to one file."),
        ("Status code", "A number a web server sends back. 200 means it answered. 403 means it refused the caller."),
        ("YAML", "A plain-text format for settings, with indentation to show what belongs to what."),
        ("Dry run", "A request the cluster checks fully but does not save."),
        ("Sidecar", "A helper program the mesh adds to each pod. It does the encryption and the identity checks for the application."),
        ("Service account", "An identity for a pod. In the mesh its certificate carries a name, the principal."),
        ("Principal", "The identity name carried by a mesh certificate, such as cluster.local/ns/arc-b/sa/api."),
        ("AuthorizationPolicy", "A mesh rule that says which principals may call a workload. Without a match the sidecar answers 403."),
        ("Fail open", "What happens when a protection breaks and traffic is let through. The system stays up but unprotected."),
        ("Fail closed", "What happens when a protection breaks and traffic is stopped. The system is down but safe."),
        ("Leak", "An attack case that reached the database. The harness counts leaks."),
        ("Istio", "The open-source service mesh that Red Hat OpenShift Service Mesh is built on."),
        ("PeerAuthentication", "A mesh resource that sets whether sidecars require mutual TLS. STRICT accepts only mutual TLS. PERMISSIVE also accepts plain text."),
        ("oc", "The command-line tool for OpenShift. You type oc to ask the cluster questions."),
        ("jq", "A tool that picks one value out of JSON text."),
        ("Heredoc", "A way to make a file by pasting its text between a first line such as cat > name <<'EOF' and a last line that says EOF."),
    ],
    "concepts": [
        {
            "heading": "2.1 What each design looks at",
            "controls": [
                {"id": "SC-7 Boundary Protection"},
                {"id": "SC-8 Transmission Confidentiality and Integrity"},
                {"id": "SC-24 Fail in Known State"},
            ],
            "paras": [
                {"bullets": [
                    "Design A (network policies alone) decides by the label on a pod and the port. A label is a key=value tag such as app=api, and anyone who can create a pod can write any label on it.",
                    "Design B (policies plus the service mesh) also checks a certificate that the mesh issues to a pod's service account, the identity the pod runs as. A pod cannot get another account's certificate by writing a label.",
                    "The extra layer costs a sidecar (a helper program) in every pod and a control plane (the part of the mesh that issues certificates) that must stay running. The harness shows what that cost buys.",
                ]},
                {
                    "control": "SC-7: Boundary Protection",
                    "text": "The control asks the organization to monitor and control communications at the external managed interfaces to the system and at key internal managed interfaces within the system. This is done using:",
                },
                {"bullets": [
                    "Kubernetes network policies: allow only web to api and api to db, chosen by pod label and port, and deny the rest.",
                    "The Istio AuthorizationPolicy (Design B): lets the database accept only the service account identity of the api.",
                    "The harness: sends the five cases and lists every attack that reached the database.",
                ]},
                {
                    "control": "SC-8: Transmission Confidentiality and Integrity",
                    "text": "The control asks the organization to protect the confidentiality, integrity or both (as selected) of transmitted information. FedRAMP assigns both. This is done using:",
                },
                {"bullets": [
                    "The Istio PeerAuthentication set to STRICT (Design B): every sidecar in arc-b accepts only encrypted mutual TLS connections.",
                    "The sidecars: do the encryption next to each program, so a sender that does not speak the mesh protocol is refused. Design A adds no encryption.",
                ]},
                {
                    "control": "SC-24: Fail in Known State",
                    "text": "The control asks the organization to fail to an organization-defined known system state for organization-defined types of system failures on organization-defined components while preserving organization-defined system state information in failure. The lab chooses two failures. This is done using:",
                },
                {"bullets": [
                    "`oc delete networkpolicy` and `oc scale` on the mesh control plane: cause the two chosen failures, all network policies deleted and the control plane stopped.",
                    "The harness and `oc get pods`: show whether each design ends open (traffic flows) or closed (traffic stops).",
                ]},
            ],
        },
        {
            "heading": "2.2 The five test cases",
            "controls": [
                {"id": "SA-8 Security and Privacy Engineering Principles"},
            ],
            "paras": [
                {"bullets": [
                    "Every case sends the same request: fetch the database page. One case is the allowed flow and four are attacks.",
                    "An attack case that gets the answer 200 is a leak, because the database answered a sender it should have refused.",
                ]},
                {
                    "control": "SA-8: Security and Privacy Engineering Principles",
                    "text": "The control asks the organization to apply organization-defined systems security and privacy engineering principles in the specification, design, development, implementation and modification of the system. The lab applies one principle: weigh a design choice with evidence, under the same conditions, before building it. This is done using:",
                },
                {"bullets": [
                    "The harness: sends the same five cases to both designs, so the only difference is the design.",
                    "A `jq` query over the results: writes the requirement (no leaks and a working allowed flow) so it can be rerun.",
                ]},
                "The table lists each case and what it fakes.",
            ],
            "table": {
                "headers": ["Case", "Who sends it", "What it fakes", "Should reach the database"],
                "rows": [
                    ("api-to-db", "The api", "Nothing", "Yes"),
                    ("web-to-db", "The web part", "Nothing, but it has no right", "No"),
                    ("stranger", "A pod with an unrelated label", "Nothing", "No"),
                    ("copied-label-plain", "A pod labeled as the api, no sidecar", "The label", "No"),
                    ("copied-label-mesh", "A pod labeled as the api, with a sidecar, wrong service account", "The label, and joins the mesh", "No"),
                ],
            },
        },
    ],
    "steps": [
        {
            "title": "Build both designs",
            "learn": "Applying the network policies to both projects and the mesh policies to arc-b creates the two designs you test later. Design A is policies alone, and Design B adds mutual TLS and an identity rule on the database.",
            "takeaway": "The two designs differ only in the mesh policies, so any difference in the results comes from the mesh.",
            "controls": [
                {"id": "SC-7 Boundary Protection", "how": "netpol.yaml denies all traffic and allows only web to api and api to db in both projects. In arc-b, mesh.yaml adds a rule that only the api identity may call the database."},
                {"id": "SC-8 Transmission Confidentiality and Integrity", "how": "mesh.yaml sets mutual TLS to STRICT in arc-b, so its sidecars accept only encrypted connections."},
            ],
            "why": "Both projects already hold the same workloads and three attack pods, and lab start installed the Service Mesh 3 Operator. You apply the supplied network policy file to both projects, then write mesh.yaml for arc-b only, the one part that differs.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p \"$HOME/arc\"\n"
                        "cd \"$HOME/arc\"\n"
                        "cat > mesh.yaml <<'EOF'\n"
                        + MESH_YAML
                        + "\nEOF\n"
                        "ls -l mesh.yaml"
                    ),
                    "label": 'Save the mesh policy file',
                    "expect": 'Example only. Date and size will differ.\n-rw-r--r-- 1 <user> <group> <size> <date> mesh.yaml',
                    "intro": 'You will now make the file mesh.yaml in your arc folder by pasting the whole block at once into the lab shell. The command prints only the file listing; the next block applies the file.',
                    "look_for": [
                        "PeerAuthentication with mode STRICT: every sidecar in arc-b accepts only mutual TLS and refuses plain text.",
                        "AuthorizationPolicy with action ALLOW: once an allow rule exists for the database, only the callers it names are accepted.",
                        "The selector app: db: the rule protects the database pods only.",
                        "The principal for the service account named api in arc-b: the caller must hold that certificate. A copied label cannot supply it.",
                    ],
                    "lines": [
                        ("cd ... cat > mesh.yaml <<'EOF' ... EOF", "Moves into the arc folder and writes everything between the first and last line into mesh.yaml. The quotes around EOF keep the text exactly as typed.", "The lab has no editor, so a paste is how you make a file. YAML needs its spaces exactly, and the paste keeps them."),
                        ("PeerAuthentication, mode: STRICT", "Every sidecar in arc-b accepts only mutual TLS and refuses plain text.", "Makes encryption mandatory, so a sender that does not speak the mesh protocol is refused."),
                        ("AuthorizationPolicy, action: ALLOW", "Once any allow rule exists for the database, only callers it names are accepted.", "Moves the decision from a label anyone can write to an identity only the mesh can issue."),
                        ("selector ... app: db", "Applies the rule to the database pods only.", "Protects only the database, which is the part the attackers are after."),
                        ("principals", "The caller (the principal, the identity name in a mesh certificate) must hold a certificate for the service account named api in arc-b. A label cannot supply that.", "Names the one caller that is allowed, so a pod that only copies a label does not match."),
                    ],
                },
                {
                    "code": (
                        f"sed \"s/NS_NAME/arc-a/\" {ARC}/netpol.yaml\" | oc apply -f -\n"
                        f"sed \"s/NS_NAME/arc-b/\" {ARC}/netpol.yaml\" | oc apply -f -\n"
                        f"oc apply -f {ARC}/mesh.yaml\" --dry-run=server\n"
                        f"oc apply -f {ARC}/mesh.yaml\"\n"
                        "oc get pods -n arc-a\n"
                        "oc get pods -n arc-b"
                    ),
                    "label": 'Apply the policies to both projects and look at the pods',
                    "screenshot": {"file": "ARC-4-shot-1b-excerpt.png", "alt": "Step 1, block 1b: the network policies and the mesh policies applied, and the pods of arc-a (1/1) and arc-b (2/2).", "width": 6.0},
                    "intro": 'You will now put the network policies in both projects, check and apply the mesh file in arc-b, and list the pods. The supplied netpol.yaml denies all incoming traffic, then allows web to api and api to db on port 8080 by pod label alone, which is the weakness this module tests. The placeholder NS_NAME in netpol.yaml is replaced by the project name.',
                    "expect": 'Example only. Names and ages will differ.\nnetworkpolicy.networking.k8s.io/default-deny-ingress created (and api-from-web, db-from-api), once for each project. A re-run prints unchanged instead of created.\nThe dry run lists peerauthentication and authorizationpolicy as created (server dry run), then the real apply lists them as created.\narc-a pods: web, api, db and the attack pods, each showing 1/1.\narc-b pods: web, api and db showing 2/2; the attack pod atk-copied-mesh shows 2/2 and the other two show 1/1.',
                    "lines": [
                        ("sed \"s/NS_NAME/arc-a/\" ... | oc apply -f -", "Swaps the placeholder for the project name and applies the result.", "Puts the same network policies in both projects."),
                        ("--dry-run=server", "Asks the cluster to check the file without saving it.", "Catches mistakes in mesh.yaml before it can change anything."),
                        ("oc get pods", "In arc-a each pod shows 1/1 containers. In arc-b the web, api and database pods show 2/2: the program plus the sidecar.", "The 2/2 against 1/1 is how you see which pods have a sidecar, and that decides which design protects them."),
                    ],
                },
            ],
            "note": "In arc-b the attack pod named atk-copied-mesh shows 2/2 because it has a sidecar. The other two attack pods opt out of the sidecar and show 1/1. The cases test that difference. On this cluster the sidecar container, istio-proxy, is a native sidecar, so oc lists it under initContainers and not under containers in the pod's YAML. The READY count still includes it. The folder $HOME/arc is shared by the architecture modules, so starting another ARC module in the same lab can overwrite netpol.yaml. Finish this module before you start another one.",
            "checkpoint": "Three network policies in each project, and mesh policies in arc-b. Web, api and database show 1/1 in arc-a and 2/2 in arc-b.",
        },
        {
            "title": "Write the attack cases and the harness",
            "learn": "Saving cases.json and harness.py gives you one test that sends the same request from each sender to the database. Both designs are then measured the same way.",
            "takeaway": "A test that runs unchanged against both designs makes their results comparable.",
            "controls": [
                {"id": "SC-7 Boundary Protection", "how": "The cases file lists one allowed flow and four attacks. The harness records the status code of each, and an attack that gets 200 is a leak."},
            ],
            "why": "The cases are data and the harness is the same code for every project. The harness sends a request from inside each sender and records the status code. 200 means the database answered, 403 means a sidecar refused the caller, and fail means the connection did not complete.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p \"$HOME/arc\"\n"
                        "cd \"$HOME/arc\"\n"
                        "cat > cases.json <<'EOF'\n"
                        + CASES_JSON
                        + "\nEOF\n"
                        "jq length cases.json"
                    ),
                    "label": 'Save the cases file',
                    "expect": 'Example only.\n5',
                    "intro": 'You will now make the file cases.json in your arc folder by pasting the whole block at once into the lab shell. The last line counts the cases to show the file reads as JSON.',
                    "look_for": [
                        "name is a label for the case. It appears in the results.",
                        "from is the sender. deploy/api is a pod of the api deployment, and a name that starts with pod/ is one of the three attack pods.",
                        "attack is true when the database should refuse the sender, and false for the allowed flow.",
                        "The file holds five cases: one allowed flow and four that should not reach the database.",
                    ],
                    "lines": [
                        ("cd ... cat > cases.json <<'EOF' ... EOF", "Moves into the arc folder and writes the text between the first and last line into cases.json.", "A paste makes the file without an editor."),
                        ("jq length cases.json", "Counts the cases in the file: 5.", "A file that jq can read and that holds five cases was pasted whole."),
                        ("name", "A label for the case, used in the results.", "Gives each result a label you can read in the results later."),
                        ("from", "The sender. deploy/api means a pod of the api deployment. `pod/atk-...` is one of the three attack pods.", "Chooses which sender the request comes from, because the sender is the thing being tested."),
                        ("attack", "True when the database should refuse this sender. False for the allowed flow.", "Tells the harness whether a 200 is good or a leak."),
                    ],
                },
                {
                    "code": (
                        "mkdir -p \"$HOME/arc\"\n"
                        "cd \"$HOME/arc\"\n"
                        "cat > harness.py <<'EOF'\n"
                        + HARNESS_PY
                        + "\nEOF\n"
                        "python3 -m py_compile harness.py && echo harness.py parses"
                    ),
                    "label": 'Save the harness',
                    "expect": 'Example only.\nharness.py parses',
                    "intro": 'You will now make the script harness.py in your arc folder by pasting the whole block at once into the lab shell. The last line checks that Python can read the script; you run it in Step 3.',
                    "look_for": [
                        "PROBE is the short program run inside each sender. It fetches the database page and prints the status code, the error code or the word fail.",
                        "probe() runs PROBE with oc exec in the application container (-c app), so the sender being tested is the application and not the sidecar.",
                        "run() builds the leak list: attack cases that got 200. It also works out whether every allowed case got 200.",
                        "The project names come from the command line, so the same code runs against arc-a and arc-b.",
                    ],
                    "lines": [
                        ("cd ... cat > harness.py <<'EOF' ... EOF", "Moves into the arc folder and writes the text between the first and last line into harness.py.", "A paste makes the file without an editor. The script is Python, which the lab shell has as python3."),
                        ("python3 -m py_compile harness.py", "Asks Python to read the script and report a typing slip. It runs nothing.", "Catches a broken paste before Step 3 uses the file."),
                        ("PROBE", "A short Python program the harness runs inside the sender. It fetches the database page and prints the status code, the error code, or the word fail.", "Sends the same request in every case, so the only thing that changes is who sends it."),
                        ("`def probe(ns, source)`", "Runs the probe inside one sender with oc exec and returns what it printed. error means oc itself failed.", "Runs the request from inside the sender, because a request from your laptop would not be the attack you want to test."),
                        ("-c app", "Picks the application container, so the sidecar in arc-b is not the one that runs the probe.", "Keeps the probe out of the sidecar, so the sender being tested is the application and nothing else."),
                        ("`def run(ns, cases)`", "Runs every case in one project and works out the leak list and whether the allowed flow works.", "Turns the raw codes into the two answers you care about: which attacks got through and whether the allowed flow still works."),
                        ("`sys.argv[1], sys.argv[2:]`", "The cases file, then one or more project names. The same code runs against arc-a and arc-b.", "The same code runs against both designs, so a difference in results comes from the design and not from the test."),
                    ],
                },
            ],
            "tip": "The harness holds no password and changes nothing in the cluster. It only runs oc exec.",
            "checkpoint": "cases.json and harness.py are both in the arc folder. Step 2b already checked that the harness parses.",
        },
        {
            "title": "Run the cases against both designs and choose by evidence",
            "learn": "Running the five cases against both projects shows which attacks each design lets through. A query then names the design that blocks every attack and still allows the api.",
            "takeaway": "Writing the requirement as a query lets you rerun the choice instead of arguing it.",
            "controls": [
                {"id": "SC-7 Boundary Protection", "how": "The harness lists the attacks that reached the database. Design A should leak the copied-label pods and Design B should not."},
                {"id": "SC-8 Transmission Confidentiality and Integrity", "how": "copied-label-plain has no sidecar, so it cannot speak mutual TLS. Its code in the arc-b results shows it was refused."},
                {"id": "SA-8 Security and Privacy Engineering Principles", "how": "The requirement is a query: no leaks and a working allowed flow. The result names the design that meets it, and the query can be rerun."},
            ],
            "why": "One command sends all five cases to both projects. Two queries then read the result file: the codes, and the project that meets the requirement.",
            "blocks": [
                {
                    "code": (
                        f"{HARNESS_RUN} arc-a arc-b > {ARC}/results-normal.json\"\n"
                        f"jq -c '.[] | .codes' {ARC}/results-normal.json\"\n"
                        f"jq -r 'to_entries[] | select((.value.leaks | length) == 0 and .value.legit_ok) | .key' {ARC}/results-normal.json\""
                    ),
                    "label": 'Run the five cases against both projects and query the result',
                    "intro": 'You will now run all five cases against arc-a and arc-b, and read the result file two ways. The run takes a minute or two.',
                    "expect": 'Example only. Codes can differ on your cluster.\nTwo lines of JSON, one for each project, that give a code for each of the five cases (api-to-db should be 200).\nThe name of each project that has no leaks and a working allowed flow.',
                    "lines": [
                        ("harness.py cases.json arc-a arc-b", "Sends the five cases to each project and saves the combined result.", "Collects the same five cases from both projects in one file, so you can compare them."),
                        ("jq -c '.[] | .codes'", "Prints the code each case got in each project, one line per project.", "Shows the raw code for each case, so you can see which mechanism refused which case."),
                        ("select(... length == 0 and .legit_ok)", "Keeps only a project with no leaks where the allowed flow works. That is the requirement written as a query.", "Writes the requirement as a query, so the choice is made by a rule that can be rerun."),
                    ],
                }
            ],
            "note": "A blocked case takes several seconds, because the probe waits before it gives up.",
            "checkpoint": "In arc-a the codes for copied-label-plain and copied-label-mesh are 200 (leaks) and api-to-db is 200. In arc-b the attack cases print 403 or fail and api-to-db is 200. The last query prints only arc-b.",
        },
        {
            "title": "Break each design on purpose and read the state it ends in",
            "learn": "Deleting the network policies and stopping the mesh control plane shows what each design does when a protection fails. Each failure ends in a state that lets traffic through or stops it.",
            "takeaway": "A protection that fails closed is down but safe; one that fails open stays up but unprotected.",
            "controls": [
                {"id": "SC-24 Fail in Known State", "how": "After each failure you run the cases or recreate the database pod and read whether the design ended open or closed. You then undo the failure."},
            ],
            "why": "A protection can fail by being removed or by a part it depends on going down. You delete every network policy. You then stop the mesh control plane (which issues certificates) and recreate the database pods. You undo each failure before you go on.",
            "blocks": [
                {
                    "code": (
                        "oc delete networkpolicy --all -n arc-a\n"
                        "oc delete networkpolicy --all -n arc-b\n"
                        "sleep 15\n"
                        f"{HARNESS_RUN} arc-a arc-b > {ARC}/results-nopolicy.json\"\n"
                        f"jq -c 'map_values(.leaks)' {ARC}/results-nopolicy.json\"\n"
                        f"sed \"s/NS_NAME/arc-a/\" {ARC}/netpol.yaml\" | oc apply -f -\n"
                        f"sed \"s/NS_NAME/arc-b/\" {ARC}/netpol.yaml\" | oc apply -f -"
                    ),
                    "label": 'Remove every network policy and read the leaks',
                    "intro": 'You will now delete all network policies in both projects, run the cases, and then put the policies back.',
                    "expect": 'Example only.\nThe cluster lists the deleted network policies in each project.\nOne line of JSON that gives the leak list for arc-a and for arc-b. Expect arc-a to leak every attack case and arc-b to leak fewer or none.\nThe network policies created again in each project.',
                    "lines": [
                        ("oc delete networkpolicy --all", "Removes every network policy in the project, as a careless cleanup would.", "Simulates a careless cleanup, to see what each design does when the network policies are gone."),
                        ("sleep 15", "Gives the network plugin time to apply the change.", "The change needs a moment to reach the network, or you would test the old state."),
                        ("jq -c 'map_values(.leaks)'", "Prints the leak list for each project with no network policies.", "Shows which attack cases now get through in each project."),
                        ("sed ... | oc apply -f -", "Puts the policies back. Do not skip this.", "Undoes the failure, so later tests start from the working design."),
                    ],
                },
                {
                    "code": (
                        "oc get deployment -n istio-system\n"
                        "oc scale deployment/istiod -n istio-system --replicas=0\n"
                        "oc delete pod -n arc-a -l tier=db\n"
                        "oc delete pod -n arc-b -l tier=db\n"
                        "sleep 60\n"
                        "oc get pods -n arc-a -l tier=db\n"
                        "oc get pods -n arc-b -l tier=db\n"
                        "oc get events -n arc-b --field-selector reason=FailedCreate\n"
                        "oc scale deployment/istiod -n istio-system --replicas=1\n"
                        "oc rollout status deployment/istiod -n istio-system\n"
                        "oc rollout restart deployment/db -n arc-b\n"
                        "oc rollout status deployment/db -n arc-b"
                    ),
                    "label": 'Stop the mesh control plane, recreate the database pods, then start it again',
                    "intro": 'You will now stop the mesh control plane, recreate the database pod in each project, look at what happens, and start the control plane again. The block takes about 8 minutes, mostly waiting, so start it and let it run.',
                    "expect": 'Example only. Names and ages will differ.\nThe deployment istiod in istio-system.\ndeployment scaled (to 0).\nThe database pod in arc-a ready again. In arc-b the pod may be missing.\nFailedCreate events in arc-b that name the sidecar injection step, if the pod is missing.\ndeployment scaled (to 1), then rollout messages until istiod and the db deployment in arc-b are successfully rolled out.',
                    "lines": [
                        ("oc get deployment -n istio-system", "Shows the name of the mesh control plane deployment. The scale commands below assume it is `istiod`.", "Confirms the real name before you scale it, because the next command assumes it."),
                        ("--replicas=0", "Stops the mesh control plane. Existing sidecars keep the certificates they already hold.", "Simulates the failure of the part that issues certificates and adds sidecars."),
                        ("oc rollout restart deployment/db -n arc-b", "Starts the arc-b database again. After the failed creates the Deployment can sit in a retry delay, and the restart makes it create the pod now that the control plane is back.", "Without it the arc-b pod can stay missing for several minutes after the control plane returns."),
                        ("oc delete pod -l tier=db", "Replaces the database pod in each project. The new pod in arc-b needs the sidecar added by the mesh control plane at creation time.", "Forces a new database pod to be created, which is when the control plane is needed."),
                        ("oc get pods ... tier=db", "Shows whether each new pod exists and is ready. In arc-b the pod may be missing altogether.", "Shows the state each design ends in: a new pod in arc-a and possibly none in arc-b."),
                        ("oc get events ... FailedCreate", "Shows why the pod is missing: the error from the sidecar injection check (the step where the mesh adds a sidecar to a new pod), which the stopped control plane cannot answer.", "Gives the reason in the cluster's own words, so you do not have to guess why the pod is missing."),
                        ("--replicas=1 and rollout status", "Starts the control plane again and waits until it and the database in arc-b are ready.", "Undoes the failure and waits until the database in arc-b is back, so the lab is left whole."),
                    ],
                },
            ],
            "security": "Stopping the mesh control plane affects every project that uses the mesh. In your own lab that is only arc-b. Start it again at the end of the block, as the last lines do.",
            "checkpoint": "With no network policies, arc-a leaks every attack case and arc-b leaks fewer or none. With the control plane stopped, the new database pod in arc-a is ready. In arc-b no new database pod appears until the control plane returns, because the sidecar injection step refuses its creation. That is a fail closed state: the database in arc-b is down, not open.",
        },
    ],
    "verify": [
        {
            "kind": "positive",
            "title": "Each design behaves as the evidence says",
            "controls": [
                {"id": "SC-7 Boundary Protection", "how": "The query states the expected result in advance: two leaks in Design A, none in Design B, and the allowed flow working in both."},
            ],
            "why": "The jq query in this test is the expected result written down before the check. The jq query prints true only when Step 3 gave exactly that result.",
            "code": (
                f"jq -e '(.[\"arc-a\"].leaks == [\"copied-label-plain\", \"copied-label-mesh\"]) and (.[\"arc-b\"].leaks == []) and ([.[].legit_ok] | all)' {ARC}/results-normal.json\""
            ),
            "expect": "Example only.\ntrue",
            "lines": [
                ("jq -e '...' results-normal.json", "Reads the result file from Step 3 and checks a yes or no statement. The -e flag makes the exit code follow the answer.", "The expected result is written down before the check, so the check cannot be talked into agreeing."),
                ("arc-a leaks == [copied-label-plain, copied-label-mesh]", "Design A lets exactly the two copied-label pods in.", "Shows what the network policy alone does not stop."),
                ("arc-b leaks == []", "Design B lets no attack in.", "Shows what the mesh adds."),
                ("[.[].legit_ok] | all", "The allowed flow works in both projects.", "A design that blocks everything would also pass the other two parts, so this one keeps it honest."),
                ("true", "All parts held.", "false means one case behaved differently from the evidence."),
            ],
            "checkpoint": "The query prints true. If it prints false, read the codes line from Step 3 and find which case differs from your prediction.",
        },
        {
            "kind": "positive",
            "title": "The protections removed in Step 4 are back",
            "controls": [
                {"id": "SC-24 Fail in Known State", "how": "Counting the policies and the ready control plane replica shows both protections from Step 4 are back."},
            ],
            "why": "Step 4 deleted the policies and stopped the control plane. Confirm both protections are back before you trust any later result.",
            "code": (
                "oc get networkpolicy -n arc-a --no-headers | wc -l\n"
                "oc get networkpolicy -n arc-b --no-headers | wc -l\n"
                "oc get deployment istiod -n istio-system -o jsonpath='{.status.readyReplicas}{\"\\n\"}'"
            ),
            "expect": (
                "Example only.\n"
                "3\n"
                "3\n"
                "1"
            ),
            "lines": [
                ("oc get networkpolicy -n arc-a --no-headers | wc -l", "Counts the network policies in arc-a: 3.", "Step 4 deleted them and put them back, so the count shows they are back."),
                ("oc get networkpolicy -n arc-b --no-headers | wc -l", "Counts the network policies in arc-b: 3.", "The same for the second design."),
                ("oc get deployment ... readyReplicas", "Prints how many copies of the mesh control plane are ready: 1.", "Step 4 stopped it, so a 1 shows it is running again."),
            ],
            "checkpoint": "Three policies in each project and one ready control plane replica.",
        },
        {
            "kind": "negative",
            "title": "Take the mesh checks away one at a time and the copied-label pods get in",
            "controls": [
                {"id": "SC-7 Boundary Protection", "how": "Mutual TLS shows a pod belongs to the mesh, but only the identity rule shows which pod it is. With the rule deleted, the copied-label pod that joined the mesh gets in."},
                {"id": "SC-8 Transmission Confidentiality and Integrity", "how": "With mutual TLS set to PERMISSIVE the database sidecar accepts plain text, so the pod with no sidecar gets in. This shows what STRICT contributes."},
            ],
            "why": "You delete the identity rule, then relax mutual TLS to PERMISSIVE, and run the cases after each change. The last command puts both settings back.",
            "code": (
                "oc delete authorizationpolicy db-from-api -n arc-b --ignore-not-found\n"
                "sleep 15\n"
                f"{HARNESS_RUN} arc-b | jq -c '.[\"arc-b\"].leaks'\n"
                "oc patch peerauthentication default -n arc-b --type=merge -p '{\"spec\":{\"mtls\":{\"mode\":\"PERMISSIVE\"}}}'\n"
                "sleep 15\n"
                f"{HARNESS_RUN} arc-b | jq -c '.[\"arc-b\"].leaks'\n"
                f"oc apply -f {ARC}/mesh.yaml\""
            ),
            "expect": "Example only.\n[\"copied-label-mesh\"]\n[\"copied-label-plain\",\"copied-label-mesh\"]",
            "lines": [
                ("oc delete ... db-from-api ...", "Removes the identity rule on the database. If it is already gone, nothing happens.", "Takes away the check on who the caller is."),
                ("[\"copied-label-mesh\"]", "Only the pod that joined the mesh now gets in. The plain-text pod is still refused by mutual TLS.", "Mutual TLS shows a pod belongs to the mesh but not which pod it is."),
                ("oc patch peerauthentication ... PERMISSIVE", "Lets the database sidecar accept plain text.", "Takes away the encryption requirement as well."),
                ("[\"copied-label-plain\",\"copied-label-mesh\"]", "Both copied-label pods now get in.", "With both mesh checks gone, only the label rule is left, which is Design A."),
                ("oc apply -f mesh.yaml", "Puts the identity rule and STRICT mode back.", "Leaves the design as it was built."),
            ],
            "checkpoint": "First only copied-label-mesh leaks, because the plain-text pod is still refused while mutual TLS is strict. Then both copied-label cases leak. The last command restores both settings. To confirm, run the Step 3 harness command again (it overwrites results-normal.json) and rerun Test 1. It must print true.",
        },
    ],
    "waivers": {
        "your_turn": "The YOUR TURN lines were removed on reviewer feedback (ENG-0); the optional command list at the end replaces them.",
    },
    "glossary": [
        ("Label spoofing", "Copying a trusted label onto a pod that is not trusted."),
        ("Mutual TLS", "Both ends present certificates and the traffic is encrypted."),
        ("Sidecar", "A helper program the mesh adds to each pod."),
        ("Principal", "The identity name carried by a mesh certificate."),
        ("AuthorizationPolicy", "A mesh rule listing which principals may call a workload."),
        ("PeerAuthentication", "A mesh resource that sets whether sidecars require mutual TLS."),
        ("Fail open", "A protection whose failure lets traffic through."),
        ("Fail closed", "A protection whose failure stops traffic."),
        ("Leak", "An attack case that reached the database."),
    ],
    "design": [
        {
            "decision": "Compare network policies alone with network policies plus a mesh",
            "how": "Two projects hold the same workloads: Design A uses network policies, and Design B adds mesh certificates, encrypted traffic and a rule that the database accepts only the api identity. The same five cases (one allowed flow, four attacks) go to both.",
            "why": "A label can be written by anyone who can create a pod, so a label-based rule can be fooled, while a certificate issued to a service account cannot be claimed by writing a label.",
            "alternatives": "Network policies alone are the alternative. Advantage: no sidecars and no control plane. Drawback: the copied-label cases leak through.",
        },
        {
            "decision": "Break each design on purpose and read the state it ends in",
            "how": "All network policies are deleted in both projects, and separately the mesh control plane is stopped while the database pod is recreated.",
            "why": "A protection can fail by removal or by a part it depends on going down, and the team should choose the end state in advance.",
            "alternatives": "A fail-open design that allows traffic when the mesh is down is the alternative. Advantage: availability is kept. Drawback: anyone who can knock out the control plane removes the protection.",
        },
    ],
    "next": "Next module: ARC-5 Verify a Reference Architecture: state the allowed flows as data, generate the rules from it, and fail a test when the cluster drifts from it.",
}

MODULE["portability"] = {
    "bullets": [
        "The comparison method ports as is: one list of attack cases, one harness, the same cases run against each design.",
        "Change these lab values first: the namespaces arc-a and arc-b, the service name db on port 8080, the container name app, the service account principal cluster.local/ns/arc-b/sa/api, and the image registry.access.redhat.com/ubi9/python-311:1 that the pods pull.",
        "Design B uses Istio objects (PeerAuthentication and AuthorizationPolicy in security.istio.io/v1). They work on any cluster that runs Istio. The Service Mesh 3 operator and the IstioCNI resource are OpenShift-specific.",
        "Network policies only count if the network plugin enforces them. The lab uses OVN-Kubernetes, the OpenShift default, so check your plugin before you read the results.",
    ],
    "headers": ["Check/part", "In this lab", "On other platforms", "What you change"],
    "rows": [
        ("Mesh install", "Red Hat OpenShift Service Mesh 3 operator, an Istio resource and an IstioCNI resource, both named default", "Install Istio with the method your platform supports", "Replace the install step. Keep the two objects in mesh.yaml."),
        ("Mesh policy", "PeerAuthentication STRICT and AuthorizationPolicy in arc-b", "The same Istio objects", "The namespace and the service account principal."),
        ("Network policy", "The network policy file applied to arc-a and arc-b with oc", "The same with kubectl, if the network plugin enforces it", "The tool name and the namespaces."),
        ("Attack harness", "harness.py uses oc exec into pods, container app", "The same with kubectl exec", "The tool name, the pod names and the container name."),
        ("Sidecar setup", "Handled by the OpenShift mesh operator and the IstioCNI resource in the lab", "Per the Istio install on your platform", "Replace the check. Confirm the sidecar is running before you test."),
    ],
}
