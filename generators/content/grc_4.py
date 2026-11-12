"""GRC-4: Evidence in the Delivery Pipeline (SA-11, SI-7, CM-6). Engineering track, level 4."""

NIST = "nist-sp-800-53r5-full.md"

SCAN_TASK = '''apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: evidence-scan
  namespace: build
spec:
  params:
    - name: image-ref
    - name: severity
      default: "HIGH,CRITICAL"
  workspaces:
    - name: evidence
  steps:
    - name: scan
      image: ghcr.io/aquasecurity/trivy:0.76.1
      env:
        - name: TRIVY_CACHE_DIR
          value: $(workspaces.evidence.path)/.trivy
      script: |
        #!/bin/sh
        rm -f $(workspaces.evidence.path)/*.json
        trivy image --no-progress --severity $(params.severity) --format json --output $(workspaces.evidence.path)/trivy.json $(params.image-ref)
    - name: gate
      image: registry.access.redhat.com/ubi9/python-312:1
      script: |
        #!/usr/bin/env python3
        import json
        report = json.load(open("$(workspaces.evidence.path)/trivy.json"))
        count = sum(len(r.get("Vulnerabilities") or []) for r in report.get("Results") or [])
        print("blocking findings:", count)
        raise SystemExit(1 if count else 0)
'''

BUNDLE_TASK = '''apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: evidence-bundle
  namespace: build
spec:
  params:
    - name: run
    - name: image-ref
  workspaces:
    - name: evidence
    - name: signing
      readOnly: true
  results:
    - name: bundle
    - name: signature
  steps:
    - name: assemble
      image: registry.access.redhat.com/ubi9/python-312:1
      workingDir: $(workspaces.evidence.path)
      script: |
        #!/usr/bin/env python3
        import hashlib
        import json
        from datetime import datetime, timezone
        raw = open("trivy.json", "rb").read()
        findings = sum(len(r.get("Vulnerabilities") or []) for r in json.loads(raw).get("Results") or [])
        policy = json.load(open("policy-check.json"))
        bundle = {"run": "$(params.run)", "image": "$(params.image-ref)",
                  "collected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "scan": {"sha256": hashlib.sha256(raw).hexdigest(), "blocking_findings": findings},
                  "policy": {"manifest": policy["manifest"], "result": policy["result"]}}
        open("bundle.json", "w").write(json.dumps(bundle, separators=(",", ":")))
    - name: sign
      image: ghcr.io/sigstore/cosign/cosign:v3.1.4
      workingDir: $(workspaces.evidence.path)
      env:
        - name: COSIGN_PASSWORD
          valueFrom:
            secretKeyRef: {name: evidence-signing, key: cosign.password}
      securityContext:
        runAsUser: 65532
      command: ["/ko-app/cosign"]
      args: ["sign-blob", "--yes", "--key", "$(workspaces.signing.path)/cosign.key", "--use-signing-config=false", "--tlog-upload=false", "--bundle", "bundle.sigstore.json", "bundle.json"]
    - name: verify
      image: ghcr.io/sigstore/cosign/cosign:v3.1.4
      workingDir: $(workspaces.evidence.path)
      command: ["/ko-app/cosign"]
      args: ["verify-blob", "--key", "$(workspaces.signing.path)/cosign.pub", "--bundle", "bundle.sigstore.json", "--insecure-ignore-tlog=true", "bundle.json"]
    - name: publish
      image: registry.access.redhat.com/ubi9/python-312:1
      workingDir: $(workspaces.evidence.path)
      securityContext:
        runAsUser: 65532
      script: |
        #!/usr/bin/env python3
        import json
        open("$(results.bundle.path)", "w").write(open("bundle.json").read())
        signature = json.load(open("bundle.sigstore.json"))
        open("$(results.signature.path)", "w").write(json.dumps(signature, separators=(",", ":")))
'''

PIPELINE = '''apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: evidence-bundle
  namespace: build
spec:
  params:
    - name: image-ref
    - name: manifest
      default: good.yaml
  workspaces:
    - name: evidence
    - name: candidate
    - name: signing
  tasks:
    - name: scan
      taskRef:
        name: evidence-scan
      params:
        - {name: image-ref, value: $(params.image-ref)}
      workspaces:
        - {name: evidence, workspace: evidence}
    - name: policy
      runAfter: ["scan"]
      taskRef:
        name: evidence-policy
      params:
        - {name: manifest, value: $(params.manifest)}
      workspaces:
        - {name: candidate, workspace: candidate}
        - {name: evidence, workspace: evidence}
    - name: bundle
      runAfter: ["policy"]
      taskRef:
        name: evidence-bundle
      params:
        - {name: run, value: $(context.pipelineRun.name)}
        - {name: image-ref, value: $(params.image-ref)}
      workspaces:
        - {name: evidence, workspace: evidence}
        - {name: signing, workspace: signing}
  results:
    - name: bundle
      value: $(tasks.bundle.results.bundle)
    - name: signature
      value: $(tasks.bundle.results.signature)
'''

WORK = "cd /workspace/grc-4\n"

ADMIT_HEAD = '''import json
import os
import subprocess

manifest = os.environ["MANIFEST"]
path = os.environ["CANDIDATE"] + "/" + manifest
'''

ADMIT_GAP_HINT = '''# Your lines go here (about four). Use these names, the last two lines need them:
#   run     the result of running: oc apply --dry-run=server -n demo -f <path>
#           (capture the output as text)
#   result  "admitted" if the exit code of run is 0, otherwise "denied"
#   text    json.dumps of a dictionary with the keys manifest, result, message
#           (message is the output and the error text of run joined together)
# Then write text to the file policy-check.json in the folder named by EVIDENCE.
'''

ADMIT_TAIL = '''print(text)
raise SystemExit(0 if result == "admitted" else 1)
'''


def heredoc(name, text):
    return "cat > " + name + " <<'EOF'\n" + text + "EOF\n"


START = (
    "tkn pipeline start evidence-bundle -n build -s pipeline \\\n"
    "  -p image-ref=\"%s\" \\\n"
    "  -p manifest=%s \\\n"
    "  -w name=evidence,claimName=evidence-work \\\n"
    "  -w name=candidate,config=candidate-manifests \\\n"
    "  -w name=signing,secret=evidence-signing \\\n"
    "  --showlog"
)

GET_RESULT = (
    "oc get pipelinerun \"$RUN\" -n build -o jsonpath='{.status.results[?(@.name==\"bundle\")].value}' > bundle.json\n"
    "oc get pipelinerun \"$RUN\" -n build -o jsonpath='{.status.results[?(@.name==\"signature\")].value}' > bundle.sigstore.json\n"
    "test -s bundle.json || echo \"bundle.json is empty: the run did not finish, read its log with tkn pipelinerun logs $RUN -n build\""
)

MODULE = {
    "intent_at_end": True,
    "id": "GRC-4",
    "slug": "EvidenceInPipeline",
    "title": "Evidence in the Delivery Pipeline",
    "draft": (
        "Live-run status (2026-11-10): the PVC size, reset, publish-step user and signing inside the pipeline were fixed and re-run; the two cosign flags, Kyverno dry run and autogen rule, Tekton configMap volume, and image pulls were confirmed. "
        "Cosign 3 hides the flags `--use-signing-config=false` and `--tlog-upload=false` from help but still accepts them (the Cosign 3.1.4 source marks both deprecated and hidden, not removed); Step 1 checks that your release accepts them. "
        "Not yet re-run end to end on the final lab state: a clean good run with the evidence-app image (registry.k8s.io/pause, no operating system packages, so Step 1 should print 0; a nonzero count is a real finding, not a fault). Confirm with `trivy image` in Step 1 and the blocking findings line in Step 4. "
        "The Kyverno check is a server-side dry run, not the Kyverno command-line tool, because the tool is not in the lab shell. "
        "The pipeline runs as the existing pipeline service account, which the lab gives edit rights in the demo namespace so the dry run can be authorized. "
        "The failing-scan test needs to pull docker.io/library/nginx:1.16 or a lab mirror of it."
    ),
    "controls": ["SA-11", "SI-7", "CM-6"],
    "mentions": ["CA-7", "CM-3"],
    "unit_values_ok": ["2 minutes", "3 minutes", "10 minutes"],
    "tool_why": True,
    "hide_draft": True,
    "hover": True,
    "terms_at_end": True,
    "minutes": {"hands_on": 48, "verify": 23},
    "tools": [
        "OpenShift Pipelines (Tekton)",
        "Trivy (free, open source)",
        "Kyverno (free, open source)",
        "Cosign (free, open source)",
        "OpenSSL",
        "oc",
        "tkn",
        "jq",
    ],
    "diagrams": [
        {
            "id": "flow",
            "title": "One run, three checks, one signed bundle",
            "caption": "This is the lab (test) setup. Each run scans the image, asks Kyverno whether a candidate change would be admitted, and signs one evidence bundle. In production the signing key lives in a key management service, bundles are stored where they cannot be edited after they are written, and verification runs in a separate system. Each step below adds one part, drawn with thick lines.",
            "per_step": True,
            "rankdir": "LR",
            "step_notes": {
                1: "You create a signing key for evidence as a secret in the build project, keep the public half in a file in your lab shell, and check the scanner and the signing flags.",
                2: "You test the policy check two ways against a bad change and keep the one that stops it before anything is created in the demo namespace.",
                3: "The three tasks are saved in the build project: scan, policy check, and bundle with signature.",
                4: "The pipeline wires the tasks in order and keeps the bundle and its signature as results on the run record in the build project. You copy them into your lab shell and verify them there.",
            },
            "zones": [
                {"id": "lab", "label": "Your lab", "kind": "boundary"},
                {"id": "cluster", "icon": "aws/group-AWS-Cloud", "label": "Lab cluster (your OpenShift cluster, in AWS)", "parent": "lab", "kind": "boundary"},
                {"id": "build", "icon": "brands/openshift", "label": "Build project", "parent": "cluster", "kind": "group"},
                {"id": "kyv", "icon": "brands/openshift", "label": "Kyverno project (the policy engine)", "parent": "cluster", "kind": "group"},
                {"id": "demo", "icon": "brands/openshift", "label": "Demo project (the application)", "parent": "cluster", "kind": "group"},
                {"id": "shell", "label": "Lab shell (a container on your computer)", "parent": "lab", "kind": "group"},
            ],
            "key": {"aws/group-AWS-Cloud": "AWS Cloud", "brands/openshift": "OpenShift project", "k8s/secret": "Kubernetes secret", "brands/tekton": "Tekton task", "brands/trivy": "Trivy image scanner", "brands/json": "JSON evidence bundle", "brands/gnubash": "Shell session"},
            "nodes": [
                {"id": "key", "title": "Evidence signing key", "icon": "k8s/secret", "sub": "Kubernetes secret evidence-signing, a Cosign key pair", "zone": "build", "kind": "warn", "s": 1},
                {"id": "scan", "icon": "brands/trivy", "title": "Scan task", "sub": "Tekton task running Trivy; fails on HIGH or CRITICAL", "zone": "build", "s": 3},
                {"id": "pol", "icon": "brands/tekton", "title": "Policy check task", "sub": "Tekton task: server-side dry run", "zone": "build", "s": 3},
                {"id": "bun", "icon": "brands/tekton", "title": "Bundle task", "sub": "Tekton task: builds and signs with Cosign", "zone": "build", "kind": "ok", "s": 3},
                {"id": "res", "icon": "brands/json", "title": "Pipeline result", "sub": "Bundle and signature kept on the pipeline run", "zone": "build", "kind": "ok", "s": 4},
                {"id": "pl", "title": "Kyverno policy", "sub": "Kyverno cluster policy that refuses the latest tag", "zone": "kyv"},
                {"id": "dep", "title": "Target namespace demo", "sub": "Target of the dry run; nothing is created", "zone": "demo"},
                {"id": "ver", "icon": "brands/gnubash", "title": "Your verification", "sub": "Shell session: cosign checks with the public key", "zone": "shell", "kind": "ok", "s": 4},
            ],
            "edges": [
                {"a": "scan", "b": "pol", "n": 1, "label": "Then", "s": 3},
                {"a": "pol", "b": "bun", "n": 2, "label": "Then", "s": 3},
                {"a": "key", "b": "bun", "label": "Signs with", "flat": True, "s": 3},
                {"a": "pol", "b": "pl", "label": "Dry run answered by", "s": 3},
                {"a": "pl", "b": "dep", "label": "Judges a change for", "flat": True},
                {"a": "bun", "b": "res", "n": 3, "label": "Keeps", "kind": "ok", "s": 4},
                {"a": "res", "b": "ver", "label": "Copied to the lab shell", "kind": "ok", "s": 4},
            ],
            "why_built": (
                "You work in the lab shell on your laptop, as in the foundation module, and you start the pipeline and check its output from there. "
                "This module adds a pipeline of three tasks to the build project on the cluster. Proof about a release should come from the same automated path that handles the release, not from a person typing it in. "
                "The policy task does not create anything in the demo namespace. The policy task asks Kyverno, which runs in its own project, whether the cluster would admit a candidate change. Kyverno's answer comes from the same rules that apply at deploy time. "
                "The signing key is a secret in the build project. The signing key is separate from any release key, so a leak of one cannot spoil the other. "
                "The bundle and its signature stay on the pipeline run in the build project. You verify the bundle and its signature in the lab shell with the public key only, so the check does not depend on anything the pipeline controls."
            ),
            "setup": [
                ("Pipeline and its three tasks", "The build namespace, run by OpenShift Pipelines", "Proof about a release comes from the automated path that handles the release, not from a person typing it in."),
                ("Signing key", "A secret in the build namespace", "The bundle task can sign without a person holding the private key, and the key stays separate from any release key."),
                ("Policy check", "A dry run sent from the build namespace to the cluster, answered by Kyverno in its own namespace", "It asks the question the cluster will ask at deploy time and creates nothing in the demo namespace."),
                ("Bundle and signature", "Results on the pipeline run in the build namespace", "The run record outlives the pods, so an auditor can read the bundle after the run."),
                ("Verification", "The lab shell on your laptop", "Checking with the public key outside the pipeline means a compromised pipeline cannot vouch for itself."),
            ],
            "reading": [
                "1. Evidence signing key: a Cosign key pair stored as a secret in the build project; the bundle task signs with it.",
                "2. Scan task: runs Trivy on the image and stops the run on any HIGH or CRITICAL finding.",
                "3. Policy check task: sends the candidate change to the cluster as a server-side dry run and creates nothing.",
                "4. Bundle task: runs only after both checks pass, builds one evidence bundle and signs it with the evidence key.",
                "5. Pipeline result: the bundle and its signature, kept on the pipeline run record in the build project.",
                "6. Kyverno policy: the rule that refuses the latest tag; it answers the dry run from the policy check task.",
                "7. Target namespace demo: the namespace the candidate change is judged for; nothing is created in it.",
                "8. Your verification: your lab shell copies the bundle and signature and checks them with the public key alone.",
            ],
        },
    ],
    "prereq": [
        "ENG-0 Terminal, Git and Your Lab (typing commands in lab shell, reading oc output, and making a file with a heredoc)",
    ],
    "lab_needs": [],
    "lab": {
        "start": "lab start grc-4",
        "env": [],
    },
    "objectives": [
        {"label": "Skill", "text": "Build a three-task pipeline that scans an image, checks a candidate change against policy, and signs one evidence bundle per passing run."},
        {"label": "Tools", "text": "Trivy scans images for known flaws; Kyverno checks candidate changes through a server-side dry run; Cosign signs the evidence bundle with a key kept as a cluster secret."},
        {"label": "Security Function", "text": "Produces tamper-evident proof per release. A failing scan or a refused change stops the pipeline before a bundle exists, so every bundle describes a passing run."},
        {"label": "NIST SA-11 Developer Testing and Evaluation", "text": "Trivy runs on every pipeline run. A HIGH or CRITICAL finding stops the run. The findings count and a hash of the report go into the bundle."},
        {"label": "NIST SI-7 Software, Firmware, and Information Integrity", "text": "Cosign signs the bundle with an evidence key. Anyone with the public key can verify the bundle is unchanged. A changed bundle fails verification."},
        {"label": "NIST CM-6 Configuration Settings", "text": "A server-side dry run asks Kyverno whether a candidate change would be admitted. The answer is recorded in the bundle and a refused change stops the run."},
    ],
    "requirement": (
        "A regulated system has to show, for every release, that it was tested and that the proof was not changed afterwards. "
        "A scan report sitting in a build log proves little: anyone with access could edit it, and nothing says which run made it. "
        "This module builds a pipeline (an automated sequence of tasks) on your cluster (the group of servers that runs your lab). It scans an image (a packaged copy of a program) with Trivy (a free scanner for known flaws), asks Kyverno (a policy engine that can refuse requests) whether a candidate change "
        "would be accepted by the cluster, and then produces one evidence bundle (a single file that holds the results and the facts about the run) "
        "signed with Cosign (a free tool that signs and checks files). A signature is made with a private key and checked with a public key, so any change to the bundle makes the check fail. "
        "A failing scan or a refused change stops the pipeline before a bundle exists, so the bundles that do exist all describe passing runs."
    ),
    "requirement_bullets": [
        "Purpose: produce tamper-evident proof per release showing the image was scanned, the change was policy-checked, and both passed (SA-11, SI-7, CM-6).",
        "The pipeline has three tasks. One scans the image with Trivy, one asks Kyverno about a candidate change in a dry run, and one signs an evidence bundle with Cosign.",
        "A failing scan or a refused change stops the pipeline before a bundle exists.",
        "You verify the bundle from the lab shell with the public key alone, so the check does not depend on the pipeline.",
    ],
    "mapping": [
        {
            "control": "SA-11 Developer Testing and Evaluation",
            "plain": "The people who build the system test it, keep proof of the testing, and fix what the tests find.",
            "source": "NIST",
            "tool": "Trivy, run by the scan task of an OpenShift Pipelines (Tekton) pipeline. Explained in section 2.1.",
            "covered": "Section 3, Step 3: the scan task is a gate. Section 3, Step 4: the scan result is kept in the bundle. Section 4, Test 3: a failing scan stops the run.",
            "cite": [
                {"file": NIST, "quote": "Produce evidence of the execution of the assessment plan and the results of the testing and evaluation"},
            ],
        },
        {
            "control": "SI-7 Software, Firmware, and Information Integrity",
            "plain": "Detect unauthorized changes to software and information, and act when one is found.",
            "source": "NIST",
            "tool": "Cosign, which signs the bundle in the bundle task. Explained in section 2.2.",
            "covered": "Section 3, Steps 1 and 3: you make the evidence key and save the task that signs. Section 3, Step 4: the bundle is signed. Section 4, Test 1: the bundle verifies. Section 4, Test 2: a changed bundle fails verification.",
            "cite": [
                {"file": NIST, "quote": "Employ integrity verification tools to detect unauthorized changes to the following software"},
            ],
        },
        {
            "control": "CM-6 Configuration Settings",
            "plain": "Settings are implemented as approved and changes to them are controlled.",
            "source": "NIST",
            "tool": "Kyverno, asked through a server-side dry run in the policy task. Explained in section 2.3.",
            "covered": "Section 3, Step 2: you choose the dry run. Section 3, Step 3: the policy task asks Kyverno whether a candidate change would be admitted. Section 3, Step 4: the run records the policy result in the bundle. Section 4, Test 4: a bad change is refused.",
            "cite": [
                {"file": NIST, "quote": "Monitor and control changes to the configuration settings in accordance with organizational policies and procedures"},
            ],
        },
    ],
    "intent": [
        {
            "control": "SA-11 Developer Testing and Evaluation",
            "feared": "A release goes out with a known serious flaw, or the test result sits only in a log nobody can find.",
            "scope": "Every image the pipeline handles.",
            "question": "For this release, which scan ran, what did it find, and can the answer be produced without rerunning anything?",
            "evidence": "A bundle per run that holds the findings count, a hash of the scan output and the image reference.",
            "sufficient": "The scan runs on every run, a HIGH or CRITICAL finding stops the run, and the result is kept with the run. NIST leaves the testing frequency and depth organization-defined.",
            "tieoff": "A stopped run is visible in the pipeline record. The developer owns the fix.",
            "tool": "Trivy runs in the scan task (Step 3). The count and a hash of the report go into the bundle (Step 3 and Step 4).",
        },
        {
            "control": "SI-7 Software, Firmware, and Information Integrity",
            "feared": "Evidence is edited after the fact, for example to make an old result look recent, and nobody can tell.",
            "scope": "The evidence bundles the pipeline produces.",
            "question": "If one character in a stored bundle changed, would anything notice?",
            "evidence": "The signature, the public key, and a verification that fails on a changed bundle.",
            "sufficient": "Each bundle is signed by a key kept for the pipeline, and anyone with the public key can check it. NIST leaves the actions on a detected change organization-defined; here the bundle is not used as evidence.",
            "tieoff": "A bundle that fails verification is reported to the owner of the pipeline. The key is separate from any release key, so a leak of one does not spoil the other.",
            "tool": "Cosign signs the bundle with a key held as a secret in the build project (Steps 1, 3 and 4).",
        },
        {
            "control": "CM-6 Configuration Settings",
            "feared": "A change that breaks a rule, such as using the latest tag, reaches production because the rule was only written down.",
            "scope": "Candidate changes to workloads in the demo namespace.",
            "question": "Would the cluster accept this change, and do we know that before the change is made?",
            "evidence": "The admission result for the candidate change, recorded in the bundle.",
            "sufficient": "The cluster enforces the rule, and the pipeline asks it the same question it will ask at deploy time, changing nothing while it asks.",
            "tieoff": "A refused change stops the run, and the Kyverno message says which rule it broke.",
            "tool": "A server-side dry run of the candidate manifest against the Kyverno policy (Steps 2 and 3).",
        },
    ],
    "terms": [
        ("Evidence bundle", "One file that holds the results of a run and the facts about it, signed so a change can be detected."),
        ("Signature", "A value made with a private key that proves who produced a file and that it was not changed."),
        ("Public and private key", "A linked pair. The private key signs, and the public key checks."),
        ("Transparency log", "A public record of signatures. The lab does not use one."),
        ("Dry run", "Asking the cluster to check a request as if it were real, without saving anything."),
        ("Admission controller", "A cluster component that can accept or refuse a request before the object is created."),
        ("Gate", "A check that stops the pipeline if it fails."),
        ("Workspace (Tekton)", "A shared folder or mounted secret that tasks in a pipeline can use."),
        ("Pipeline result", "A small value a run keeps in its record after it finishes."),
        ("Digest", "A fixed fingerprint of an image's exact contents. A tag can move to a different image. A digest cannot."),
        ("Cluster", "A group of servers that work together as one system. Here it is your own OpenShift cluster in AWS."),
        ("Namespace", "A named section of the cluster that keeps workloads apart. OpenShift also calls it a project."),
        ("Pod", "One running copy of a program inside the cluster."),
        ("Pipeline", "An automated sequence of tasks. Each task runs in its own pod."),
        ("Task", "One stage of a pipeline. It runs its steps in a pod and can pass or fail."),
        ("Pipeline run", "One execution of a pipeline. Its record keeps the status and the results."),
        ("Tekton", "The pipeline engine inside OpenShift Pipelines."),
        ("Service account", "An identity for a program instead of a person."),
        ("Config map", "A stored file or setting that the cluster keeps and can hand to a program."),
        ("Environment variable", "A named value that a program can read when it starts, such as MANIFEST."),
        ("Heredoc", "A way to save typed text into a file from the shell: everything between the first EOF line and the last EOF line becomes the file."),
        ("Secret", "A protected cluster object that holds sensitive values such as a key."),
        ("Image", "A packaged copy of a program with everything it needs. The cluster starts pods from images."),
        ("Image tag", "A label on an image, such as latest. A tag can be moved to a different image."),
        ("Manifest", "A file that describes an object for the cluster, such as a Deployment."),
        ("Deployment", "A cluster object that keeps a set of pods running from one image."),
        ("Candidate", "A change you are checking before it is made. Here it is a Deployment file that nothing has created yet."),
        ("Kyverno", "A policy engine that can refuse requests to the cluster."),
        ("Policy", "A rule the cluster checks. Kyverno holds the policies in this lab."),
        ("Enforce mode", "A policy setting that refuses a request that breaks the rule."),
        ("Audit mode", "A policy setting that lets a request through and only records a report afterward."),
        ("Policy report", "A list of the results Kyverno recorded when it checked objects against its policies."),
        ("Trivy", "A free scanner for known flaws in container images."),
        ("Vulnerability", "A known flaw in software that an attacker might use."),
        ("Severity", "How serious a flaw is: LOW, MEDIUM, HIGH or CRITICAL."),
        ("Cosign", "A free tool that signs and verifies images and other files."),
        ("Hash", "A fixed-length fingerprint of content. The same content always gives the same hash."),
        ("Base64", "A text encoding for binary data. It is not encryption."),
        ("Key management service", "A managed system that holds keys and signs on request without exposing the private key."),
        ("YAML", "A plain-text format for settings, written as indented lines of name and value. Cluster objects are described in it."),
        ("JSON", "A plain-text format for data: names and values written inside curly braces."),
        ("oc", "The OpenShift command-line tool. It sends your commands to the cluster."),
        ("tkn", "The command-line tool for OpenShift Pipelines. It starts and reads pipeline runs."),
        ("jq", "A command-line tool that reads and picks fields out of JSON."),
        ("Exit code", "A number a command returns when it ends. Zero means success. Any other number means failure."),
        ("Tamper-evident", "Built so that any change to it can be seen afterward."),
        ("openssl", "A command-line tool for cryptography. Here it makes a random password for the signing key."),
    ],
    "concepts": [
        {
            "heading": "2.1 Why one signed bundle",
            "controls": [
                {"id": 'SA-11 Developer Testing and Evaluation'},
            ],
            "paras": [
                {"bullets": [
                    "A pipeline produces many pieces of proof: a scan report, a policy answer, a run name, a time.",
                    "A bundle collects the facts into one small file; a signature makes any later edit visible.",
                    "A reader can check the bundle with a public key alone, without trusting the person who hands it over.",
                    "A failed check stops the run, so no bundle exists for it and every bundle describes a passing run.",
                ]},
                {
                    "control": 'SA-11: Developer Testing and Evaluation',
                    "text": 'The control asks the organization to require the developer to plan and carry out ongoing security and privacy testing, to produce evidence of the results, to have a verifiable flaw remediation process, and to correct the flaws that testing finds. NIST leaves the testing frequency and depth organization-defined. This is done using:',
                },
                {"bullets": [
                    "Trivy in the scan task: scans the image on every run and writes the report.",
                    "The gate step of the scan task: stops the run when the report holds any HIGH or CRITICAL finding.",
                    "The evidence bundle: records the findings count and a hash of the report, so the result stays with the run.",
                    "The developer: fixes the flaws the scan finds, because the pipeline supplies the testing and the evidence and not the fix.",
                ]},
                "The table shows four design choices in this module, the two options for each, and which one the module uses:",
            ],
            "table": {
                "headers": ["Choice", "Option A", "Option B", "What this module does"],
                "rows": [
                    ("Signing key", "Reuse the release signing key", "A separate evidence key", "A separate key, so evidence signing and release signing can be rotated and revoked on their own"),
                    ("Policy check", "Read Kyverno reports", "Dry-run the change against the policy", "Dry run, because reports exist only after an object does (Step 2 proves it)"),
                    ("Failure behavior", "Write a bundle that says failed", "Write no bundle", "Write no bundle, so every bundle that exists describes a passing run"),
                    ("Image reference", "A tag", "A digest", "A digest, so the bundle names exactly what was scanned"),
                ],
            },
        },
        {
            "heading": "2.2 What the signature does and does not prove",
            "controls": [
                {"id": 'SI-7 Software, Firmware, and Information Integrity'},
            ],
            "paras": [
                {"bullets": [
                    "The signature proves the bundle is byte-for-byte what the pipeline signed.",
                    "The signature does not prove the scan was thorough, the pipeline was configured correctly, or the private key was never copied.",
                    "The key is a plain cluster secret in the lab, a shortcut a real system would replace with a key management service.",
                    "Verification must run outside the pipeline so a compromised pipeline cannot vouch for itself.",
                ]},
                {
                    "control": 'SI-7: Software, Firmware, and Information Integrity',
                    "text": 'The control asks the organization to use integrity verification tools to detect unauthorized changes to organization-defined software, firmware and information, and to take organization-defined actions when one is detected. Here the information is the evidence bundle. This is done using:',
                },
                {"bullets": [
                    "Cosign in the bundle task: signs the bundle with the evidence key, so a changed bundle no longer matches its signature.",
                    "The verify step of the bundle task and your own check in the lab shell: confirm the signature with the public key, and a changed bundle fails.",
                    "The lab's chosen action: a bundle that fails verification is not used as evidence.",
                ]},
            ],
        },
        {
            "heading": "2.3 How the policy check works without changing anything",
            "controls": [
                {"id": 'CM-6 Configuration Settings'},
            ],
            "paras": [
                {"bullets": [
                    "A server-side dry run sends the manifest to the cluster API without saving anything.",
                    "Kyverno checks the request and returns a refusal or an approval.",
                    "A server-side dry run sees only policies in Enforce mode.",
                    "A policy in Audit mode lets the request through, so a dry run of a breaking change still succeeds.",
                ]},
                {
                    "control": 'CM-6: Configuration Settings',
                    "text": 'The control asks the organization to establish and document configuration settings at the most restrictive mode consistent with operational requirements, implement them, approve any deviations, and monitor and control changes to them. Here the setting is that a Deployment may not use the latest image tag. This is done using:',
                },
                {"bullets": [
                    "The Kyverno policy grc-enforce-no-latest-tag in Enforce mode: implements the setting by refusing a Deployment that uses the latest tag.",
                    "The policy task: asks the cluster the deploy-time question with a server-side dry run that creates nothing.",
                    "The evidence bundle: records the answer, and a refused change stops the run.",
                ]},
            ],
            "production": "In the real environment the signing key lives in a key management service. Bundles are stored where they cannot be edited after they are written, and verification runs in a separate system before a release is accepted. The lab uses a cluster secret and your own shell.",
        },
    ],
    "steps": [
        {
            "title": "Make the evidence signing key and check the ingredients",
            "learn": "Making the evidence key pair and running a trial scan shows what the pipeline will sign and what the gate will see before anything is built.",
            "takeaway": "A separate key for evidence means signing and release can be rotated and revoked on their own.",
            "controls": [
                {"id": 'SI-7 Software, Firmware, and Information Integrity', "how": 'You make a key pair used only for evidence and check that Cosign accepts the signing flags. The public half stays in your lab shell for later verification.'},
                {"id": 'SA-11 Developer Testing and Evaluation', "how": 'You run Trivy once on the demo image to see what the pipeline gate will see. The count tells you whether the good run in Step 4 will pass.'},
            ],
            "why": "Make a key pair used only for evidence and keep the public half in your lab shell. Check the tools: the signing task uses two Cosign flags, and your Cosign release must accept them. The scan count tells you what the pipeline gate will see.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p /workspace/grc-4\n"
                        "cd /workspace/grc-4\n"
                        "oc get pods -n kyverno\n"
                        "oc get clusterpolicy grc-enforce-no-latest-tag\n"
                        "oc delete secret evidence-signing -n build --ignore-not-found\n"
                        "COSIGN_PASSWORD=\"$(openssl rand -base64 24)\" cosign generate-key-pair k8s://build/evidence-signing\n"
                        "oc get secret evidence-signing -n build -o jsonpath='{.data.cosign\\.pub}' | base64 -d > cosign.pub\n"
                        "head -n 1 cosign.pub\n"
                        "cosign sign-blob --use-signing-config=false --tlog-upload=false --help > /dev/null && echo flags-accepted\n"
                        "IMAGE=$(oc get pods -n demo -l app=evidence-app -o jsonpath='{.items[0].status.containerStatuses[0].imageID}')\n"
                        "echo \"$IMAGE\"\n"
                        "trivy image --quiet --severity HIGH,CRITICAL --format json \"$IMAGE\" | jq '[.Results[]?.Vulnerabilities[]?] | length'"
                    ),
                    "label": 'Make the signing key and check the tools',
                    "intro": 'You will now make a signing key for evidence, save its public half in a file, and check that Kyverno, Cosign and Trivy are ready. The step needs the lab shell to reach the internet (Trivy downloads its database). Running the block again is safe, but it replaces the key, so bundles you made earlier no longer verify with the new public key.',
                    "expect": 'Example only. Your names, digest and count will differ.\n(the pods in the kyverno namespace, all Running)\nNAME  ADMISSIONS  BACKGROUND  VALIDATE ACTION  READY ...\ngrc-enforce-no-latest-tag  ...  Enforce  true ...\n(Cosign reports that it created the secret evidence-signing in the build namespace)\n-----BEGIN PUBLIC KEY-----\nflags-accepted\n<image reference>@sha256:<digest>\n<n>',
                    "lines": [
                        ("mkdir -p ... && cd ...", "Makes a folder for this module and moves into it, so files from other modules cannot collide with yours. The folder persists between lab sessions.", "The key, the public key file and your notes for this module stay in one folder, apart from other modules."),
                        ("oc get pods -n kyverno", "Confirms the policy engine is running.", "The policy check in Step 2 needs Kyverno running, so you confirm it now and not halfway through a pipeline run."),
                        ("`oc get clusterpolicy grc-enforce-no-latest-tag`", "Shows the policy the lab created. The READY column should be true.", "The pipeline will ask this policy about a bad change, so you check that it exists and is ready before you rely on it."),
                        ("oc delete secret evidence-signing --ignore-not-found", "Removes a key left from an earlier attempt, so the next command does not fail because the secret already exists. No output is fine.", "A leftover key from an earlier attempt would make the next command fail, so you clear the way first."),
                        ("COSIGN_PASSWORD=... cosign generate-key-pair k8s://build/evidence-signing", "Makes a key pair and stores it as the secret evidence-signing. The password is random, lives for this one command, and is stored only in the secret.", "The pipeline needs a private key of its own to sign with. A new pair keeps evidence signing apart from any release key."),
                        ("base64 -d > cosign.pub", "Decodes the public key into a file. Secrets are stored base64-encoded, a text encoding that is not encryption.", "You verify later with the public key alone, so you take that half out of the cluster and keep it in a file."),
                        ("head -n 1 cosign.pub", "Prints the first line of the public key file.", "A key file starts with BEGIN PUBLIC KEY; an empty answer means the key was not saved."),
                        ("cosign sign-blob ... --help && echo flags-accepted", "Checks that your Cosign release accepts the two flags that turn off the public transparency log. An unknown flag error means the release does not fit this module.", "The signing task uses these two flags, so you find out now whether your release accepts them and not in the middle of a run."),
                        ("IMAGE=$(oc get pods ...)", "Reads the exact image digest the evidence application is running, not a tag that could move.", "You scan and sign evidence about one exact image, so you name it by its digest, which cannot move."),
                        ("trivy image ... | jq length", "Counts HIGH and CRITICAL findings in that image. This is the number the gate will see.", "If the image already has blocking findings, the good run in Step 4 would correctly stop, so you learn the number now."),
                    ],
                }
            ],
            "security": "The private key is stored as an ordinary cluster secret in the lab. Anyone who can read secrets in the build project can read it. Keep that access to the pipeline and its administrators, and move the key to a key management service in the real environment.",
            "action": "Run the block. Read the count Trivy prints. A nonzero count is a real result and means the good run in Step 4 will correctly stop. If the count is not zero, tell your AI assistant the number before you go on.",
            "checkpoint": "The policy shows READY true, the flag check prints flags-accepted, cosign.pub starts with BEGIN PUBLIC KEY, and IMAGE ends in a `sha256` digest.",
        },
        {
            "title": "Decide how the policy check runs, using the cluster's own answers",
            "learn": "Testing both ways of asking Kyverno about a bad change before the object exists shows which option works in a pipeline.",
            "takeaway": "A dry run stops a bad change before it exists; a policy report appears only after.",
            "controls": [
                {"id": 'CM-6 Configuration Settings', "how": 'The dry run is refused with a message naming the policy. The report count is zero because nothing was created.'},
            ],
            "why": "Test the dry run and the policy report on the bad candidate; only the dry run answers before the object exists.",
            "blocks": [
                {
                    "code": (
                        "cd /workspace/grc-4\n"
                        "oc get clusterpolicy grc-enforce-no-latest-tag -o jsonpath='{.spec.rules[0].validate.failureAction}{\"\\n\"}'\n"
                        "oc get configmap candidate-manifests -n build -o jsonpath='{.data.bad\\.yaml}' > bad.yaml\n"
                        "oc apply --dry-run=server -n demo -f bad.yaml\n"
                        "oc get policyreports.wgpolicyk8s.io -n demo -o json | jq '[.items[] | select((.scope.name // \"\") | startswith(\"candidate-app\"))] | length'"
                    ),
                    "label": 'Try both ways of asking Kyverno about the bad change',
                    "intro": 'You will now check the policy mode, copy the bad candidate out of the cluster, and ask about it in two ways. The lab stored the bad candidate in the config map candidate-manifests. Nothing is created.',
                    "expect": 'Example only. The wording comes from Kyverno and your release.\nEnforce\nError from server: ... denied the request ... grc-enforce-no-latest-tag ...\n0',
                    "lines": [
                        ("cd (the module folder)", "Moves into the module folder from Step 1.", "bad.yaml is saved here, beside your other files."),
                        ("jsonpath ... failureAction", "Prints the policy's mode. Enforce means a breaking request is refused. Audit would only record it.", "Only a policy in Enforce mode refuses a bad change, so you check the mode before you judge either option."),
                        ("oc get configmap candidate-manifests ... > bad.yaml", "Copies the bad candidate out of the cluster so you can see it and use it.", "You need the bad candidate in a file so you can test both options against the same change."),
                        ("oc apply --dry-run=server", "Option one: asks the cluster to process the change without saving it. The Kyverno answer comes back as an error.", "This is the option that can stop a bad change before it exists, so you see what it says about this one."),
                        ("`oc get policyreports.wgpolicyk8s.io ... | jq length`", "Option two: counts the policy reports whose scope (the object a report is about) is the candidate. A report exists only for an object that already exists, so a bad change that was never created has none. The reports of other workloads are not counted.", "This is the other option, and the count shows it has nothing to say about a change that was never created."),
                    ],
                }
            ],
            "action": "Run the block and read what each option told you about the bad change.",
            "checkpoint": "The mode is Enforce, the dry run is refused with a message that names `grc-enforce-no-latest-tag`, and the report count for the candidate is 0 because nothing was created. The dry run is the option that stops a bad change before it exists, so the pipeline uses it.",
        },
        {
            "title": "Save the tasks, and write the policy check script yourself",
            "learn": "Saving the three tasks and writing the policy check script builds the pipeline's core: a gate that stops the run before any bundle exists.",
            "takeaway": "Each task exits with an error on failure, so the bundle task only starts after both checks pass.",
            "controls": [
                {"id": 'SA-11 Developer Testing and Evaluation', "how": 'The scan task fails the run on any HIGH or CRITICAL finding. The bundle task puts a hash of the report into the bundle.'},
                {"id": 'CM-6 Configuration Settings', "how": 'You write the dry-run script. It records the answer in policy-check.json and fails the task on a denial.'},
                {"id": 'SI-7 Software, Firmware, and Information Integrity', "how": 'The bundle task signs the bundle and verifies its own signature. The signature covers the exact bytes.'},
            ],
            "why": "Each task can be read and reused on its own. A task that exits with an error stops the pipeline there. The scan fails on a finding; the policy task fails on a refusal; the bundle task signs and verifies in the same run.",
            "blocks": [
                {
                    "code": WORK + heredoc("evidence-scan.yaml", SCAN_TASK),
                    "label": 'Save the scan task',
                    "intro": 'You will now save this YAML as evidence-scan.yaml in the module folder. Paste all the lines at once into the lab shell. The file uses spaces only, never tabs.',
                    "expect": 'Example only. Saving the file prints nothing.',
                    "lines": [
                        ("cd (the module folder)", "Moves into the module folder.", "The file is made in the folder you stand in."),
                        ("cat > evidence-scan.yaml <<'EOF' ... EOF", "Saves everything between the first and last line as the file. The quotes around EOF keep the dollar signs for Tekton to fill in.", "No editor is needed; the paste is the whole file."),
                        ("params severity", "Which severities count as blocking. The default is HIGH and CRITICAL.", "The blocking level is a parameter, so a run can use a stricter or looser level without editing the task."),
                        ("workspaces evidence", "The shared folder tasks use to hand files to each other.", "The later tasks read the scan report from here, so the report must sit on a folder they share."),
                        ("the Trivy image line", "The public Trivy image, at a fixed version.", "Nothing is built by the lab, and every learner scans with the same version."),
                        ("rm -f ...*.json", "Clears files left by an earlier run, so old evidence cannot be mistaken for new.", "The bundle will carry a hash of this report, so a report left from another run could make wrong evidence look right."),
                        ("TRIVY_CACHE_DIR ... .trivy", "Keeps the downloaded vulnerability database in the shared folder, so the next run reuses it. The rm line only removes json files, so the database stays.", "Downloading the database on every run is slow, so keeping it on the shared folder makes later runs quick."),
                        ("trivy image ... --format json --output", "Scans the image and keeps the report as trivy.json. The severity filter means the file holds only the blocking findings.", "The bundle needs the report to hash, and the gate step needs it to count."),
                        ("gate step: the Python lines", "Reads the report, adds up the findings and exits with an error if the count is above zero.", "This is the step that makes a serious finding stop the run before any bundle exists."),
                    ],
                },
                {
                    "code": (
                        WORK +
                        "oc get configmap policy-kit -n build -o jsonpath='{.data.evidence-policy\\.yaml}' > evidence-policy.yaml\n"
                        "cat evidence-policy.yaml"
                    ),
                    "label": 'Get the policy check task',
                    "intro": 'You will now copy the policy check task out of the config map and print it. The lab supplies the task, and the last step of the task runs a Python file called admit.py, which you write in the next block.',
                    "expect": 'Example only. The first lines of the file are shown; the rest follows the same layout.\napiVersion: tekton.dev/v1\nkind: Task\nmetadata:\n  name: evidence-policy\n  namespace: build\nspec:\n  ...',
                    "lines": [
                        ("cd (the module folder)", "Moves into the module folder.", "The file is saved in the folder you stand in."),
                        ("oc get configmap policy-kit ... > evidence-policy.yaml", "Copies the task file out of the config map policy-kit into a file.", "The task is supplied, so you read it and apply it and do not retype it."),
                        ("workspaces candidate", "A read-only folder that holds the candidate manifests.", "The task must read the change it is asked about, and it should not be able to alter it."),
                        ("get-oc step", "Copies the oc program out of the public image quay.io/openshift/origin-cli:4.22.0 into a shared folder.", "The Python image has no oc, so oc is brought in this way."),
                        ("env MANIFEST, CANDIDATE, EVIDENCE", "Hands your script three environment variables: the manifest name, the candidate folder and the evidence folder.", "Your script reads plain variables and needs no Tekton syntax."),
                        ("volumes admit-script, and command python3 /admit/admit.py", "Mounts a config map called admit-script as the folder /admit and runs admit.py from it. You create that config map from your file below.", "The task runs your script, so what you write is what the pipeline does."),
                    ],
                },
                {
                    "code": WORK + heredoc("admit.py", ADMIT_HEAD + ADMIT_GAP_HINT + ADMIT_TAIL) + "test -s admit.py && grep -q 'dry-run=server' admit.py && echo \"ok: admit.py has your lines\" || echo \"NOT READY: admit.py is empty or has no dry-run line; write your lines and run the block again\"\n",
                    "label": 'Save admit.py: supplied lines around your part (about 10 minutes)',
                    "intro": 'You will now save admit.py in one paste. The first lines and the last two lines are supplied. Your part is the gap between them, which is about four lines. Before you press Enter, replace the comment lines that start with # inside the block with your own lines, using the spec in those comments. Use run, result and text as the names, because the last two supplied lines use result and text. Do not open the reference answer yet: try first. The block prints ok when admit.py has content and a dry-run line.',
                    "expect": 'Example only. Your lines will differ.\nok: admit.py has your lines',
                    "lines": [
                        ("cat > admit.py <<'EOF' ... EOF", "Saves everything between the first and last line as admit.py in one go. The quotes around EOF keep the text as typed.", "One file, one paste: the supplied lines and yours end up together in the same file."),
                        ("`import json, os, subprocess` (supplied)", "Loads the three Python tools the script needs: JSON text, environment variables and running another program (`subprocess`).", "Your lines use all three."),
                        ("manifest = os.environ[\"MANIFEST\"] (supplied)", "Reads the candidate file name, for example good.yaml.", "The same script then works for any candidate."),
                        ("path = ... (supplied)", "Joins the candidate folder and the file name.", "This is the file you hand to oc."),
                        ("run (yours)", "The finished process of oc apply with --dry-run=server, -n demo and -f path. Use `subprocess.run` with `capture_output=True` and `text=True`.", "The cluster, through Kyverno, answers whether it would admit the change, and nothing is created."),
                        ("result (yours)", "The word admitted when `run.returncode` is 0, otherwise denied.", "The bundle records a clear word and not only an exit code."),
                        ("text (yours)", "json.dumps of a dictionary with manifest, result and message (`run.stdout` plus `run.stderr`).", "The bundle task reads manifest and result from this file, so the key names must match."),
                        ("write to policy-check.json (yours)", "Writes text to the file policy-check.json in the folder named by the EVIDENCE variable.", "The record must exist even when the change is denied, so it is written before the script can exit."),
                        ("print(text) (supplied)", "Shows the record in the task log.", "You read the answer in the log of the run."),
                        ("raise SystemExit(0 if result == \"admitted\" else 1) (supplied)", "Ends the script with success for an admitted change and an error for a denied one.", "A denied change must stop the run, so that no bundle is made for it."),
                        ("test -s admit.py && grep -q 'dry-run=server' admit.py && echo ok || echo NOT READY", "Prints ok if admit.py has content and a dry-run line, and NOT READY if not.", "Pasting the block without writing your lines leaves no dry run in the file, and the policy check would fail later with a Python error."),
                    ],
                },
                {
                    "code": WORK + heredoc("evidence-bundle.yaml", BUNDLE_TASK),
                    "label": 'Save the bundle task',
                    "intro": 'You will now save this YAML as evidence-bundle.yaml in the module folder. Paste all the lines at once into the lab shell.',
                    "expect": 'Example only. Saving the file prints nothing.',
                    "lines": [
                        ("results bundle, signature", "The two values the task hands back to the pipeline.", "The pipeline can only keep a value that a task returns, so the task names the two values it hands back."),
                        ("assemble step: the SHA-256 call", "The fingerprint of the scan report, so the bundle commits to the exact report.", "The bundle holds a hash and not the whole report, so a reader can later check the report against it."),
                        ("assemble step: json.dumps(bundle, separators=...)", "Builds the bundle as one compact line: run name, image, time, the scan summary and the policy result.", "One compact line gives the signature a single exact set of bytes to cover, and gives a reader the facts in one place."),
                        ("secretKeyRef cosign.password", "Gives Cosign the key password from the secret.", "The key password must never sit in a file or on a command line, so the task takes it from the secret."),
                        ("sign step: cosign sign-blob --bundle", "Signs the bundle file and writes the signature, with the digest it covers, to the signature file. It runs in the public cosign image.", "This is the step that makes any later edit to the bundle detectable."),
                        ("verify step: cosign verify-blob --bundle", "Checks the signature right away. A failure here stops the run.", "A bad signature should stop the run at once, before a bundle that cannot be verified is kept."),
                        ("publish step", "Hands the bundle and its signature to the pipeline as results.", "Results are how the pipeline keeps the bundle and signature after the pod is gone, so you read them back from the run record."),
                    ],
                },
                {
                    "code": (
                        WORK +
                        "oc create configmap admit-script -n build --from-file=admit.py --dry-run=client -o yaml | oc apply -f -\n"
                        "oc get configmap admit-script -n build\n"
                        "oc apply -f evidence-scan.yaml --dry-run=server\n"
                        "oc apply -f evidence-scan.yaml -f evidence-policy.yaml -f evidence-bundle.yaml\n"
                        "tkn task list -n build"
                    ),
                    "label": 'Save your script, check and apply the three tasks',
                    "intro": 'You will now save admit.py as the config map admit-script, check the scan task file with a dry run, apply all three task files, and list the tasks. Running the block again after you change admit.py updates the script.',
                    "expect": 'Example only. Your ages will differ.\nconfigmap/admit-script created\nNAME  DATA  AGE\nadmit-script  1  <age>\ntask.tekton.dev/evidence-scan created (server dry run)\ntask.tekton.dev/evidence-scan created\ntask.tekton.dev/evidence-policy created\ntask.tekton.dev/evidence-bundle created\nNAME  DESCRIPTION  AGE\nevidence-bundle  ...  <age>\nevidence-policy  ...  <age>\nevidence-scan  ...  <age>',
                    "lines": [
                        ("cd (the module folder)", "Moves into the module folder, where the files are.", "oc reads the files from here."),
                        ("oc create configmap admit-script ... | oc apply -f -", "Stores your admit.py as a config map. The dry-run create plus apply means a second run just updates it.", "The policy task mounts this config map and runs your script from it."),
                        ("oc get configmap admit-script", "Reads the config map back from the cluster. DATA 1 means admit.py is in it.", "The output shows the cluster holds your script. DATA 0 or an error means admit.py was empty; rewrite it."),
                        ("--dry-run=server", "Asks the cluster to check the file without saving it.", "A mistake in the file shows up now, before anything is saved."),
                        ("oc apply -f ... -f ... -f ...", "Saves all three tasks. Each YAML above is its own file. Applying again just updates them.", "The pipeline in Step 4 refers to these tasks by name, so they must exist first."),
                        ("tkn task list", "Lists the saved tasks. Your three should be there.", "It confirms all three tasks were saved before you wire them together."),
                    ],
                },
                {
                    "code": (
                        WORK +
                        "tkn task start evidence-policy -n build -s pipeline \\\n"
                        "  -p manifest=good.yaml \\\n"
                        "  -w name=candidate,config=candidate-manifests \\\n"
                        "  -w name=evidence,claimName=evidence-work \\\n"
                        "  --showlog"
                    ),
                    "label": 'Check your script on the good candidate',
                    "intro": 'You will now run the policy check task alone on the good candidate, whose answer you already know: admitted. The step needs the cluster to reach the internet the first time, because it pulls two public images. If the task fails at once with a Python error, admit.py is probably empty or incomplete: rewrite it. On the first run the log can stop early at "Waiting for logs..." while the images download. The task still finishes: follow it with tkn taskrun logs --last -f -n build.',
                    "expect": 'Example only. Your run name and message will differ.\nTaskRun started: evidence-policy-run-<id>\n[admit] {"manifest": "good.yaml", "result": "admitted", "message": "deployment.apps/candidate-app created (server dry run)\\n"}',
                    "lines": [
                        ("cd (the module folder)", "Moves into the module folder.", "Every block starts from a known folder."),
                        ("tkn task start evidence-policy", "Runs only the policy check task, once.", "You test your script alone before it sits inside the pipeline."),
                        ("-s pipeline", "Runs it as the pipeline service account, which may dry-run changes in the demo namespace.", "The dry run needs rights in the demo namespace."),
                        ("-p manifest=good.yaml", "Asks about the good candidate, which uses a fixed image tag and not latest.", "The right answer is known: admitted."),
                        ("-w name=candidate,config=candidate-manifests", "Gives the task the candidate manifests as a read-only folder.", "The task reads the change from here."),
                        ("-w name=evidence,claimName=evidence-work", "Gives the task the shared evidence folder. The lab created this storage, named evidence-work, for you.", "Your script writes policy-check.json here."),
                        ("[admit] {...\"result\": \"admitted\"...}", "The line your print(text) wrote. The result must be admitted.", "This is the positive check against the known answer. The negative check is Test 4."),
                    ],
                },
                {
                    "code": (
                        WORK +
                        "oc get configmap policy-kit -n build -o jsonpath='{.data.admit\\.reference\\.py}' > admit.reference.py\n"
                        "cat admit.reference.py"
                    ),
                    "label": 'Only after you have tried: the reference answer',
                    "intro": 'You will now read the reference answer, but only after you have tried to write your own lines and run the check above. If your script did not print admitted, compare it with this one, find the difference, fix your admit.py, and run the previous blocks again. Your script matches the reference if it behaves the same way, even when the wording differs.',
                    "expect": 'Example only. The file is about 11 lines and ends with:\nprint(text)\nraise SystemExit(0 if result == "admitted" else 1)',
                    "lines": [
                        ("oc get configmap policy-kit ... > admit.reference.py", "Copies the reference answer out of the config map into a file named admit.reference.py. Your own admit.py is not changed.", "You compare behavior with a working version, and your file stays yours."),
                        ("cat admit.reference.py", "Prints the reference answer.", "Compare the oc call, the result word, the keys of the dictionary and the file name with yours."),
                    ],
                },
            ],
            "tip": "Keep these files in git so changes to the pipeline are reviewed like any other change (CM-3).",
            "action": "Paste the scan task and the bundle task. Copy out the policy task, save admit.py with your own lines in the gap from the spec, then save the script to the cluster, apply the three tasks and run the policy check on the good candidate. Open the reference answer only after you have tried.",
            "checkpoint": "tkn lists evidence-scan, evidence-policy and evidence-bundle, and the policy check run alone prints a record with result admitted for good.yaml.",
        },
        {
            "title": "Wire the pipeline, run it, and read the bundle",
            "learn": "Running the full pipeline on a good image and candidate produces one signed bundle and stores it on the run record.",
            "takeaway": "An auditor reads the bundle and signature from the run record, not from your lab shell.",
            "controls": [
                {"id": 'SA-11 Developer Testing and Evaluation', "how": 'The run scans the image and keeps the findings count and a report hash in the bundle. Bundle and signature stay on the run record.'},
                {"id": 'CM-6 Configuration Settings', "how": 'The run asks Kyverno about the good candidate. The admission answer is recorded in the bundle.'},
                {"id": 'SI-7 Software, Firmware, and Information Integrity', "how": 'The run signs the bundle and keeps signature and bundle on the run record. You copy both to your lab shell.'},
            ],
            "why": "The pipeline orders the tasks and passes shared folders between them. The pipeline keeps the bundle and signature as its results, and an auditor reads them from the run record after the pods are gone.",
            "blocks": [
                {
                    "code": WORK + heredoc("evidence-bundle-pipeline.yaml", PIPELINE),
                    "label": 'Save the pipeline',
                    "intro": 'You will now save this YAML as evidence-bundle-pipeline.yaml in the module folder. Paste all the lines at once into the lab shell.',
                    "expect": 'Example only. Saving the file prints nothing.',
                    "lines": [
                        ("cat > evidence-bundle-pipeline.yaml <<'EOF' ... EOF", "Saves everything between the first and last line as the file.", "No editor is needed; the paste is the whole file."),
                        ("params image-ref, manifest", "What to scan and which candidate to check. The default candidate is the good one.", "The pipeline runs on any image and any candidate, so these are inputs and are not fixed in the file."),
                        ("workspaces", "The shared evidence folder, the candidate manifests and the signing secret.", "Each task gets only the folders it needs, and the signing key reaches only the bundle task."),
                        ("runAfter", "Puts the tasks in order: scan, then policy, then bundle. A failed task means the later ones never start.", "The order is the rule: the bundle comes last, so it can exist only after both checks pass."),
                        ("$(context.pipelineRun.name)", "The name of this run, written into the bundle so the bundle names the run that made it.", "A reader can later tie a bundle to the exact run that made it."),
                        ("results", "Exposes the bundle and the signature in the run record.", "The run record is where you and an auditor read the bundle and signature after the pods are gone."),
                    ],
                },
                {
                    "code": (
                        WORK +
                        "IMAGE=$(oc get pods -n demo -l app=evidence-app -o jsonpath='{.items[0].status.containerStatuses[0].imageID}')\n"
                        "oc apply -f evidence-bundle-pipeline.yaml --dry-run=server\n"
                        "oc apply -f evidence-bundle-pipeline.yaml\n"
                        + START % ("$IMAGE", "good.yaml") + "\n"
                        "RUN=$(tkn pipelinerun describe --last -n build -o jsonpath='{.metadata.name}')\n"
                        + GET_RESULT
                    ),
                    "label": 'Run the pipeline and copy out the bundle',
                    "intro": 'You will now apply the pipeline, run it on the demo image with the good candidate, and copy the bundle and its signature out of the run record. The step needs the cluster to reach the internet: the first run pulls four public images and the Trivy database, which can take a few minutes.',
                    "expect": 'Example only. Your run name and times will differ.\npipeline.tekton.dev/evidence-bundle created (server dry run)\npipeline.tekton.dev/evidence-bundle created\n(the task logs stream: scan, then policy, then bundle; the scan log ends with: blocking findings: 0)\n(the last three commands print nothing when the run succeeded; they save bundle.json and bundle.sigstore.json and check that the first is not empty)',
                    "lines": [
                        ("cd (the module folder)", "Moves into the module folder.", "The bundle and signature files are saved here."),
                        ("IMAGE=$(oc get pods ...)", "Reads the evidence application's image digest again, so the block also works in a new lab shell.", "A new lab shell does not remember the earlier value, so the block sets it again."),
                        ("oc apply --dry-run=server, then oc apply", "Checks and saves the pipeline.", "The pipeline refers to the tasks you saved, so a mistake in this file should show before the run begins."),
                        ("tkn pipeline start evidence-bundle", "Starts one run.", "This is the run that produces the bundle you verify next."),
                        ("-s pipeline", "Runs it as the pipeline service account, which can dry-run changes in the demo namespace.", "The policy task needs rights in the demo namespace to ask its dry-run question, and this account has them."),
                        ("-p image-ref=\"$IMAGE\"", "The exact image digest from Step 1.", "The bundle must name exactly what was scanned, so the run gets the digest and not a tag."),
                        ("-w name=evidence,claimName=evidence-work", "The shared storage evidence-work, which the lab created. It carries files between the tasks.", "The three tasks hand files to each other through this folder."),
                        ("-w name=candidate,config=candidate-manifests", "The candidate manifests as a read-only folder.", "The policy task reads the change it checks from here."),
                        ("-w name=signing,secret=evidence-signing", "The signing key secret.", "Only the bundle task needs the key, and this is how it reaches it."),
                        ("jsonpath status.results", "Reads the bundle and the signature out of the run record into two files.", "You verify the bundle from your lab shell, so you copy it and its signature out of the run record into two files."),
                    ],
                },
            ],
            "action": "Paste the pipeline file, then apply it and run it. Test 1 prints the bundle fields.",
            "checkpoint": "All three tasks finish and bundle.json and the signature file exist. Test 1 shows your image, a time, blocking_findings 0 and policy result admitted.",
        },
    ],
    "verify": [
        {
            "kind": "positive",
            "title": "The bundle verifies with the public key, outside the pipeline",
            "controls": [
                {"id": 'SI-7 Software, Firmware, and Information Integrity', "how": 'You verify the bundle from the lab shell with the public key alone, outside the pipeline. Verified OK means the bundle is exactly what was signed.'},
            ],
            "why": "The pipeline checked its own signature, which proves only that it can read its own work. Verify from the lab shell with the public key alone, so the check depends on nothing the pipeline controls.",
            "code": (
                "cd /workspace/grc-4\n"
                "cosign verify-blob --key cosign.pub --bundle bundle.sigstore.json --insecure-ignore-tlog=true bundle.json\n"
                "jq '{run, image, collected_at, blocking: .scan.blocking_findings, policy: .policy.result}' bundle.json"
            ),
            "expect": (
                "Example only. Names and times will differ.\n"
                "Verified OK\n"
                "{\n"
                "  \"run\": \"evidence-bundle-run-x7k2p\",\n"
                "  \"image\": \"registry.k8s.io/pause@sha256:3f1c0a9e5b7d2c4a8e6f1b0d9c3a7e5f2b4d6c8a0e1f3b5d7c9a1e3f5b7d9c0a\",\n"
                "  \"collected_at\": \"2026-10-29T21:40:07Z\",\n"
                "  \"blocking\": 0,\n"
                "  \"policy\": \"admitted\"\n"
                "}"
            ),
            "lines": [
                ("cd (the module folder)", "Moves into the module folder, where bundle.json and the signature file from Step 4 are.", "Both commands read those files."),
                ("cosign verify-blob --key cosign.pub --bundle ...", "Checks the signature on bundle.json with the public key alone. The log check is skipped because the lab does not use a transparency log.", "The check depends on nothing the pipeline controls."),
                ("Verified OK", "The bundle is exactly what was signed.", "Any other answer means the bundle cannot be trusted."),
                ("jq '{run, image, ...}'", "Prints the main fields of the bundle: run name, image, time, blocking findings and the policy answer.", "Shows what the signature vouches for."),
            ],
            "checkpoint": "Cosign prints Verified OK, and the bundle names your image digest, a recent time, zero blocking findings and an admitted change.",
        },
        {
            "kind": "negative",
            "title": "A changed bundle fails verification",
            "controls": [
                {"id": 'SI-7 Software, Firmware, and Information Integrity', "how": "A changed copy of the bundle fails verification because the signature covered the original bytes. The lab's action on a failure is that the bundle is not used as evidence."},
            ],
            "why": "Change the time in a copy of the bundle and verify the copy; the signature covered the original bytes, so verification must fail.",
            "code": (
                "cd /workspace/grc-4\n"
                "sed 's/\"collected_at\":\"[^\"]*\"/\"collected_at\":\"2030-01-01T00:00:00Z\"/' bundle.json > tampered.json\n"
                "diff bundle.json tampered.json | head -n 2\n"
                "cosign verify-blob --key cosign.pub --bundle bundle.sigstore.json --insecure-ignore-tlog=true tampered.json"
            ),
            "expect": (
                "Example only. The exact wording depends on your Cosign release.\n"
                "1c1\n"
                "< {\"run\":\"...\",...,\"collected_at\":\"2026-10-29T21:40:07Z\",...}\n"
                "Error: ... (a signature mismatch message, for example: invalid signature when validating ASN.1 encoded signature; it may not name tampered.json)"
            ),
            "lines": [
                ("cd (the module folder)", "Moves into the module folder.", "The copy is made beside the real bundle."),
                ("sed ... > tampered.json", "Makes a copy with the time changed to the year 2030, the edit someone would make to pass old evidence off as new.", "The signature must detect this tampering."),
                ("diff bundle.json tampered.json | head -n 2", "Shows the changed line.", "Confirms the copy really differs."),
                ("cosign verify-blob ... tampered.json", "Verifies the copy with the same command as before.", "Verification of the copy must fail: the signature covered the original bytes."),
            ],
            "checkpoint": "Verification fails with an error about the signature or the digest. `diff` shows the changed time. If it prints Verified OK, the bundle is not protected and you must stop and report it.",
        },
        {
            "kind": "negative",
            "title": "A failing scan stops the pipeline and leaves no bundle",
            "controls": [
                {"id": 'SA-11 Developer Testing and Evaluation', "how": 'An old image with known serious flaws fails the scan, so the later tasks never start. The run record holds no bundle, so no evidence can claim the image passed.'},
            ],
            "why": "Run the same pipeline on an old image with known serious flaws. The step needs the cluster to reach the internet (it pulls the old image and the Trivy database). The scan must fail, the later tasks must never start, and the run record must hold no bundle at all.",
            "code": (
                "cd /workspace/grc-4\n"
                + START % ("docker.io/library/nginx:1.16", "good.yaml") + " || true\n"
                "RUN=$(tkn pipelinerun describe --last -n build -o jsonpath='{.metadata.name}')\n"
                "oc get pipelinerun \"$RUN\" -n build -o jsonpath='{.status.conditions[0].reason}{\"\\n\"}'\n"
                "oc get taskrun -n build -l tekton.dev/pipelineRun=$RUN -o jsonpath='{range .items[*]}{.metadata.labels.tekton\\.dev/pipelineTask} {.status.conditions[0].reason}{\"\\n\"}{end}'\n"
                "oc get pipelinerun \"$RUN\" -n build -o jsonpath='{.status.results}{\"\\n\"}'"
            ),
            "expect": (
                "Example only. Counts and run names will differ.\n"
                "[scan : gate] blocking findings: <a long count, over a hundred>\n"
                "Failed\n"
                "scan StepFailed\n"
                "(empty line: the run has no results)"
            ),
            "lines": [
                ("tkn pipeline start ... nginx:1.16 || true", "Runs the pipeline on an old image. The || true keeps the block going when the run fails, which is what should happen.", "The run is meant to fail."),
                ("conditions[0].reason", "Prints how the run ended: Failed.", "The run must not succeed."),
                ("get taskrun ... pipelineTask", "Lists the tasks that started and how they ended: only scan, StepFailed (Tekton's word for a task whose step failed).", "The policy and bundle tasks never started."),
                ("status.results", "Prints the results of the run. They are empty.", "No bundle exists, so nothing can claim this image passed."),
            ],
            "checkpoint": "The run reason is Failed, only the scan task exists and its reason is StepFailed, and the results are empty. No bundle was made, so no bundle can claim this image passed.",
        },
        {
            "kind": "negative",
            "title": "A change that breaks policy stops the pipeline",
            "controls": [
                {"id": 'CM-6 Configuration Settings', "how": 'The bad candidate that uses the latest tag is refused by the policy task, so the bundle task never starts. The output is a refused change and no bundle.'},
            ],
            "why": "Run the pipeline on the good image but with the bad candidate, the Deployment that uses the latest tag. The scan will pass, the policy task must record the denial and fail, and the bundle task must never start.",
            "code": (
                "cd /workspace/grc-4\n"
                "IMAGE=$(oc get pods -n demo -l app=evidence-app -o jsonpath='{.items[0].status.containerStatuses[0].imageID}')\n"
                + START % ("$IMAGE", "bad.yaml") + " || true\n"
                "RUN=$(tkn pipelinerun describe --last -n build -o jsonpath='{.metadata.name}')\n"
                "oc get taskrun -n build -l tekton.dev/pipelineRun=$RUN -o jsonpath='{range .items[*]}{.metadata.labels.tekton\\.dev/pipelineTask} {.status.conditions[0].reason}{\"\\n\"}{end}'\n"
                "oc get pipelinerun \"$RUN\" -n build -o jsonpath='{.status.results}{\"\\n\"}'"
            ),
            "expect": (
                "Example only. The wording depends on your Kyverno release.\n"
                "(the policy task log shows a denial message that names grc-enforce-no-latest-tag)\n"
                "(two lines, in either order)\n"
                "scan Succeeded\n"
                "policy StepFailed\n"
                "(empty line: the run has no results)"
            ),
            "lines": [
                ("IMAGE=$(oc get pods ...)", "Reads the demo image digest again, so the block works on its own.", "The scan should pass on this image."),
                ("tkn pipeline start ... bad.yaml || true", "Runs the pipeline with the candidate that uses the latest tag. The || true keeps the block going when the run fails.", "The run is meant to fail at the policy task."),
                ("get taskrun ... pipelineTask", "Lists the tasks that started: scan Succeeded, policy StepFailed, and no bundle task.", "The bundle task must never start after a refusal."),
                ("status.results", "Prints the results of the run. They are empty.", "No bundle exists for a refused change."),
            ],
            "checkpoint": "The scan succeeded, the policy task failed (StepFailed), no bundle task exists and the results are empty. In the log, the message names the policy `grc-enforce-no-latest-tag`.",
        },
    ],
    "glossary": [
        ("Cosign", "A free tool that signs and verifies images and other files."),
        ("Trivy", "A free scanner for known flaws in container images."),
        ("Kyverno", "A policy engine that can refuse requests to the cluster."),
        ("Tekton", "The pipeline engine inside OpenShift Pipelines."),
        ("Severity", "How serious a flaw is: LOW, MEDIUM, HIGH or CRITICAL."),
        ("Secret", "A protected cluster object that holds sensitive values such as a key."),
        ("Base64", "A text encoding for binary data. It is not encryption."),
        ("Key management service", "A managed system that holds keys and signs on request without exposing the private key."),
    ],
    "design": [
        {
            "decision": "Policy check by server-side dry run",
            "how": "The policy task runs a short script you write: it sends the candidate manifest to the cluster with a server-side dry run, records the answer and message in a file, and fails the task if the change was denied.",
            "why": "The dry run asks the same admission question the cluster will ask at deploy time and stops a bad change before any object exists, while policy reports exist only for objects that were already created.",
            "alternatives": "Advantage of reading policy reports instead: the pipeline needs no permission to dry-run in the target namespace. Drawback: a report appears only after the object exists, so the bad change is already in the cluster when anyone learns of it. Cost of the dry run: it sees only policies in Enforce mode.",
        },
        {
            "decision": "A failed run leaves no bundle",
            "how": "Each task fails the run when its check fails, so the bundle task never starts and the pipeline keeps no bundle and no signature.",
            "why": "Every bundle that exists then describes a passing run, and a reader never has to inspect a field to learn whether a run passed.",
            "alternatives": "Advantage of writing a signed bundle that records the failure: the failed attempt itself becomes evidence an auditor can trace. Drawback: readers must check a status field in every bundle, and one careless consumer could treat any signed bundle as a pass.",
        },
        {
            "decision": "A separate evidence key, verified outside the pipeline",
            "how": "The pipeline signs the bundle with a key made only for evidence and held as a cluster secret. You verify the bundle from the lab shell with the public key alone.",
            "why": "A separate key can be rotated or revoked without touching release signing, and verification outside the pipeline means a compromised pipeline cannot vouch for itself.",
            "alternatives": "Advantage of reusing the release signing key: one less secret to protect and rotate. Drawback: a single leak would spoil both evidence and releases. The lab keeps the key as a plain secret, a shortcut a real system would replace with a key management service.",
        },
    ],
    "next": "Next module: GRC-5 Continuous Control Monitoring Design: turn policy reports and cluster state into machine-readable results, detect drift against a baseline, and measure how much of a team's control set has fresh, automated evidence.",
}

MODULE["portability"] = {
    "bullets": [
        "Works on any Kubernetes cluster with OpenShift Pipelines (Tekton), Trivy, Kyverno in Enforce mode, and Cosign 3.x.",
        "Change these lab values first: the build namespace, the pipeline service account, the evidence volume name, and the evidence-signing secret name.",
        "The signing key is a plain cluster secret in the lab. Replace it with a key management service in production.",
        "The policy check uses oc apply --dry-run=server; replace oc with kubectl on non-OpenShift clusters.",
    ],
    "headers": ["Check/part", "In this lab (OpenShift)", "On other Kubernetes", "What you change"],
    "rows": [
        ("Image scan", "Trivy in a pipeline pod, pulls its database from the internet", "Trivy, Grype, or any scanner that exits non-zero on a finding", "The scanner image and the report format parsed by the gate step."),
        ("Policy check", "oc apply --dry-run=server against Kyverno in Enforce mode", "kubectl apply --dry-run=server with Kyverno; for OPA/Gatekeeper, replace the check", "Replace oc with kubectl; ensure the admission webhook is in Enforce mode."),
        ("Signing", "cosign sign-blob --tlog-upload=false with a cluster secret", "Cosign with a key management service key, or sigstore with a transparency log", "The key reference and whether to upload to a log."),
        ("Bundle storage", "Tekton pipeline result (compact JSON)", "Any artifact store: OCI registry, S3, or a git-managed file", "The publish step in the bundle task."),
        ("Verification", "cosign verify-blob --key cosign.pub in the lab shell", "Same command in a separate system outside the pipeline", "Nothing if Cosign 3.x is available; the key path."),
    ],
}
