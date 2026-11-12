"""AI-1: Put the model behind a gateway (SC-7, AC-3, SC-5)."""

NIST = "nist-sp-800-53r5-full.md"
WORK = "cd /workspace/ai-1\n"
GW = "GW=http://model-gateway.ai-lab.svc:8080\n"
BODY = "'{\"request_id\":\"summary-ok\",\"input\":\"hello\"}'"
LOOP = (
    "oc exec -i -n ai-lab probe -- sh -s \"$TOKEN\" <<'EOF' | sort | uniq -c\n"
    "for i in 1 2 3 4 5 6 7 8 9 10; do\n"
    "  curl -s -m 5 -o /dev/null -w \"%{http_code}\\n\" -H \"Authorization: Bearer $1\" -d '{\"request_id\":\"summary-ok\",\"input\":\"hello\"}' http://model-gateway:8080/v1/answer\n"
    "done\n"
    "EOF"
)
APPLY_POLICY = (
    "oc create configmap gateway-policy -n ai-lab --from-file=policy.conf --dry-run=client -o yaml | oc apply -f -\n"
    "oc rollout restart deploy/model-gateway -n ai-lab\n"
    "oc rollout status deploy/model-gateway -n ai-lab --timeout=120s\n"
)

MODULE = {
    "intent_at_end": True,
    "terms_at_end": True,
    "id": "AI-1",
    "slug": "ModelGateway",
    "title": "Put the Model Behind a Gateway",
    "draft": (
        "Written without a live cluster; no command in this module has been run. Unconfirmed: the nginx image tag (ubi9/nginx-124:1), that curl exists in the probe image, "
        "that the stub accepts a curl form-encoded body, how curl behaves on a dropped connection (expected: exit 28), "
        "and that AID-3 and AID-4 port-forward still reaches the stub while the NetworkPolicy stub-from-gateway-only exists. "
        "The lab start state for every AI and AID module must delete that policy (oc delete networkpolicy stub-from-gateway-only -n ai-lab --ignore-not-found). "
        "The model is a stub that never reads the prompt, so the gateway is tested with fixed request ids only."
    ),
    "controls": ["SC-7", "AC-3", "SC-5"],
    "mentions": [],
    "unit_values_ok": ["32 characters", "3 seconds", "5 seconds", "120 seconds", "10 requests", "2 requests"],
    "minutes": {"hands_on": 40, "verify": 15},
    "tools": ["nginx (reverse proxy, free, open source)", "NetworkPolicy (OpenShift)", "Stub model service (provided by the lab)", "oc", "curl", "jq", "openssl"],
    "tool_why": True,
    "hide_draft": True,
    "hover": True,
    "diagrams": [
        {
            "id": "gateway",
            "title": "Only the gateway reaches the model",
            "caption": "In the lab (test) setup, a test pod sends requests to the model gateway, and the gateway is the only path to the stub model. A network policy blocks every other path. New parts are drawn with thick lines.",
            "per_step": True,
            "rankdir": "LR",
            "step_notes": {
                1: "The gateway and the network policy go in. A request through the gateway reaches the stub model, and a request straight to the stub is refused.",
                2: "The gateway reads a token from a Secret and refuses a request that has no token or a wrong one.",
                3: "A policy file sets how often one client may send and how large a request may be, and the gateway refuses the rest.",
            },
            "zones": [
                {"id": "cluster", "icon": "brands/openshift", "label": "Your cluster (your OpenShift cluster, in AWS)", "kind": "boundary"},
                {"id": "ns", "icon": "k8s/ns", "label": "Namespace ai-lab", "parent": "cluster", "kind": "group"},
            ],
            "key": {"k8s/pod": "Kubernetes pod", "k8s/deploy": "Kubernetes deployment", "k8s/svc": "Kubernetes service", "k8s/netpol": "Kubernetes network policy", "k8s/secret": "Kubernetes secret", "k8s/cm": "Kubernetes config map"},
            "nodes": [
                {"id": "client", "icon": "k8s/pod", "title": "Test pod", "sub": "Sends the requests you try", "zone": "ns"},
                {"id": "gw", "icon": "k8s/deploy", "title": "Model gateway", "sub": "Nginx in front of the model", "zone": "ns", "kind": "ok", "s": 1},
                {"id": "stub", "icon": "k8s/svc", "title": "Stub model", "sub": "Stand-in for a real model", "zone": "ns"},
                {"id": "np", "icon": "k8s/netpol", "title": "Network policy", "sub": "Only the gateway may reach the stub", "zone": "ns", "kind": "warn", "s": 1},
                {"id": "tok", "icon": "k8s/secret", "title": "Token secret", "sub": "Secret gateway-auth holds the accepted token", "zone": "ns", "kind": "ok", "s": 2},
                {"id": "pol", "icon": "k8s/cm", "title": "Limit rules", "sub": "Config map gateway-policy: rate and body size", "zone": "ns", "kind": "ok", "s": 3},
            ],
            "edges": [
                {"a": "client", "b": "gw", "label": "Allowed", "kind": "ok", "s": 1},
                {"a": "gw", "b": "stub", "label": "Forwards", "kind": "ok", "s": 1},
                {"a": "client", "b": "stub", "label": "Refused", "kind": "bad", "s": 1},
                {"a": "np", "b": "stub", "label": "Guards", "s": 1},
                {"a": "tok", "b": "gw", "label": "Token", "s": 2},
                {"a": "pol", "b": "gw", "label": "Limits", "s": 3},
            ],
            "reading": [
                "1. Test pod: sends the requests you try.",
                "2. Model gateway: an nginx deployment that every allowed request passes through on its way to the model.",
                "3. Stub model: a stand-in for a real model that only the gateway may reach.",
                "4. Network policy: blocks any path to the stub model that does not start at the gateway.",
                "5. Token secret: holds the token the gateway accepts.",
                "6. Limit rules: a config map that sets the request rate and the largest request body the gateway lets through.",
            ],
        },
    ],
    "prereq": [
        "CPS-4 Isolate and Limit Workloads (NetworkPolicy, hardened pod settings and resource limits)",
        "AID-3 AI-Assisted Automation Under Review (the stub model service and request ids)",
    ],
    "lab_needs": [],
    "lab": {
        "start": "lab start ai-1",
        "env": [],
    },
    "requirement": (
        "A model service (a program that writes text when you ask) is a component of the system like any other, so it sits behind a controlled entry point. "
        "Every caller reaches it through one gateway (a front door program that passes requests on), and no caller reaches it directly. "
        "The gateway lets in only callers that prove who they are, and it limits how much each caller can ask for, because a model answer costs time and money. "
        "This module puts the lab's stub model service behind an nginx gateway, shuts the direct path with a network rule, requires a secret token, and caps both the request rate and the request size."
    ),
    "objectives": [
        {"label": "Skill", "text": "Put a model service behind a gateway, close the direct path with a NetworkPolicy, require a token, and limit the rate and size of requests."},
        {"label": "Tools", "text": "`nginx` is the gateway; a NetworkPolicy closes the direct path; `oc` applies the settings; `curl` sends the test requests; `openssl` makes the token."},
        {"label": "Security Function", "text": "Narrows the ways to reach the model to one managed entry point, refuses callers without the token, and refuses callers that ask too often or send too much."},
        {"label": "NIST SC-7 Boundary Protection", "text": "The only network path to the stub is the gateway, and a request sent straight to the stub is refused."},
        {"label": "NIST AC-3 Access Enforcement", "text": "The gateway passes a request only when it carries the token, and answers 401 otherwise."},
        {"label": "NIST SC-5 Denial-of-Service Protection", "text": "The gateway answers 429 to a caller that asks too fast and 413 to a request that is too large."},
    ],
    "requirement_bullets": [
        "Purpose: show that a model service is reached through one managed entry point, that the entry point enforces who may use it, and that it limits how much one caller can use.",
        "You build the gateway settings, a NetworkPolicy, a token check and the rate limit. You write one line yourself: the rate limit rule.",
        "You test one request that must pass and three that must be refused.",
    ],
    "mapping": [
        {
            "control": "SC-7 Boundary Protection",
            "plain": "Reach the system only through managed entry points, and watch and control traffic at them.",
            "source": "NIST",
            "tool": "A NetworkPolicy and the nginx gateway. Explained in section 2.1.",
            "covered": "Section 3, Step 1: deploy the gateway and close the direct path to the stub. Section 4, Test 2: a request sent straight to the stub is refused.",
            "cite": [
                {"file": NIST, "quote": "Connect to external networks or systems only through managed interfaces"},
            ],
        },
        {
            "control": "AC-3 Access Enforcement",
            "plain": "Allow access only when the access is authorized.",
            "source": "NIST",
            "tool": "The token check in the nginx gateway. Explained in section 2.2.",
            "covered": "Section 3, Step 2: refuse a request without the token. Section 4, Test 1: a request with the token passes. Section 4, Test 3: a request with no token or a wrong token is refused.",
            "cite": [
                {"file": NIST, "quote": "Enforce approved authorizations for logical access to information and system resources"},
            ],
        },
        {
            "control": "SC-5 Denial-of-Service Protection",
            "plain": "Protect against, or limit the effect of, events that make the system unavailable.",
            "source": "NIST",
            "tool": "The rate limit and the body size limit in the nginx gateway. Explained in section 2.3.",
            "covered": "Section 3, Step 3: limit how often one caller can ask and how large a request can be. Section 4, Test 4: a fast burst and a large request are refused.",
            "cite": [
                {"file": NIST, "quote": "Employ the following controls to achieve the denial-of-service objective"},
            ],
        },
    ],
    "intent": [
        {
            "control": "SC-7 Boundary Protection",
            "feared": "Someone reaches the model service by a path that has no checks, so the checks on the front door are worth nothing.",
            "scope": "Network paths into the stub model service in project ai-lab. Paths out of it are outside this module.",
            "question": "From which places can a request reach the model service, and does each one go through the gateway?",
            "evidence": "The network rule, and a request sent straight to the stub that is refused while the same request through the gateway works.",
            "sufficient": "The gateway is the only caller the network rule allows to reach the stub. NIST has the organization define the monitoring and control at the managed interfaces, so this module treats the gateway log as the monitoring and leaves its review to a later module.",
            "tieoff": "A refused direct request is expected. If one ever succeeds, the network rule is wrong and the model service is open.",
            "tool": "A NetworkPolicy named stub-from-gateway-only (Step 1) allows traffic to the stub only from pods that carry the label app=model-gateway.",
        },
        {
            "control": "AC-3 Access Enforcement",
            "feared": "Anyone who can reach the gateway can use the model, including a caller nobody approved.",
            "scope": "Requests to the path /v1/ on the gateway.",
            "question": "What does a caller have to hold to be let in, and what happens to a request without it?",
            "evidence": "A request with the token that passes, and requests with no token and a wrong token that are refused with 401.",
            "sufficient": "The gateway compares the Authorization header with the one approved value before it passes anything on. The lab uses one shared token to keep the module small. A real system gives each caller its own identity, so one caller can be cut off alone.",
            "tieoff": "A refused request gets 401 and is written to the gateway log, so a person can see who was turned away.",
            "tool": "A map block in the gateway settings (Step 2) sets a flag when the header equals Bearer plus the token, and a rule in the policy file returns 401 when the flag is 0.",
        },
        {
            "control": "SC-5 Denial-of-Service Protection",
            "feared": "One caller, by mistake or on purpose, sends so many or such large requests that the model service is slow or unusable for everyone else, or that the bill grows without limit.",
            "scope": "The rate and size of requests that reach the model service through the gateway.",
            "question": "How fast can one caller ask, how large can a request be, and what does the gateway do when either is exceeded?",
            "evidence": "A fast burst that gets some 429 answers, and an oversize request that gets 413.",
            "sufficient": "The gateway sets a rate per caller address with a small burst allowance and a body size cap. NIST leaves the kinds of denial-of-service events and the controls to the organization, and the lab picks two: a rate limit and a size limit. The numbers are the lab's choice and not a NIST value.",
            "tieoff": "Refused requests are logged, so a caller who keeps hitting a limit can be seen. A later module builds that detection.",
            "tool": "A limit_req_zone in the gateway settings with the limit_req rule you write in Step 3, and a client_max_body_size line.",
        },
    ],
    "terms": [
        ("Model service", "A program that writes text when you ask. Here a stub stands in for it."),
        ("Stub model service", "A small program that stands in for a model and returns a fixed answer for each request id. It needs no key and no internet access."),
        ("Gateway", "A front door program. Every request to the model goes through it, and it decides whether to pass the request on."),
        ("Reverse proxy", "A program that receives requests on behalf of another program and passes them on. nginx does this here."),
        ("nginx", "A free web server that is often used as a reverse proxy. Here it is the gateway."),
        ("NetworkPolicy", "A cluster rule that says which pods may send traffic to which other pods. Without one, any pod in the cluster can reach any other."),
        ("Pod", "One running copy of a program in the cluster."),
        ("Label", "A name and value attached to a pod, such as app=model-gateway. A NetworkPolicy picks pods by their labels."),
        ("Token", "A long secret string that works like a password for one program. Anyone who holds it can use the gateway, so never commit it or print it into a log."),
        ("Config map", "A stored file or setting that the cluster keeps and can hand to a program."),
        ("Secret (cluster)", "Like a config map, but meant for sensitive values such as a token. The cluster handles it with more care."),
        ("Rate limit", "A cap on how many requests one caller may send in a period of time."),
        ("Burst", "A small number of extra requests the rate limit lets through at once before it starts refusing."),
        ("HTTP status code", "A number a web server sends back to say what happened. 200 means success, 401 means not allowed in, 413 means the request was too large and 429 means too many requests."),
        ("Request id", "A short name sent with each question. The stub picks its fixed answer by this name."),
        ("Probe pod", "A small pod you start only to send test requests from inside the cluster, so a test comes from a place that is not the gateway."),
        ("Project", "A named section of the cluster that keeps workloads apart. OpenShift also calls it a namespace."),
        ("oc", "The command-line tool for OpenShift. You type oc to ask the cluster questions."),
        ("curl", "A command that sends a web request and prints the answer."),
        ("jq", "A tool that picks one value out of JSON text."),
        ("openssl", "A tool for cryptography. Here it makes a random token."),
        ("Heredoc", "A way to make a file by pasting its text between a first line such as cat > name <<'EOF' and a last line that says EOF."),
        ("Exit status", "A number a command leaves behind when it ends. 0 means success and anything else means a problem."),
    ],
    "concepts": [
        {
            "heading": "2.1 One front door and no side door",
            "controls": [
                {"id": "SC-7 Boundary Protection"},
            ],
            "paras": [
                {"bullets": [
                    "A check at the front door protects nothing if a side door lets callers reach the model service directly, so the network rule that closes the side door matters as much as the gateway.",
                    "By default any pod in the cluster can reach any other pod, so you must add the rule that narrows it.",
                    "The gateway is also the one place where requests can be counted and logged.",
                ]},
                {
                    "control": "SC-7: Boundary Protection",
                    "text": "The control asks the system to monitor and control communications at its external managed interfaces and to connect to external networks or systems only through managed interfaces. NIST leaves some of the detail, such as the managed interfaces and what is monitored, to the organization. This is done using:",
                },
                {"bullets": [
                    "The nginx gateway: the one managed interface in front of the model service.",
                    "The NetworkPolicy stub-from-gateway-only: allows traffic to the stub only from pods labelled app=model-gateway, so a request from any other pod is dropped.",
                ]},
            ],
        },
        {
            "heading": "2.2 Who may use the model",
            "controls": [
                {"id": "AC-3 Access Enforcement"},
            ],
            "paras": [
                {"bullets": [
                    "The gateway answers 401 when the request carries no approved token, and passes the request on only when it does.",
                    "The token is kept in a Secret and a file with permission 600 in your working folder. It is never written into the gateway settings you commit.",
                    "A shared token proves a caller holds the token, not which caller it is, so a real system gives each caller its own.",
                ]},
                {
                    "control": "AC-3: Access Enforcement",
                    "text": "The control asks the system to enforce approved authorizations for logical access to information and system resources, in line with the access control policy. Here the resource is the model service, and the approval is holding the token. This is done using:",
                },
                {"bullets": [
                    "The Secret gateway-auth: holds the map block that compares the Authorization header with the approved value.",
                    "The policy file: returns 401 for any request where the flag is 0.",
                ]},
            ],
        },
        {
            "heading": "2.3 Limits on rate and size",
            "controls": [
                {"id": "SC-5 Denial-of-Service Protection"},
            ],
            "paras": [
                {"bullets": [
                    "A model answer costs time or money, so a caller who asks too fast or sends something huge can exhaust a service that is otherwise working. OWASP calls this unbounded consumption (LLM10).",
                    "A rate limit answers 429 when a caller asks faster than the allowed rate, after a small burst. A size limit answers 413 before the request body is read in full.",
                    "These limits reduce the effect of a flood but do not stop a determined attack from many addresses. That needs limits further out, in front of the cluster.",
                ]},
                {
                    "control": "SC-5: Denial-of-Service Protection",
                    "text": "The control asks the organization to protect against, or limit the effects of, denial-of-service events, using controls it selects. NIST leaves the types of events and the controls to the organization. This is done using:",
                },
                {"bullets": [
                    "limit_req_zone and the limit_req rule you write: refuse a caller that asks faster than the zone allows, after the burst.",
                    "client_max_body_size: refuses a request body larger than the cap before it reaches the model.",
                ]},
                "The table lists the answers the gateway can give and why.",
            ],
            "table": {
                "headers": ["Answer", "When the gateway gives it", "Where it is decided"],
                "rows": [
                    ("`200`", "The token is right and the caller is within the limits", "Passed on to the stub"),
                    ("`401`", "No token, or a wrong one", "The policy file"),
                    ("`413`", "The request body is over the size cap", "client_max_body_size"),
                    ("`429`", "The caller asked faster than the rate allows", "limit_req"),
                ],
            },
        },
    ],
    "steps": [
        {
            "title": "Deploy the gateway and close the direct path to the stub",
            "learn": "Running the gateway and then adding a NetworkPolicy shows the difference between a front door that exists and a front door that is the only door.",
            "takeaway": "A gateway protects nothing until the network refuses every other path to the service behind it.",
            "controls": [
                {"id": "SC-7 Boundary Protection", "how": "You deploy the nginx gateway, show that the stub can still be reached directly, then add a NetworkPolicy so only the gateway can reach it."},
            ],
            "why": "You first make the gateway and a probe pod. The gateway settings are kept in config maps, the pod runs without root, drops all extra Linux permissions and has a read-only root file system, as you did in CPS-4. The first test shows that a request sent straight to the stub works, which is the problem. Then the NetworkPolicy closes it.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p /workspace/ai-1 && cd /workspace/ai-1\n"
                        "cat > nginx.conf <<'EOF'\n"
                        "pid /tmp/nginx.pid;\n"
                        "events {}\n"
                        "http {\n"
                        "  access_log /dev/stdout;\n"
                        "  client_body_temp_path /tmp/body;\n"
                        "  proxy_temp_path /tmp/proxy;\n"
                        "  fastcgi_temp_path /tmp/fcgi;\n"
                        "  uwsgi_temp_path /tmp/uwsgi;\n"
                        "  scgi_temp_path /tmp/scgi;\n"
                        "  limit_req_zone $binary_remote_addr zone=perclient:1m rate=2r/s;\n"
                        "  limit_req_status 429;\n"
                        "  include /etc/gateway-auth/*.conf;\n"
                        "  server {\n"
                        "    listen 8080;\n"
                        "    location = /healthz { return 200 \"ok\\n\"; }\n"
                        "    location /v1/ {\n"
                        "      include /etc/gateway-policy/policy.conf;\n"
                        "      proxy_pass http://stub-model:8080;\n"
                        "    }\n"
                        "  }\n"
                        "}\n"
                        "EOF\n"
                        "echo '# rules are added in later steps' > policy.conf\n"
                        "oc create configmap gateway-conf -n ai-lab --from-file=nginx.conf --dry-run=client -o yaml | oc apply -f -\n"
                        "oc create configmap gateway-policy -n ai-lab --from-file=policy.conf --dry-run=client -o yaml | oc apply -f -"
                    ),
                    "label": "Write the gateway settings and store them in the cluster",
                    "intro": "You will now paste the gateway settings as a heredoc and store them in two config maps. The rate zone is defined here, but nothing uses it yet. You write the rule that uses it in Step 3.",
                    "expect": "Example only. The wording of the answers may differ.\nconfigmap/gateway-conf created\nconfigmap/gateway-policy created",
                    "lines": [
                        ("mkdir -p /workspace/ai-1 && cd /workspace/ai-1", "Makes a folder for this module and moves into it.", "All the files for this module go in one folder so you can find them again."),
                        ("cat > nginx.conf <<'EOF'", "Writes everything up to the line EOF into the file nginx.conf. The quotes around EOF stop the shell from changing the dollar signs.", "nginx uses dollar signs in its own settings, and they must reach the file unchanged."),
                        ("pid /tmp/nginx.pid; ... _temp_path /tmp/...", "Moves every file nginx writes to /tmp.", "The pod's root file system is read-only, so nginx can write only to the /tmp folder you give it."),
                        ("access_log /dev/stdout;", "Sends one log line for every request to the pod's output.", "The gateway is where requests are counted, and a later module reads these lines."),
                        ("limit_req_zone $binary_remote_addr zone=perclient:1m rate=2r/s;", "Defines a zone named perclient that counts requests per caller address and allows a steady 2 requests a second. It does nothing until a rule uses it.", "The rate is set once, in the main settings, and the rule that applies it comes later."),
                        ("limit_req_status 429;", "Makes the refusal answer 429, the code for too many requests.", "The default would be 503, which looks like a broken service."),
                        ("include /etc/gateway-auth/*.conf;", "Reads any file the Secret mounts here. There is none yet, and that is allowed.", "Step 2 adds the token check without changing this file."),
                        ("location = /healthz { return 200 ... }", "Answers the health path itself, without calling the stub.", "A check that the gateway is running should not depend on the model."),
                        ("include /etc/gateway-policy/policy.conf; proxy_pass http://stub-model:8080;", "Applies the rules in policy.conf to every request to /v1/ and then passes it to the stub.", "All the rules live in one small file that you change in each step."),
                        ("echo '# rules are added in later steps' > policy.conf", "Makes a policy file that holds only a comment.", "The gateway needs the file to exist before there are any rules in it."),
                        ("oc create configmap ... --dry-run=client -o yaml | oc apply -f -", "Builds the config map from the file and applies it. Run again, it updates the existing one instead of failing.", "You will change policy.conf twice, and this form works the first time and every time after."),
                    ],
                },
                {
                    "code": (
                        "oc apply -n ai-lab -f - <<'EOF'\n"
                        "apiVersion: apps/v1\n"
                        "kind: Deployment\n"
                        "metadata:\n"
                        "  name: model-gateway\n"
                        "spec:\n"
                        "  replicas: 1\n"
                        "  selector:\n"
                        "    matchLabels:\n"
                        "      app: model-gateway\n"
                        "  template:\n"
                        "    metadata:\n"
                        "      labels:\n"
                        "        app: model-gateway\n"
                        "    spec:\n"
                        "      automountServiceAccountToken: false\n"
                        "      containers:\n"
                        "      - name: nginx\n"
                        "        image: registry.access.redhat.com/ubi9/nginx-124:1\n"
                        "        command: [\"nginx\", \"-e\", \"/dev/stderr\", \"-c\", \"/etc/gateway/nginx.conf\", \"-g\", \"daemon off;\"]\n"
                        "        ports:\n"
                        "        - containerPort: 8080\n"
                        "        securityContext:\n"
                        "          allowPrivilegeEscalation: false\n"
                        "          readOnlyRootFilesystem: true\n"
                        "          runAsNonRoot: true\n"
                        "          capabilities:\n"
                        "            drop: [\"ALL\"]\n"
                        "          seccompProfile:\n"
                        "            type: RuntimeDefault\n"
                        "        resources:\n"
                        "          requests: {cpu: 50m, memory: 64Mi}\n"
                        "          limits: {cpu: 200m, memory: 128Mi}\n"
                        "        volumeMounts:\n"
                        "        - {name: conf, mountPath: /etc/gateway}\n"
                        "        - {name: policy, mountPath: /etc/gateway-policy}\n"
                        "        - {name: auth, mountPath: /etc/gateway-auth}\n"
                        "        - {name: tmp, mountPath: /tmp}\n"
                        "      volumes:\n"
                        "      - {name: conf, configMap: {name: gateway-conf}}\n"
                        "      - {name: policy, configMap: {name: gateway-policy}}\n"
                        "      - {name: auth, secret: {secretName: gateway-auth, optional: true}}\n"
                        "      - {name: tmp, emptyDir: {}}\n"
                        "---\n"
                        "apiVersion: v1\n"
                        "kind: Service\n"
                        "metadata:\n"
                        "  name: model-gateway\n"
                        "spec:\n"
                        "  selector:\n"
                        "    app: model-gateway\n"
                        "  ports:\n"
                        "  - port: 8080\n"
                        "    targetPort: 8080\n"
                        "EOF\n"
                        "oc rollout status deploy/model-gateway -n ai-lab --timeout=120s\n"
                        "oc run probe -n ai-lab --image=registry.access.redhat.com/ubi9/ubi-minimal:9.5 --restart=Never -- sleep infinity\n"
                        "oc wait --for=condition=Ready pod/probe -n ai-lab --timeout=120s"
                    ),
                    "label": "Run the gateway and a probe pod",
                    "intro": "You will now start the gateway as a hardened pod with a Service in front of it, and a probe pod to send test requests from. The probe is not the gateway, so it stands in for any other pod in the cluster.",
                    "expect": "Example only. The wording of the answers may differ.\ndeployment.apps/model-gateway created\nservice/model-gateway created\ndeployment \"model-gateway\" successfully rolled out\npod/probe created\npod/probe condition met",
                    "lines": [
                        ("replicas: 1 ... app: model-gateway", "Runs one copy of the gateway and gives it the label app=model-gateway.", "The NetworkPolicy picks the gateway by this label."),
                        ("automountServiceAccountToken: false", "Keeps the cluster login token out of the pod.", "The gateway never calls the cluster, so it gets no credentials, as in CPS-4."),
                        ("image: registry.access.redhat.com/ubi9/nginx-124:1", "Uses the Red Hat nginx image. Unconfirmed: this tag exists. Check it with the image registry before you rely on it.", "A tagged image is the same each time you start it."),
                        ("command: [\"nginx\", \"-e\", \"/dev/stderr\", \"-c\", \"/etc/gateway/nginx.conf\", ...]", "Starts nginx with your settings file and sends its error log to the pod output, since the root file system is read-only.", "The image's own start script would use its own settings instead of yours."),
                        ("allowPrivilegeEscalation: false ... drop: [\"ALL\"]", "Forbids gaining extra permissions, requires a non-root user, drops all extra Linux permissions and uses the default system call filter.", "The gateway is the part everyone can reach, so it is the part to harden most."),
                        ("readOnlyRootFilesystem: true ... emptyDir: {}", "Makes the file system read-only and gives nginx an empty scratch folder at /tmp.", "A compromised gateway cannot change its own program files."),
                        ("limits: {cpu: 200m, memory: 128Mi}", "Caps what the gateway can use.", "A flood against the gateway cannot take the whole node."),
                        ("secret: {secretName: gateway-auth, optional: true}", "Mounts the Secret from Step 2 if it exists, and starts without it if it does not.", "The gateway can start now and get its token check later."),
                        ("kind: Service ... port: 8080", "Gives the gateway the stable name model-gateway on port 8080.", "Callers use a name and not a pod address."),
                        ("oc run probe ... -- sleep infinity", "Starts a pod from a small Red Hat image that only waits.", "You send test requests from it with oc exec."),
                        ("oc wait --for=condition=Ready pod/probe ...", "Waits until the probe is ready.", "The next block would fail if it ran too early."),
                    ],
                },
                {
                    "code": (
                        GW
                        + "oc exec -n ai-lab probe -- curl -s -m 5 -o /dev/null -w 'gateway: %{http_code}\\n' $GW/healthz\n"
                        "oc exec -n ai-lab probe -- curl -s -m 5 -o /dev/null -w 'direct to stub: %{http_code}\\n' http://stub-model:8080/healthz\n"
                        "oc apply -n ai-lab -f - <<'EOF'\n"
                        "apiVersion: networking.k8s.io/v1\n"
                        "kind: NetworkPolicy\n"
                        "metadata:\n"
                        "  name: stub-from-gateway-only\n"
                        "spec:\n"
                        "  podSelector:\n"
                        "    matchLabels:\n"
                        "      app: stub-model\n"
                        "  policyTypes: [\"Ingress\"]\n"
                        "  ingress:\n"
                        "  - from:\n"
                        "    - podSelector:\n"
                        "        matchLabels:\n"
                        "          app: model-gateway\n"
                        "    ports:\n"
                        "    - {port: 8080, protocol: TCP}\n"
                        "EOF\n"
                        "sleep 3\n"
                        "oc exec -n ai-lab probe -- curl -s -m 5 -o /dev/null -w 'direct to stub: %{http_code}\\n' http://stub-model:8080/healthz; echo \"curl exit status: $?\"\n"
                        "oc exec -n ai-lab probe -- curl -s -m 5 -o /dev/null -w 'gateway: %{http_code}\\n' $GW/healthz"
                    ),
                    "label": "Show the side door, then close it",
                    "intro": "You will now send a request straight to the stub from the probe, and see that it works. That is the side door. You then add the NetworkPolicy and repeat the request. The gateway's own health path never touches the stub, so it answers either way.",
                    "expect": "Example only. Before the policy, both requests answer 200. After it, the direct request gets no answer within 5 seconds (code 000, exit status 28) and the gateway still answers 200.\ngateway: 200\ndirect to stub: 200\nnetworkpolicy.networking.k8s.io/stub-from-gateway-only created\ndirect to stub: 000\ncurl exit status: 28\ngateway: 200",
                    "lines": [
                        ("GW=http://model-gateway.ai-lab.svc:8080", "Stores the gateway address in a variable for this block.", "The address is typed once."),
                        ("curl -s -m 5 -o /dev/null -w 'gateway: %{http_code}\\n' $GW/healthz", "Sends a request from inside the probe, gives up after 5 seconds, hides the body and prints only the status code.", "The status code is all you need to see that the gateway works."),
                        ("http://stub-model:8080/healthz", "Sends a request straight to the stub, around the gateway.", "This is the side door. Before the policy it answers."),
                        ("podSelector: matchLabels: app: stub-model", "Says the rule protects the pods labelled app=stub-model.", "The rule belongs on the service you want to protect."),
                        ("policyTypes: [\"Ingress\"]", "Makes the rule about traffic coming in.", "Once a pod is selected for incoming traffic, anything not allowed is dropped."),
                        ("from: - podSelector: matchLabels: app: model-gateway", "Allows incoming traffic only from pods labelled app=model-gateway, on port 8080.", "The gateway is the one managed interface."),
                        ("sleep 3", "Waits a moment for the network to apply the rule.", "A check made at once could still see the old rule."),
                        ("echo \"curl exit status: $?\"", "Prints the exit status of the curl before it. 28 means curl timed out. Unconfirmed: oc exec passes the status through on this cluster.", "A timeout and not an error answer shows that the network dropped the request."),
                    ],
                },
            ],
            "action": "Paste the three blocks in order.",
            "checkpoint": "Before the policy, both the gateway and the stub answer 200. After it, the direct request prints 000 and exit status 28 while the gateway still answers 200.",
        },
        {
            "title": "Require a token at the gateway",
            "learn": "Keeping the approved token in a Secret and making the gateway compare each request with it shows how access is enforced at the one managed entry point.",
            "takeaway": "A front door that anyone can walk through is a path, not a control, so decide who is let in and refuse the rest.",
            "controls": [
                {"id": "AC-3 Access Enforcement", "how": "You make a random token, store it in a Secret, and make the gateway refuse any request that does not carry it."},
            ],
            "why": "The token is made once with openssl and kept in a file readable only by you. The gateway gets it through a Secret, not through the config map, so the policy file you may later share does not contain it. The rule that refuses a request is two lines in the policy file.",
            "blocks": [
                {
                    "code": (
                        WORK
                        + "openssl rand -hex 16 > token\n"
                        "chmod 600 token\n"
                        "TOKEN=$(cat token)\n"
                        "printf 'map $http_authorization $token_ok {\\n  default 0;\\n  \"Bearer %s\" 1;\\n}\\n' \"$TOKEN\" > auth.conf\n"
                        "chmod 600 auth.conf\n"
                        "oc create secret generic gateway-auth -n ai-lab --from-file=auth.conf --dry-run=client -o yaml | oc apply -f -\n"
                        "cat > policy.conf <<'EOF'\n"
                        "if ($token_ok = 0) {\n"
                        "    return 401;\n"
                        "}\n"
                        "EOF\n"
                        + APPLY_POLICY
                        + "wc -c < token"
                    ),
                    "label": "Make the token, store it in a Secret and turn on the check",
                    "intro": "You will now make a random token, store it in a Secret, add the rule to the policy file, and restart the gateway so it reads both. The command prints the length of the token file and never the token.",
                    "expect": "Example only. The wording of the answers may differ.\nsecret/gateway-auth created\nconfigmap/gateway-policy configured\ndeployment.apps/model-gateway restarted\ndeployment \"model-gateway\" successfully rolled out\n33",
                    "lines": [
                        ("openssl rand -hex 16 > token", "Makes 16 random bytes and writes them as 32 hexadecimal characters into the file token.", "A random value cannot be guessed, as a chosen word could."),
                        ("chmod 600 token", "Makes the file readable and writable by you only.", "Anyone who reads the token can use the gateway."),
                        ("TOKEN=$(cat token)", "Reads the token into a variable for this block.", "The next line needs the value."),
                        ("printf 'map $http_authorization $token_ok {...}' \"$TOKEN\" > auth.conf", "Writes an nginx map block. It sets $token_ok to 1 only when the Authorization header is exactly Bearer followed by the token, and to 0 otherwise.", "This is the comparison with the approved value. Single quotes keep the shell from touching the nginx variables."),
                        ("chmod 600 auth.conf", "Makes this file private too, since it holds the token.", "The file is a second copy of the secret."),
                        ("oc create secret generic gateway-auth ... --from-file=auth.conf", "Stores the file in a Secret, applied in a way that can be repeated.", "The token stays out of the config map that holds your settings."),
                        ("if ($token_ok = 0) { return 401; }", "Answers 401 when the flag is 0. The line is in the policy file, so it applies to /v1/ and not to the health path.", "Refusing is the enforcement. The map only sets the flag."),
                        ("oc rollout restart deploy/model-gateway ...", "Restarts the gateway so it reads the new Secret and policy.", "nginx reads its settings only when it starts."),
                        ("wc -c < token", "Prints the number of bytes in the token file. 32 characters and a line end make 33.", "You confirm the token exists without printing it."),
                    ],
                },
            ],
            "action": "Paste the block and read the last number.",
            "checkpoint": "The rollout finishes and the last line prints 33.",
        },
        {
            "title": "Limit how often and how much, and write the rate rule yourself",
            "learn": "Defining a rate zone does nothing until a rule uses it, which you see by testing before and after you write the rule. A size cap, which the gateway checks before it reads the request in full, comes first.",
            "takeaway": "Defining a limit is not applying it. Test that the limit refuses something.",
            "controls": [
                {"id": "SC-5 Denial-of-Service Protection", "how": "You add a request size cap, see that the rate zone alone refuses nothing, then write the one rule that applies it."},
            ],
            "why": "You are supplied the size cap, because it is one line with no choice in it. You write the rate rule yourself, because the choice in it is the learning: which zone, and how large a burst. The first burst test shows that the zone from Step 1 has done nothing. The reference line is in the lines table of the second block, so try before you read it.",
            "blocks": [
                {
                    "code": (
                        WORK
                        + GW
                        + "TOKEN=$(cat token)\n"
                        "echo 'client_max_body_size 1k;' >> policy.conf\n"
                        + APPLY_POLICY
                        + LOOP
                    ),
                    "label": "Add the size cap and send ten fast requests with no rate rule yet",
                    "intro": "You will now add the size cap, restart the gateway, and send ten requests as fast as the probe can. No rule uses the rate zone yet, so none should be refused.",
                    "expect": "Example only. All ten answers are 200.\ndeployment.apps/model-gateway restarted\ndeployment \"model-gateway\" successfully rolled out\n     10 200",
                    "lines": [
                        ("echo 'client_max_body_size 1k;' >> policy.conf", "Adds a line that refuses a request body larger than 1 kilobyte with 413.", "A summary request here is a few dozen bytes, so a megabyte body is not a real request."),
                        ("oc exec -i -n ai-lab probe -- sh -s \"$TOKEN\" <<'EOF'", "Runs the short loop that follows inside the probe, so the ten requests go out within a fraction of a second. The token is passed in as the first argument, which the loop reads as $1.", "Ten separate oc exec calls are too slow to trip a limit of 2 requests a second."),
                        ("for i in 1 2 3 4 5 6 7 8 9 10; do curl ... done", "Sends ten requests with the token and prints only each status code.", "The codes show what the gateway did with each."),
                        ("sort | uniq -c", "Counts how many times each code appeared.", "Ten 200 answers means the zone from Step 1 refused nothing."),
                    ],
                },
                {
                    "code": (
                        WORK
                        + GW
                        + "TOKEN=$(cat token)\n"
                        "echo 'limit_req zone=perclient burst=2 nodelay;' >> policy.conf\n"
                        + APPLY_POLICY
                        + LOOP
                    ),
                    "label": "Write the rate rule, apply it and send the ten requests again",
                    "intro": "You will now apply the rate rule. Write the line yourself before you run this block. It must name the zone perclient from Step 1 and allow a burst of 2 requests with nodelay, which serves the burst at once and refuses the rest. The block shows the answer in its lines table. Replace the echo line with your own and compare.",
                    "expect": "Example only. The first requests pass and the rest are refused, and the exact split varies with timing.\ndeployment.apps/model-gateway restarted\ndeployment \"model-gateway\" successfully rolled out\n      3 200\n      7 429",
                    "lines": [
                        ("echo 'limit_req zone=perclient burst=2 nodelay;' >> policy.conf", "The reference line. It applies the zone perclient, lets 2 extra requests through at once on top of the steady rate, and answers the rest at once with 429 and not after a delay.", "This is the line that turns the rate zone from a definition into a limit."),
                        ("limit_req zone=perclient", "Names the zone to count against.", "The zone only counts for rules that name it."),
                        ("burst=2 nodelay", "Allows a short burst and serves it without waiting.", "Real callers send a few requests together, and a burst of 2 is generous for a lab that sends one at a time."),
                    ],
                },
            ],
            "tip": "If you run the second block twice, policy.conf holds the rule twice, and nginx refuses to start. Open policy.conf, remove the repeat, and apply the config map again.",
            "action": "Paste the first block, write your rate rule, then run the second block with your line in place of the reference.",
            "checkpoint": "Before the rate rule all ten answers are 200. After it some are 429.",
        },
    ],
    "verify": [
        {
            "kind": "positive",
            "title": "A request with the token passes",
            "controls": [
                {"id": "AC-3 Access Enforcement", "how": "A request that carries the approved token is passed on and answered, so the check lets the right callers in."},
            ],
            "why": "Send one request with the token through the gateway. If it did not pass, every refusal in the next tests could be a fault in the gateway and not a check working.",
            "code": (
                WORK
                + GW
                + "TOKEN=$(cat token)\n"
                "oc exec -n ai-lab probe -- curl -s -m 5 -H \"Authorization: Bearer $TOKEN\" -d " + BODY + " $GW/v1/answer | jq -r '.request_id, .model'"
            ),
            "expect": "Example only.\nsummary-ok\nstub-1",
            "lines": [
                ("TOKEN=$(cat token)", "Reads the token from the private file.", "You never type the token."),
                ("curl -s -m 5 -H \"Authorization: Bearer $TOKEN\" -d ...", "Sends the request with the token in the Authorization header.", "This is the one thing the gateway checks."),
                ("-d '{\"request_id\":\"summary-ok\",\"input\":\"hello\"}'", "Sends the request id the stub knows.", "The stub answers by request id."),
                ("jq -r '.request_id, .model'", "Prints the request id and the model name from the answer.", "Both appear only if the stub really answered."),
            ],
            "checkpoint": "The output shows summary-ok and stub-1.",
        },
        {
            "kind": "negative",
            "title": "A request sent straight to the stub is refused",
            "controls": [
                {"id": "SC-7 Boundary Protection", "how": "A request from the probe straight to the stub gets no answer, so the gateway is the only way in."},
            ],
            "why": "Send a request straight to the stub, with the token, from the probe. Having the token must not matter, because the network drops the request before the stub sees it.",
            "code": (
                WORK
                + "TOKEN=$(cat token)\n"
                "oc exec -n ai-lab probe -- curl -s -m 5 -o /dev/null -w 'direct to stub: %{http_code}\\n' -H \"Authorization: Bearer $TOKEN\" -d " + BODY + " http://stub-model:8080/v1/answer; echo \"curl exit status: $?\"\n"
                "oc get networkpolicy stub-from-gateway-only -n ai-lab -o jsonpath='{.spec.ingress[0].from[0].podSelector.matchLabels}'"
            ),
            "expect": "Example only. Unconfirmed: the exit status 28 on this cluster.\ndirect to stub: 000\ncurl exit status: 28\n{\"app\":\"model-gateway\"}",
            "lines": [
                ("http://stub-model:8080/v1/answer", "Sends the request to the stub, not the gateway.", "This is the side door."),
                ("-w 'direct to stub: %{http_code}\\n'", "Prints the status code. 000 means no answer came.", "No answer within 5 seconds is how a dropped request looks."),
                ("oc get networkpolicy ... -o jsonpath='{...matchLabels}'", "Prints the one label the policy allows.", "You see which pods are let in, so the test names its cause."),
            ],
            "checkpoint": "The direct request prints 000, not 200, and the policy shows app model-gateway.",
        },
        {
            "kind": "negative",
            "title": "No token and a wrong token are refused",
            "controls": [
                {"id": "AC-3 Access Enforcement", "how": "Requests with no token and with a wrong token both get 401, so the gateway enforces the approved value and not just the presence of a header."},
            ],
            "why": "Send the same request with no token and then with a wrong one. A gateway that only checks a header is present would let the wrong one through.",
            "code": (
                GW
                + "oc exec -n ai-lab probe -- curl -s -m 5 -o /dev/null -w 'no token: %{http_code}\\n' -d " + BODY + " $GW/v1/answer\n"
                "oc exec -n ai-lab probe -- curl -s -m 5 -o /dev/null -w 'wrong token: %{http_code}\\n' -H 'Authorization: Bearer not-the-token' -d " + BODY + " $GW/v1/answer"
            ),
            "expect": "Example only.\nno token: 401\nwrong token: 401",
            "lines": [
                ("curl ... -d ... $GW/v1/answer", "Sends the request with no Authorization header.", "A caller with no token must not get in."),
                ("-H 'Authorization: Bearer not-the-token'", "Sends a token that is not the approved one.", "Holding a header is not enough."),
                ("-w 'no token: %{http_code}\\n'", "Prints the status code for each.", "401 is the answer that means not allowed in."),
            ],
            "checkpoint": "Both lines show 401.",
        },
        {
            "kind": "negative",
            "title": "A fast burst and an oversize request are refused",
            "controls": [
                {"id": "SC-5 Denial-of-Service Protection", "how": "A burst of ten fast requests gets some 429 answers, and a 2000-byte body gets 413, so both limits refuse what they should."},
            ],
            "why": "Send ten requests in one quick loop and count the answers, then send a body larger than the cap. A limit that was defined but never applied would show ten 200 answers.",
            "code": (
                WORK
                + GW
                + "TOKEN=$(cat token)\n"
                + LOOP + "\n"
                "sleep 3\n"
                "head -c 2000 /dev/zero | tr '\\0' a | oc exec -i -n ai-lab probe -- curl -s -m 5 -o /dev/null -w 'oversize body: %{http_code}\\n' -H \"Authorization: Bearer $TOKEN\" --data-binary @- $GW/v1/answer"
            ),
            "expect": "Example only. The split between 200 and 429 varies with timing, and at least one 429 must appear.\n      3 200\n      7 429\noversize body: 413",
            "lines": [
                ("for i in 1 2 ... 10; do curl ... done", "Sends ten requests with the token in one quick loop inside the probe.", "Only a loop is fast enough to pass the rate."),
                ("sort | uniq -c", "Counts each answer.", "At least one 429 shows the rate rule works."),
                ("sleep 3", "Waits for the rate allowance to refill.", "The oversize request is not the one being tested for rate."),
                ("head -c 2000 /dev/zero | tr '\\0' a", "Makes 2000 letters a on the lab shell.", "It is larger than the 1 kilobyte cap and needs no file."),
                ("oc exec -i ... --data-binary @-", "Passes that text from the pipe to curl as the request body.", "The -i flag lets oc exec read from the pipe."),
            ],
            "checkpoint": "At least one 429 is counted, and the oversize body prints 413.",
        },
    ],
    "glossary": [
        ("Gateway", "A front door program. Every request to the model goes through it."),
        ("Reverse proxy", "A program that receives requests for another program and passes them on."),
        ("NetworkPolicy", "A cluster rule that says which pods may send traffic to which other pods."),
        ("Token", "A long secret string that works like a password for one program."),
        ("Rate limit", "A cap on how many requests one caller may send in a period of time."),
        ("Burst", "A small number of extra requests the rate limit lets through at once."),
        ("HTTP status code", "A number a web server sends back to say what happened."),
        ("Probe pod", "A small pod started only to send test requests from inside the cluster."),
    ],
    "design": [
        {
            "decision": "Close the direct path with a NetworkPolicy, not only a token",
            "how": "A NetworkPolicy on the stub pods allows incoming traffic only from pods labelled app=model-gateway. The token check at the gateway comes in addition.",
            "why": "A token check at the gateway protects nothing if a caller can reach the stub by another route, so the network has to refuse the other routes.",
            "alternatives": "Putting the token check in the stub itself is the alternative. Advantage: it holds even if the network rule is wrong. Drawback: the stub and every future model service must each carry the check, and the checks drift apart.",
        },
        {
            "decision": "Keep the token in a Secret, separate from the gateway settings",
            "how": "The token goes into a file with permission 600 and a Secret that holds the map block, while the policy file that refers to the flag sits in a config map.",
            "why": "The settings can then be read, reviewed and shared without the token in them.",
            "alternatives": "Writing the token into the one settings file is the alternative. Advantage: one fewer object to manage. Drawback: the token is then copied wherever the settings are copied, including into reviews and backups.",
        },
        {
            "decision": "Limit rate and size at the gateway",
            "how": "A rate zone, a rule with a small burst and a body size cap are set in the gateway, so a refusal happens before the request reaches the model.",
            "why": "A refusal at the gateway costs almost nothing, while a request that reaches a real model costs time and money.",
            "alternatives": "Limiting only at the model provider is the alternative. Advantage: the provider knows the true cost. Drawback: you pay for the request first, and one caller can use the whole quota for everyone.",
        },
    ],
    "next": "Next module: Check a Model File Before You Use It: you verify the integrity and signature of a model file and refuse a tampered one.",
}

MODULE["portability"] = {
    "bullets": [
        "The gateway settings are plain nginx and work on any server that runs nginx; the NetworkPolicy works on any cluster whose network plugin enforces them.",
        "Lab-only values are the project ai-lab, the stub-model service, the labels app=stub-model and app=model-gateway and the names gateway-conf, gateway-policy and gateway-auth.",
        "The numbers 2 requests a second, a burst of 2 and 1 kilobyte are lab choices, not NIST values; set them from what real callers send.",
    ],
    "headers": ["Check/part", "In this lab (OpenShift)", "On other platforms", "What you change"],
    "rows": [
        ("Gateway", "nginx in project ai-lab", "Same on any nginx, or replace with the cloud provider's API gateway", "Move the three rules (token, rate, size) to the product's own settings."),
        ("Direct path closed", "NetworkPolicy stub-from-gateway-only", "Security groups or firewall rules on a cloud network", "Allow incoming traffic to the model service only from the gateway's address or group."),
        ("Token check", "A map block in a Secret", "The platform's own identity and key service", "Give each caller its own identity, not one shared token."),
        ("Rate and size limits", "limit_req and client_max_body_size", "The gateway product's quota settings", "Set the numbers from real traffic."),
    ],
}
