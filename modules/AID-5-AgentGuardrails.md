# AID-5: Safe Adoption Pattern for Agents (AC-6, SC-7, SI-4, SA-11)

| Item | Detail |
| --- | --- |
| Sequence | Module 28 of 29 in the recommended order |
| Timed work | About 75 minutes (55 hands-on, 20 verify) |
| Standalone start | `lab start aid-5` |
| Combined start | Continue from the end state of the previous module |
| Tools | Kyverno (free, open source), Kubernetes NetworkPolicy, Grafana alerting (free, open source), Loki (free, open source), Stub model service (provided by the lab), Python (python3), oc, curl, jq |
| Prerequisites | AID-4 (the idea only: an agent's own code can limit what it may run; this module moves those limits into the platform), ENG-0 Terminal, Git and Your Lab (the lab shell and reading oc output) |

## Section 1. Module Overview

- Purpose: show that platform policy, not agent-author discipline, enforces the same limits for every agent project.
- You apply three Kyverno baseline policies and three guardrail policies (writing the cluster-wide one yourself), create a Grafana alert rule, and run a fixed attempt set that measures the block rate.
- You run the measurement, remove the guardrail policies, run it again, and restore them, so the number falls and returns.

- **Skill:** Apply Kyverno policies that give every labeled agent project a read-only identity and a network limit on creation, write a guardrail policy that refuses write power and secrets, create a Grafana alert on the audit log, and measure how many of a fixed set of injection attempts are blocked.
- **Tools:** Kyverno generate rules create the per-project defaults; Kyverno validate rules refuse non-compliant workloads and roles; a Kubernetes NetworkPolicy limits egress to one destination; a Grafana alert rule reads the audit log in Loki; `run_eval.py` and `report.py` measure the block rate.
- **Security Function:** Enforces least privilege and boundary protection by platform policy. Every labeled agent project inherits a read-only identity, a one-destination network limit and guardrail policies on creation, without the agent author doing anything. A measurement reports how many of thirteen injection attempts those guardrails stop.
- **NIST AC-6 Least Privilege:** Kyverno generate rules create a read-only role per labeled project; validate rules refuse any role or binding that adds more, so the generated limit cannot be loosened by the agent author.
- **NIST SC-7 Boundary Protection:** A generated network policy allows only the stub model service and DNS lookup in each agent project, applying deny by default and allow by exception (SC-7(5)).
- **NIST SI-4 System Monitoring:** A Grafana alert rule on the audit log in Loki fires when the agent identity requests anything outside get, list and watch on pods and events in its own project.
- **NIST SA-11 Developer Testing and Evaluation:** `report.py` runs thirteen injection attempts and three benign actions against the real cluster and exits with failure when any unexpected miss or error appears.

## Section 2. The Tools

### Tools used in this module

Each tool name links to its official overview. The table columns say how each tool is used in the lab and why the lab uses it instead of another way of doing the same job.

| Tool (overview link) | What it is | Used in this lab | Why this tool |
| --- | --- | --- | --- |
| [Kyverno](https://kyverno.io/docs/) | A policy engine that checks and enforces rules on Kubernetes resources. | Generates default objects when a labelled project is created and refuses agent workloads that carry write power or secrets. | It is the policy engine the lab already uses to check and enforce rules on cluster objects, so there are real policies to count and read as evidence. It is free and open source. |
| [NetworkPolicy](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/network_security/network-policy) | Rules for which pods may talk to which. Once a policy selects a pod, it accepts only what the policies allow. | Limits an agent to reaching the model service and nothing else. | It is the built-in way to limit which pods can talk to which, so you need no extra product to show what a blocked connection looks like. |
| [Grafana alerting](https://grafana.com/docs/grafana/latest/alerting/fundamentals/) | Rules that run a query on a schedule and send a notification when the result crosses a threshold. | Alerts when the agent identity acts outside its list. | It runs a log query on a schedule and notifies when the result crosses a limit, so a detection becomes an alert without writing a separate program. |
| [Grafana Loki](https://grafana.com/docs/loki/latest/) | Log storage that indexes only labels and keeps compressed log data in object storage. | Holds the records the alert reads. | It stores logs cheaply and is free and open source, so the lab can keep the logs that detections and investigations need without a paid logging product. |
| [Stub model service](https://kubernetes.io/docs/concepts/services-networking/service/) | A small stand-in for an AI model that the lab runs in the cluster. It gives fixed, scripted answers, so no model account or key is needed. (No vendor page exists for it; the link explains the Kubernetes Service it runs as.) | Holds the attempts that should be blocked and the actions that must still work. | A real model needs an account, a key and money. A scripted stand-in gives the same answers every time, so every learner sees the same behavior and a test can check it. |
| [Python 3](https://docs.python.org/3/tutorial/introduction.html) | General-purpose language, used here for small helper scripts. | Runs report.py, which measures the block rate. | Python reads and writes JSON easily and is already in the lab shell, so a small script needs nothing installed. |
| [oc](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/cli_tools/openshift-cli-oc) | The OpenShift command-line tool for creating and managing applications and projects from a terminal. | Applies the policies and runs the probe. | It is the one command that talks to the cluster, so every module uses it to ask what is true and to make changes. You sign in once, and it works on OpenShift objects as well as standard Kubernetes ones. Unlike clicking in the web console, a command can be pasted, repeated and checked by a test. |
| [curl](https://curl.se/docs/manpage.html) | Command-line tool for transferring data over URLs, used here to call web endpoints. | Makes web calls to lab services to check results. | It calls a web address from the terminal, so you can check what a service really returns instead of trusting a screen. |
| [jq](https://jqlang.org/) | Command-line JSON processor. | Reads results. | It picks one field out of a long JSON reply, so a test can read a single value. |

### How it fits together

#### Guardrails every agent project inherits

- The diagram shows the lab (test) setup.
- The policies run on a one-server OpenShift cluster, the probe runs in project agents, and the attempt set runs from the lab shell.
- In production, a pipeline creates the projects and always applies the agent label, the alert feeds an on-call channel, and the attempt set runs in the build pipeline after every policy change.
- Each step below adds one part, drawn with thick lines.

How the lab is set up, and why:

- You work in the lab shell on your laptop and send commands to your lab cluster, as in the foundation module.
- The previous module put limits inside one agent's own code, and this module moves the same limits into the platform, so they apply to every agent project without anyone adding them.
- Kyverno already runs in the cluster and watches for new projects that carry the agent label, and it creates the identity, the read-only role and the network limit for them, so the defaults come with the project.
- A guardrail policy refuses an agent workload that asks for more, so the defaults cannot be loosened by the person who builds the agent.
- The network limit allows only the stand-in model service in project ai-lab, because the agent needs that one destination and nothing else.
- Cluster audit records reach Loki and Grafana watches them, so a step outside the list is noticed even when the platform refuses it.
- The attempt set runs from the lab shell, so you can repeat the measurement after any change.

![Guardrails every agent project inherits](img/AID-5-diagram-1.png)

- **1. Baseline policy:** a Kyverno policy in project kyverno that generates the defaults in every project that carries the agent label.
- **2. Guardrail policy:** a Kyverno policy that refuses agent pods, roles and bindings that carry write power, another identity or secrets.
- **3. Agent identity:** the service account agent-runner and its read-only role, generated in project agents.
- **4. Network limit:** a network policy generated in project agents that allows only the stub model service and name lookup.
- **5. Probe workload:** the pod agent-probe in project agents, running as agent-runner, used to test the network limit from inside.
- **6. Stub model service:** the Python service in project ai-lab, the one destination the agent may reach.
- **7. Loki (the log store):** holds the cluster audit records, including every request made as the agent identity.
- **8. Alert rule in Grafana:** reads the audit records in Loki and fires when the agent identity acts outside its list.
- **9. Attempt set:** the Python script run_eval.py in lab shell, which sends thirteen attempts at the guardrails and measures the blocked share.

Where each part runs, and why:

| Part | Where it runs | Why it is built this way |
| --- | --- | --- |
| Lab shell | On your laptop | You apply the policies, run the probe and run the attempt set from here, the same workspace as in the foundation module. |
| Kyverno and its six policies | Kyverno runs in project kyverno; the policies are cluster-wide objects | The cluster checks policies for every project, so no team has to remember to add the limits. |
| Agent project | Project agents on the lab cluster, created with the agent label | The label is what asks Kyverno to generate the identity, role, binding and network limit. |
| Network limit | A network policy in project agents | It lets the agent reach only the stub model service and name lookup, so a steered agent cannot send data anywhere else. |
| Stub model service | Pods in project ai-lab | It is the one destination the agent is allowed to reach, and it needs no account or key. |
| Probe workload | A pod in project agents that runs as the generated identity | It lets you test the network limit from inside, the way an agent would meet it. |
| Alert rule | In Grafana, reading audit records in Loki (project siem) | A refusal nobody sees is a lost signal, so the rule tells a person when the identity steps outside its list. |
| Attempt set | Runs in the lab shell and sends dry-run requests to the cluster | A fixed list lets you measure the block rate and repeat it after every change. |

### 2.1 The pattern, layer by layer (AC-6 Least Privilege, SC-7 Boundary Protection, SI-4 System Monitoring)

- AID-4 put limits inside one agent's own code; this module puts the same limits in the platform so every agent project gets them.
- A limit that the platform enforces cannot be removed by a bug in the agent's own code.
- A limit that depends on each author remembering it fails the day someone skips it.
- A limit that the platform applies and refuses to let anyone loosen can be measured, which is what Step 4 does.

#### AC-6: Least Privilege

*The control asks the organization to allow only the authorized accesses for users, or processes acting on behalf of users, that are necessary to accomplish assigned tasks. This is done using:*

- Kyverno baseline policy (generate rule): creates one read-only role per labeled agent project, so every agent starts with the same small access.
- Kyverno guardrail policy (validate rule): refuses any role with a verb outside get, list and watch and any binding other than agent-read, so the access cannot grow.

#### SC-7: Boundary Protection

*The control asks the organization to monitor and control communications at the external managed interfaces to the system and at key internal managed interfaces. The enhancement SC-7(5) adds deny by default and allow by exception. This is done using:*

- Generated Kubernetes network policy: lets agent pods reach only the stub model service and name lookup and denies every other connection.
- Probe workload and attempt set: prove from inside the project that the model service connects and the cluster API does not.
- Residual risk list: records that the model service is a destination the policy cannot judge.

#### SI-4: System Monitoring

*The control asks the organization to monitor the system to detect attacks and unauthorized connections, to identify unauthorized use through organization-defined techniques and methods, and to analyze detected events and anomalies. This is done using:*

- Grafana alert rule: counts audit-log requests by the agent identity outside get, list and watch on pods and events in its own project. This is the lab's own monitoring objective. The rule fires when the count is above zero.
- Loki: stores the cluster audit records the rule searches, so a request is counted even when the platform refused it.

The table below lists each layer of the pattern, what it does and what it cannot do:

| Layer | What it does | What it cannot do |
| --- | --- | --- |
| Baseline policy | Gives every labeled project an identity, a read-only role and a network limit | Protect a project nobody labeled |
| Guardrail policy | Refuses write roles, other bindings, other identities and secrets | Judge what an allowed read is used for |
| Network policy | Allows one destination and denies the rest | Tell good data from bad data sent to the allowed destination |
| Alert rule | Tells a person when the identity steps outside its list | Stop the step, it only reports it |
| Attempt set | Measures the share blocked and the time to detect | Cover attacks nobody put in the set |

### 2.2 The attempt set (SA-11 Developer Testing and Evaluation)

- The stub model service holds thirteen attempts that should be blocked and three benign actions that must still work, grouped by the layer each one tests.
- The runner sends each item to the real cluster, as a server-side dry run (the cluster checks the request and changes nothing) where an object is involved, so nothing is created.
- The last attempt, E-13, sends data to the model service; the network policy allows that destination on purpose because the agent needs it, so the platform cannot block it.
- E-13 is listed as residual risk, so the run reports 12 of 13 blocked and treats E-13 as the one expected miss, which keeps the gap visible.

#### SA-11: Developer Testing and Evaluation

*The control asks the developer of a system component to test it, produce evidence of the execution and results of the testing and evaluation, and correct the flaws found. This is done using:*

- run_eval.py: sends each attempt to the real cluster as a dry run and decides blocked, allowed or error from the platform's reply.
- report.py: prints one line per attempt and the block rate, and exits with failure when a miss is not on the residual list, so a new flaw cannot pass unnoticed.
- Three benign actions: show that a guardrail which blocks everything does not score well.

The table below lists the attempts by layer tested and the result each one should give:

| Attempts | Layer tested | Expected result |
| --- | --- | --- |
| E-01 to E-03 | Pod mounts or reads a secret | Refused by the guardrail policy |
| E-04 | Pod runs as another identity | Refused by the guardrail policy |
| E-05, E-06, E-12 | A write role, a binding to a stronger role, a cluster-wide binding | Refused by the guardrail policy |
| E-07 to E-10 | Read secrets, delete, read another project, create | Forbidden by the role |
| E-11 | Connect to the cluster API | Blocked by the network policy |
| E-13 | Send data to the model service | Not blocked: residual risk |
| B-01 to B-03 | A compliant pod, a read, a model call | Must still work |

> **IN PRODUCTION:** In the real environment projects are created by a pipeline that always sets the agent label, so the baseline cannot be skipped, and the attempt set runs on every change to the guardrails. The lab labels the projects by hand so you see the effect of the label.

### Design decisions

#### Generate the agent defaults from a project label

- How: A Kyverno generate rule watches for projects labeled as agent projects and creates the identity, a read-only role, the binding and a network policy, with synchronize on so edits are put back. In a real environment the project pipeline always sets the label.
- Why: Limits that depend on each author remembering them fail the day someone skips one, whereas the platform applies them and restores them.
- Alternatives: A template or runbook that each team copies is the alternative. Advantage: it is simple and needs no admission controller. Drawback: copies drift and a skipped step goes unnoticed.

#### Refuse any role verb that is not on an allowed list

- How: Validate rules refuse a pod that runs as another identity or touches a secret, and a role that holds any verb outside get, list and watch.
- Why: A list of known bad verbs misses the one nobody thought of, such as impersonate (act as another identity) or escalate (hand out more power).
- Alternatives: A blocked verb list is the alternative. Advantage: it is quicker to write and easier to read. Drawback: it silently allows every verb that was not listed.

#### Score the guardrails with attacks and benign actions together

- How: The runner sends thirteen attempts that should be blocked and three actions that must still work, as dry runs, and exits with failure on any unexpected result. The attempt that sends data to the model service is the documented expected miss.
- Why: The benign cases stop a guardrail that blocks everything from scoring well, and naming the residual gap keeps it visible.
- Alternatives: Reporting only the block percentage is the alternative. Advantage: a single number that is easy to track. Drawback: it hides over-blocking and unexplained gaps.

## Section 3. Implement

- Start: type `lab start aid-5` in the terminal on your own computer (PowerShell on Windows, Terminal on Mac), not in the lab shell.
- Enter lab shell with `lab shell`. Every other command in this module runs inside lab shell.
- If a step fails: run `lab reset aid-5` on your own computer and repeat the step once. If it still fails, copy the whole command and error and ask your AI assistant. Do not skip the step.

### Step 1. Make the project defaults come with the label (AC-6 Least Privilege, SC-7 Boundary Protection)

**Learning point: Apply three Kyverno baseline policies that generate the agent identity, a read-only role, the binding and a network limit whenever a project carries the agent label. Count the objects that appeared without a command from you.**

- A project that carries `agent-platform=true` triggers three policies.
- The first policy creates the identity and role, the second creates the binding, and the third creates the network policy.
- The setting `synchronize: true` keeps all three in step.

What this step adds (thick lines and outlines are new):

![Guardrails every agent project inherits, after step 1](img/AID-5-step-1.png)

- Kyverno in project kyverno applies three baseline policies. Together they generate the agent identity, a read-only role and a network limit in project agents, and in every other project that carries the agent label.

#### 1a. Read the permissions for the Kyverno background controller

You will now print the file kyverno-agent-baseline.yaml, which the start state already saved, after making this module's folder if it is missing.

- The command changes nothing; if cat says there is no such file, type lab start aid-5 on your own computer.

```bash
mkdir -p /workspace/aid-5/guardrails
cd /workspace/aid-5/guardrails
cat kyverno-agent-baseline.yaml
```

**Expected output:**

```
Example only. The file text is printed.
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kyverno-agent-baseline
  labels:
    rbac.kyverno.io/aggregate-to-background-controller: "true"
rules:
  - apiGroups: [""]
    resources: ["serviceaccounts"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["rbac.authorization.k8s.io"]
    resources: ["roles", "rolebindings"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["networking.k8s.io"]
    resources: ["networkpolicies"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: [""]
    resources: ["pods", "events"]
    verbs: ["get", "list", "watch"]
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| mkdir -p /workspace/aid-5/guardrails ; cd ... | Makes the folder where every file of this module goes and moves into it. Every later block that uses these files starts with a cd to it. | The folder is made once, here, and the later blocks can rely on it. |
| cat kyverno-agent-baseline.yaml | Prints the supplied file. | You read what Kyverno is allowed to do before you apply it. |
| name: kyverno-agent-baseline | A cluster role named for what it is for. | A clear name makes it easy to find this permission later, when you need to explain why Kyverno may create these objects. |
| aggregate-to-background-controller | The label that adds these permissions to the Kyverno background controller. Without it the generate rules cannot create anything. | Kyverno acts only with permissions it holds, so you add them with this label instead of changing Kyverno itself. |
| `serviceaccounts`, roles, rolebindings, networkpolicies | The four kinds of object the baseline creates, with the verbs needed to create and keep them. | The controller needs full control over exactly these four kinds and no more. |
| pods, events: get list watch | A controller can only grant permissions it holds itself. The generated role grants these two reads, so the controller needs them. | Without these reads the role creation would be refused, so you grant them here once. |

#### 1b. Save the baseline policy: identity and read-only role

You will now make the file agent-baseline.yaml, in the same folder, by pasting the whole block (a heredoc) into the lab shell.

- The quoted EOF keeps every character exactly as shown, including the spaces at the start of lines, which YAML needs.
- The command prints ok when agent-baseline.yaml has content.

```bash
cd /workspace/aid-5/guardrails
cat > agent-baseline.yaml <<'EOF'
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: agent-baseline
spec:
  rules:
    - name: identity
      match: &trigger
        any:
          - resources:
              kinds: ["Namespace"]
              selector:
                matchLabels:
                  agent-platform: "true"
      generate:
        apiVersion: v1
        kind: ServiceAccount
        name: agent-runner
        namespace: "{{ request.object.metadata.name }}"
        synchronize: true
        data:
          metadata:
            labels:
              managed-by: agent-baseline
    - name: read-only-role
      match: *trigger
      generate:
        apiVersion: rbac.authorization.k8s.io/v1
        kind: Role
        name: agent-read
        namespace: "{{ request.object.metadata.name }}"
        synchronize: true
        data:
          rules:
            - apiGroups: [""]
              resources: ["pods", "events"]
              verbs: ["get", "list", "watch"]
EOF
test -s agent-baseline.yaml && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from the first block. | The file is made in the folder you are standing in. |
| cat > agent-baseline.yaml <<'EOF' ... EOF | Writes everything between the first and the last line into the file. Running it again replaces the file with the same text. | The lab has no editor, so a paste is how you make the file. |
| test -s agent-baseline.yaml && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| match: &trigger | Fires for a Namespace that carries agent-platform=true. The &trigger name saves repeating the same match in the second rule. | The label is the switch: a project that carries it gets the defaults, and one that does not is left alone. |
| name: identity | Creates the service account agent-runner in the new project. {{ request.object.metadata.name }} is the new project's name. | Each agent needs a named identity of its own so permissions can be tied to it and to nothing else. |
| name: read-only-role | Creates the role agent-read: get, list and watch on pods and events, nothing else. | This role is the most any generated identity can do, which is the limit the rest of the module protects. |
| synchronize: true | If someone edits or deletes a generated object, Kyverno puts it back. | A default that someone can quietly delete is not a default, so Kyverno restores any generated object that is changed. |

#### 1c. Save the baseline policy: role binding

You will now make the file agent-binding.yaml, in the same folder, by pasting the whole block into the lab shell.

- The command prints ok when agent-binding.yaml has content.

```bash
cd /workspace/aid-5/guardrails
cat > agent-binding.yaml <<'EOF'
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: agent-binding
spec:
  rules:
    - name: role-binding
      match:
        any:
          - resources:
              kinds: ["Namespace"]
              selector:
                matchLabels:
                  agent-platform: "true"
      generate:
        apiVersion: rbac.authorization.k8s.io/v1
        kind: RoleBinding
        name: agent-read
        namespace: "{{ request.object.metadata.name }}"
        synchronize: true
        data:
          roleRef:
            apiGroup: rbac.authorization.k8s.io
            kind: Role
            name: agent-read
          subjects:
            - kind: ServiceAccount
              name: agent-runner
              namespace: "{{ request.object.metadata.name }}"
EOF
test -s agent-binding.yaml && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from the first block. | The file is made in the folder you are standing in. |
| test -s agent-binding.yaml && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| match: any: resources: Namespace | The same trigger as in the first policy: a project that carries agent-platform=true. The &trigger shortcut works only inside one file, so the match is written out again. | The binding is created for exactly the same projects as the identity and the role. |
| name: role-binding | Binds agent-runner to agent-read, in that project only. | A role does nothing until it is bound to an identity, and binding it inside the project keeps its reach there. |
| synchronize: true | If someone edits or deletes the binding, Kyverno puts it back. | A default that someone can quietly delete is not a default. |

#### 1d. Save the baseline policy: network limit

You will now make the file agent-network.yaml, in the same folder, by pasting the whole block into the lab shell.

- The command prints ok when agent-network.yaml has content.

```bash
cd /workspace/aid-5/guardrails
cat > agent-network.yaml <<'EOF'
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: agent-network
spec:
  rules:
    - name: network-limit
      match:
        any:
          - resources:
              kinds: ["Namespace"]
              selector:
                matchLabels:
                  agent-platform: "true"
      generate:
        apiVersion: networking.k8s.io/v1
        kind: NetworkPolicy
        name: agent-egress
        namespace: "{{ request.object.metadata.name }}"
        synchronize: true
        data:
          spec:
            podSelector: {}
            policyTypes: ["Ingress", "Egress"]
            egress:
              - to:
                  - namespaceSelector:
                      matchLabels:
                        kubernetes.io/metadata.name: ai-lab
                    podSelector:
                      matchLabels:
                        app: stub-model
                ports:
                  - protocol: TCP
                    port: 8080
              - to:
                  - namespaceSelector:
                      matchLabels:
                        kubernetes.io/metadata.name: openshift-dns
                ports:
                  - protocol: UDP
                    port: 5353
                  - protocol: TCP
                    port: 5353
EOF
test -s agent-network.yaml && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from the first block. | The file is made in the folder you are standing in. |
| test -s agent-network.yaml && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| name: network-limit | Creates a network policy with no ingress and two egress rules (rules for traffic that leaves a pod). | Without this, a steered agent could reach any service in the cluster, so the default allows only the one destination it needs. |
| podSelector: app: stub-model, port 8080 | The first egress rule: pods may reach pods labeled app=stub-model in project ai-lab on port 8080. | The agent needs the model service and nothing else. |
| openshift-dns, port 5353 | The second egress rule: the cluster name lookup service, on port 5353 over UDP and TCP. | Without name lookup the agent could not find the model service by name. Everything else is denied. |

#### 1e. Apply the files and create a labeled project

You will now apply the permissions and the three baseline policies, create a project that carries the label, and list what the policies generated.

- An error right after the copy usually means one of the three policy files is empty: paste its block again.

```bash
cd /workspace/aid-5/guardrails
oc apply -f kyverno-agent-baseline.yaml
oc explain clusterpolicy.spec.rules.generate
oc apply -f agent-baseline.yaml -f agent-binding.yaml -f agent-network.yaml --dry-run=server
oc apply -f agent-baseline.yaml -f agent-binding.yaml -f agent-network.yaml
oc create namespace agents --dry-run=client -o yaml | oc label --local -f - agent-platform=true -o yaml | oc apply -f -
sleep 10
oc get serviceaccount,role,rolebinding,networkpolicy -n agents
```

**Expected output:**

```
Example only. The wording of the messages comes from oc. On a second run the lines say unchanged.
clusterrole.rbac.authorization.k8s.io/kyverno-agent-baseline created
<the fields your Kyverno release accepts for a generate rule>
clusterpolicy.kyverno.io/agent-baseline created (server dry run)
clusterpolicy.kyverno.io/agent-binding created (server dry run)
clusterpolicy.kyverno.io/agent-network created (server dry run)
clusterpolicy.kyverno.io/agent-baseline created
clusterpolicy.kyverno.io/agent-binding created
clusterpolicy.kyverno.io/agent-network created
namespace/agents created
<a table that lists serviceaccount/agent-runner, role/agent-read, rolebinding/agent-read and networkpolicy/agent-egress, and other objects OpenShift adds to every project>
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from the first block. | The files you apply are in that folder. |
| oc apply -f kyverno-agent-baseline.yaml | Applies the permissions first. | The controller needs its permissions before the policies can create anything, so this goes first. |
| oc explain ...generate | Prints the fields your Kyverno release accepts. If a field differs, use the one it shows. | Policy fields differ between Kyverno releases, so you check what yours accepts before you rely on the files. |
| --dry-run=server | Asks the cluster to check the three policies without saving them. | A server check finds a mistake in a policy before it is saved, with the cluster itself as the judge. |
| oc apply -f agent-baseline.yaml -f agent-binding.yaml -f agent-network.yaml | Saves the three baseline policies. Applying again changes nothing. | Together they generate the identity, the role, the binding and the network limit. |
| oc create namespace agents --dry-run=client -o yaml \| oc label --local ... \| oc apply -f - | Builds the project definition with the label already on it, so the rule sees the label at creation. Applying it twice is safe. | The label must be present when the project is created for the rule to fire, so it is added before the project is saved. |
| oc get serviceaccount,role,rolebinding,networkpolicy -n agents | Lists the objects. You created none of them. | Counting what appeared proves the rules did the work for you. |

![Output from a real lab run: Apply the files and create a labeled project](img/AID-5-shot-1e.png)

> **NOTE:** Four objects now exist in project agents and you ran no command to create any of them. If you start this module over with lab reset aid-5 (typed on your laptop), the start state removes the policies, the agents projects and the alert rule; your files in /workspace/aid-5 stay.

> **YOUR TURN:** Read the supplied permissions, paste the three policy blocks, run the last block, and read the list.

> **CHECKPOINT:** The list shows the service account agent-runner, the role agent-read, the role binding agent-read and the network policy agent-egress. If they do not appear within a minute, read the policy status with oc get clusterpolicy agent-baseline -o yaml, then copy the whole command and its output and ask your AI assistant.

> **TAKEAWAY:** A generate rule with `synchronize: true` keeps the defaults in place, so an edited generated object is restored.

**How this meets the controls**

- **AC-6:** A generate rule creates the agent identity and a role that can only get, list and watch pods and events in every labeled project. The objects appear without a person running a command.
- **SC-7:** The same generate rule creates a network policy that allows only the model service and name lookup. The policy appears with the project and is restored if someone changes it.

### Step 2. Refuse agent workloads that carry write power or secrets (AC-6 Least Privilege)

**Learning point: Apply three guardrail policies that refuse any agent pod, role or binding that carries write power, an extra identity, or secrets. Write the cluster-wide binding rule yourself and check it against two dry-run attempts.**

- A validate rule checks an object when it is created and refuses it with a message when it does not match the pattern.
- The first two guardrail files are supplied; you write the third (cluster-wide bindings) yourself.

What this step adds (thick lines and outlines are new):

![Guardrails every agent project inherits, after step 2](img/AID-5-step-2.png)

- Three guardrail policies, also applied by Kyverno in project kyverno, refuse agent workloads and roles that would give an agent write power or secrets.

#### 2a. Save the guardrail policy for agent pods

You will now make the file agent-guardrails.yaml, in the same folder, by pasting the whole block into the lab shell.

- The command prints ok when agent-guardrails.yaml has content.
- Read the two rules in the block first; they show the pattern for the rule you write in 2d.

```bash
cd /workspace/aid-5/guardrails
cat > agent-guardrails.yaml <<'EOF'
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: agent-guardrails
spec:
  background: false
  rules:
    - name: service-account
      match: &agent-pods
        any:
          - resources:
              kinds: ["Pod"]
              namespaceSelector:
                matchLabels:
                  agent-platform: "true"
      validate:
        failureAction: Enforce
        message: "Agent pods must run as the service account agent-runner."
        pattern:
          spec:
            serviceAccountName: agent-runner
    - name: no-secrets
      match: *agent-pods
      validate:
        failureAction: Enforce
        message: "Agent pods must not mount or read secrets."
        pattern:
          spec:
            =(volumes):
              - X(secret): "null"
            containers:
              - =(env):
                  - =(valueFrom):
                      X(secretKeyRef): "null"
                =(envFrom):
                  - X(secretRef): "null"
            =(initContainers):
              - =(env):
                  - =(valueFrom):
                      X(secretKeyRef): "null"
                =(envFrom):
                  - X(secretRef): "null"
EOF
test -s agent-guardrails.yaml && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from Step 1. | The file is made in the folder you are standing in. |
| test -s agent-guardrails.yaml && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| namespaceSelector ... agent-platform | Applies the rule only in projects that carry the agent label, so every labeled project is covered, not one named project. | Tying the rules to the label means any future agent project is covered without editing the policy. |
| name: service-account | The pod must name agent-runner as its service account. A pod that names default or any other identity is refused. | Fixing the identity means a pod cannot borrow a stronger one. |
| X(secret): "null" | The field secret must not be present. The test is applied to volumes, to the environment variables of every container and init container, and to environment sources. | Secrets are the most sensitive thing a pod could reach, so the policy refuses every route to them. |
| failureAction: Enforce | Refuse the request. Audit would only report it. | Audit would only report a violation, and Enforce is what makes the policy a guardrail. |

#### 2b. Save the guardrail policy for roles and bindings

You will now make the file agent-guardrails-roles.yaml, in the same folder, by pasting the whole block into the lab shell.

- The command prints ok when agent-guardrails-roles.yaml has content.

```bash
cd /workspace/aid-5/guardrails
cat > agent-guardrails-roles.yaml <<'EOF'
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: agent-guardrails-roles
spec:
  background: false
  rules:
    - name: read-only-roles
      match:
        any:
          - resources:
              kinds: ["Role"]
              namespaceSelector:
                matchLabels:
                  agent-platform: "true"
      validate:
        failureAction: Enforce
        message: "Agent roles may only get, list and watch pods and events."
        deny:
          conditions:
            any:
              - key: '{{ request.object.rules[].verbs[] || `[]` | [?!contains(`["get","list","watch"]`, @)] | length(@) }}'
                operator: GreaterThan
                value: 0
              - key: '{{ request.object.rules[].resources[] || `[]` | [?!contains(`["pods","events"]`, @)] | length(@) }}'
                operator: GreaterThan
                value: 0
    - name: approved-binding
      match:
        any:
          - resources:
              kinds: ["RoleBinding"]
              namespaceSelector:
                matchLabels:
                  agent-platform: "true"
      validate:
        failureAction: Enforce
        message: "Only the read-only role agent-read may be bound in an agent project."
        deny:
          conditions:
            any:
              - key: "{{ request.object.roleRef.name }}"
                operator: NotEquals
                value: agent-read
EOF
test -s agent-guardrails-roles.yaml && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from Step 1. | The file is made in the folder you are standing in. |
| test -s agent-guardrails-roles.yaml && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| name: read-only-roles | Refuses a role if any verb is not get, list or watch, or any resource is not pods or events. The [?!contains(...)] part keeps the values that are not on the list and counts them. | Counting values that are not on the allowed list refuses a verb nobody thought of, which a list of banned verbs would miss. |
| name: approved-binding | Refuses a role binding to anything but agent-read. | Without this, someone could give the identity a stronger role by adding a binding. |
| failureAction: Enforce | Refuse the request. Audit would only report it. | Audit would only report a violation, and Enforce is what makes the policy a guardrail. |

#### 2c. Save the top of the cluster-wide binding policy

You will now save the top half of the policy you write: the policy name and the match that picks out cluster role bindings (role bindings that work in every project).

- The finished policy must refuse a cluster role binding that names the identity agent-runner and allow every other one.
- The command prints ok when the file has content.

```bash
cd /workspace/aid-5/guardrails
cat > agent-guardrails-cluster.yaml <<'EOF'
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: agent-guardrails-cluster
spec:
  background: false
  rules:
    - name: no-cluster-wide-binding
      match:
        any:
          - resources:
              kinds: ["ClusterRoleBinding"]
EOF
test -s agent-guardrails-cluster.yaml && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from Step 1. | The file is made in the folder you are standing in. |
| cat > agent-guardrails-cluster.yaml <<'EOF' | Starts a new file, replacing any earlier one of this name. The next block adds to it. | Starting fresh each time makes the two blocks safe to run again from the top. |
| test -s agent-guardrails-cluster.yaml && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| kinds: ["ClusterRoleBinding"] | Picks out cluster role bindings. There is no project selector, because a cluster role binding belongs to no project. | The rule must see the object that could escape the limit of one project. |

#### 2d. Write the half that decides

You will now write the half that decides.

- The spec is: refuse any cluster role binding that has a subject (the identity a binding is given to) named agent-runner, and allow every other cluster role binding.
- Type the block below and replace each WRITE part with your own text before you run it.
- The read-only-roles rule in 2b is the pattern: it counts the unwanted values and refuses when the count is more than 0.
- The subjects are the list request.object.subjects, and the filter [?name=='agent-runner'] keeps the ones named agent-runner.
- In the expression, put the empty-list fallback and the pipe to length(@) after the filter [?name=='agent-runner'], as in 2b.
- Do not open the reference answer in 2f yet.
- Running the block adds to the file, so if you get it wrong, run block 2c again to start the file over.

```bash
cd /workspace/aid-5/guardrails
cat >> agent-guardrails-cluster.yaml <<'EOF'
      validate:
        failureAction: Enforce
        message: "WRITE: one sentence that says what was refused and why"
        deny:
          conditions:
            any:
              - key: "{{ WRITE: the number of subjects named agent-runner }}"
                operator: WRITE
                value: WRITE
EOF
```

**Expected output:**

```
Example only. Saving a file prints nothing.
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cat >> agent-guardrails-cluster.yaml <<'EOF' | Adds to the end of the file. The top half stays. | The top half is already right, so you write only the part that decides. |
| failureAction: Enforce | Refuse the request. Audit would only report it. | Audit would only report a violation, and Enforce is what makes the policy a guardrail. |
| message: WRITE | The sentence a person sees when the request is refused. Say what was refused and why. | A refusal that explains itself saves a developer from guessing. |
| deny: conditions: any: | The request is refused when any listed condition is true. | Refusing on a true condition is the pattern the roles rule in 2b uses. |
| key: WRITE | A JMESPath expression in double curly brackets that gives the number of subjects named agent-runner. | A count is a number you can compare, and it is 0 for every other binding. |
| operator and value: WRITE | The comparison that is true when the count is more than 0. | The comparison decides between refuse and allow, so it is the part to get exactly right. |

#### 2e. Check your policy

You will now check your policy on the server, apply it, and try two cluster role bindings as a dry run, so nothing is created.

- The first dry-run binding must be refused and the second must be allowed.
- An error right after the copy usually means agent-guardrails-cluster.yaml is empty: paste the two blocks again.

```bash
cd /workspace/aid-5/guardrails
oc apply -f agent-guardrails-cluster.yaml --dry-run=server
oc apply -f agent-guardrails-cluster.yaml
sleep 5
oc create clusterrolebinding try-agent --clusterrole=view --serviceaccount=agents:agent-runner --dry-run=server 2>&1 | head -n 8
oc create clusterrolebinding try-other --clusterrole=view --user=someone-else --dry-run=server 2>&1 | head -n 8
```

**Expected output:**

```
Example only. The wording comes from oc and Kyverno.
clusterpolicy.kyverno.io/agent-guardrails-cluster created (server dry run)
clusterpolicy.kyverno.io/agent-guardrails-cluster created
error: failed to create clusterrolebinding: admission webhook "<name>" denied the request:

resource ClusterRoleBinding//try-agent was blocked due to the following policies

agent-guardrails-cluster:
  <rule name>: <your message>
clusterrolebinding.rbac.authorization.k8s.io/try-other created (server dry run)
Warnings about ClusterPolicy being deprecated, or about kyverno-reports-controller permissions, may print as well. They are harmless.
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from Step 1. | Your file is in that folder. |
| --dry-run=server (first line) | Asks the cluster to check your policy without saving it. A mistake in the expression shows up here. | A server check is the quickest way to find a typo. |
| oc apply -f agent-guardrails-cluster.yaml | Saves your policy. | The policy must exist before it can refuse anything. |
| --serviceaccount=agents:agent-runner | Tries a cluster role binding for the agent identity. Your policy must refuse it, and the output shows your message. | This is the case the policy exists for. |
| --user=someone-else | Tries a cluster role binding for another identity. Your policy must allow it. | A guardrail that refuses everything is not a guardrail, so you test the allowed case too. |
| 2>&1 \| head -n 8 | Shows the first eight lines of the answer, including an error. The refusal message is on line 6, so a shorter cut would hide it. | A refusal arrives as an error, and you want to read it. |

#### 2f. Compare with the reference answer

You will now compare your file with the reference answer, a file the start state saved in /workspace/aid-5/answers, but only after you have tried and run the check above.

- The command prints the lines where your file differs from the reference.
- A different message or a different way of writing the same test is fine; what matters is the two results of the check above.
- The two commented lines are for when yours still does not work after two tries: remove the # to copy the reference over yours, so the rest of the module works.

```bash
cd /workspace/aid-5/guardrails
diff agent-guardrails-cluster.yaml ../answers/agent-guardrails-cluster.answer.yaml && echo "same as the reference"
# Only if yours still does not work after two tries, use the reference:
# cp ../answers/agent-guardrails-cluster.answer.yaml agent-guardrails-cluster.yaml
```

**Expected output:**

```
Example only. The lines that differ are shown, or the words same as the reference.
< message: "<your message>"
---
> message: "The agent-runner identity must not be bound cluster-wide."
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| diff yours reference | Prints the lines that differ between your file and the reference. It prints nothing when they are the same. | Comparing after you tried shows what you missed without giving the answer away first. |
| # cp ... (commented out) | Copies the reference over your file when the # is removed. | A stuck policy would break Test 2 and Step 4, so there is a safe way forward. |

#### 2g. Check, apply and list the guardrail policies

You will now check the three guardrail policies on the server, apply them, and list all six policies.

- An error right after the copy usually means a policy file is empty: paste its block again.

```bash
cd /workspace/aid-5/guardrails
oc apply -f agent-guardrails.yaml -f agent-guardrails-roles.yaml -f agent-guardrails-cluster.yaml --dry-run=server
oc apply -f agent-guardrails.yaml -f agent-guardrails-roles.yaml -f agent-guardrails-cluster.yaml
oc get clusterpolicy agent-baseline agent-binding agent-network agent-guardrails agent-guardrails-roles agent-guardrails-cluster
```

**Expected output:**

```
Example only. The wording comes from oc. A line says configured instead of created for a policy that already exists, for example agent-guardrails-cluster after Step 2e. Warning lines about deprecated ClusterPolicy and reports-controller permissions may also appear.
clusterpolicy.kyverno.io/agent-guardrails created (server dry run)
clusterpolicy.kyverno.io/agent-guardrails-roles created (server dry run)
clusterpolicy.kyverno.io/agent-guardrails-cluster created (server dry run)
clusterpolicy.kyverno.io/agent-guardrails created
clusterpolicy.kyverno.io/agent-guardrails-roles created
clusterpolicy.kyverno.io/agent-guardrails-cluster created
<a table that lists the six policies, each with READY true>
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from Step 1. | The files you apply are in that folder. |
| --dry-run=server | Asks the cluster to check the policies without saving them. A mistake in a JMESPath expression (a small language for picking values out of data) shows up here. | A mistake in a JMESPath expression shows up here, before the policy can block or admit the wrong things. |
| oc get clusterpolicy ... | Lists the three baseline and the three guardrail policies and whether each is ready. | A policy that is not ready protects nothing, so you confirm that it is. |

![Output from a real lab run: Check, apply and list the guardrail policies](img/AID-5-shot-2g.png)

> **SECURITY:** The role rule counts values that are not on the allowed list instead of looking for known bad verbs such as delete. A list of known bad verbs misses the one nobody thought of, such as impersonate (act as another identity) or escalate (hand out more power).

> **YOUR TURN:** Paste the first two guardrail files, save the top of the third and write its deciding half, check it, compare it with the reference, then validate and apply all three and list the policies.

> **CHECKPOINT:** Your policy refuses the cluster role binding for agent-runner with your message and allows the one for someone-else. All six policies show READY true. The generated role from Step 1 still exists, because it passed the rules.

> **TAKEAWAY:** Counting values that are not on the allowed list catches the verb nobody thought of, which a list of known bad verbs misses.

**How this meets the control**

- **AC-6:** The guardrail policy refuses a pod that runs as another identity or reads a secret, a role with any verb outside get, list and watch, a binding to any role but agent-read, and a cluster-wide binding for the agent identity.

### Step 3. Alert when the agent identity acts outside its list (SI-4 System Monitoring)

**Learning point: Create a Grafana alert rule that counts any request by the agent identity outside get, list and watch on pods and events in project agents. A refusal the platform makes but nobody sees is a lost signal.**

- The platform refuses a forbidden request at once.
- The time that matters is how long until a person is told, which Test 3 measures.

What this step adds (thick lines and outlines are new):

![Guardrails every agent project inherits, after step 3](img/AID-5-step-3.png)

- An alert rule in Grafana reads the audit records in Loki, in project siem, and fires when the agent identity acts outside its list.

#### 3a. Create the alert rule in Grafana

You will now create the alert rule through the Grafana interface for programs.

- The lab variables hold the address and the sign-in.

```bash
OLD=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/v1/provisioning/alert-rules" | jq -r '.[] | [.title, .uid] | @tsv' | grep '^agent-out-of-list' | cut -f2)
test -z "$OLD" || curl -s -X DELETE -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/v1/provisioning/alert-rules/$OLD"
FOLDER=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/folders" | jq -r 'map(select(.title == "siem-detect"))[0].uid')
LOKI_UID=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/datasources/name/Loki" | jq -r .uid)
EXPR='sum(count_over_time({log_type="audit"} |= "system:serviceaccount:agents:agent-runner" | json | objectRef_resource!="" | verb!~"get|list|watch" or objectRef_resource!~"pods|events" or objectRef_namespace!="agents" [5m]))'
QUERY=$(jq -n --arg ds "$LOKI_UID" --arg expr "$EXPR" '{refId:"A",datasourceUid:$ds,relativeTimeRange:{from:600,to:0},model:{refId:"A",expr:$expr,queryType:"instant",instant:true}}')
COND=$(jq -n '{refId:"B",datasourceUid:"-100",relativeTimeRange:{from:0,to:0},model:{refId:"B",type:"classic_conditions",datasource:{type:"__expr__",uid:"-100"},conditions:[{type:"query",query:{params:["A"]},reducer:{type:"last",params:[]},evaluator:{type:"gt",params:[0]},operator:{type:"and"}}]}}')
RULE=$(jq -n --arg folder "$FOLDER" --argjson a "$QUERY" --argjson b "$COND" '{orgID:1,title:"agent-out-of-list",ruleGroup:"agents",folderUID:$folder,noDataState:"OK",execErrState:"Error","for":"0s",condition:"B",labels:{control:"SI-4"},annotations:{summary:"agent-out-of-list"},data:[$a,$b]}')
curl -s -X POST -u "$GRAFANA_USER:$GRAFANA_PASSWORD" -H 'Content-Type: application/json' -H 'X-Disable-Provenance: true' -d "$RULE" "$GRAFANA_URL/api/v1/provisioning/alert-rules" | jq -r .title
```

**Expected output:**

```
Example only.
agent-out-of-list
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| OLD=... ; test -z "$OLD" \|\| curl -X DELETE ... | Looks for a rule with the same title and removes it, so running the block again replaces the rule instead of failing. | A second run must leave one rule, not two. |
| FOLDER=..., LOKI_UID=... | Looks up the Grafana folder siem-detect and the Loki data source. | The rule has to live in the right folder and read the right data source, so you look them up instead of typing ids. |
| EXPR='sum(count_over_time({log_type="audit"} \|= ... | The search. It keeps audit lines that name the agent identity, then keeps requests that name an object (so discovery calls such as listing API groups are ignored), then keeps those whose verb is not get, list or watch, or whose object is not pods or events, or whose project is not agents, and counts them over the last 5 minutes. | The search defines what outside the list means, so a refused request is counted the same as an allowed one. |
| QUERY=..., COND=... | The two parts of a Grafana rule: the query, and the condition that fires when the count is above 0. | Grafana separates the question from the decision, so the limit can change without changing the search. |
| RULE=... "for":"0s" | Fires as soon as the condition is true. noDataState OK means a quiet period is normal, not a fault. | With no waiting time, the only delay is how often Grafana checks, which Test 3 measures. |
| curl -X POST ... /alert-rules | Creates the rule and prints its title. | Creating the rule through the interface for programs makes it repeatable and checkable. |

![Grafana alert rules list showing agent-out-of-list in the agents group](img/AID-5-grafana-rule.png)

> **NOTE:** The line filter on the full service account name catches requests the identity makes itself and requests made on its behalf by someone allowed to impersonate it, which is how the attempt set is sent. One rule covers project agents only; a second agent project needs its own copy of the rule.

> **YOUR TURN:** Run the block.

> **CHECKPOINT:** The command prints agent-out-of-list.

> **TAKEAWAY:** An alert on a refused request matters as much as one on an allowed request, because the platform refused it and now a person knows.

**How this meets the control**

- **SI-4:** The Grafana alert rule counts any request by the agent identity outside its list in the audit log, whether the platform refused it or not. It fires as soon as the count is above zero.

### Step 4. Start a probe, build the attempt set and measure the block rate (SC-7 Boundary Protection, SA-11 Developer Testing and Evaluation)

**Learning point: Start a probe workload as the generated identity, fetch thirteen injection attempts and three benign actions from the stub, run them against the real cluster, and read the block rate and the list of misses.**

- The probe is admitted only because it satisfies the guardrail policy.
- The runner sends each manifest as a server dry run and runs each network attempt from inside the probe.
- The runner decides whether an attempt was blocked by looking for the platform's refusal words, and prints the share blocked.
- E-13, the attempt that sends data to the model service, is the documented residual miss.

What this step adds (thick lines and outlines are new):

![Guardrails every agent project inherits, after step 4](img/AID-5-step-4.png)

- A probe workload runs in project agents under the generated identity, and the network limit lets it reach the stub model service in project ai-lab and nothing else. From the lab shell you send a fixed set of injection attempts at the guardrails in the cluster, and you measure the share that is blocked.

#### 4a. Read the probe pod

You will now print agent-probe.yaml, which the start state already saved in the same folder, so you can read it.

- The command changes nothing.

```bash
cd /workspace/aid-5/guardrails
cat agent-probe.yaml
```

**Expected output:**

```
Example only. The file text is printed.
apiVersion: v1
kind: Pod
metadata:
  name: agent-probe
  namespace: agents
spec:
  serviceAccountName: agent-runner
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: registry.access.redhat.com/ubi9/python-311:1
      command: ["sleep", "infinity"]
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from Step 1. | The file is in the folder you are standing in. |
| serviceAccountName: agent-runner | The identity from Step 1. The guardrail policy requires it. | The probe must use the generated identity to test what an agent would really face. |
| securityContext: runAsNonRoot, `seccompProfile` | Starts the workload without root and with the default filter on what the program may ask the operating system to do. | Starting with fewer powers is how agent pods should be built, and the probe follows that rule. |
| capabilities drop ALL | Gives the container none of the extra Linux powers. | An agent pod should hold no extra powers it does not use. |
| sleep infinity | Does nothing, so you can run tests inside it. | The probe only has to exist, so that tests can run inside it. |

#### 4b. Start the probe

You will now start the probe and wait until it runs.

- Starting the probe needs the cluster to pull the probe image from the internet.

```bash
cd /workspace/aid-5/guardrails
oc apply -f agent-probe.yaml
oc wait pod/agent-probe -n agents --for=condition=Ready --timeout=180s
```

**Expected output:**

```
Example only. The wording comes from oc. On a second run the first line says unchanged.
pod/agent-probe created
pod/agent-probe condition met
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from Step 1. | The probe file is in that folder. |
| oc apply -f agent-probe.yaml | Creates the probe pod. The guardrail policy from Step 2 judges it first: a pod that ran as another identity or read a secret would be refused here, with a message that names the rule. | The probe doubles as a check that a compliant agent pod is admitted. |
| oc wait ... --for=condition=Ready | Waits until the probe is running. | The connection attempts run inside the probe, so it has to be up first. |

#### 4c. Save the attempt runner as run_eval.py

You will now make the file `run_eval.py`, in the same folder, by pasting the whole block into the lab shell.

- The command prints ok when run_eval.py has content.

```bash
cd /workspace/aid-5/guardrails
cat > run_eval.py <<'EOF'
import json
import subprocess

BLOCK_MARKERS = ("forbidden", "denied the request", "blocked due to")
RESIDUAL = {"E-13"}
PROBE = "import socket,sys\ntry:\n socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=3).close()\n print('CONNECTED')\nexcept OSError:\n print('BLOCKED')"


def attempt(item):
    kind, payload = item["kind"], item["payload"]
    if kind == "egress":
        args = ["oc", "exec", "-n", "agents", "agent-probe", "--", "python3", "-c", PROBE, payload["host"], str(payload["port"])]
        done = subprocess.run(args, capture_output=True, text=True)
        return "blocked" if "BLOCKED" in done.stdout else "allowed" if "CONNECTED" in done.stdout else "error"
    args = ["oc", "apply", "--dry-run=server", "-f", "-"] if kind == "manifest" else payload
    done = subprocess.run(args, input=json.dumps(payload) if kind == "manifest" else None, capture_output=True, text=True)
    text = (done.stdout + done.stderr).lower()
    if done.returncode == 0:
        return "allowed"
    return "blocked" if any(marker in text for marker in BLOCK_MARKERS) else "error"
EOF
test -s run_eval.py && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from Step 1. | The file is made in the folder you are standing in. |
| test -s run_eval.py && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| BLOCK_MARKERS | Words that appear only in a platform refusal. A command that fails for another reason, such as a typing mistake, is reported as an error and not as blocked. | A command can fail for many reasons, and only a platform refusal should count as blocked. |
| RESIDUAL = {"E-13"} | The attempts the platform is known not to block. Anything missed that is not listed here fails the run. | Writing the known gap down makes any new miss stand out as a surprise. |
| PROBE | A one-line Python connection test that runs inside the probe. | The network attempt has to run from inside the probe, as an agent's would. |
| kind == "egress" | A connection attempt from inside the probe. BLOCKED or CONNECTED decides the result. | A connection attempt is judged by whether it opened, not by an error message. |
| oc apply --dry-run=server -f - | Sends an object to the cluster for checking and discards it. Admission policies run, so a refusal is real, and nothing is created. | The real admission rules judge the object but nothing is created, so you can run the set again and again. |
| `done.returncode == 0` | A command that succeeded was allowed. | A command the platform accepted is a miss for an attack and the right result for a benign action. |

#### 4d. Save the report script as report.py

You will now make the file `report.py`, next to `run_eval.py`, by pasting the whole block into the lab shell.

- The command prints ok when report.py has content.

```bash
cd /workspace/aid-5/guardrails
cat > report.py <<'EOF'
import json
import sys

from run_eval import RESIDUAL, attempt


def main(path):
    with open(path, encoding="utf-8") as handle:
        items = json.load(handle)
    results = [(item, attempt(item)) for item in items]
    for item, got in results:
        print(f"{item['id']} expect={item['expect']} got={got} {item['name']}")
    attacks = [(item["id"], got) for item, got in results if item["expect"] == "block"]
    blocked = sum(1 for _, got in attacks if got == "blocked")
    benign = [got for item, got in results if item["expect"] == "allow"]
    missed = [name for name, got in attacks if got != "blocked"]
    print(f"attacks blocked: {blocked} of {len(attacks)} ({100 * blocked / len(attacks):.1f} percent)")
    print(f"benign allowed: {benign.count('allowed')} of {len(benign)}")
    print("missed:", ", ".join(missed) or "none")
    errors = [item["id"] for item, got in results if got == "error"]
    surprise = [name for name in missed if name not in RESIDUAL]
    return 1 if errors or surprise or benign.count("allowed") != len(benign) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
EOF
test -s report.py && echo ok || echo EMPTY
```

**Expected output:**

```
Example only.
ok
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from Step 1. | The file is made in the folder you are standing in. |
| test -s report.py && echo ok \|\| echo EMPTY | Prints ok if the file has content and EMPTY if it has none. | Pasting the block twice can leave the file empty. If EMPTY shows, paste the block again. |
| results = [(item, attempt(item)) ...] | Runs every attempt once. | One pass over every attempt gives one consistent run to measure. |
| print(f"{item['id']} expect=... got=...") | One line per attempt, so you can see which guardrail did what. | A line for each attempt shows which guardrail did what, not only a total. |
| blocked / len(attacks) | The block rate: attempts blocked, out of attempts that should be blocked. | The block rate is the headline number you repeat after every change. |
| benign.count('allowed') | The false alarm check. A guardrail that blocks everything would score 100 percent on attacks and fail here. | A guardrail that blocks everything would score well on attacks, so benign actions must still work. |
| surprise | A miss that is not on the residual list. | Misses already on the residual list are expected, and any other miss is a defect. |
| return 1 if ... | Exit status 1 (the number a program leaves behind when it ends) when anything unexpected happens, so a pipeline can fail on it. | A non-zero status lets a pipeline stop on a failure without a person reading the output. |

#### 4e. Fetch the attempt set and run it against the guardrails

You will now fetch the sixteen items from the stub, run every one against the real cluster, and print the block rate.

- An error right after the copy usually means run_eval.py or report.py is empty: paste its block again.

```bash
cd /workspace/aid-5/guardrails
curl -s http://127.0.0.1:8089/healthz >/dev/null || { oc port-forward -n ai-lab svc/stub-model 8089:8080 & sleep 3; }
curl -s -X POST http://127.0.0.1:8089/v1/answer -d '{"request_id": "eval-set"}' | jq -r .reply | jq . > eval-set.json
jq length eval-set.json
python3 report.py eval-set.json; echo "exit status: $?"
```

**Expected output:**

```
Example only. One line is printed for each item. If the tunnel was already open, the Forwarding line does not appear.
Forwarding from 127.0.0.1:8089 -> 8080
16
E-01 expect=block got=blocked <name of the attempt>
(the same kind of line for each of the sixteen items, B-01 to B-03 with expect=allow got=allowed)
attacks blocked: 12 of 13 (92.3 percent)
benign allowed: 3 of 3
missed: E-13
exit status: 0
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from Step 1. | `report.py`, `run_eval.py` and `eval-set.json` are files in that folder. |
| curl -s ... >/dev/null \|\| { oc port-forward ... 8089:8080 & sleep 3; } | Asks the stub if it already answers on port 8089. Only if it does not, it opens a port forward, a tunnel from port 8089 in your shell to the stub model service, and keeps it running in the background. | The attempt set is held by the stub, which is only reachable through a tunnel. Checking first stops a second tunnel from failing. |
| request_id": "`eval-set`" | Asks the stub for the attempt set, which comes back as JSON (a plain-text data format of names and values). The id picks the fixed answer. | The id selects the fixed set of attempts, so every learner measures the same thing. |
| jq length `eval-set.json` | Counts the items. There are sixteen: thirteen attempts and three benign actions. | Counting the items checks that you fetched the whole set before you measure it. |
| python3 `report.py` `eval-set.json` | Runs the whole set and prints the result. | This is the measurement itself, run against the real cluster. |

![Output from a real lab run: Fetch the attempt set and run it against the guardrails](img/AID-5-shot-4e.png)

> **NOTE:** E-13 gets through because the agent has to reach the model service, so no network rule can stop it. The real answers are the small read-only role, checking what comes back (AID-3) and logging what is sent (AID-3 and AID-4).

> **YOUR TURN:** Read the probe and start it, paste both Python files, and run the last block. Read every line.

> **CHECKPOINT:** The probe is running. Sixteen items are counted, twelve of thirteen attempts are blocked (92.3 percent), all three benign actions are allowed, the only miss is E-13, and the exit status is 0. E-11 (the cluster API) shows blocked and B-03 (the model service) shows allowed, so the network limit was tested from inside.

> **TAKEAWAY:** Naming the residual gap matters: E-13 gets through because the agent needs the model service.

**How this meets the controls**

- **SC-7:** The attempt set tries two connections from inside the probe: the model service connects (allowed) and the cluster API is blocked (denied). That is the network policy at work.
- **SA-11:** The runner sends thirteen attempts and three benign actions at the real cluster and reports the block rate. A miss not on the residual list fails the run with status 1.

## Section 4. Verify It Works

### Test 1 (positive). A second agent project inherits the defaults (AC-6 Least Privilege, SC-7 Boundary Protection)

- The pattern is only useful if a new team gets it without doing anything.
- You create a labeled and an unlabeled project and count the generated objects in each; the unlabeled project shows that the process creating projects must apply the label.
- Kyverno can take up to a minute to generate the objects under load, so the block waits for the second project to fill before it counts.

```bash
oc create namespace agents-b --dry-run=client -o yaml | oc label --local -f - agent-platform=true -o yaml | oc apply -f -
oc create namespace agents-c --dry-run=client -o yaml | oc apply -f -
for i in $(seq 1 24); do N=$(oc get serviceaccount/agent-runner role/agent-read rolebinding/agent-read networkpolicy/agent-egress -n agents-b --ignore-not-found -o name | wc -l); test "$N" -ge 4 && break; sleep 5; done
sleep 10
for ns in agents agents-b agents-c; do
  echo "$ns: $(oc get serviceaccount/agent-runner role/agent-read rolebinding/agent-read networkpolicy/agent-egress -n $ns --ignore-not-found -o name | wc -l) of 4 objects"
done
```

**Expected output:**

```
Example only.
agents: 4 of 4 objects
agents-b: 4 of 4 objects
agents-c: 0 of 4 objects
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| oc create namespace agents-b ... \| oc label --local ... \| oc apply -f - | Creates a second project with the label on it from the start. Running it again changes nothing. | A new agent project is the case the pattern is for. |
| oc create namespace agents-c --dry-run=client -o yaml \| oc apply -f - | Creates a project without the label. | It shows what a project the process forgot to label gets. |
| oc get serviceaccount/agent-runner role/agent-read ... --ignore-not-found -o name \| wc -l | Counts how many of the four generated objects exist in a project. | Four of four means the defaults arrived without a person adding them. |
| agents: 4 of 4 / agents-b: 4 of 4 / agents-c: 0 of 4 | The two labeled projects have all four, the unlabeled one has none. | The pattern covers every labeled project, so the label must be set by the process that creates projects. |

![Output from a real lab run: A second agent project inherits the defaults](img/AID-5-shot-test1.png)

> **CHECKPOINT:** Both labeled projects show 4 of 4, which is 100 percent of agent projects covered. The unlabeled project shows 0 of 4. Delete agents-c afterward with oc delete namespace agents-c.

**How this meets the controls**

- **AC-6:** Here you create a second labeled project and compare its generated objects with those of an unlabeled project. Four of four objects in the labeled project is the evidence that the limit arrives without a person adding it.
- **SC-7:** Here the generated network policy is one of the four objects counted in each labeled project. The unlabeled project shows the limit of the pattern: no label, no boundary.

### Test 2 (negative). The measurement catches a weakened guardrail (SA-11 Developer Testing and Evaluation)

- You remove the guardrail policies, run the attempt set again and watch the number fall, because a measurement that cannot fall proves nothing.
- You put the policies back and confirm the number returns to 12 of 13.

```bash
cd /workspace/aid-5/guardrails
oc delete clusterpolicy agent-guardrails agent-guardrails-roles agent-guardrails-cluster --ignore-not-found
sleep 5
python3 report.py eval-set.json | tail -n 3
oc apply -f agent-guardrails.yaml -f agent-guardrails-roles.yaml -f agent-guardrails-cluster.yaml
sleep 10
python3 report.py eval-set.json | tail -n 3
```

**Expected output:**

```
Example only. The exact count of misses depends on which attempts reach an admission check.
attacks blocked: 5 of 13 (38.5 percent)
benign allowed: 3 of 3
missed: E-01, E-02, E-03, E-04, E-05, E-06, E-12, E-13
attacks blocked: 12 of 13 (92.3 percent)
benign allowed: 3 of 3
missed: E-13
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| cd /workspace/aid-5/guardrails | Moves into the folder from Step 1, where `report.py`, `eval-set.json` and the policy files are. | The commands read those files. |
| oc delete clusterpolicy agent-guardrails ... --ignore-not-found | Removes the three guardrail policies. The baseline policies stay. The flag makes a second run safe. | You weaken the platform on purpose to see whether the measurement notices. |
| python3 `report.py` `eval-set.json` \| tail -n 3 | Runs the whole attempt set and shows only the three summary lines. | The block rate must fall, or the measurement proves nothing. |
| oc apply -f agent-guardrails.yaml -f ... | Puts the three guardrail policies back. | The next run shows the rate returning. |
| attacks blocked: 12 of 13 | The block rate after the policies are back. | It is the same number as in Step 4, so the change was the cause. |

![Output from a real lab run: The measurement catches a weakened guardrail](img/AID-5-shot-test2.png)

> **CHECKPOINT:** With the policy gone the block rate drops and the missed list grows by the seven manifest attempts. After it is restored the rate returns to 12 of 13. The first run lists misses that are not on the residual list, so report.py on its own would exit with status 1.

**How this meets the control**

- **SA-11:** Here you remove the guardrail policies and run the attempt set, and the block rate falls. After you restore the policies the rate returns, which shows the measurement can detect a weakened guardrail.

### Test 3 (negative). Time to detect an out-of-list action (SI-4 System Monitoring)

- You make the identity ask for something outside its list and time how long the alert takes to fire.
- The earlier attempt runs also acted outside the list, so the first loop waits until the rule is quiet (after earlier tests this can take about 5 minutes) and the clock starts from a quiet rule.
- Read the time to detect from the output line.

```bash
N=0
while curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/prometheus/grafana/api/v1/rules" | jq -e '.data.groups[].rules[] | select(.name == "agent-out-of-list" and .state == "firing")' > /dev/null && test "$N" -lt 60; do N=$((N + 1)); sleep 10; done
oc get secrets -n agents --as=system:serviceaccount:agents:agent-runner
START=$(date +%s)
N=0
while test "$N" -lt 60 && ! curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/prometheus/grafana/api/v1/rules" | jq -e '.data.groups[].rules[] | select(.name == "agent-out-of-list" and .state == "firing")' > /dev/null; do
  N=$((N + 1))
  sleep 10
done
NOW=$(date +%s)
if test "$N" -lt 60; then echo "alert firing after $((NOW - START)) seconds"; else echo "no alert after 60 tries"; fi
```

**Expected output:**

```
Example only. Your number depends on the audit log delay and the rule's evaluation interval.
Error from server (Forbidden): secrets is forbidden: User "system:serviceaccount:agents:agent-runner" cannot list resource "secrets" in API group "" in the namespace "agents"
alert firing after 140 seconds
```

| Part | What it does | Why you run it |
| --- | --- | --- |
| N=0 ; while curl ... \| jq -e '... .state == "firing"' ... sleep 10 | Waits until the alert rule is quiet, up to 60 tries ten seconds apart. The rule is read from Grafana over the web, signing in with the lab variables. | The clock must start from a quiet rule, because the earlier attempt runs also acted outside the list. |
| oc get secrets -n agents --as=system:serviceaccount:agents:agent-runner | Asks for secrets as the agent identity. The platform refuses it at once. | It is the action outside the identity's list that the alert should notice. |
| START=$(date +%s) | Notes the time in seconds. | The time to detect is measured from the moment of the request. |
| while ... ! curl ... \| jq -e '... .state == "firing"' ... sleep 10 | Checks every ten seconds whether the rule is firing, up to 60 tries. | The first check that finds it firing ends the wait. |
| alert firing after N seconds | The measured time to detect. | Read the time to detect from the output line. |

![Output from a real lab run: Time to detect an out-of-list action](img/AID-5-shot-test3.png)

> **CHECKPOINT:** The platform refuses at once, and the alert fires some time later. You have a measured time to detect. If the first loop ends after 60 tries with the alert still firing, wait and run the block again. If the script prints no alert after 60 tries, check the rule's health and the audit record field names used in the Step 3 search, then copy the whole block and its output and ask your AI assistant.

**How this meets the control**

- **SI-4:** Here you make the identity ask for something outside its list and time how long the alert takes to fire. The measured time is the evidence of how soon a person is told.

## Section 5. What Each Control Is For

### Control mapping

| Control | What it requires, in plain words | Tool or service | Where this module covers it |
| --- | --- | --- | --- |
| AC-6 Least Privilege | Give each identity only the access its job needs. | Kyverno generate and validate policies (the baseline policy and the guardrail policy). Explained in section 2.1. | Section 3, Step 1: generate one read-only role (a named list of actions an identity may do) per agent project. Section 3, Step 2: refuse any role or binding that adds more. Section 4, Test 1: a second project inherits it. |
| SC-7 Boundary Protection | Monitor and control communications at managed interfaces. The enhancement SC-7(5) adds deny by default and allow by exception, which is how the lab treats the edge of an agent project. | A Kubernetes NetworkPolicy, generated by the Kyverno baseline policy and enforced by the cluster's network plugin (the part that carries pod traffic). Explained in section 2.1. | Section 3, Step 1: generate a network policy that allows one destination and denies the rest. Section 3, Step 4: prove both from inside a probe. |
| SI-4 System Monitoring | Watch the system for attacks and unauthorized use, and analyze what is found. | A Grafana alert rule on the cluster audit log in Loki. Explained in section 2.1. | Section 3, Step 3: alert on the agent identity acting outside its list. Section 4, Test 3: measure how long detection takes. |
| SA-11 Developer Testing and Evaluation | Test the system, keep the results as evidence, and correct the flaws found. | The attempt set run by `run_eval.py` and `report.py` (Python 3), against the stub model service's fixed list. Explained in section 2.2. | Section 3, Step 4: build the attempt set and the block rate (the share of attempts the guardrails stop). Section 4, Test 2: the measurement catches a weakened guardrail. |

### What each control is for

Each table below says what the control is trying to prevent and how this module's tool meets it.

#### AC-6 Least Privilege

| Question | Answer |
| --- | --- |
| Control Intent | A new agent is given a convenient broad role because narrowing it is extra work, and a planted instruction inherits all of it. |
| The operational question | For any agent in any agent project, what is the most its identity can do, and who has to remember to make that true? |
| What evidence proves it | The generated role and binding in each agent project, and refused attempts to add more. |
| How much is enough | The identity and its read-only role come with the project and are kept in step by the policy. A role that adds a write verb, or a binding to any other role, is refused. NIST does not list which accesses a job needs. The lab allows get, list and watch on pods and events in the agent's own project. |
| How the tool in this module satisfies it | Kyverno (the policy engine in your lab) generate rules (rules that create objects, Step 1) and validate rules (rules that check and refuse objects, Step 2). |

#### SC-7 Boundary Protection

| Question | Answer |
| --- | --- |
| Control Intent | An agent that is steered can send data anywhere, or reach internal services nobody expected it to touch. |
| The operational question | Where can an agent workload connect, and what happens when it tries anywhere else? |
| What evidence proves it | The network policy in each agent project, one allowed connection, and refused connections to other targets. |
| How much is enough | SC-7(5) asks for deny by default and allow by exception, and the lab applies it at the edge of each agent project. Everything is denied except the model service and name lookup. The model service remains a destination the policy cannot judge, which is stated as residual risk. |
| How the tool in this module satisfies it | A generated NetworkPolicy (Step 1). The attempt set in Step 4 tests it from inside a probe. |

#### SI-4 System Monitoring

| Question | Answer |
| --- | --- |
| Control Intent | An agent identity does something it should never do, the platform refuses, and nobody notices that someone tried. |
| The operational question | If the agent identity asks for something outside its list, who is told, and how soon? |
| What evidence proves it | The alert rule (a saved search that Grafana runs on a schedule), its state after a forbidden request, and the measured time between the request and the alert. |
| How much is enough | Any request by the agent identity for a verb or object outside its list, or in another project, raises an alert, whether or not the platform refused it. NIST leaves the monitoring objectives to the organization. The lab's objective is any action by the agent identity outside get, list and watch of pods and events in its own project. |
| How the tool in this module satisfies it | A Grafana alert rule on the audit log (the record the cluster keeps of every request) in Loki (the log store in your lab), timed in Test 3. |

#### SA-11 Developer Testing and Evaluation

| Question | Answer |
| --- | --- |
| Control Intent | The guardrails are believed to work because they were written carefully, and a change quietly breaks one. |
| The operational question | What share of a known set of attacks does the platform block today, and what changes that number? |
| What evidence proves it | A repeatable run of thirteen attempts and three benign actions, with the counts, and the list of what is missed. |
| How much is enough | The set contains attempts against each guardrail and benign actions that must still work, so a guardrail that blocks everything does not score well. NIST leaves the depth and coverage of testing to the organization; the lab fixes thirteen attempts. A miss that is not on the documented residual list fails the run. |
| How the tool in this module satisfies it | `run_eval.py` and `report.py` (Step 4), and Test 2, which shows the number falling when a guardrail is removed. |

## Section 6. Next Steps

### Using this in other environments

- The Kyverno policies were written for Kyverno 1.19.2; on another version, check each policy with a server dry run before relying on it, because generate-rule fields can differ between releases.
- The generated network policy is a standard Kubernetes NetworkPolicy, but it only limits traffic where the cluster's network plugin enforces NetworkPolicy, so confirm that on your platform.
- The Grafana alert rule is created through the Grafana provisioning API and depends on lab-only values: the folder siem-detect, the data source named Loki, the label log_type and the audit field names objectRef_resource, objectRef_namespace and verb.
- The attempt runner calls oc and decides blocked or allowed from the refusal words in BLOCK_MARKERS, so those words must match the refusal wording of your cluster.

The table shows what changes on each platform:

| Check/part | In this lab (OpenShift) | On other platforms | What you change |
| --- | --- | --- | --- |
| Baseline generate rules | Kyverno 1.19.2 ClusterPolicy; trigger label agent-platform=true | Kyverno on any Kubernetes cluster | Check each policy with a server dry run on your version; rename the label if your project process uses another. |
| Network limit | NetworkPolicy allowing project ai-lab, label app=stub-model, port 8080, and project openshift-dns, port 5353 | NetworkPolicy, where the network plugin enforces it | Replace the allowed destination, its labels and port, and the name lookup project and port. Replace the check if your plugin does not enforce NetworkPolicy. |
| Guardrail validate rules | Kyverno deny conditions in JMESPath; role agent-read; identity agent-runner | Kyverno on any Kubernetes cluster | Rename the role and identity if you use other names. |
| Alert rule | Grafana provisioning API; folder siem-detect; data source Loki; audit records in project siem | Replace the check | Replace the folder, data source, labels, field names and identity filter with those of your log pipeline. |
| Attempt runner (`report.py`) | oc; probe pod agent-probe in project agents; stub service in project ai-lab; BLOCK_MARKERS | Replace the check | Replace oc and the project names, and set BLOCK_MARKERS to your cluster's refusal wording. |
| Agent label | Applied by hand with oc label in this lab | Project creation pipeline applies the label | Nothing in the policies; only how the label is delivered changes. |

> **TIP:** Next module: ARC-5 Verify a Reference Architecture: AID-5 is the last module of the AI development dimension, so move to level 5 of the architecture dimension and check a reference architecture's list of allowed flows against the live network policies.

<details>
<summary><strong>Section 7. Terms</strong></summary>

Each term is also explained the first time it appears. In Word, hover over an underlined term to see its meaning, or Ctrl+click it to jump to this table.

| Term | Plain meaning |
| --- | --- |
| Admission policy | A rule checked when an object is created. It can refuse the object before it exists. |
| Agent | A loop in which a model proposes the next step and a program carries it out. |
| Alert | A message sent when a rule matches something in the logs. |
| Alert rule | A saved search that Grafana runs on a schedule. It notifies someone when the result crosses a limit. |
| Attempt set | The fixed list of thirteen injection attempts and three harmless actions that the runner sends to the cluster. |
| Audit log | The record the cluster keeps of every request made to it, with who asked and what they asked for. |
| AWS | Amazon Web Services, the cloud your lab runs in. |
| Background controller | The part of Kyverno that creates and updates the objects that generate rules produce. |
| Baseline | The agreed starting configuration that the system is expected to match. |
| Baseline policy | A policy that creates part of the same defaults (identity and role, binding, or network limit) in every project that carries the agent label. This module uses three. |
| Benign action | A harmless request that must still work. It shows that a guardrail does not block everything. |
| Block rate | The share of attempts the guardrails stopped, out of all attempts. |
| Cluster | A group of servers that work together as one system. Here it is your own OpenShift cluster in AWS. |
| Cluster policy | A Kyverno policy that applies to the whole cluster. |
| Cluster role binding | A binding that gives a role to an identity in every project, not only one. |
| Contact point | A saved destination for alerts. Here it is the lab chat channel. |
| Container | A sealed box that holds one program and everything it needs to run. |
| Controller | A program in the cluster that keeps the real state matching what you asked for. |
| Deny by default and allow by exception | Block every connection, then allow only the ones on a short list. |
| diff | A command that shows the differences between two files. |
| DNS | The system that turns names into network addresses. |
| Drift | When the real system no longer matches what the files say it should be. |
| Dry run | A check that reads and validates a request without making any change. |
| Egress | Network traffic that leaves a pod. |
| Evidence | Saved records that show a system is set up and behaving as claimed. |
| Exit status | A number a command leaves behind when it ends. 0 means success and anything else means a problem. |
| Generate rule | A Kyverno rule that creates other objects when a trigger object appears, and keeps them in step. |
| Grafana | The dashboard and alerting tool in the lab. It reads logs from Loki. |
| Guardrail | A limit enforced by the platform around an agent, so it holds whatever the agent or its author does. |
| Heredoc | A way to make a file by pasting its text between a first line such as cat > name <<'EOF' and a last line that says EOF. |
| Identity | The name the cluster knows a user or a program by. It decides what that user or program may do. |
| Image | A packaged copy of a program and everything it needs to run. A container starts from an image. |
| Ingress | The way traffic from outside the cluster reaches a program inside it. |
| Injection attempt | A planted instruction or request meant to make an agent do something it should not. The attempt set tests the platform against a fixed list of them. |
| JMESPath | A small language for picking values out of JSON. Kyverno rules use it to look inside the object being checked. |
| jq | A tool that picks one value out of JSON text. |
| JSON | A plain-text format for data: names and values written inside curly braces. |
| Kubernetes | The open-source system that runs and manages containers across servers. OpenShift is built on it. |
| Kyverno | A policy engine that runs in your lab cluster. It checks objects as they are created and can also create objects for you. |
| Label | A name and value tag on an object, such as agent-platform=true, used to pick objects. |
| Loki | A log store that runs in your lab cluster. Programs send log lines to it and you search them later. |
| Manifest | A YAML file that describes the objects to create in the cluster. |
| mkdir | A command that makes a new folder. |
| Model | A program that writes text when you ask. Here a stub stands in for it. |
| Namespace | A named section of the cluster that holds a set of related parts. |
| Network policy | A rule about which network connections a group of pods may make. |
| NIST | The US National Institute of Standards and Technology. It publishes the security control catalog these modules cite. |
| oc | The command-line tool for OpenShift. You type oc to ask the cluster questions. |
| OpenShift | The Red Hat platform your lab cluster runs on. It is Kubernetes with extra security and tools built in. |
| Operator | A program that installs and looks after another tool inside the cluster. |
| Pipeline | A set of automated steps that run in order, such as scan, check and sign. |
| Pod | The smallest running unit on the cluster: one or more containers together. |
| Policy | A set of rules written down so that a tool can enforce them. |
| Port forward | A tunnel from your shell to a service inside the cluster, so a command in lab shell can reach it. |
| Probe | A small workload that only waits, so you can run tests from inside it. |
| Project | A named section of the cluster that keeps workloads apart. OpenShift also calls it a namespace. |
| Query | A question you ask a data store, written in a query language, such as a log search. |
| Residual risk | What the guardrails cannot stop. It is listed, so a new miss stands out from a known one. |
| Role | A named list of actions an identity may do, such as reading pods. |
| Role binding | The link that gives a role to an identity. |
| Route | An OpenShift object that gives a program inside the cluster an address reachable from outside. |
| Rule | A written condition that a tool checks. |
| Runbook | Step-by-step instructions for handling a known situation. |
| Runner | The program or container that carries out the steps of a pipeline. |
| Secret | A cluster object that holds a small sensitive value, such as a password or a token. |
| Selector | A rule that picks objects by their labels. |
| Service account | An identity for a program instead of a person. |
| Stub model service | A small program that stands in for a model and returns a fixed answer for each request id. |
| Subject | The identity a role binding gives a role to, such as a service account. |
| TCP | The standard way programs send data reliably over a network. |
| Template | A file with blanks that are filled in when it is used. |
| UID | The number that identifies the user a process runs as. |
| Validate rule | A Kyverno rule that checks an object when it is created and refuses it, with a message, if it does not match. |
| Workload | A program the cluster runs. |
| YAML | A plain-text format for settings: lines of name: value, with indentation to show what belongs to what. |

</details>
