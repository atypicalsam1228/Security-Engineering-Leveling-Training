# AID-5 start state: Safe Adoption Pattern for Agents

Applied by `lab start` / `lab reset` in file-name order.

Implemented: the files listed below.
- 10-ensure-stub.sh calls ../aid-2/10-ensure-stub.sh. The stub serves eval-set (13 attempts, 3 benign).
- 20-forwarder.sh ensures the audit log forwarder to Loki (a shared helper in ../_common).
- 30-kyverno-and-grafana.sh checks the Kyverno CRD, creates the Grafana contact point mattermost, its route and folder siem-detect.
- reset.d/10-remove-aid5-work.sh removes the learner's six Kyverno policies (agent-baseline, agent-binding, agent-network, agent-guardrails, agent-guardrails-roles, agent-guardrails-cluster), ClusterRole, projects agents, agents-b and agents-c, and the Grafana rule.

Still needed: see TODO.md. Nothing here has run on a live cluster.
- 40-supplied-files.sh copies ref/kyverno-agent-baseline.yaml and ref/agent-probe.yaml to /workspace/aid-5/guardrails (step 1 and step 4 only read them), and ref/agent-guardrails-cluster.answer.yaml to /workspace/aid-5/answers. The learner writes agent-guardrails-cluster.yaml in step 2c and opens the answer only after trying. The script never touches files the learner wrote.
