"""ARC-5: Verify a Reference Architecture (security architecture, level 5)."""

FEDRAMP_HIGH = "fedramp-high-baseline.md"
NIST = "nist-sp-800-53r5-full.md"

FLOWS_YAML = 'namespace: arc-ref\nflows:\n  - from: web\n    to: api\n    port: 8080\n  - from: api\n    to: db\n    port: 8080\n  - from: api\n    to: cache\n    port: 8080'
GEN_NETPOL = 'import hashlib\nimport sys\n\nimport yaml\n\nflows_path, out_path = sys.argv[1], sys.argv[2]\ndata = yaml.safe_load(open(flows_path))\ndigest = hashlib.sha256(open(flows_path, "rb").read()).hexdigest()[:12]\n\n\ndef netpol(name, selector, rule):\n    spec = {"podSelector": selector, "policyTypes": ["Ingress"]}\n    if rule:\n        spec["ingress"] = [rule]\n    meta = {"name": name, "namespace": data["namespace"], "labels": {"arc-flows": digest}}\n    return {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy", "metadata": meta, "spec": spec}\n\n\ndocs = [netpol("default-deny-ingress", {}, None)]\nfor flow in data["flows"]:\n    source = {"podSelector": {"matchLabels": {"app": flow["from"]}}}\n    rule = {"from": [source], "ports": [{"protocol": "TCP", "port": flow["port"]}]}\n    name = "allow-%s-to-%s-%d" % (flow["from"], flow["to"], flow["port"])\n    docs.append(netpol(name, {"matchLabels": {"app": flow["to"]}}, rule))\n\nwith open(out_path, "w") as out:\n    yaml.safe_dump_all(docs, out, sort_keys=True)\nprint("wrote %d policies, flows hash %s" % (len(docs), digest))'
GEN_ADMISSION = 'import hashlib\nimport sys\n\nimport yaml\n\nflows_path, out_path = sys.argv[1], sys.argv[2]\ndata = yaml.safe_load(open(flows_path))\ndigest = hashlib.sha256(open(flows_path, "rb").read()).hexdigest()[:12]\napps = sorted({flow[end] for flow in data["flows"] for end in ("from", "to")})\n\n\ndef rule(name, kind, message, pattern):\n    where = {"kinds": [kind], "namespaces": [data["namespace"]], "operations": ["CREATE", "UPDATE"]}\n    validate = {"failureAction": "Enforce", "message": message, "pattern": pattern}\n    return {"name": name, "match": {"any": [{"resources": where}]}, "validate": validate}\n\n\nlabel = {"metadata": {"labels": {"arc-flows": digest}}}\nknown = {"metadata": {"labels": {"app": " | ".join(apps)}}}\npolicy = {\n    "apiVersion": "kyverno.io/v1",\n    "kind": "ClusterPolicy",\n    "metadata": {"name": "arc-ref-flows", "annotations": {"pod-policies.kyverno.io/autogen-controllers": "none"}},\n    "spec": {"background": True, "rules": [\n        rule("policy-from-flows", "NetworkPolicy", "Network policies here must be generated from flows.yaml.", label),\n        rule("known-components", "Pod", "Pods here must carry an app label that flows.yaml lists.", known),\n    ]},\n}\nwith open(out_path, "w") as out:\n    yaml.safe_dump(policy, out, sort_keys=True)\nprint("wrote the admission check for %s, flows hash %s" % (", ".join(apps), digest))'
LIVE_NET = 'import json\nimport subprocess\nfrom concurrent.futures import ThreadPoolExecutor\n\nCONNECT = "import socket; socket.create_connection((\'%s\', %d), 3); print(\'open\')"\n\n\ndef oc_json(args):\n    done = subprocess.run(["oc", *args, "-o", "json"], capture_output=True, text=True, timeout=60)\n    return json.loads(done.stdout) if done.returncode == 0 else None\n\n\ndef policy_flows(ns):\n    found, selected = set(), set()\n    for pol in (oc_json(["get", "networkpolicy", "-n", ns]) or {"items": []})["items"]:\n        target = pol["spec"].get("podSelector", {}).get("matchLabels", {}).get("app", "*")\n        selected.add(target)\n        for rule in pol["spec"].get("ingress", []):\n            for src in rule.get("from", []):\n                source = src.get("podSelector", {}).get("matchLabels", {}).get("app", "?")\n                found |= {(source, target, p.get("port")) for p in rule.get("ports", [])}\n    return found, selected\n\n\ndef reachable(ns, apps, ports):\n    pairs = [(a, b, p) for a in apps for b in apps for p in ports if a != b]\n\n    def one(pair):\n        a, b, p = pair\n        cmd = ["oc", "exec", "deploy/" + a, "-n", ns, "-c", "app", "--", "python3", "-c", CONNECT % (b, p)]\n        done = subprocess.run(cmd, capture_output=True, text=True, timeout=60)\n        return pair if done.returncode == 0 and "open" in done.stdout else None\n\n    with ThreadPoolExecutor(max_workers=12) as pool:\n        return {r for r in pool.map(one, pairs) if r}, len(pairs)'
DRIFT_RULES = 'from live_net import oc_json\n\n\ndef deployed_apps(ns):\n    items = (oc_json(["get", "deployment", "-n", ns]) or {"items": []})["items"]\n    return {d["spec"]["template"]["metadata"]["labels"].get("app", "?") for d in items}\n\n\ndef policy_hashes(ns):\n    items = (oc_json(["get", "networkpolicy", "-n", ns]) or {"items": []})["items"]\n    return {p["metadata"].get("labels", {}).get("arc-flows", "none") for p in items}\n\n\ndef admission_hash():\n    item = oc_json(["get", "clusterpolicy", "arc-ref-flows"])\n    if not item:\n        return None\n    rule = item["spec"]["rules"][0]["validate"]\n    return rule["pattern"]["metadata"]["labels"]["arc-flows"] if rule.get("failureAction") == "Enforce" else "not-enforced"\n\n\ndef find_drift(ns, listed, apps, digest, by_policy, by_traffic):\n    drift = []\n    for kind, live in (("policy", by_policy), ("traffic", by_traffic)):\n        drift += [(kind + " missing", f) for f in sorted(listed - live)]\n        drift += [(kind + " extra", f) for f in sorted(live - listed)]\n    drift += [("unlisted component", (a,)) for a in sorted(deployed_apps(ns) - set(apps))]\n    drift += [("stale network policy", (h,)) for h in sorted(policy_hashes(ns) - {digest})]\n    if admission_hash() != digest:\n        drift.append(("admission check", (str(admission_hash()),)))\n    return drift'
CONFORMANCE = 'import hashlib\nimport json\nimport sys\nimport time\n\nimport yaml\n\nfrom drift_rules import find_drift\nfrom live_net import policy_flows, reachable\n\npath = sys.argv[1]\nstarted = time.perf_counter()\ndata = yaml.safe_load(open(path))\nns = data["namespace"]\ndigest = hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]\nlisted = {(f["from"], f["to"], f["port"]) for f in data["flows"]}\napps = sorted({name for flow in listed for name in flow[:2]})\nby_policy, _ = policy_flows(ns)\nby_traffic, tested = reachable(ns, apps, sorted({f[2] for f in listed}))\ndrift = find_drift(ns, listed, apps, digest, by_policy, by_traffic)\nconfirmed = len(listed & by_policy & by_traffic)\nreport = {\n    "flows_listed": len(listed),\n    "flows_confirmed": confirmed,\n    "coverage_percent": round(100 * confirmed / len(listed)),\n    "pairs_tested": tested,\n    "unlisted_pairs_blocked": tested - len(listed) - len(by_traffic - listed),\n    "drift": [[kind, list(item)] for kind, item in drift],\n    "seconds": round(time.perf_counter() - started, 1),\n}\nprint(json.dumps(report, indent=2))\nsys.exit(1 if drift else 0)'

MODULE = {
    "intent_at_end": True,
    "terms_at_end": True,
    "id": "ARC-5",
    "slug": "Reference",
    "title": "Verify a Reference Architecture",
    "draft": (
        "Run live on 2026-11-10 and every step and test passed (see live-run/findings-ARC-5.md). Kyverno 1.19.2 accepts operations in the match block, rule-level failureAction and the app-label pattern. "
        "One Step 2 apply failed once because the Kyverno webhook was not answering after a restart; Step 2 now waits for the admission controller and retries. "
        "Every oc call prints a Kyverno ClusterPolicy deprecation warning that the expected output leaves out. "
        "The lab chooses a 10 second polling interval and a 180 second give-up time; the 300 second limit for the comparison is the five-minute maximum FedRAMP assigns for CM-8(3). "
        "A flow is counted as covered when a live network policy allows it and a real connection succeeds. This module tests one port per flow and does not prove anything about traffic that leaves the project."
    ),
    "controls": ["PL-8", "SC-7", "CM-2", "CM-8"],
    "mentions": ["CA-7"],
    "unit_values_ok": ["10 seconds", "10 second", "180 seconds", "180 second", "300 seconds", "300 second", "3 seconds", "15 seconds", "15 second", "12 characters"],
    "minutes": {"hands_on": 46, "verify": 16},
    "tools": ["OpenShift Container Platform", "Kubernetes NetworkPolicy", "Kyverno (free, open source)", "oc", "jq", "python3"],
    "tool_why": True,
    "hide_draft": True,
    "hover": True,
    "diagrams": [
        {
            "id": "reference",
            "title": "One list of allowed flows drives everything",
            "caption": "This is the lab (test) setup: you run everything from your lab shell against one project on your own cluster. In production the generators and the conformance test would run in a pipeline on a schedule, and a failure would be sent to a person. Each step adds one thing, drawn with thick lines.",
            "per_step": True,
            "rankdir": "LR",
            "step_notes": {
                1: "You write the list of allowed flows in your arc folder in lab shell and check it. The project arc-ref on the cluster runs four components and no policies yet.",
                2: "The generators read the list and write the network policies and the admission check into files in your arc folder. You then apply them to the cluster: the admission rule goes to Kyverno and the network policies go to the project arc-ref.",
                3: "The conformance test reads the live policies from the cluster and opens a connection from each component to every other one in arc-ref.",
                4: "You send a hand-written policy and an unlisted pod to the cluster, and the admission rule refuses them.",
                5: "The drift timer causes drift in arc-ref on purpose, runs the conformance test again and again from lab shell, and prints how long the test took to notice.",
            },
            "zones": [
                {"id": "shell", "label": "Your lab shell", "kind": "boundary"},
                {"id": "cluster", "icon": "aws/group-AWS-Cloud", "label": "Your cluster", "kind": "boundary"},
                {"id": "ref", "icon": "brands/openshift", "label": "Project arc-ref", "parent": "cluster", "kind": "group"},
                {"id": "kyv", "icon": "brands/openshift", "label": "Project kyverno", "parent": "cluster", "kind": "group", "labeljust": "r"},
            ],
            "key": {"brands/python": "Python script", "k8s/deploy": "Kubernetes deployment", "k8s/netpol": "Kubernetes network policy", "brands/openshift": "OpenShift project", "aws/group-AWS-Cloud": "AWS Cloud"},
            "nodes": [
                {"id": "flows", "title": "Allowed flows list", "sub": "YAML file flows.yaml", "zone": "shell", "kind": "ok"},
                {"id": "gen", "title": "Two generator scripts", "icon": "brands/python", "sub": "Python scripts, one per output", "zone": "shell", "s": 2},
                {"id": "conf", "title": "Conformance test", "icon": "brands/python", "sub": "Python script, fails on drift", "zone": "shell", "kind": "warn", "s": 3},
                {"id": "timer", "title": "Drift timer", "icon": "brands/python", "sub": "Supplied Python script drift_timer.py", "zone": "shell", "s": 5},
                {"id": "apps", "title": "Four components", "icon": "k8s/deploy", "sub": "Kubernetes deployments web, api, db, cache", "zone": "ref"},
                {"id": "np", "title": "Network policies", "icon": "k8s/netpol", "sub": "Kubernetes network policies, one per listed flow", "zone": "ref", "s": 2},
                {"id": "chg", "title": "Unlisted change", "sub": "Hand-made policy, extra pod or deletion", "zone": "ref", "kind": "bad", "s": 4},
                {"id": "adm", "title": "Kyverno admission rule", "sub": "Kyverno cluster policy, refuses unlisted parts", "zone": "kyv", "kind": "ok", "s": 2},
            ],
            "edges": [
                {"a": "flows", "b": "gen", "label": "Read", "s": 2},
                {"a": "gen", "b": "np", "label": "Generates, you apply", "s": 2},
                {"a": "gen", "b": "adm", "label": "Generates, you apply", "s": 2},
                {"a": "conf", "b": "apps", "label": "Reads and probes", "s": 3},
                {"a": "adm", "b": "chg", "label": "Refuses", "kind": "bad", "s": 4},
                {"a": "conf", "b": "chg", "label": "Detects", "kind": "warn", "beside": True, "s": 5},
                {"a": "timer", "b": "conf", "label": "Runs it", "s": 5},
                {"a": "timer", "b": "chg", "label": "Causes", "kind": "bad", "s": 5},
            ],
            "why_built": (
                "You write the list and run the scripts in lab shell on your laptop, as in the foundation module, and everything they act on runs on your cluster. "
                "This module adds a project named arc-ref with four components, and two kinds of object that the generators write into the cluster: network policies in arc-ref and an admission rule that Kyverno checks. "
                "The list, the generators and the test stay in lab shell, because the list is the one thing a person owns and reviews, and the cluster should hold only what is generated from it. "
                "The admission rule sits with Kyverno, which already runs in the cluster, because only something inside the cluster can refuse a request before it is saved. "
                "The conformance test runs from lab shell and reaches into the components with oc exec, because it has to look at the cluster from outside to notice a change nobody listed. "
                "The timer runs the test again and again from lab shell, so the delay between a change and the first failure can be measured."
            ),
            "setup": [
                ("Lab shell", "A container on your laptop", "The list, the generators, the conformance test and the timer live here, so a person edits one file and everything else is built from it."),
                ("Project arc-ref", "On your cluster", "It holds the four components and the generated network policies, so the test has a small system to compare with the list."),
                ("Network policies", "In project arc-ref", "The cluster enforces them on every connection. They are generated, so they are the same every time."),
                ("Kyverno admission rule", "A cluster-wide object checked by Kyverno", "It refuses new things that the list does not account for, before they are saved."),
                ("Conformance test", "A script in lab shell that uses oc", "It looks at the cluster from outside, so it can find a change that admission could not refuse."),
                ("Drift timer", "A supplied script in lab shell", "It repeats the test on an interval and records how long detection takes."),
            ],
            "legend": [
                ("Your lab shell", "The tools container on your laptop where you write the list, run the generators and run the test."),
                ("Your cluster", "Your own OpenShift cluster in AWS. It holds the project arc-ref and Kyverno."),
                ("Project arc-ref", "The named section of the cluster that holds the four components and the generated network policies."),
                ("Project kyverno", "The named section of the cluster where Kyverno runs."),
                ("Allowed flows list", "The file flows.yaml. It is the only thing a person edits."),
                ("Two generator scripts", "Short scripts that read the list and write the network policies and the admission rule."),
                ("Conformance test", "A script that compares the live policies and real connections with the list, and exits with failure when they differ."),
                ("Drift timer", "A supplied script that causes drift on purpose, runs the conformance test again and again, and prints how long it took to notice."),
                ("Four components", "The web, api, db and cache parts that run in arc-ref."),
                ("Network policies", "The generated rules that allow each listed flow and block every other flow."),
                ("Unlisted change", "A change the list does not name: a hand-written policy, an extra pod, or a deleted policy or rule."),
                ("Kyverno admission rule", "A rule generated from the list. It refuses a hand-written network policy and a pod that the list does not name."),
            ],
            "reading": [
                "1. Your lab shell: the tools container on your laptop where you write the list, run the generators and run the test.",
                "2. Your cluster: your own OpenShift cluster in AWS. It holds the project arc-ref and Kyverno.",
                "3. Project arc-ref: the named section of the cluster that holds the four components and the generated network policies.",
                "4. Project kyverno: the named section of the cluster where Kyverno runs.",
                "5. Allowed flows list: the file flows.yaml. It is the only thing a person edits.",
                "6. Two generator scripts: they read the list and write the network policies and the admission rule. You apply the output to the cluster.",
                "7. Conformance test: it compares the live policies and real connections with the list, and exits with failure when they differ.",
                "8. Drift timer: it causes drift on purpose, runs the conformance test again and again, and prints how long it took to notice.",
                "9. Four components: the web, api, db and cache parts that run in the project arc-ref.",
                "10. Network policies: the generated rules that allow each listed flow and block every other flow.",
                "11. Unlisted change: a hand-written policy, an extra pod or a deleted policy, none of which the list names.",
                "12. Kyverno admission rule: it refuses a hand-written network policy and a pod that the list does not name.",
            ],
        },
    ],
    "prereq": [
        "ENG-0 Terminal, Git and Your Lab (typing commands in lab shell, making a file with a heredoc, reading oc output)",
    ],
    "lab_needs": [],
    "lab": {
        "start": "lab start arc-5",
        "env": [],
    },
    "requirement": (
        "A reference architecture is only useful to other teams if the running system (your cluster, the group of servers your lab runs on) provably matches it, and keeps matching it. "
        "This module makes the allowed flows between four components (separately running parts) into data: a short YAML file (a plain-text list format). "
        "From that one file you generate the network policies (rules for which pods, the running copies of a program, may talk to which), which block every flow not on the list, and an admission check, "
        "which refuses new parts and hand-written policies that the list does not account for. You then build a conformance test: a script (a program run from top to bottom) that compares the "
        "live policies and the real traffic paths with the list, and exits with failure when anything differs. A supplied timer measures how many "
        "flows the test covers and how fast it notices three kinds of drift. A team that inherits this pattern edits one file and gets the rules, "
        "the guard and the test."
    ),
    "requirement_bullets": [
        "Purpose: show that a running system matches its reference architecture and keeps matching it (PL-8, SC-7, CM-2, CM-8).",
        "You write one YAML list of allowed flows between four components. Two generators turn it into network policies and a Kyverno admission rule, and a conformance test compares the running project with the list.",
        "You apply the generated files to the project arc-ref and run the conformance test. You then try to add something the list does not name, and use a supplied timer to measure how fast three kinds of drift are noticed.",
    ],
    "objectives": [
        {"label": "Skill", "text": "Write one list of allowed flows, generate network policies and an admission rule from it, and build a conformance test that compares the running project with the list and times how fast it notices drift."},
        {"label": "Tools", "text": "`python3` with PyYAML runs the generators and the test. Kubernetes NetworkPolicy blocks every flow the list does not allow, and Kyverno refuses unlisted policies and pods. `oc` applies the files and reads the cluster, `jq` reads the test report, and OpenShift runs the four components."},
        {"label": "Security Function", "text": "Blocks every flow between components that the list does not allow, and refuses unlisted policies and pods when they are created. It also detects drift that gets around that (a deleted policy, an extra deployment, an edited list) and measures the detection time."},
        {"label": "NIST PL-8 Security and Privacy Architectures", "text": "The flow list is the architecture written as data. The Python generators build the running rules from it and the conformance test fails when the project no longer matches it."},
        {"label": "NIST SC-7 Boundary Protection", "text": "Kubernetes NetworkPolicy objects start from default deny and allow only listed flows. The conformance test opens real connections between every pair of components, and Kyverno refuses a hand-written policy."},
        {"label": "NIST CM-2 Baseline Configuration", "text": "The flow list is the baseline. The generators put a hash of it on every object. The conformance test reports any object or admission rule built from an older version of the list."},
        {"label": "NIST CM-8 System Component Inventory", "text": "Kyverno refuses a pod the list does not name, and the conformance test reports an unlisted deployment. The drift timer measures how long that detection takes against the 300 second limit (FedRAMP's five-minute maximum delay)."},
    ],
    "mapping": [
        {
            "control": "PL-8 Security and Privacy Architectures",
            "plain": "The security design states how information is protected and is kept up to date as the system changes.",
            "source": "NIST; FedRAMP",
            "tool": "The flow list flows.yaml, the two generator scripts and the conformance test. Explained in section 2.1.",
            "covered": "Section 3, Steps 1 and 2: write the flow list and generate and apply the rules from it. Section 4, Test 1: the project matches the list.",
            "cite": [
                {"file": NIST, "quote": "Describe the requirements and approach to be taken for protecting the confidentiality, integrity, and availability of organizational information"},
                {"file": FEDRAMP_HIGH, "quote": "PL-8 (b) [at least annually and when a significant change occurs]"},
            ],
        },
        {
            "control": "SC-7 Boundary Protection",
            "plain": "Traffic between key internal parts is controlled and denied by default.",
            "source": "NIST",
            "tool": "Kubernetes NetworkPolicy objects generated from the list, and a Kyverno admission rule. Explained in section 2.1.",
            "covered": "Section 3, Step 2: generate the deny-by-default policies. Section 3, Step 3: test a real connection between every pair of components. Section 3, Step 4: a hand-written policy is refused. Section 3, Step 5: a deleted policy is found.",
            "cite": [
                {"file": NIST, "quote": "Monitor and control communications at the external managed interfaces to the system and at key internal managed interfaces within the system"},
                {"file": NIST, "quote": "Deny network communications traffic by default and allow network communications traffic by exception"},
            ],
        },
        {
            "control": "CM-2 Baseline Configuration",
            "plain": "A current baseline is kept under configuration control, and a change from it is a visible event.",
            "source": "NIST; FedRAMP",
            "tool": "The flow list as the baseline, and the flows hash label on every generated object. Explained in section 2.1.",
            "covered": "Section 3, Step 2: each generated object carries the hash. Section 4, Test 2: generation is repeatable. Section 4, Test 4: a list edited without regenerating shows as drift.",
            "cite": [
                {"file": NIST, "quote": "Develop, document, and maintain under configuration control, a current baseline"},
                {"file": FEDRAMP_HIGH, "quote": "CM-2 (b) (1) [at least annually and when a significant change occurs]"},
            ],
        },
        {
            "control": "CM-8 System Component Inventory",
            "plain": "The list of components matches what is running, and an unauthorized component is detected by automated means.",
            "source": "NIST; FedRAMP",
            "tool": "The known-components rule of the Kyverno admission policy, the conformance test and the drift timer. Explained in section 2.2.",
            "covered": "Section 3, Step 3: the test reports a deployment the list does not name. Section 3, Step 4: the admission rule refuses an unlisted pod. Section 3, Step 5: time how fast an unlisted deployment is detected.",
            "cite": [
                {"file": NIST, "quote": "Includes all components within the system"},
                {"file": FEDRAMP_HIGH, "quote": "automated mechanisms with a maximum five-minute delay in detection."},
                {"file": FEDRAMP_HIGH, "quote": "CM-8 (3) (a)-2 [continuously]"},
            ],
        },
    ],
    "intent": [
        {
            "control": "PL-8 Security and Privacy Architectures",
            "feared": "Each team draws its own picture of what may talk to what, and the pictures and the running systems disagree.",
            "scope": "The flows between the components of one project, written once and inherited by other projects.",
            "question": "Where is the one place the allowed flows are written, and what in the running system is built from it?",
            "evidence": "The flow file, the generators, and a conformance result that shows the running project matches the file.",
            "sufficient": "A reviewer can read one short file and trust that it describes the running system, because a test fails when it does not. NIST leaves the review frequency organization-defined; FedRAMP assigns at least annually and when a significant change occurs.",
            "tieoff": "Someone owns the file, and changes to it go through review before the generators run.",
            "tool": "flows.yaml, the generators and the flow checker (Steps 1 and 2).",
        },
        {
            "control": "SC-7 Boundary Protection",
            "feared": "An unlisted flow is opened by hand during an incident and never closed.",
            "scope": "Every ordered pair of the four components, on every port the list uses.",
            "question": "Of all the pairs that could talk, which can, and is that exactly the list?",
            "evidence": "A result for every pair from real connection attempts, and the policies read from the cluster.",
            "sufficient": "Every listed flow works, every other pair is blocked, and the generated policies are the only network policies in the project. The lab tests one port per flow.",
            "tieoff": "A hand-written policy is refused at admission. A change that bypasses admission is found by the test.",
            "tool": "The generated network policies, the admission rule and the connection probes in the conformance test.",
        },
        {
            "control": "CM-2 Baseline Configuration",
            "feared": "The baseline file is edited and nobody regenerates the cluster from it, or the cluster is changed and the file is not.",
            "scope": "The flow file and everything generated from it.",
            "question": "If the file and the cluster disagree, which one does the system tell you about, and how soon?",
            "evidence": "The hash in each generated object, compared with the hash of the current file.",
            "sufficient": "Every generated object names the version of the file it came from, and a mismatch is reported. NIST leaves the baseline review times organization-defined; FedRAMP assigns at least annually and when a significant change occurs.",
            "tieoff": "Regenerating is part of the same change as editing the file.",
            "tool": "The flows hash label and the stale-policy check in the conformance test.",
        },
        {
            "control": "CM-8 System Component Inventory",
            "feared": "A component appears that nobody listed, and it is found only at the next assessment.",
            "scope": "Pods and deployments in the project.",
            "question": "How long can an unlisted component exist before something tells you?",
            "evidence": "A refusal at admission, or a conformance failure, and the measured time to the failure.",
            "sufficient": "Unlisted pods are refused, and an unlisted deployment is detected by an automated check. The enhancement CM-8(3) asks for automated detection of unauthorized components. The lab runs the check every 10 seconds and measures the worst case against the 300 second limit, which is the five-minute maximum delay FedRAMP assigns for CM-8(3).",
            "tieoff": "Someone receives the failure. This module only makes the test fail; alerting is outside this module.",
            "tool": "The known-components admission rule and the drift timer (Steps 4 and 5).",
        },
    ],
    "terms": [
        ("Reference architecture", "A design that other teams copy. Here it is the list of allowed flows plus everything generated from it."),
        ("Generator", "A script that produces configuration from data, so people edit the data and never the output."),
        ("Conformance test", "A script that compares the running system with the intended design and fails when they differ."),
        ("Drift", "Any difference between the intended design and the running system."),
        ("Coverage", "The share of listed flows that the test confirms with both a live policy and a real working connection."),
        ("Admission check", "A rule applied when something is created or changed, which can refuse the request."),
        ("Admission rule", "The Kyverno policy generated from the list. It is the admission check this module builds."),
        ("Admission webhook", "The way the cluster asks Kyverno whether to allow a request before it is saved."),
        ("Default deny", "A network policy that selects every pod and allows nothing, so any flow not allowed by another policy is blocked."),
        ("Enforce", "The Kyverno setting that makes a rule refuse a request. The other setting, Audit, only records it."),
        ("Ordered pair", "A sender and a receiver in a fixed order, so web to api and api to web are two different pairs."),
        ("oc exec", "An oc command that runs a command inside a running container."),
        ("Probe", "A real connection attempt made only to see whether it works."),
        ("Flows hash", "A short fingerprint of the flow file. Each generated object carries it so a stale object can be seen."),
        ("Hash", "A short fingerprint of some text. The same text always gives the same hash, and any change to the text gives a different one."),
        ("Cluster", "A group of servers that work together as one system. Here it is your own OpenShift cluster."),
        ("Project", "A named section of the cluster that keeps one set of work apart from others. Here it is arc-ref. OpenShift also calls it a namespace."),
        ("Pod", "One running copy of a program in the cluster."),
        ("Deployment", "A cluster object that keeps a set of identical pods running. Each of the four components is a deployment."),
        ("Component", "One separately running part of the system, such as the web part or the database."),
        ("Network policy", "A cluster rule that lists which pods may send traffic to which other pods, chosen by pod label and port. Anything not listed is blocked."),
        ("Label", "A key=value tag on a cluster object, such as app=web. Network policies pick pods by label."),
        ("Port", "A number that picks which program on a pod receives a request, such as 8080."),
        ("Kyverno", "A program in your cluster that checks every request to create or change something against rules, and can refuse the request."),
        ("YAML", "A plain-text format for settings and lists, with indentation to show what belongs to what."),
        ("Script", "A text file of code that the computer runs from top to bottom."),
        ("Function", "A named group of commands or code that you call by name."),
        ("Exit code", "The number a command leaves behind when it ends. 0 means success. Any other number means something needs attention."),
        ("Pipeline", "An automated sequence of tasks that runs without a person typing each command."),
        ("Poll", "To ask again and again at a fixed interval until something changes."),
        ("oc", "The command-line tool for OpenShift. You type oc to ask the cluster questions."),
        ("jq", "A tool that picks one value out of JSON text."),
        ("Heredoc", "A way to make a file by pasting its text between a first line such as cat > name <<'EOF' and a last line that says EOF."),
    ],
    "concepts": [
        {
            "heading": "2.1 Data in, rules out",
            "controls": [
                {"id": "PL-8 Security and Privacy Architectures"},
                {"id": "SC-7 Boundary Protection"},
                {"id": "CM-2 Baseline Configuration"},
            ],
            "paras": [
                {"bullets": [
                    "A person edits one list of allowed flows. Scripts called generators turn it into network policies and an admission check, and nobody writes the output by hand.",
                    "Generated policies are the same every time, so a test can compare them with the running system. Hand-written policies drift and differ between teams.",
                ]},
                "The four layers are the flow list, the network policies, the admission rule and the conformance test. Each has a limit, which is why all four are used together:",
                {"bullets": [
                    "The flow list enforces nothing by itself.",
                    "The network policies cannot notice that someone deleted them.",
                    "The admission rule cannot stop a delete or a change made before the rule existed.",
                    "The conformance test finds a difference but cannot prevent it.",
                ]},
                {
                    "control": "PL-8: Security and Privacy Architectures",
                    "text": "The control asks the organization to develop security and privacy architectures that describe how information is protected, and to review and update them (NIST leaves the frequency organization-defined; FedRAMP assigns at least annually and when a significant change occurs). This is done using:",
                },
                {"bullets": [
                    "The flow list flows.yaml: the architecture written as data, one entry per allowed call between two components.",
                    "The two generator scripts: write the network policies and the admission rule from the list, so the running project is built from the architecture file.",
                    "The conformance test: fails when the running project no longer matches the list.",
                ]},
                {
                    "control": "SC-7: Boundary Protection",
                    "text": "The control asks the organization to monitor and control communications at the external managed interfaces to the system and at key internal managed interfaces within the system. The enhancement SC-7(5) asks for deny by default and allow by exception. This is done using:",
                },
                {"bullets": [
                    "Kubernetes NetworkPolicy objects: a default-deny policy plus one allow policy per listed flow, so every other flow is blocked.",
                    "The Kyverno admission rule: refuses a hand-written network policy that was not generated from the list.",
                    "The conformance test: opens a real connection between every pair of components to show that the unlisted pairs are blocked.",
                ]},
                {
                    "control": "CM-2: Baseline Configuration",
                    "text": "The control asks the organization to develop, document and maintain under configuration control a current baseline configuration of the system, and to review and update it (NIST leaves the frequency organization-defined; FedRAMP assigns at least annually and when a significant change occurs), when organization-defined circumstances require it, and when system components are installed or upgraded. This is done using:",
                },
                {"bullets": [
                    "The flow list: the baseline, kept as one file.",
                    "The flows hash label: the generators put a hash of the list on every object, so each object names the version of the list it came from.",
                    "The conformance test: reports a network policy or admission rule whose hash differs from the current list as stale.",
                ]},
            ],
        },
        {
            "heading": "2.2 What the conformance test compares",
            "controls": [
                {"id": "CM-8 System Component Inventory"},
            ],
            "paras": [
                {"bullets": [
                    "The test reads the network policies in the project and works out which flows they allow. It then opens a real connection between every ordered pair of components and records which succeed.",
                    "A flow is covered only when a live policy allows it and a real connection succeeds. Coverage is the share of listed flows that are covered.",
                ]},
                "The test reports four kinds of drift:",
                {"bullets": [
                    "Policy or traffic drift: a listed flow that no policy allows or no connection reaches, or an unlisted flow that a policy allows or a connection reaches.",
                    "Unlisted component drift: a deployment whose app label the list does not name.",
                    "Stale network policy drift: a policy that carries the hash of an older version of the list.",
                    "Admission check drift: the admission rule is missing, is not set to Enforce, or was built from another version of the list.",
                ]},
                {
                    "control": "CM-8: System Component Inventory",
                    "text": "The control asks the organization to develop and document an inventory of system components that accurately reflects the system and includes all components within it. Its enhancement CM-8(3) asks for automated detection of unauthorized components. This is done using:",
                },
                {"bullets": [
                    "The flow list: names the allowed components, so it is the inventory.",
                    "The known-components rule in the Kyverno admission policy: refuses a pod whose app label the list does not name.",
                    "The conformance test: reports a deployment whose app label the list does not name.",
                    "The drift timer: measures how long that detection takes and checks it against the 300 second limit (FedRAMP's five-minute maximum delay).",
                ]},
            ],
        },
    ],
    "steps": [
        {
            "title": "State the allowed flows as data",
            "learn": 'Writing the flow list and running the supplied checker gives you the one file everything else is generated from, and proves it has the shape the generators expect.',
            "takeaway": 'The architecture is one short file that a person owns and a tool checks.',
            "controls": [
                {"id": "PL-8 Security and Privacy Architectures", "how": "The supplied checker rejects a flow list in the wrong shape."},
            ],
            "why": "The list is the architecture: each entry says one component may call another on one port. A supplied checker rejects a file in the wrong shape, so a typo cannot become a silent gap.",
            "note": "The lab has already installed Kyverno in the kyverno project and runs the four components in arc-ref. The supplied files check_flows.py, flows-bad.txt and drift_timer.py are in the arc folder.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p \"$HOME/arc/generated\"\n"
                        "cd \"$HOME/arc\"\n"
                        "cat > flows.yaml <<'EOF'\n"
                        + FLOWS_YAML
                        + "\nEOF\n"
                        "wc -l flows.yaml"
                    ),
                    "label": 'Save the allowed flows list',
                    "intro": 'You will now make the file flows.yaml in your arc folder by pasting the whole block at once into the lab shell. The last line counts its lines; the next block checks the content.',
                    "expect": 'Example only.\n11 flows.yaml',
                    "look_for": [
                        "namespace names the project the list describes, and every generated object is placed there.",
                        "Each entry under flows is one allowed flow. The list is the whole architecture, so a path not listed is not allowed.",
                        "from and to are the app labels of the caller and the receiver. These are the component names.",
                        "Each flow has one TCP port, so allowing a path never opens more than intended.",
                    ],
                    "lines": [
                        ("cd ... cat > flows.yaml <<'EOF' ... EOF", "Moves into the arc folder and writes the text between the first and last line into flows.yaml. The quotes around EOF keep the text exactly as typed.", "The lab has no editor, so a paste is how you make a file. The check on the last line shows the paste arrived whole."),
                        ("namespace: arc-ref", "The project (a named section of the cluster) the list describes. Every generated object is placed there.", "Puts every generated object in the right project, so none lands somewhere unexpected."),
                        ("flows", "A list. Every entry is one allowed flow.", "One entry per allowed path means the list is the whole architecture."),
                        ("from, to", "The app label (a key=value tag on a pod) of the caller and of the receiver. These are the component names.", "Names components by the label the policies select on, so the list and the cluster speak the same words."),
                        ("port: 8080", "The one TCP port (a number that picks which program on a pod receives a request) the flow may use.", "Limits each flow to one port, so allowing a path never opens more than intended."),
                    ],
                },
                {
                    "code": (
                        "cd \"$HOME/arc\"\n"
                        "python3 check_flows.py flows.yaml"
                    ),
                    "label": 'Check the list',
                    "intro": 'You will now check the list with the supplied checker.',
                    "expect": 'Example only.\nflows file OK: 3 flows, 4 components',
                    "lines": [
                        ("cd \"$HOME/arc\"", "Moves to the folder that holds the kit. Later steps use short names from here.", "The later commands use short file names, so you stand where the kit lives."),
                        ("check_flows.py flows.yaml", "Rejects a file with unknown keys, repeated flows, a flow from a component to itself, or a port outside 1 to 65535.", "Catches a typo in the list before it can produce wrong policies."),
                    ],
                },
            ],
            "checkpoint": "The checker prints flows file OK: 3 flows, 4 components.",
        },
        {
            "title": "Generate the network policies and the admission check",
            "learn": 'Generating and applying the two files turns the list into a default-deny network and an admission guard, both stamped with the hash of the list.',
            "takeaway": 'Nobody writes the policies by hand: edit the list, run the generators, apply.',
            "controls": [
                {"id": "PL-8 Security and Privacy Architectures", "how": "The generators write the policies and the admission rule from the list, so the running project is built from the architecture file."},
                {"id": "SC-7 Boundary Protection", "how": "The policy generator writes a default-deny policy and one allow policy per listed flow, and you apply them to arc-ref."},
                {"id": "CM-2 Baseline Configuration", "how": "Both generators stamp every object with a hash of the flow list, so a change to the baseline means a change to the list."},
            ],
            "why": "The network policy generator and the admission check generator read the same file and stamp every output with a short hash of it. You apply the admission check first, so it already guards the project when the network policies arrive.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p \"$HOME/arc/generated\"\n"
                        "cd \"$HOME/arc\"\n"
                        "cat > gen_netpol.py <<'EOF'\n"
                        + GEN_NETPOL
                        + "\nEOF\n"
                        "python3 -m py_compile gen_netpol.py \u0026\u0026 echo gen_netpol.py parses"
                    ),
                    "label": 'Save the network policy generator',
                    "expect": 'Example only.\ngen_netpol.py parses',
                    "intro": 'You will now make the script `gen_netpol.py` in your arc folder by pasting the whole block at once into the lab shell. The last line checks that Python can read it; you run it in the third block.',
                    "look_for": [
                        "The input list and the output file come from the command line, so the script never changes when the architecture changes.",
                        "The hash is a short fingerprint of the list file, held in the variable digest. Every policy carries it, so a policy from an older list can be seen later.",
                        "The network policy generator first writes a policy that selects every pod and allows nothing, which is default deny.",
                        "One allow policy is built for each flow in the list, with the receiver and the sender chosen by label and one TCP port.",
                        "The policies are written in a fixed order, so the same list always gives the same file.",
                    ],
                    "lines": [
                        ("`cd ... cat > gen_netpol.py <<'EOF' ... EOF`", "Moves into the arc folder and writes the text between the first and last line into `gen_netpol.py`. The quotes around EOF keep the text exactly as typed.", "The lab has no editor, so a paste is how you make a file. The check on the last line shows the paste arrived whole."),
                        ("`flows_path, out_path = sys.argv[1], sys.argv[2]`", "The input file and the output file come from the command line.", "The same script serves any list, so you never edit the generator to change the architecture."),
                        ("`digest = sha256(file)[:12]`", "The first 12 characters of a fingerprint of the file. It changes whenever the file changes.", "Stamps every object with the version of the list it came from, which makes a stale object visible later."),
                        ("`def netpol(...)`", "Builds one network policy as a dictionary (a Python structure of names and values). An empty rule means deny all.", "One function builds every policy, so they all have the same shape."),
                        ("`docs = [netpol(\"default-deny-ingress\", {}, None)]`", "The first policy selects every pod and allows nothing: the default deny.", "Starts the project from deny all, so anything not listed is blocked."),
                        ("for flow in data[\"flows\"]", "Adds one allow policy per listed flow: the receiver and the sender chosen by label, and one TCP port.", "Turns each list entry into one allow policy, so adding a flow means adding a line to the list."),
                        ("yaml.safe_dump_all", "Writes all policies to one file in a fixed order, so the same list always gives the same file.", "Same list, same file every time, so the repeatability check in Verify can pass."),
                    ],
                },
                {
                    "code": (
                        "mkdir -p \"$HOME/arc/generated\"\n"
                        "cd \"$HOME/arc\"\n"
                        "cat > gen_admission.py <<'EOF'\n"
                        + GEN_ADMISSION
                        + "\nEOF\n"
                        "python3 -m py_compile gen_admission.py \u0026\u0026 echo gen_admission.py parses"
                    ),
                    "label": 'Save the admission check generator',
                    "expect": 'Example only.\ngen_admission.py parses',
                    "intro": 'You will now make the script gen_admission.py in your arc folder by pasting the whole block at once into the lab shell. The last line checks that Python can read it; you run it in the next block.',
                    "look_for": [
                        "The set of allowed component names is built from the list itself, so the list is the only place names are written.",
                        "The admission policy has two rules, policy-from-flows and known-components. Both apply to create and update requests in the project, and each refuses a request that fails its pattern.",
                        "The policy-from-flows rule requires a network policy to carry the current hash, so a policy not generated from this list is refused.",
                        "The known-components rule requires a pod to carry an app label from the list, so an unlisted component is refused.",
                        "The annotation set to none stops Kyverno from copying the pod rule onto deployments, so an unlisted deployment can still be created and the conformance test can find it.",
                    ],
                    "lines": [
                        ("cd ... cat > gen_admission.py <<'EOF' ... EOF", "Moves into the arc folder and writes the text between the first and last line into gen_admission.py. The quotes around EOF keep the text exactly as typed.", "The lab has no editor, so a paste is how you make a file. The check on the last line shows the paste arrived whole."),
                        ("apps = sorted({...})", "Every component name that appears in any flow, as the allowed set.", "Builds the set of allowed component names from the list itself."),
                        ("`def rule(...)`", "Builds one Kyverno rule that applies to create and update requests in the project and refuses a request that fails the pattern.", "Makes both rules from one shape, so they refuse in the same way."),
                        ("label = {...arc-flows: digest}", "The pattern for network policies: the label must equal the current hash.", "Refuses a network policy that was not generated from the current list."),
                        ("known = {...app: the names joined...}", "The pattern for pods: the app label must be one of the listed names, written as one string with a vertical bar between the names.", "Refuses a pod whose app label is not in the list."),
                        ("`autogen-controllers: none`", "Stops Kyverno from copying the pod rule onto deployments (its automatic rule generation), so an unlisted deployment can still be created and the conformance test can find it. The pod rule still refuses that deployment's pods.", "Keeps an unlisted deployment creatable, so the conformance test, and not admission, is what finds it."),
                    ],
                },
                {
                    "code": (
                        "cd \"$HOME/arc\"\n"
                        "mkdir -p generated\n"
                        "python3 gen_netpol.py flows.yaml generated/networkpolicies.yaml\n"
                        "python3 gen_admission.py flows.yaml generated/admission.yaml\n"
                        "oc apply -f generated/admission.yaml --dry-run=server\n"
                        "oc apply -f generated/admission.yaml\n"
                        "oc wait clusterpolicy/arc-ref-flows --for=condition=Ready --timeout=120s\n"
                        "oc rollout status deployment/kyverno-admission-controller -n kyverno --timeout=180s\n"
                        "for try in 1 2 3; do oc apply -f generated/networkpolicies.yaml --dry-run=server && break; echo 'the Kyverno webhook is not answering yet, retrying'; sleep 15; done\n"
                        "for try in 1 2 3; do oc apply -f generated/networkpolicies.yaml && break; echo 'the Kyverno webhook is not answering yet, retrying'; sleep 15; done\n"
                        "oc get networkpolicy -n arc-ref --show-labels"
                    ),
                    "label": 'Generate both files and apply them',
                    "intro": 'You will now run both generators, apply the admission check first and then the network policies, and list the policies with their labels.',
                    "expect": 'Example only. Hashes and ages will differ.\nwrote 4 policies, flows hash <hash>\nwrote the admission check for api, cache, db, web, flows hash <hash>\nThe dry run lists clusterpolicy.kyverno.io/arc-ref-flows as created (server dry run), then the real apply lists it as created.\nclusterpolicy.kyverno.io/arc-ref-flows condition met\ndeployment "kyverno-admission-controller" successfully rolled out\nThe dry run and then the real apply list four networkpolicy objects as created (a re-run says configured or unchanged).\nA warning that ClusterPolicy is deprecated may print after each oc command that touches Kyverno policies. It is harmless.\nFour network policies in arc-ref, each with the same arc-flows=<hash> label.',
                    "lines": [
                        ("cd ... mkdir -p generated", "Moves into the arc folder and makes the folder for the generated files if it is not there.", "The commands below use short names from here, and the folder must exist to receive the files."),
                        ("`gen_netpol.py ... gen_admission.py`", "Write the two generated files. Never edit them. Edit the flow list and run these again.", "Produce the objects from the list, so nobody writes the output by hand."),
                        ("--dry-run=server", "Asks the cluster to check each file without saving it.", "Catches a mistake in the generated files before they can change the cluster."),
                        ("oc apply -f generated/admission.yaml", "Installs the admission check first, so the network policies that follow are checked by it.", "The guard goes first, so the policies that follow are checked by it."),
                        ("oc wait ... Ready", "Waits until Kyverno reports the policy ready.", "A rule that is not ready yet would not check the next apply."),
                        ("oc rollout status deployment/kyverno-admission-controller", "Waits until the Kyverno component that answers admission requests is fully running.", "The policy can be Ready before the component that serves the check is answering, and a request sent too early fails with connection refused."),
                        ("for try in 1 2 3; do ... && break; ...; done", "Tries the apply up to three times, stopping at the first success and pausing 15 seconds between tries.", "If Kyverno restarts at the wrong moment, a second try succeeds, so a short outage does not stop you."),
                        ("--show-labels", "Shows the flows hash on every network policy.", "Confirms each policy carries the current hash."),
                    ],
                },
            ],
            "tip": "Because both generators write in a fixed order, running them twice gives byte-identical files. Test 2 checks that.",
            "checkpoint": "Four network policies, each with the same arc-flows label, and the admission policy is ready.",
        },
        {
            "title": "Build the conformance test",
            "learn": 'Building and running the conformance test gives you a pass or fail answer to whether the running project matches the list, with coverage as a number.',
            "takeaway": 'A conformance test turns the question of whether the system matches its design into an exit code.',
            "controls": [
                {"id": "SC-7 Boundary Protection", "how": "The test opens a real connection from each component to every other, so a policy that says a flow is allowed is checked against real traffic."},
                {"id": "CM-8 System Component Inventory", "how": "The test lists the deployments in arc-ref and reports any whose app label the list does not name."},
            ],
            "why": "Three small files make the test: one reads the live policies and opens real connections, one holds the comparison rules, and one prints a single report and exits with failure on drift. A pipeline can act on the exit code the script returns.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p \"$HOME/arc/generated\"\n"
                        "cd \"$HOME/arc\"\n"
                        "cat > live_net.py <<'EOF'\n"
                        + LIVE_NET
                        + "\nEOF\n"
                        "python3 -m py_compile live_net.py \u0026\u0026 echo live_net.py parses"
                    ),
                    "label": 'Save the live checks',
                    "expect": 'Example only.\nlive_net.py parses',
                    "intro": 'You will now make the script live_net.py in your arc folder by pasting the whole block at once into the lab shell. The last line checks that Python can read it; conformance.py uses it.',
                    "look_for": [
                        "oc_json() is the one way the code asks the cluster. A failed command gives nothing instead of a crash.",
                        "policy_flows() works out which flows the live network policies allow, as sender, receiver and port.",
                        "reachable() tries a real connection from each component to every other on each port, using oc exec. A policy that says allowed proves nothing about traffic.",
                        "reachable() runs its attempts at the same time, so blocked pairs do not add up their waiting time.",
                    ],
                    "lines": [
                        ("cd ... cat > live_net.py <<'EOF' ... EOF", "Moves into the arc folder and writes the text between the first and last line into live_net.py. The quotes around EOF keep the text exactly as typed.", "The lab has no editor, so a paste is how you make a file. The check on the last line shows the paste arrived whole."),
                        ("`def oc_json(args)`", "Runs oc and returns its JSON answer, or nothing if the command failed.", "Gives the other functions one safe way to ask the cluster, so a failed command gives a clear nothing and not a crash."),
                        ("`def policy_flows(ns)`", "Works out which flows the live policies allow, as (from, to, port), and which components they select.", "Reads what the cluster really allows, which can differ from what the list says."),
                        ("`def reachable(ns, apps, ports)`", "Tries a TCP connection from each component to every other on each port, using oc exec in the app container.", "A policy that says allowed proves nothing about traffic, so this opens real connections."),
                        ("ThreadPoolExecutor(max_workers=12)", "Runs the 12 connection attempts at once, so blocked pairs do not add up their waiting time.", "Runs the attempts at once, so the whole test stays short enough to run often."),
                    ],
                },
                {
                    "code": (
                        "mkdir -p \"$HOME/arc/generated\"\n"
                        "cd \"$HOME/arc\"\n"
                        "cat > drift_rules.py <<'EOF'\n"
                        + DRIFT_RULES
                        + "\nEOF\n"
                        "python3 -m py_compile drift_rules.py \u0026\u0026 echo drift_rules.py parses"
                    ),
                    "label": 'Save the drift rules',
                    "expect": 'Example only.\ndrift_rules.py parses',
                    "intro": 'You will now make the script drift_rules.py in your arc folder by pasting the whole block at once into the lab shell. The last line checks that Python can read it; conformance.py uses it.',
                    "look_for": [
                        "deployed_apps() lists the app labels of the deployments that exist, so a component nobody listed can be seen.",
                        "policy_hashes() reads the hash on each live network policy, so a policy built from an older list can be seen.",
                        "admission_hash() returns nothing when the admission rule is missing, and a not-enforced marker when it is not set to Enforce.",
                        "find_drift() puts every difference in one list: policy, traffic, unlisted component, stale policy and admission check.",
                    ],
                    "lines": [
                        ("cd ... cat > drift_rules.py <<'EOF' ... EOF", "Moves into the arc folder and writes the text between the first and last line into drift_rules.py. The quotes around EOF keep the text exactly as typed.", "The lab has no editor, so a paste is how you make a file. The check on the last line shows the paste arrived whole."),
                        ("`def deployed_apps(ns)`", "The app labels of the deployments that exist.", "Lets the test see a component that nobody listed."),
                        ("`def policy_hashes(ns)`", "The flows hash found on each live network policy.", "Reveals a policy built from an older list."),
                        ("`def admission_hash()`", "The hash the live admission rule enforces, or nothing when the rule is missing or not set to Enforce.", "Shows whether the guard exists, enforces and matches the current list."),
                        ("`def find_drift(...)`", "Compares policies, traffic, deployments, hashes and the admission rule with the list and returns every difference.", "Puts every kind of difference in one list, so the report is complete."),
                    ],
                },
                {
                    "code": (
                        "mkdir -p \"$HOME/arc/generated\"\n"
                        "cd \"$HOME/arc\"\n"
                        "cat > conformance.py <<'EOF'\n"
                        + CONFORMANCE
                        + "\nEOF\n"
                        "python3 -m py_compile conformance.py \u0026\u0026 echo conformance.py parses"
                    ),
                    "label": 'Save the conformance test',
                    "expect": 'Example only.\nconformance.py parses',
                    "intro": 'You will now make the script conformance.py in your arc folder by pasting the whole block at once into the lab shell. The last line checks that Python can read it; you run it in the next block.',
                    "look_for": [
                        "listed holds the flows from the file. by_policy holds what the live policies allow. by_traffic holds what really connects.",
                        "A flow is confirmed only when it appears in listed, by_policy and by_traffic. Coverage is the share of listed flows that are confirmed.",
                        "The report lists every drift found, the pairs tested, and the time the run took.",
                        "The script exits with 1 when anything drifted and 0 when nothing did. A pipeline reads that number.",
                    ],
                    "lines": [
                        ("cd ... cat > conformance.py <<'EOF' ... EOF", "Moves into the arc folder and writes the text between the first and last line into conformance.py. The quotes around EOF keep the text exactly as typed.", "The lab has no editor, so a paste is how you make a file. The check on the last line shows the paste arrived whole."),
                        ("listed = {...}", "The flows from the file, as a set of (from, to, port).", "The intended design in a form the code can compare."),
                        ("by_policy, _ = policy_flows(ns)", "The flows the live policies allow.", "The design as the policies describe it."),
                        ("by_traffic, tested = reachable(...)", "The flows that really connect, and how many pairs were tried.", "The design as real connections show it."),
                        ("confirmed = len(listed & by_policy & by_traffic)", "Counts a flow as covered only when both the policy and the real connection agree with the list.", "A flow counts only if the policy and the traffic both agree, which makes coverage mean something."),
                        ("sys.exit(1 if drift else 0)", "A failing exit code when anything drifted.", "The exit code is what a pipeline reads, so the test can stop a change."),
                    ],
                },
                {
                    "code": (
                        "cd \"$HOME/arc\"\n"
                        "python3 conformance.py flows.yaml\n"
                        "echo \"exit code $?\""
                    ),
                    "label": 'Run the conformance test on the clean project',
                    "intro": 'You will now run the conformance test once on the project as you built it.',
                    "expect": 'Example only. The time will differ.\n{\n  "flows_listed": 3,\n  "flows_confirmed": 3,\n  "coverage_percent": 100,\n  "pairs_tested": 12,\n  "unlisted_pairs_blocked": 9,\n  "drift": [],\n  "seconds": <n>\n}\nexit code 0',
                    "lines": [
                        ("cd \"$HOME/arc\"", "Moves into the arc folder where the files are.", "The commands use short file names from here."),
                        ("conformance.py flows.yaml", "Prints the report. The drift list should be empty.", "A first clean run proves the test passes when the project matches, so a later failure means something."),
                        ("echo \"exit code $?\"", "Prints the exit code, 0 when nothing drifted.", "Shows the number a pipeline would act on."),
                    ],
                },
            ],
            "note": "Python finds live_net.py and drift_rules.py because they sit next to conformance.py in the arc folder.",
            "checkpoint": "flows_listed 3, flows_confirmed 3, coverage_percent 100, pairs_tested 12, unlisted_pairs_blocked 9, an empty drift list and exit code 0.",
        },
        {
            "title": "Try to add something nobody listed",
            "learn": 'Sending an open policy and an unlisted pod shows the admission rule refusing both before anything is saved.',
            "takeaway": 'Admission stops unlisted additions, so the test only has to find what got around it.',
            "controls": [
                {"id": "SC-7 Boundary Protection", "how": "You try to create a hand-written policy that allows every sender, and the admission rule refuses it."},
                {"id": "CM-8 System Component Inventory", "how": "You try to start a pod whose app label the list does not name, and the admission rule refuses it."},
            ],
            "why": "The admission rule should refuse a hand-written policy that opens everything and a pod the list does not name. The admission rule cannot refuse a delete, so Step 5 times how fast a delete is noticed.",
            "blocks": [
                {
                    "code": (
                        "echo '{\"apiVersion\":\"networking.k8s.io/v1\",\"kind\":\"NetworkPolicy\",\"metadata\":{\"name\":\"open-all\",\"namespace\":\"arc-ref\"},\"spec\":{\"podSelector\":{},\"ingress\":[{}],\"policyTypes\":[\"Ingress\"]}}' | oc apply -f -\n"
                        "oc run extra -n arc-ref --image=registry.access.redhat.com/ubi9/ubi-minimal:9.5 --labels=app=extra --restart=Never -- sleep 60\n"
                        "oc get networkpolicy,pod -n arc-ref | grep -E 'open-all|extra'"
                    ),
                    "label": 'Try a hand-written policy and an unlisted pod',
                    "intro": 'You will now send two requests that the admission rule should refuse, then look for either object.',
                    "expect": 'Example only. The wording of the messages will differ.\nAn error from the admission webhook that names the rule policy-from-flows and says the network policy must be generated from flows.yaml.\nAn error from the admission webhook that names the rule known-components and says the pod must carry an app label that flows.yaml lists.\n(the last command prints nothing)',
                    "lines": [
                        ("echo '{...open-all...}' | oc apply -f -", "Tries to create a network policy named open-all that allows every sender. It has no flows hash label.", "Tries the careless fix someone might make in an emergency, to see the guard refuse it."),
                        ("oc run extra ... --labels=app=extra", "Tries to start a pod whose app label is not in the list.", "Tries to add a component nobody listed, to see the guard refuse it."),
                        ("grep -E 'open-all|extra'", "Shows whether either object exists. Nothing should print.", "Silence is the proof, because a refused request leaves nothing behind."),
                    ],
                },
            ],
            "note": "The block ends with no output on purpose: a refused request leaves nothing behind. Read the two refusal messages above it and check they name the rules policy-from-flows and known-components.",
            "checkpoint": "The hand-written policy and the extra pod are both refused, and neither object exists.",
        },
        {
            "title": "Measure how fast drift is caught",
            "learn": 'Timing three kinds of drift measures how long a deleted policy, a deleted admission rule and an unlisted deployment stay unnoticed, and checks that against the 300 second limit.',
            "takeaway": 'A check is only a promise once you have measured how quickly it notices.',
            "controls": [
                {"id": "CM-8 System Component Inventory", "how": "The CM-8(3) enhancement asks for automated detection of unauthorized components. The timer causes three kinds of drift, and the last query checks each worst case against the 300 second limit (FedRAMP's five-minute maximum delay)."},
            ],
            "why": "A test nobody has timed promises nothing. The timer causes each drift, runs your test every 10 seconds until it fails, undoes the drift and prints how long detection took. The worst case is the 10 second interval plus one run, compared with the 300 second limit.",
            "blocks": [
                {
                    "code": (
                        "cd \"$HOME/arc\"\n"
                        "rm -f drift-times.json\n"
                        "for kind in policy admission component; do\n"
                        "  python3 drift_timer.py flows.yaml \"$kind\" | tee -a drift-times.json\n"
                        "done\n"
                        "jq -s 'all(.[]; .worst_case_s < 300 and .recovered)' drift-times.json"
                    ),
                    "label": 'Time three kinds of drift',
                    "intro": 'You will now run the supplied drift timer for three kinds of drift and query the saved lines. The drift timer takes a few minutes.',
                    "expect": 'Example only. Every time will differ.\nOne line of JSON for each kind of drift (policy, admission, component) with its kind, <detected_after_s>, <worst_case_s> and recovered.\ntrue',
                    "lines": [
                        ("cd ... rm -f drift-times.json", "Moves into the arc folder and removes the numbers from an earlier run, if any.", "A rerun then starts with an empty file, so old lines cannot change the final yes or no."),
                        ("for kind in policy admission component", "Repeats the timer for three kinds of drift: a deleted default-deny policy, a deleted admission rule, and an unlisted deployment.", "Covers three different ways drift happens, because each is found by a different part of the test."),
                        ("drift_timer.py flows.yaml \"$kind\"", "Confirms a clean start, causes the drift, polls every 10 seconds until the test fails, undoes the drift, and prints one line of JSON.", "Gives a measured detection time for one kind of drift, and undoes it so the next starts clean."),
                        ("tee -a drift-times.json", "Shows each line and also appends it to a file for the queries below.", "Keeps the numbers for the queries that follow."),
                        ("all(.[]; .worst_case_s < 300 and .recovered)", "True only if every kind of drift was caught within the limit and the project recovered.", "Turns the requirement into a yes or no that you can rerun."),
                    ],
                }
            ],
            "note": "The timer takes a few minutes in all. If a line shows detected_after_s as null, the test never failed within the 180 second give-up time: that drift is invisible to your test, which is a finding to fix before anything else.",
            "checkpoint": "Each kind of drift has a detection time, recovered is true for all three, and the last query prints true.",
        },
    ],
    "verify": [
        {
            "kind": "positive",
            "title": "The project matches the list and coverage is complete",
            "controls": [
                {"id": "PL-8 Security and Privacy Architectures", "how": "The query prints true only when there is no drift and every listed flow is confirmed by both policy and traffic."},
            ],
            "why": "State the pass condition as a query: no drift, and every listed flow confirmed by both policy and traffic.",
            "code": "cd \"$HOME/arc\"\npython3 conformance.py flows.yaml | jq -e '.coverage_percent == 100 and (.drift | length) == 0'",
            "expect": "Example only.\ntrue",
            "lines": [
                ("cd \"$HOME/arc\"", "Moves into the arc folder.", "The test and the list are there."),
                ("python3 conformance.py flows.yaml", "Runs the conformance test and prints its report.", "Compares the running project with the list."),
                ("jq -e '.coverage_percent == 100 and (.drift | length) == 0'", "Prints true only when coverage is 100 percent and the drift list is empty.", "A yes or no that a pipeline can act on."),
            ],
            "checkpoint": "The query prints true.",
        },
        {
            "kind": "positive",
            "title": "Generation is repeatable",
            "controls": [
                {"id": "CM-2 Baseline Configuration", "how": "The test generates the policies twice and compares the two files byte for byte."},
            ],
            "why": "Generate again to a second file and compare the two byte for byte. Only a repeatable generator lets a later difference be trusted as drift.",
            "code": (
                "cd \"$HOME/arc\"\n"
                "python3 gen_netpol.py flows.yaml generated/again.yaml\n"
                "diff generated/networkpolicies.yaml generated/again.yaml && echo identical"
            ),
            "expect": (
                "Example only.\n"
                "wrote 4 policies, flows hash 6d328d57c080\n"
                "identical"
            ),
            "lines": [
                ("`gen_netpol.py flows.yaml generated/again.yaml`", "Generates the policies a second time into a new file.", "Gives a second copy to compare against."),
                ("diff ... && echo identical", "Compares the two files byte for byte and prints identical when there is no difference.", "Shows the generator is repeatable."),
            ],
            "checkpoint": "The word identical appears. The hash is a fingerprint of your exact file text, so it matches the example only if your flows.yaml is identical to the one in Step 1.",
        },
        {
            "kind": "negative",
            "title": "The flow checker rejects a bad list",
            "controls": [
                {"id": "CM-2 Baseline Configuration", "how": "A baseline with an invalid entry would produce wrong policies. The checker must fail on a bad list with exit code 1, so the list never reaches the generators."},
            ],
            "why": "The kit includes a list with a port outside the valid range and a component that calls itself. The checker must reject that list and exit with failure, so a bad list never reaches the generators.",
            "code": (
                "cd \"$HOME/arc\"\n"
                "python3 check_flows.py flows-bad.txt\n"
                "echo \"exit code $?\""
            ),
            "expect": (
                "Example only.\n"
                "FAIL: flow 1: port must be a whole number from 1 to 65535\n"
                "FAIL: flow 2: from and to are the same component\n"
                "exit code 1"
            ),
            "lines": [
                ("check_flows.py flows-bad.txt", "Runs the checker on the bad list from the kit.", "A bad list must be stopped before it reaches the generators."),
                ("FAIL: flow 1: port must be ...", "The first flow has a port outside 1 to 65535.", "The message names the flow and the rule it breaks."),
                ("FAIL: flow 2: from and to are the same component", "The second flow calls itself.", "A second mistake is reported in the same run."),
                ("exit code 1", "1 means the list was rejected.", "Other programs read this number."),
            ],
            "checkpoint": "Two FAIL lines and exit code 1.",
        },
        {
            "kind": "negative",
            "title": "Editing the list without regenerating shows as drift",
            "controls": [
                {"id": "CM-2 Baseline Configuration", "how": "The test reports the new flow as missing and the old hash as stale."},
            ],
            "why": "A copy of the list with one extra flow stands in for a change someone made to the file and did not regenerate from. Every object built from the old list is now out of date, and the test must say so.",
            "code": (
                "cd \"$HOME/arc\"\n"
                "cp flows.yaml flows-extra.yaml\n"
                "echo \"  - from: web\" >> flows-extra.yaml\n"
                "echo \"    to: db\" >> flows-extra.yaml\n"
                "echo \"    port: 8080\" >> flows-extra.yaml\n"
                "python3 conformance.py flows-extra.yaml > drift-extra.json\n"
                "echo \"exit code $?\"\n"
                "jq -c '.drift[]' drift-extra.json"
            ),
            "expect": (
                "Example only. The hash is a fingerprint of your exact file text, so it differs if your text differs.\n"
                "exit code 1\n"
                "[\"policy missing\",[\"web\",\"db\",8080]]\n"
                "[\"traffic missing\",[\"web\",\"db\",8080]]\n"
                "[\"stale network policy\",[\"6d328d57c080\"]]\n"
                "[\"admission check\",[\"6d328d57c080\"]]"
            ),
            "lines": [
                ("cp ... echo >> flows-extra.yaml", "Makes a copy of the list and adds one more flow, web to db.", "Stands in for an edit made without regenerating."),
                ("conformance.py flows-extra.yaml > drift-extra.json", "Runs the test against the edited list. The cluster is not changed.", "The cluster was built from the old list, so it now disagrees."),
                ("exit code 1", "1 means drift was found.", "A pipeline would stop here."),
                ("policy missing / traffic missing", "No policy allows web to db and no connection works.", "The new flow is on the list but not in the cluster."),
                ("stale network policy", "The policies carry the hash of the old list.", "Objects built from an older list are visible."),
                ("admission check", "The admission rule was built from the old list.", "The guard is out of date too."),
            ],
            "checkpoint": "Exit code 1 with the new flow missing in policy and traffic, the old hash reported as stale, and the admission check reported as built from another version. Nothing in the cluster was changed, so nothing needs restoring.",
        },
    ],
    "waivers": {
        "your_turn": "The YOUR TURN lines were removed on reviewer feedback (ENG-0); the optional command list replaces them.",
    },
    "glossary": [
        ("Reference architecture", "A design other teams copy."),
        ("Generator", "A script that produces configuration from data."),
        ("Conformance test", "A script that compares the running system with the intended design and fails on a difference."),
        ("Drift", "Any difference between the intended design and the running system."),
        ("Coverage", "The share of listed flows the test confirms with a policy and a real connection."),
        ("Admission check", "A rule applied when something is created or changed, which can refuse it."),
        ("Flows hash", "A short fingerprint of the flow file carried by every generated object."),
        ("Network policy", "A cluster rule that limits which pods may send traffic to which other pods."),
    ],
    "design": [
        {
            "decision": "Keep the allowed flows in one data file and generate from it",
            "how": "One short YAML file lists the components and allowed flows. Generators write a default-deny policy, one allow policy per flow and an admission policy, each carrying a hash of the file.",
            "why": "Hand-written policies drift and differ between teams, whereas generated ones are identical every time and a test can compare them with the running system.",
            "alternatives": "Hand-written policies reviewed in pull requests are the alternative. Advantage: full flexibility for unusual rules. Drawback: drift, style differences and no machine link between the list and the objects.",
        },
        {
            "decision": "Add a timed conformance test to the admission check",
            "how": "The test compares the live policies, the real connections between every ordered pair, the deployments and the hash with the file, and a short timer reruns it.",
            "why": "Admission cannot stop a delete, so only a repeated comparison catches one, and the worst-case detection time is the interval plus one run.",
            "alternatives": "Admission alone is the alternative. Advantage: bad changes are refused at once and nothing needs polling. Drawback: it is blind to deletes and to drift that happened before the rule existed.",
        },
    ],
    "next": "This is the last module in the track. ARC-5 closes the architecture dimension: you stated the allowed flows once as data, generated the rules from it and proved the cluster still matches it.",
}


MODULE["portability"] = {
    "bullets": [
        "The flow list, the two generators and the conformance logic are plain YAML and Python. They port to any Kubernetes cluster whose network plugin enforces NetworkPolicy and that runs Kyverno.",
        "Change these lab values first: the project arc-ref, the four component names and port 8080 in flows.yaml, the kyverno project, the cluster policy name arc-ref-flows, and the two public images ubi9/python-311:1 and ubi9/ubi-minimal:9.5.",
        "The probes use oc exec into a container named app in each deployment. On another platform use kubectl exec and check that your containers have that name and can open a TCP connection.",
        "The 10 second interval and the 180 second give-up time are lab choices. The 300 second limit is the five-minute maximum detection delay FedRAMP assigns for CM-8(3). In production use the delay your authorization assigns, run the test from a pipeline on a schedule, and send a failure to a person.",
    ],
    "headers": ["Check/part", "In this lab", "On other platforms", "What you change"],
    "rows": [
        ("Flow list and generators", "flows.yaml and two Python scripts using PyYAML in the lab shell", "The same files with any Python 3 that has PyYAML", "The namespace, component names and port."),
        ("Network policies", "Kubernetes NetworkPolicy, enforced by the OpenShift default network plugin OVN-Kubernetes", "Kubernetes NetworkPolicy, if the cluster's network plugin enforces it", "Check that your plugin enforces NetworkPolicy. If it does not, replace the check."),
        ("Admission rule", "Kyverno cluster policy arc-ref-flows", "The same, where Kyverno is installed", "The policy name and the namespace. With another policy engine, replace the check."),
        ("Connection probes", "oc exec into the app container, then python3 opens a TCP connection", "kubectl exec, if the container has python3 or another way to open a connection", "The tool name, the container name and the probe command."),
        ("Drift timer", "Supplied drift_timer.py run from the lab shell", "A scheduled job or pipeline that runs the same test", "The runner. The test stays the same."),
        ("Detection limit", "300 seconds, the FedRAMP five-minute maximum for CM-8(3)", "The value your authorization assigns", "The limit in the jq query at the end of Step 5."),
    ],
}
