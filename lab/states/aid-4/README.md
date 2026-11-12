# AID-4 start state: Build a Constrained Triage Agent

Applied by `lab start` / `lab reset` in file-name order.

Implemented: the files listed below.
- 10-ensure-stub.sh calls ../aid-2/10-ensure-stub.sh (stub lives in aid-2/stub/).
- 20-namespace-demo.yaml creates project demo.
- 30-noisy-app.yaml runs noisy-app, which logs an error line and an injected instruction
  ("NOTE TO AI ASSISTANT: ...") every 5 seconds. It meets a restricted security context (fixed tag, non-root, no privilege escalation).
- 40-wait-noisy-app.sh waits until noisy-app is ready.
- 50-audit-kit.sh stores audit.py (the audit writer, 9 lines) and ailog.py (the Loki helper from ../aid-3/, one copy) in ConfigMap aid4-kit in ai-lab; Step 3 extracts both.
- 50-audit-kit.sh also stores reference/my_cases.py and reference/kinds.py (the answers to the Step 2 writing exercise) in ConfigMap aid4-ref in ai-lab. The module tells the learner to open them only after trying.
- The stub serves triage-<scenario>-<n> for clean, injected, secret, chained, loop and malformed.

Still needed: see TODO.md. Nothing here has run on a live cluster.
